# YOLO 동물·사람 탐지 모델

노루(`roe_deer`)·멧돼지(`wild_boar`)·사람(`person`)을 탐지하는 YOLO 모델을 학습해서 Raspberry Pi 4 에서 돌리는 순서입니다.
기존 `aicar/od.py`(COCO SSD)에는 노루·멧돼지 클래스가 없어 따로 학습합니다.

| 파일 | 내용 |
|------|------|
| `yolo/train/train_animal.ipynb` | Colab 학습·평가·NCNN 변환 노트북 (초안) |
| `yolo/train/data.yaml` | 클래스와 데이터셋 경로 |
| `yolo/benchmark/dual_ncnn_pi_benchmark.py` | Pi 추론 시간 측정 (GPIO·모터를 쓰지 않음) |
| `yolo/models/README.md` | 모델 버전·성능·받는 곳 기록 |

## 1. 학습 (Colab)

1. 데이터셋(이미지·라벨)을 Drive `wildlife_yolo_project/dataset/` 에 `images/{train,val,test}`, `labels/{train,val,test}` 로 둡니다.
2. `yolo/train/data.yaml` 을 같은 폴더에 올립니다.
3. Colab 에서 `train_animal.ipynb` 를 열고 런타임을 GPU(T4)로 바꾼 뒤 위에서부터 실행합니다.
4. test 세트 평가 결과(클래스별 recall)를 `yolo/models/README.md` 표에 적습니다. 목표는 재현율 85% 이상입니다([PROJECT_PLAN.md](PROJECT_PLAN.md)).

## 2. NCNN 변환

노트북 마지막 셀의 `best.export(format='ncnn', imgsz=640)` 이 `best_ncnn_model/` 폴더를 만듭니다.
폴더 이름을 `animal_yolo26n_ncnn` 으로 바꾸고 zip 으로 받아 PC 의 `yolo/models/` 에 풉니다.
폴더 안에는 `model.ncnn.param`, `model.ncnn.bin`, `metadata.yaml` 세 개만 있으면 됩니다(`__pycache__`, `model_ncnn.py` 는 필요 없음).

## 3. Pi 로 복사 (노트북 PowerShell)

```
scp -r C:\AutoTank\yolo pi@<파이주소>:/home/pi/
```

Pi 에 필요한 패키지 (처음 한 번):

```
pip install ultralytics==8.4.211 ncnn
```

## 4. 벤치마크 (Pi)

```
cd ~/yolo
python3 benchmark/dual_ncnn_pi_benchmark.py --source video --video <녹화 영상.mp4>
python3 benchmark/dual_ncnn_pi_benchmark.py --source images --images <사진 폴더>
```

- 결과는 `yolo/benchmark/results/` 에 CSV(프레임별)·JSON(요약)으로 저장됩니다. git 에는 넣지 않고, 요약 수치만 `yolo/models/README.md` 에 옮깁니다.
- `--mode person|animal|dual|all` 로 모델별·동시 실행 시간을 따로 잴 수 있습니다.
- 이 차의 카메라는 CSI 라서 `--source camera`(OpenCV `VideoCapture`)로는 열리지 않습니다([IR_camera.md](IR_camera.md)). 지금은 영상이나 사진으로 측정합니다.
- 측정값은 모델 추론만의 시간입니다. 주행 CNN·화면·모터가 함께 돌 때의 FPS 는 아닙니다.
