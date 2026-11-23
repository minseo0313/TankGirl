# 파라미터

규칙([driving-rules.md](driving-rules.md))에 쓰는 숫자는 모두 여기에만 적습니다.
값을 바꾸면 "근거" 칸에 날짜와 이유(시험 결과 등)를 함께 적습니다.

"코드" 칸 읽는 법:
- 상수 이름이 있으면 그 이름으로 코드에 있습니다. 값을 바꿀 때 코드도 같이 고칩니다.
- "(숫자로 씀)"이면 코드에 이름 없이 숫자로 들어가 있습니다. 바꿀 일이 생기면 상수로 빼는 것부터 합니다.
- 비어 있으면 아직 코드에 없는 제안 값입니다 (`[미반영]` 규칙용).

## 주행

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `RUN_SPEED` | 70 | PWM 0~100 | DRV-01 | `aicar/ar.py` `RUN_SPEED` | 원본 aicar 값 (60, 70, 80, 90 중 선택) |
| `ANGLE_GAIN` | 0.8 | 배 | DRV-01 | `aicar/ar.py` `ANGLE_GAIN` | 원본 aicar 값 (0.7~1.1 중 선택) |
| `MANUAL_FORWARD_SPEED` | 80 | PWM | DRV-02 | `aicar/ar.py` (숫자로 씀) | 원본 aicar 값 |
| `MANUAL_BACK_SPEED` | -70 | PWM | DRV-02 | `aicar/ar.py` (숫자로 씀) | 원본 aicar 값 |
| `MANUAL_TURN_SPEED` | ±70 | PWM | DRV-02 | `aicar/ar.py` (숫자로 씀) | 원본 aicar 값, 좌우 반대 방향 |
| `RESTART_NUM` | 33 | 프레임 | DRV-04, SAFE-02 | `aicar/ar.py` `RESTART_NUM` | 원본 aicar 값 |
| `OBSERVE_SEC` | 5.0 | 초 | DRV-06, DET-04 | | 제안. 정차 후 보는 시간 |

## 안전

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `HORN_DISTANCE` | 350 | mm | SAFE-01 | `aicar/ar.py` `HORN_DISTANCE` | 원본 aicar 값 |
| `STOP_DISTANCE` | 110 → 목표 200 | mm | SAFE-02, SAFE-07 | `aicar/ar.py` `STOP_DISTANCE` | 원본 aicar 값 110. 계획서 초기 목표 20cm, 속도별 제동거리 시험으로 조정 |
| `PERSON_CONF` | 0.25 | 0~1 | SAFE-06 | | 제안. 사람은 놓치지 않도록 낮게 유지 (동물 확정 기준보다 높이지 않음) |
| `DETECT_STALE_SEC` | 1.0 | 초 | SAFE-06, SAFE-08 | | 제안. `DETECT_HOLD_SEC` 이하로 둡니다. 더 길면 사람 표시가 먼저 꺼져 보호 공백이 생깁니다. Pi 탐지 1회가 이보다 짧은지 벤치마크로 확인 |

## 탐지

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `DETECT_CONF` | 0.25 | 0~1 | DET-01, DRV-05, SAFE-03 | `aicar/yolo_detect.py` `DETECT_CONF` | 벤치마크와 같은 값 |
| `DETECT_HOLD_SEC` | 1.0 | 초 | DET-01, SAFE-03 | `aicar/yolo_detect.py` `DETECT_HOLD_SEC` | 한두 프레임 놓쳐도 탐지 상태 유지 |
| `DETECT_HORN_FRAMES` | 5 | 프레임 | DET-02, LAMP-03 | `aicar/ar.py` (숫자로 씀) | 원본 `[H]` 경적과 같은 길이 |
| `ANIMAL_CONFIRM_CONF` | 0.5 | 0~1 | DET-03 | | 제안. 평가 데이터의 정밀도 보고 조정 |
| `CONFIRM_SEC` | 1.0 | 초 | DET-03 | | 제안 |

## 서보

서보 1(`P17`) = 위아래, 서보 2(`P27`) = 좌우.

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `SERVO_CENTER` | 90 | 도 | AIM-01, AIM-05 | `aicar/ar.py` `SERVO_CENTER` | 기준 각도 |
| `SERVO_MIN` / `SERVO_MAX` | 0 / 180 | 도 | AIM-01 | `aicar/ar.py` `SERVO_MIN`, `SERVO_MAX` | MG90S 180도형 전체 범위 |
| `SERVO_STEP` | 10 | 도 | AIM-01 | `aicar/ar.py` `SERVO_STEP` | 한 번 누를 때 이동량 |
| `SERVO_SWEEP_STEP` | 2 | 도/프레임 | AIM-01 | `aicar/ar.py` `SERVO_SWEEP_STEP` | 약 1초에 60도 |
| `SERVO_HOLD_SEC` | 1.5 | 초 | AIM-01, AIM-05 | `aicar/ar.py` `SERVO_HOLD_SEC` | 0.5초에서는 90도 이동이 중간에 멈춤 (2026-10-29 영상) |
| `SERVO_LEFT` | 1 | 부호 | AIM-01, AIM-02 | `aicar/ar.py` `SERVO_LEFT` | 각도가 커지면 왼쪽. 반대로 돌면 -1 |
| `SERVO_UP` | 1 | 부호 | AIM-02 | | 제안. 각도가 커지면 위. 반대로 돌면 -1 |
| `AIM_TILT_MIN` / `AIM_TILT_MAX` | 60 / 120 | 도 | AIM-03 | | 제안. 차체에 부딪히지 않는 범위를 실차에서 확인 |
| `CAM_HFOV_DEG` | 53.5 | 도 | AIM-02 | | OV5647 기본 렌즈 가로 화각 (실측 필요) |
| `CAM_VFOV_DEG` | 41.4 | 도 | AIM-02 | | OV5647 기본 렌즈 세로 화각 (실측 필요) |
| `AIM_DEADBAND_PX` | 40 | 픽셀 | AIM-02, STIM-01 | | 제안. 이 안이면 조준 완료로 보고 움직이지 않음 |
| `AIM_MAX_STEP_DEG` | 10 | 도 | AIM-02 | | 제안. `SERVO_STEP`과 같은 값에서 시작 |
| `AIM_INTERVAL_SEC` | 0.3 | 초 | AIM-02 | | 제안. 서보가 도착하기 전에 다음 명령을 주지 않도록 |
| `AIM_LOST_SEC` | 2.0 | 초 | AIM-04 | | 제안 |
| `MANUAL_OVERRIDE_SEC` | 5.0 | 초 | AIM-06 | | 제안 |

## 램프

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `BLINK_DIFF` | 9 | PWM | LAMP-01 | `aicar/ar.py` (숫자로 씀) | 원본 aicar 값. 좌우 모터 차이가 이보다 크면 방향지시등 |

## 자극

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `AIM_TIMEOUT_SEC` | 3.0 | 초 | STIM-01 | | 제안. 조준이 안 맞아도 이 시간 뒤 자극 |
| `STIMULUS_SEC` | 3.0 | 초 | STIM-02 | | 제안. "제한된 시간 동안" (계획서) |
| `ZONE_COOLDOWN_SEC` | 60 | 초 | STIM-03 | | 제안 |

## 재관찰과 판정

| 이름 | 값 | 단위 | 규칙 | 코드 | 근거 |
|------|----|------|------|------|------|
| `REOBSERVE_WAIT_SEC` | 1.0 | 초 | OBS-01 | | 제안. 자극 직후 흔들림이 가라앉을 시간 |
| `REOBSERVE_SEC` | 5.0 | 초 | OBS-01 | | 제안 |
| `EDGE_MARGIN_PX` | 40 | 픽셀 | OBS-01 | | 제안. 화면 가장자리로 본 폭 |
| `MAX_RESPONSES` | 2 | 회 | OBS-02, LOG-02 | | 계획서 "잔류 시 최대 2회" |
