#############################################################################################
#
# <yolo_detect.py>  YOLO 동물·사람 탐지 (ar.py 에서 사용)
#
# 사람 모델(person_yolo26n_ncnn)과 노루·멧돼지 모델(animal_yolo26n_ncnn)을 별도 스레드에서 돌립니다.
# 주행 루프는 submit() 으로 최신 화면만 넘기고 기다리지 않으므로 조향이 늦어지지 않습니다.
# 탐지가 주행보다 느리면 그 사이 화면은 건너뜁니다.
#
# 모델 폴더는 yolo/train/train_all.ipynb 가 만든 <프로젝트>_models.zip 을 aicar/ 에서 풀면
# aicar/<프로젝트>/ 안에 놓입니다.
#
# 자체 점검: python3 yolo_detect.py  (모델·ultralytics 없이 탐지 상태 판단만 확인)
#
#############################################################################################
import os
import threading
import time

PERSON_DIR = 'person_yolo26n_ncnn'      # COCO 사전학습 모델 (person 만 사용)
ANIMAL_DIR = 'animal_yolo26n_ncnn'      # 노루·멧돼지 학습 모델
PERSON_IMGSZ = 416                      # 모델을 만든 크기와 같아야 합니다 (metadata.yaml)
ANIMAL_IMGSZ = 640
DETECT_CONF = 0.25                      # 이 신뢰도 이상만 탐지로 봅니다 (벤치마크와 같은 값)
DETECT_HOLD_SEC = 1.0                   # 마지막 탐지 후 이 시간 동안 탐지 상태를 유지 (한두 장 놓쳐도 깜빡이지 않게)
# shortcut: 시험을 위해 우선 클래스 2번(wild_boar, 멧돼지)만 동물로 탐지. 노루도 쓰려면 'roe_deer' 를 다시 넣기
ANIMAL_NAMES = ('wild_boar',)

def hasModels(modelDir):
    '''modelDir 안에 사람·동물 모델 폴더가 모두 있으면 True.'''
    return all(os.path.isdir(os.path.join(modelDir, d)) for d in (PERSON_DIR, ANIMAL_DIR))

def detectState(now, lastPerson, lastAnimal, hold=DETECT_HOLD_SEC):
    '''마지막 탐지 시각으로 지금 (사람 있음, 동물 있음) 을 판단합니다.'''
    return (now - lastPerson < hold, now - lastAnimal < hold)

class Detector:
    def __init__(self, modelDir):
        from ultralytics import YOLO       # 무거운 라이브러리라 탐지 모델이 있을 때만 불러옵니다
        self.person = YOLO(os.path.join(modelDir, PERSON_DIR), task='detect')
        self.animal = YOLO(os.path.join(modelDir, ANIMAL_DIR), task='detect')
        self.personIds = [k for k, v in self.person.names.items() if v == 'person']
        self.animalIds = [k for k, v in self.animal.names.items() if v in ANIMAL_NAMES]
        if not self.personIds or not self.animalIds:
            raise ValueError('모델 클래스가 예상과 다릅니다. person=%s animal=%s'
                             % (self.person.names, self.animal.names))
        self.lock = threading.Lock()
        self.conf = DETECT_CONF            # ar.py 가 설정(settings.py)이 바뀌면 다시 넣습니다
        self.hold = DETECT_HOLD_SEC
        self.frame = None                  # 다음에 탐지할 화면 (주행 루프가 계속 덮어씀)
        self.boxes = []                    # [(x1, y1, x2, y2, 이름, 신뢰도), ...] 카메라 640x480 좌표
        self.lastPerson = 0.0              # 마지막으로 사람을 본 시각
        self.lastAnimal = 0.0              # 마지막으로 노루·멧돼지를 본 시각
        self.inferMs = 0                   # 마지막 탐지 1회 소요 시간
        self.error = None                  # 탐지 스레드가 멈춘 원인
        threading.Thread(target=self._run, daemon=True).start()

    def submit(self, frame):
        '''주행 루프에서 화면 1장마다 부릅니다. 기다리지 않습니다.'''
        with self.lock:
            self.frame = frame

    def state(self):
        '''(사람 있음, 동물 있음, 박스 목록, 탐지 시간 mS) 를 돌려줍니다.'''
        with self.lock:
            person, animal = detectState(time.time(), self.lastPerson, self.lastAnimal, self.hold)
            return person, animal, self.boxes, self.inferMs

    def _predict(self, model, frame, ids, imgsz):
        r = model.predict(source=frame, classes=ids, conf=self.conf, imgsz=imgsz,
                          device='cpu', verbose=False)[0]
        return [(int(x1), int(y1), int(x2), int(y2), str(model.names[int(c)]), float(p))
                for (x1, y1, x2, y2), c, p in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]

    def _run(self):
        try:
            while True:
                with self.lock:
                    frame, self.frame = self.frame, None
                if frame is None:
                    time.sleep(0.01)
                    continue
                t0 = time.time()
                boxes = (self._predict(self.person, frame, self.personIds, PERSON_IMGSZ)
                         + self._predict(self.animal, frame, self.animalIds, ANIMAL_IMGSZ))
                now = time.time()
                with self.lock:
                    self.boxes = boxes
                    self.inferMs = int((now - t0) * 1000)
                    if any(b[4] == 'person' for b in boxes): self.lastPerson = now
                    if any(b[4] in ANIMAL_NAMES for b in boxes): self.lastAnimal = now
        except Exception as e:             # 스레드 밖으로는 전달되지 않으므로 원인을 남기고 알립니다
            self.error = e
            print('[탐지 오류] 탐지를 멈춥니다 → 사람 정지·동물 경적이 동작하지 않습니다.')
            print('  원인: %s: %s' % (type(e).__name__, e))

if __name__ == '__main__':
    assert detectState(10.0, 9.5, 0.0) == (True, False)    # 0.5초 전 사람 → 아직 있음
    assert detectState(10.0, 8.9, 9.9) == (False, True)    # 1.1초 전 사람 → 없음, 동물 있음
    assert detectState(10.0, 0.0, 0.0) == (False, False)   # 아무것도 본 적 없음
    print('yolo_detect 자체 점검 통과')
