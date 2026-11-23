# 주행 + YOLO 동물·사람 탐지

차 한 대에서 주행 CNN(조향)과 YOLO 탐지(노루 `roe_deer`·멧돼지 `wild_boar`·사람 `person`)를 함께 돌립니다.
학습은 Colab 노트북 하나에서 두 모델을 차례로 하고, 결과 zip 하나를 Pi 에 풀면 `ar.py` 가 둘 다 읽습니다.
기존 `aicar/od.py`(COCO SSD)에는 노루·멧돼지 클래스가 없어 따로 학습합니다.

```
[Pi]    gi.py wayA      시작할 때 모드 선택: 1 주행 사진(차선 영역) / 2 YOLO 사진(원본 → aicar/yolo_raw/<날짜>/)
[Pi]    dl.py wayA      주행 사진 정리 → [Z] wayA.zip
[Pi]    label.py        yolo_raw 사진에 상자 → label.py --zip → yolo_dataset.zip
[Colab] train_detect.ipynb  yolo_dataset.zip → detect_models.zip   (탐지만)
        train_all.ipynb     wayA.zip + yolo_dataset.zip → wayA_models.zip  (주행 + 탐지)
[Pi]    ar.py wayA      wayA_models.zip 을 ~/aicar/ 에서 풀고 실행 → 주행 + 탐지
```

| 파일 | 내용 |
|------|------|
| `aicar/gi.py` | 시작할 때 수집 모드 선택. 2 객체 탐지: YOLO 라벨링용 원본 사진(640x480) 저장 |
| `aicar/label.py` | Pi 안에서 라벨링(OpenCV 창), `--zip` 으로 `yolo_dataset.zip` |
| `yolo/train/train_detect.ipynb` | YOLO 만 학습·평가·NCNN 변환 → `detect_models.zip` |
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

## 2. 라벨링 (Pi 안에서)

설치할 것 없이 Pi 에서 바로 합니다. 사진이 Pi 밖으로 나가지 않습니다.

```
cd ~/aicar
python3 label.py                     # sudo 없이. yolo_raw/ 아래 사진을, 아직 안 한 것부터 한 장씩 (껐다 켜면 이어서)
python3 label.py yolo_raw/20261123   # 폴더를 지정하면 그 폴더 사진만 (다른 곳의 사진도 가능)
```

| 키 | 하는 일 |
|----|---------|
| 마우스로 끌기 | 상자 그리기 (지금 고른 클래스로) |
| `0` `1` `2` | 클래스: 0 `person` 사람(노랑), 1 `roe_deer` 노루(초록), 2 `wild_boar` 멧돼지(빨강) |
| `Z` / `C` | 마지막 상자 지우기 / 이 사진 상자 모두 지우기 |
| `Space` `N` / `B` | 저장하고 다음 / 이전 사진 |
| `E` | 동물 없음(배경 사진)으로 저장하고 다음 |
| `D` | 흐린 사진을 `yolo_raw_deleted/` 로 치우기 (지우지 않고 옮김) |
| `X` `ESC` | 저장하고 끝내기 (클래스별 상자 수 출력) |

- 라벨은 사진 옆에 같은 이름의 `.txt` (YOLO 형식)로 저장됩니다. 빈 `.txt` 는 배경 사진입니다.
- 보이는 몸 전체를 꼭 맞게 감쌉니다. 가장자리에 일부만 보여도 알아볼 수 있으면 그립니다.
- 사람이 찍혀 있으면 `person` 상자도 그립니다 (안 그리면 사람을 배경으로 배움).
- 배경 사진은 전체의 10% 안팎만 남깁니다. 클래스마다 상자 50개 이상을 권합니다.

다 하면 학습용 zip 으로 묶습니다. train/val/test 를 7:2:1 로 나누고(같은 사진이면 늘 같은 나눔), 학습 노트북이 읽는 구조로 만듭니다.

```
python3 label.py --zip                       # yolo_raw/ 전체 → aicar/yolo_dataset.zip
python3 label.py yolo_raw/20261123 --zip     # 지정한 폴더만 묶기
```

Roboflow 등 다른 도구를 써도 됩니다. 클래스 순서는 `0 person`, `1 roe_deer`, `2 wild_boar` 이고, YOLOv8 형식으로 내보낸 zip 을 그대로 쓸 수 있습니다.

## 3. 학습 (Colab)

탐지만 학습할 때 (주행 CNN 은 그대로 둠):

1. `yolo/train/train_detect.ipynb` 를 Colab 에서 열고 `yolo_dataset.zip` 하나를 올립니다.
2. 런타임 유형을 T4 GPU 로 바꾸고 모두 실행합니다. Drive 연결을 물으면 허용합니다(결과 백업용, `MyDrive/aicar_models/`).
3. 4번 셀의 test 평가 결과(클래스별 recall)를 `yolo/models/README.md` 에 적습니다. 목표는 재현율 85% 이상입니다([PROJECT_PLAN.md](../planning/PROJECT_PLAN.md)).
4. 끝나면 `detect_models.zip` 이 내려받아집니다. Pi 에서 주행 프로젝트 폴더에 풉니다: `cd ~/aicar && unzip -o detect_models.zip -d wayA`

주행 CNN 과 함께 학습할 때는 `yolo/train/train_all.ipynb` 에 `wayA.zip`(dl.py [Z]) 과 `yolo_dataset.zip` 을 함께 올리고, 끝나면 `wayA_models.zip` 을 받습니다.

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
