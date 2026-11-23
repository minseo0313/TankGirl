# 문서 안내

| 폴더 | 무엇이 있나 | 먼저 볼 문서 |
|------|-------------|--------------|
| [planning/](planning/) | 캡스톤 수행계획서 (배경, 목표, 정량 목표, 일정) | [PROJECT_PLAN.md](planning/PROJECT_PLAN.md) |
| [hardware/](hardware/) | 부품별 정리: 배선, 핀, 점검 방법 | [DC_moter.md](hardware/DC_moter.md), [DC_moter_driver.md](hardware/DC_moter_driver.md), [Servo_moter.md](hardware/Servo_moter.md), [IR_camera.md](hardware/IR_camera.md), [LCD.md](hardware/LCD.md) |
| [software/](software/) | 학습과 탐지, 모듈 사이 약속 | [YOLO.md](software/YOLO.md), [interfaces.md](software/interfaces.md) |
| [business-rules/](business-rules/) | 로봇이 무엇을 보면 어떻게 움직이나 (규칙, 파라미터) | [README.md](business-rules/README.md) |
| [scenarios/](scenarios/) | 규칙이 이어진 실제 흐름, 시험 항목 | [README.md](scenarios/README.md) |
| [issues/](issues/) | 문제 해결 기록 (날짜별) | |

문서끼리 관계:

```
planning (왜, 무엇을)
  → business-rules (어떤 상황에 어떻게)  → scenarios (처음부터 끝까지 흐름)
  → software/interfaces (모듈끼리 주고받는 형식)
  → hardware (부품과 배선)
```

새 문서는 위 폴더 중 맞는 곳에 넣습니다. 그림은 그 폴더의 `images/`에 둡니다.
