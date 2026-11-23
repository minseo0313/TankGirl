# 주행 + YOLO 동물·사람 탐지

차 한 대에서 주행 CNN(조향)과 YOLO 탐지(노루 `roe_deer`·멧돼지 `wild_boar`·사람 `person`)를 함께 돌립니다.
학습은 Colab 노트북 하나에서 두 모델을 차례로 하고, 결과 zip 하나를 Pi 에 풀면 `ar.py` 가 둘 다 읽습니다.
기존 `aicar/od.py`(COCO SSD)에는 노루·멧돼지 클래스가 없어 따로 학습합니다.

```
[Pi]    gi.py wayA      시작할 때 모드 선택: 1 주행 사진(차선 영역) / 2 YOLO 사진(원본 → aicar/yolo_raw/<날짜>/)
[Pi]    dl.py wayA      주행 사진 정리 → [Z] wayA.zip
[PC]    라벨링          yolo_raw 사진에 박스 → yolo_dataset.zip
[Colab] train_all.ipynb wayA.zip + yolo_dataset.zip → wayA_models.zip
[Pi]    ar.py wayA      wayA_models.zip 을 ~/aicar/ 에서 풀고 실행 → 주행 + 탐지
```

| 파일 | 내용 |
|------|------|
| `aicar/gi.py` | 시작할 때 수집 모드 선택. 2 객체 탐지: YOLO 라벨링용 원본 사진(640x480) 저장 |
| `yolo/train/train_all.ipynb` | 1부 주행 CNN(`aicarA.ipynb` 그대로) + 2부 YOLO 학습·평가·NCNN 변환 + 3부 결과 zip |
| `yolo/train/data.yaml` | YOLO 클래스 순서 (라벨링 도구에서도 이 순서로) |
| `aicar/yolo_detect.py` | 탐지 스레드 (`ar.py` 가 사용) |
| `aicar/ar.py` | 주행 + 탐지. `[O]` 로 탐지 켜기·끄기 |
| `yolo/benchmark/dual_ncnn_pi_benchmark.py` | Pi 추론 시간 측정 (GPIO·모터를 쓰지 않음) |
| `yolo/models/README.md` | 모델 버전·성능·받는 곳 기록 |

## 1. 사진 모으기 (Pi)

```
cd ~/aicar
sudo python3 gi.py        # 시작하면 "2. 객체 탐지 이미지 수집" 을 고름 (프로젝트 이름 없어도 됨)
```

- 주행 사진(1번 모드)은 차선 영역만 잘라 200x66 으로 줄인 것이라 탐지 학습에 쓸 수 없습니다. 탐지용은 반드시 2번 모드로 찍습니다.
- 2번 모드는 카메라 화면 전체(640x480)를 `yolo_raw/<날짜>/<시각>.jpg` 로 저장합니다. 화면에 차선 사각형은 나오지 않습니다.
  - `[P]` 또는 마우스 가운데 버튼: 1장
  - 마우스 왼쪽 버튼(녹화): 1초마다 1장 (`DETECT_SHOT_SEC`), 오른쪽 버튼: 멈춤
- 노루·멧돼지 모형이나 사람이 화면에 보일 때 찍습니다. 낮·밤(IR), 가까이·멀리, 여러 각도로 고르게 모읍니다.
- 끝나면 터미널에 저장한 장수가 나오고, 사진 소유자를 원래 사용자로 돌려 둡니다.

## 2. 라벨링 (PC)

1. `yolo_raw/` 를 PC 로 가져옵니다: `scp -r pi@<파이주소>:/home/pi/aicar/yolo_raw C:\AutoTank\`
2. 라벨링 도구(Roboflow, LabelImg 등)에서 YOLO 형식으로 박스를 그립니다. 클래스 순서는 `0 person`, `1 roe_deer`, `2 wild_boar`.
3. 아래 구조로 `yolo_dataset.zip` 을 만듭니다. test 는 학습에 쓰지 않는 평가용입니다.
   ```
   images/train  images/val  images/test
   labels/train  labels/val  labels/test
   ```

## 3. 학습 (Colab)

1. `yolo/train/train_all.ipynb` 를 Colab 에서 엽니다.
2. 파일 창에 `wayA.zip`(dl.py [Z]) 과 `yolo_dataset.zip` 을 올립니다.
3. 런타임 유형을 T4 GPU 로 바꾸고 모두 실행합니다. Drive 연결을 물으면 허용합니다(결과 백업용, `MyDrive/aicar_models/`).
4. 2부의 test 평가 결과(클래스별 recall)를 `yolo/models/README.md` 에 적습니다. 목표는 재현율 85% 이상입니다([PROJECT_PLAN.md](../planning/PROJECT_PLAN.md)).
5. 끝나면 `wayA_models.zip` 이 내려받아집니다.

사람 모델은 학습하지 않고 COCO 사전학습 `yolo26n.pt` 를 416px NCNN 으로 변환만 합니다.

## 4. 주행 + 탐지 (Pi)

```
scp C:\Users\<사용자>\Downloads\wayA_models.zip pi@<파이주소>:/home/pi/aicar/
ssh pi@<파이주소>
cd ~/aicar && unzip -o wayA_models.zip      # wayA/ 안에 .pt 와 두 YOLO 폴더가 놓임
pip install ultralytics==8.4.211 ncnn       # 처음 한 번
python3 ar.py wayA
```

- 시작할 때 터미널에 `[탐지] YOLO 모델을 읽었습니다` 가 나오면 탐지가 켜집니다. 모델이 없거나 읽지 못하면 이유를 출력하고 주행만 합니다.
- 사람이 보이면 `PERSON STOP` 을 표시하고 정지합니다(적색 신호와 같은 방식). 사람 없이 노루·멧돼지만 보이면 경적을 울립니다.
- 마지막 탐지 후 1초(`DETECT_HOLD_SEC`) 동안 탐지 상태를 유지합니다.
- 화면 오른쪽 위 `YOLO ... mS` 가 탐지 1회 시간입니다. 탐지는 별도 스레드라 조향은 매 화면 계속됩니다. 탐지 스레드가 오류로 멈추면 `YOLO ERROR` 를 표시하고 터미널에 원인을 출력합니다(이때 사람 정지가 동작하지 않음).
- `[O]` 로 탐지를 끄고 주행만 할 수 있습니다.

## 5. 벤치마크 (Pi, 모델만)

```
cd ~/yolo
python3 benchmark/dual_ncnn_pi_benchmark.py --source video --video <녹화 영상.mp4>
python3 benchmark/dual_ncnn_pi_benchmark.py --source images --images <사진 폴더>
```

- 기본 모델 경로는 `yolo/models/` 입니다. 다른 모델은 `--person-model`, `--animal-model` 로 지정합니다.
- 결과는 `yolo/benchmark/results/` 에 CSV·JSON 으로 저장됩니다. 요약 수치만 `yolo/models/README.md` 에 옮깁니다.
- 이 차의 카메라는 CSI 라서 `--source camera`(OpenCV `VideoCapture`)로는 열리지 않습니다([IR_camera.md](../hardware/IR_camera.md)).
- 측정값은 모델 추론만의 시간입니다. 실제 주행 중 탐지 시간은 `ar.py` 화면의 `YOLO ... mS` 로 봅니다.
