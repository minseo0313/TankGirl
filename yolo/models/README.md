# YOLO 모델 기록

모델 파일(`.param`, `.bin`)은 용량이 커서 git 에 넣지 않습니다(`.gitignore`의 `yolo/models/*/`).
받은 모델은 이 폴더에 아래 이름으로 풀어 둡니다. 벤치마크 스크립트가 이 경로를 기본값으로 씁니다.

```
yolo/models/
  person_yolo26n_ncnn/   model.ncnn.param, model.ncnn.bin, metadata.yaml
  animal_yolo26n_ncnn/   model.ncnn.param, model.ncnn.bin, metadata.yaml
```

## 모델 목록

| 이름 | 날짜 | 기반 | 학습 데이터 | 클래스 | imgsz | 형식 | 성능 | 받는 곳 |
|------|------|------|-------------|--------|-------|------|------|---------|
| `person_yolo26n_ncnn` | 2026-11-12 | YOLO26n (Ultralytics 8.4.211) | COCO 사전학습 (추가 학습 없음) | COCO 80종 (`person` 만 사용) | 416 | NCNN | 미측정 | Notion `yolo 학습 모델 파일_1112` → `dual_ncnn_models.zip` |
| `animal_yolo26n_ncnn` | 2026-11-12 | YOLO26n (Ultralytics 8.4.211) | Drive `wildlife_yolo_project/dataset` (`yolo/train/data.yaml`) | `person`, `roe_deer`, `wild_boar` | 640 | NCNN | 미측정 | 위와 같음 |

새 모델을 만들면 위 표에 한 줄을 추가하고, 성능 칸에는 test 세트 기준 클래스별 재현율(recall)과 Pi 추론 시간(`yolo/benchmark` 결과의 mean·p95)을 적습니다.

## 참고

- 지금은 사람은 COCO 사전학습 모델, 노루·멧돼지는 따로 학습한 모델로 두 모델을 함께 씁니다(dual). 두 모델이라 느릴 수 있습니다.
- 너무 느리면 사람 이미지를 함께 학습해 3-class 모델 하나로 합칩니다. `animal_yolo26n_ncnn` 의 클래스 목록에 `person` 이 이미 있지만 사람 이미지로 학습했는지는 확인되지 않았으므로, 합치기 전에 test 세트로 사람 재현율을 따로 잽니다(벤치마크 `--mode animal` 과 `dual` 비교).
- Ultralytics 는 AGPL-3.0 라이선스입니다. 저장소나 결과물을 공개할 때 확인합니다.
