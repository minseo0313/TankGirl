#############################################################################################
#
# mg90s_test.py : Tower Pro MG90S 마이크로 서보모터 단독 테스트
#
#   실행: python3 script/mg90s_test.py          기본 핀 P17(물리 11번)
#         python3 script/mg90s_test.py 18       확장보드 P 번호(= GPIO BCM 번호) 지정
#   1) 자동 점검: 0 → 45 → 90 → 135 → 180 → 90 도로 움직이고, 0~180 도를 천천히 왕복합니다.
#   2) 키 조작: a=-10도, d=+10도, s=90도, 숫자=그 각도 (입력 후 Enter). q 또는 Ctrl+C 로 종료합니다.
#
#   배선: 갈색=GND(라즈베리파이 GND 와 공통), 빨강=+5V, 주황=신호 핀
#
#############################################################################################
import sys
import time
from gpiozero import AngularServo
from power_check import checkPower      # Raspberry Pi 전압 부족 경고
from servo_test import PHYSICAL_PIN     # GPIO(BCM) 번호 → 물리 핀 번호

DEFAULT_PIN = 17       # gi_servo.py 의 servo1 과 같은 핀 (물리 11번)
# MG90S 데이터시트: 50Hz, 0.5ms(0도) ~ 2.5ms(180도). gpiozero 기본값(1~2ms)이면 약 90도만 움직입니다.
MIN_PULSE = 0.0005
MAX_PULSE = 0.0025
STEP_ANGLES = [0, 45, 90, 135, 180, 90]
HOLD_SEC = 1.0          # 단계별 각도 유지 시간
SWEEP_STEP = 5          # 왕복 시 각도 간격(도)
SWEEP_DELAY = 0.03      # 왕복 시 간격마다 대기(초)
KEY_STEP = 10           # a/d 키 1회당 각도 변화량(도)

def stepTest(servo):
    '''정해진 각도로 차례로 움직입니다.'''
    print('\n[1/2] 단계 이동')
    for angle in STEP_ANGLES:
        servo.angle = angle
        print('  %3d도' % angle)
        time.sleep(HOLD_SEC)
        checkPower('%d도 이동 후' % angle)

def sweepTest(servo):
    '''0~180도를 천천히 한 번 왕복합니다. 끊기거나 떨리면 전원 부족을 의심하세요.'''
    print('\n[2/2] 0 ↔ 180도 왕복')
    angles = list(range(0, 181, SWEEP_STEP))
    for angle in angles + angles[::-1]:
        servo.angle = angle
        time.sleep(SWEEP_DELAY)
    servo.angle = 90
    checkPower('왕복 후')

def manualControl(servo):
    '''키 입력으로 움직입니다. a/d = ±KEY_STEP도, s = 90도, 숫자 = 그 각도, q = 종료.'''
    print('\n[키 조작] a=-%d도  d=+%d도  s=90도  숫자=그 각도  q=종료 (입력 후 Enter, ddd 처럼 반복 가능)'
          % (KEY_STEP, KEY_STEP))
    angle = 90
    while True:
        text = input('키> ').strip().lower()
        if text == 'q':
            return
        if text and set(text) <= set('ads'):
            for key in text:
                angle = 90 if key == 's' else angle + (KEY_STEP if key == 'd' else -KEY_STEP)
            angle = max(0, min(180, angle))   # 끝 각도에서 멈춤
        else:
            try:
                value = float(text)
            except ValueError:
                print('  a / d / s / 숫자 / q 중에서 입력하세요.')
                continue
            if not 0 <= value <= 180:
                print('  0~180 사이로 입력하세요.')
                continue
            angle = value
        servo.angle = angle
        print('  %.0f도' % angle)

def parsePin(args):
    '''커맨드 라인 인수를 GPIO(BCM) 번호로 변환합니다. 잘못된 번호면 안내 후 종료합니다.'''
    if not args:
        return DEFAULT_PIN
    try:
        pin = int(args[0])
    except ValueError:
        sys.exit('[오류] 핀 번호는 확장보드의 P 번호(숫자)로 입력하세요. 예: python3 script/mg90s_test.py 18')
    if pin not in PHYSICAL_PIN:
        sys.exit('[오류] 확장보드에 없는 P 번호: %d (P0~P27 만 가능)' % pin)
    return pin

if __name__ == '__main__':
    pin = parsePin(sys.argv[1:])
    print('MG90S 테스트: 주황(신호) → P%d (물리 %d번 핀), 빨강 → +5V, 갈색 → GND' % (pin, PHYSICAL_PIN[pin]))
    checkPower('시작')
    servo = AngularServo(pin, min_angle=0, max_angle=180,
                         min_pulse_width=MIN_PULSE, max_pulse_width=MAX_PULSE)
    try:
        stepTest(servo)
        sweepTest(servo)
        manualControl(servo)
    except (KeyboardInterrupt, EOFError):
        print('\n[중단]')
    finally:
        servo.detach()      # 신호를 끊어 정지 상태에서 떨림·발열 방지
        servo.close()
    print('테스트 종료')
