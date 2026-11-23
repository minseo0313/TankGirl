#############################################################################################
#
# <label.py>  객체 탐지(YOLO) 라벨링 도구 - 라즈베리파이 안에서 (설치할 것 없음, OpenCV 창)
#
# $ cd aicar && python3 label.py            yolo_raw/ 사진을 한 장씩 띄워 상자를 그림 (sudo 필요 없음)
# $ python3 label.py --zip                  라벨링한 사진을 train/val/test 7:2:1 로 나눠 yolo_dataset.zip 생성
# $ python3 label.py --test                 자체 점검 (화면 없이)
#
# 사진: gi.py 2번 모드(객체 탐지 이미지 수집)가 찍은 yolo_raw/<날짜>/*.jpg
# 라벨: 사진 옆에 같은 이름의 .txt (YOLO 형식: 클래스 중심x 중심y 폭 높이, 0~1)
#       .txt 가 없으면 "아직 안 함", 빈 .txt 는 "동물 없음(배경 사진)"
#       → 껐다 켜면 아직 안 한 사진부터 이어서 합니다
#
# 키 (카메라 창처럼 창을 한 번 클릭한 뒤 누름)
#   마우스로 끌기  상자 그리기 (지금 고른 클래스로)
#   [0] [1] [2]    클래스 고르기: 0 person(사람)  1 roe_deer(노루)  2 wild_boar(멧돼지)
#   [Z]            마지막 상자 지우기         [C] 이 사진 상자 모두 지우기
#   [Space] [N]    저장하고 다음 사진         [B] 저장하고 이전 사진
#   [E]            "동물 없음(배경)"으로 저장하고 다음
#   [D]            흐리거나 쓸모없는 사진을 yolo_raw_deleted/ 로 치우기 (지우지 않고 옮김)
#   [X] [ESC]      저장하고 끝내기 (끝나면 클래스별 상자 수 출력)
# 상자 없이 [Space] 를 누르면 저장하지 않고 넘어갑니다 (아직 안 한 사진으로 남음).
#
#############################################################################################
import argparse
import random
import shutil
import sys
import zipfile
from pathlib import Path

# 학습 클래스 순서: yolo/train/data.yaml, 학습 노트북, yolo_detect.py 와 같아야 합니다
CLASSES = ('person', 'roe_deer', 'wild_boar')
COLORS = ((0, 215, 255), (60, 220, 60), (60, 60, 255))     # BGR: 사람 노랑, 노루 초록, 멧돼지 빨강
RAW_DIR = Path('yolo_raw')
DELETED_DIR = Path('yolo_raw_deleted')
ZIP_FILE = Path('yolo_dataset.zip')
SPLIT = (('train', 0.7), ('val', 0.2), ('test', 0.1))     # 학습 노트북이 images/<split>, labels/<split> 로 읽음
SPLIT_SEED = 0                  # 같은 사진이면 몇 번 묶어도 같은 나눔 (평가 결과를 비교할 수 있게)
MIN_BOX_PX = 6                  # 이보다 작게 끈 것은 실수 클릭으로 보고 버림
FEW_BOXES = 50                  # 클래스별 상자가 이보다 적으면 경고 (학습이 잘 안 됨)
BAR_H = 44                      # 사진 아래 안내 줄 높이

# 라벨 파일 읽고 쓰기 -------------------------------------------------------------------------
def toYolo(box, w, h):
    '''(cls, x1, y1, x2, y2) 픽셀 → "cls cx cy bw bh" (0~1).'''
    c, x1, y1, x2, y2 = box
    x1, x2 = sorted((max(0, min(w, x1)), max(0, min(w, x2))))
    y1, y2 = sorted((max(0, min(h, y1)), max(0, min(h, y2))))
    return '%d %.6f %.6f %.6f %.6f' % (c, (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h)

def fromYolo(line, w, h):
    '''"cls cx cy bw bh" → (cls, x1, y1, x2, y2) 픽셀. 형식이 틀리면 None.'''
    try:
        c, cx, cy, bw, bh = line.split()
        c, cx, cy, bw, bh = int(c), float(cx), float(cy), float(bw), float(bh)
    except ValueError:
        return None
    if not 0 <= c < len(CLASSES):
        return None
    return (c, round((cx - bw / 2) * w), round((cy - bh / 2) * h), round((cx + bw / 2) * w), round((cy + bh / 2) * h))

def labelPath(img):
    return img.with_suffix('.txt')

def readLabels(img, w, h):
    '''(상자 목록, 라벨 파일이 있나). 깨진 줄은 건너뜀.'''
    p = labelPath(img)
    if not p.exists():
        return [], False
    boxes = [b for b in (fromYolo(l, w, h) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()) if b]
    return boxes, True

def writeLabels(img, boxes, w, h):
    labelPath(img).write_text(''.join(toYolo(b, w, h) + '\n' for b in boxes), encoding='utf-8')

def findImages(raw=RAW_DIR):
    return sorted(p for p in Path(raw).rglob('*.jpg') if p.is_file())

def summary(images):
    '''(라벨링한 사진 수, 배경 사진 수, 안 한 사진 수, 클래스별 상자 수).'''
    done = empty = todo = 0
    counts = [0] * len(CLASSES)
    for img in images:
        p = labelPath(img)
        if not p.exists():
            todo += 1
            continue
        lines = [l for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
        if not lines:
            empty += 1
        done += 1
        for l in lines:
            b = fromYolo(l, 1, 1)
            if b:
                counts[b[0]] += 1
    return done, empty, todo, counts

def printSummary(images):
    done, empty, todo, counts = summary(images)
    print('라벨링 %d장 (그중 배경 %d장), 아직 안 함 %d장' % (done, empty, todo))
    for name, n in zip(CLASSES, counts):
        print('  %-10s 상자 %d개%s' % (name, n, '  ← 적음 (%d개 이상 권장)' % FEW_BOXES if n < FEW_BOXES else ''))

# 학습용 zip --------------------------------------------------------------------------------------
def splitImages(images, seed=SPLIT_SEED):
    '''라벨이 있는 사진을 train/val/test 로 나눔. 3장 이상이면 val, test 에 최소 1장씩.'''
    imgs = sorted(images)
    random.Random(seed).shuffle(imgs)
    n = len(imgs)
    nVal = max(1, round(n * SPLIT[1][1])) if n >= 3 else 0
    nTest = max(1, round(n * SPLIT[2][1])) if n >= 3 else 0
    nTrain = n - nVal - nTest
    return {'train': imgs[:nTrain], 'val': imgs[nTrain:nTrain + nVal], 'test': imgs[nTrain + nVal:]}

def makeZip(raw=RAW_DIR, out=ZIP_FILE):
    '''라벨이 있는 사진만 모아 학습 노트북 구조(images/<split>, labels/<split>)로 묶습니다. 묶은 장수 dict.'''
    labeled = [img for img in findImages(raw) if labelPath(img).exists()]
    if len(labeled) < 3:
        raise ValueError('라벨링한 사진이 %d장뿐입니다. 3장 이상 필요합니다 (권장: 클래스마다 상자 %d개 이상)' % (len(labeled), FEW_BOXES))
    parts = splitImages(labeled)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for split, imgs in parts.items():
            for img in imgs:
                name = '%s_%s' % (img.parent.name, img.stem)        # 날짜 폴더가 달라도 이름이 겹치지 않게
                z.write(img, 'images/%s/%s.jpg' % (split, name))
                z.write(labelPath(img), 'labels/%s/%s.txt' % (split, name))
    return {k: len(v) for k, v in parts.items()}

# 라벨링 창 -----------------------------------------------------------------------------------
class Labeler:
    def __init__(self, images):
        import cv2 as cv
        self.cv = cv
        self.images = images
        self.cls = 1                       # 처음엔 노루
        self.boxes, self.drag, self.msg = [], None, ''
        done = [labelPath(p).exists() for p in images]
        self.i = done.index(False) if False in done else 0           # 아직 안 한 사진부터
        self.load()

    def load(self):
        img = self.cv.imread(str(self.images[self.i]))
        if img is None:                                   # 깨진 사진: 검은 화면으로 띄우고 [D] 로 치우게
            import numpy as np
            self.msg = 'cannot read image - press D'
            img = np.zeros((480, 640, 3), np.uint8)
        self.img = img
        self.h, self.w = img.shape[:2]
        self.boxes, self.hasFile = readLabels(self.images[self.i], self.w, self.h)
        self.boxes = list(self.boxes)

    def save(self):
        '''상자가 있거나, 이미 라벨 파일이 있던 사진(배경 포함)이면 저장. 둘 다 아니면 안 한 사진으로 남김.'''
        if not self.boxes and not self.hasFile:
            return False
        try:
            writeLabels(self.images[self.i], self.boxes, self.w, self.h)
        except OSError as e:
            print('[라벨 오류] 저장 실패: %s\n  사진 폴더가 root 소유이면: sudo chown -R $USER:$USER %s' % (e, RAW_DIR))
            return False
        return True

    def go(self, d):
        self.save()
        self.i = max(0, min(len(self.images) - 1, self.i + d))
        self.load()

    def mouse(self, event, x, y, flags, param):
        cv = self.cv
        x, y = max(0, min(self.w - 1, x)), max(0, min(self.h - 1, y))
        if event == cv.EVENT_LBUTTONDOWN:
            self.drag = (x, y, x, y)
        elif event == cv.EVENT_MOUSEMOVE and self.drag:
            self.drag = (self.drag[0], self.drag[1], x, y)
        elif event == cv.EVENT_LBUTTONUP and self.drag:
            x1, y1 = self.drag[:2]
            self.drag = None
            if abs(x - x1) >= MIN_BOX_PX and abs(y - y1) >= MIN_BOX_PX:
                self.boxes.append((self.cls, min(x1, x), min(y1, y), max(x1, x), max(y1, y)))

    def draw(self):
        cv = self.cv
        view = cv.copyMakeBorder(self.img, 0, BAR_H, 0, 0, cv.BORDER_CONSTANT, value=(40, 40, 40))
        for c, x1, y1, x2, y2 in self.boxes:
            cv.rectangle(view, (x1, y1), (x2, y2), COLORS[c], 2)
            cv.putText(view, CLASSES[c], (x1 + 2, max(14, y1 - 4)), cv.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[c], 1)
        if self.drag:
            x1, y1, x2, y2 = self.drag
            cv.rectangle(view, (x1, y1), (x2, y2), COLORS[self.cls], 1)
        # 안내 줄 (OpenCV 는 한글을 못 그려 영어로)
        state = 'EMPTY (background)' if self.hasFile and not self.boxes else ('%d boxes' % len(self.boxes))
        top = '%d/%d  %s  [%s]  %s' % (self.i + 1, len(self.images), self.images[self.i].name, state, self.msg)
        cv.putText(view, top, (6, self.h + 17), cv.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1)
        x = 6
        for c, name in enumerate(CLASSES):
            label = '[%d] %s' % (c, name)
            cv.putText(view, label, (x, self.h + 37), cv.FONT_HERSHEY_SIMPLEX, 0.5,
                       COLORS[c], 2 if c == self.cls else 1)
            x += 12 + 9 * len(label)
        cv.putText(view, 'Z undo  Space next  B back  E empty  D trash  X quit', (self.w - 330, self.h + 17),
                   cv.FONT_HERSHEY_SIMPLEX, 0.4, (170, 170, 170), 1)
        return view

    def trash(self):
        img = self.images[self.i]
        dst = DELETED_DIR / img.parent.name
        dst.mkdir(parents=True, exist_ok=True)
        for p in (img, labelPath(img)):
            if p.exists():
                shutil.move(str(p), str(dst / p.name))
        print('[라벨] 치움: %s → %s/' % (img.name, dst))
        del self.images[self.i]
        if not self.images:
            return False
        self.i = min(self.i, len(self.images) - 1)
        self.load()
        return True

    def run(self):
        cv = self.cv
        cv.namedWindow('Label', cv.WINDOW_AUTOSIZE)        # 크기 그대로: 마우스 좌표 = 사진 좌표
        cv.setMouseCallback('Label', self.mouse)
        while True:
            cv.imshow('Label', self.draw())
            k = cv.waitKey(20) & 0xFF
            self.msg = '' if k != 255 else self.msg
            if k in (ord('x'), ord('X'), 27):
                self.save()
                break
            if k in (ord('0'), ord('1'), ord('2')):
                self.cls = k - ord('0')
            elif k in (ord('z'), ord('Z')) and self.boxes:
                self.boxes.pop()
            elif k in (ord('c'), ord('C')):
                self.boxes = []
            elif k in (ord(' '), ord('n'), ord('N')):
                if not self.boxes and not self.hasFile:
                    print('[라벨] %s: 상자 없이 넘어감 (아직 안 한 사진으로 남음, 배경이면 [E])' % self.images[self.i].name)
                if self.i == len(self.images) - 1:
                    self.save()
                    self.msg = 'LAST IMAGE'
                else:
                    self.go(1)
            elif k in (ord('b'), ord('B')):
                self.go(-1)
            elif k in (ord('e'), ord('E')):
                self.boxes, self.hasFile = [], True
                self.save()
                if self.i < len(self.images) - 1:
                    self.go(1)
            elif k in (ord('d'), ord('D')):
                if not self.trash():
                    break
        cv.destroyAllWindows()

# 자체 점검 ------------------------------------------------------------------------------------
def selfTest():
    import tempfile
    assert toYolo((1, 160, 120, 480, 360), 640, 480) == '1 0.500000 0.500000 0.500000 0.500000'
    assert fromYolo('1 0.5 0.5 0.5 0.5', 640, 480) == (1, 160, 120, 480, 360)
    assert fromYolo('7 0.5 0.5 0.1 0.1', 640, 480) is None and fromYolo('bad', 640, 480) is None
    assert toYolo((2, 700, 500, 600, 400), 640, 480).startswith('2 0.968750')    # 화면 밖 → 가장자리로 자름
    with tempfile.TemporaryDirectory() as t:
        raw = Path(t) / 'yolo_raw' / '20261123'
        raw.mkdir(parents=True)
        imgs = []
        for i in range(10):
            p = raw / ('1530%02d_000.jpg' % i)
            p.write_bytes(b'\xff\xd8fakejpg')
            imgs.append(p)
        writeLabels(imgs[0], [(1, 10, 10, 100, 100), (0, 200, 50, 300, 400)], 640, 480)
        for p in imgs[1:8]:
            writeLabels(p, [(2, 5, 5, 50, 50)], 640, 480)
        writeLabels(imgs[8], [], 640, 480)                                   # 배경 사진, imgs[9] 는 안 함
        assert readLabels(imgs[0], 640, 480) == ([(1, 10, 10, 100, 100), (0, 200, 50, 300, 400)], True)
        assert readLabels(imgs[9], 640, 480) == ([], False)
        done, empty, todo, counts = summary(imgs)
        assert (done, empty, todo, counts) == (9, 1, 1, [1, 1, 7]), (done, empty, todo, counts)
        out = Path(t) / 'yolo_dataset.zip'
        n = makeZip(Path(t) / 'yolo_raw', out)
        assert n == {'train': 6, 'val': 2, 'test': 1}, n                     # 9장 → 7:2:1
        names = zipfile.ZipFile(out).namelist()
        assert len(names) == 18 and 'images/train/' in ''.join(names) and 'labels/test/' in ''.join(names)
        assert all(('images/%s/' % s) in ''.join(names) for s in ('train', 'val', 'test'))
        assert not any('153009' in x for x in names)                         # 안 한 사진은 빠짐
        assert splitImages(imgs, 0) == splitImages(list(reversed(imgs)), 0)   # 순서와 상관없이 같은 나눔
        for p in imgs[1:]:
            labelPath(p).unlink(missing_ok=True)
        try:
            makeZip(Path(t) / 'yolo_raw', out)
            raise AssertionError('1장으로는 묶으면 안 됨')
        except ValueError:
            pass
    print('label 자체 점검 통과')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='객체 탐지(YOLO) 라벨링 도구')
    ap.add_argument('--zip', action='store_true', help='라벨링한 사진을 yolo_dataset.zip 으로 묶기')
    ap.add_argument('--test', action='store_true', help='자체 점검')
    args = ap.parse_args()
    if args.test:
        selfTest()
        sys.exit(0)
    images = findImages()
    if not images:
        print('%s/ 에 사진이 없습니다. gi.py 를 2번(객체 탐지 이미지 수집) 모드로 실행해 찍어 주세요.' % RAW_DIR)
        sys.exit(1)
    if args.zip:
        try:
            n = makeZip()
        except ValueError as e:
            print('[묶기 실패] %s' % e)
            sys.exit(1)
        print('%s 를 만들었습니다: train %d장, val %d장, test %d장' % (ZIP_FILE, n['train'], n['val'], n['test']))
        printSummary(images)
        print('→ Colab 에서 yolo/train/train_detect.ipynb 를 열고 이 zip 을 올려 학습합니다.')
        sys.exit(0)
    print('라벨링 시작: 사진 %d장 (아직 안 한 사진부터). 창을 한 번 클릭한 뒤 키를 누르세요.' % len(images))
    Labeler(images).run()
    printSummary(findImages())
    print('다 했으면: python3 label.py --zip')
