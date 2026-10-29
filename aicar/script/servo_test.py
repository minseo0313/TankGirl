#############################################################################################
#
# servo_test.py : 서보모터 배선 점검용 테스트 (카메라·모터 코드 없이 서보만 동작)
#
#   실행: python3 script/servo_test.py            기본 핀 P17(물리 11번), P27(물리 13번)
#         python3 script/servo_test.py 18 27      확장보드 P 번호(= GPIO BCM 번호) 지정 (1 개 이상)
#   지정한 서보모터를 차례로 0 → 90 → 180 → 90 → 0 도로 움직입니다. Ctrl+C 로 중단합니다.
#
#   터미널에 각도가 출력되는데 서보가 움직이지 않으면 코드가 아닌 배선·전원 문제입니다.
#
#############################################################################################
import sys
import time
from gpiozero import AngularServo
from power_check import checkPower   # Raspberry Pi 전압 부족 경고

DEFAULT_PINS = [17, 27]      # 핀을 지정하지 않았을 때: gi_servo.py 의 servo1·servo2 와 같은 핀 (물리 11·13번)
# GPIO(BCM) 번호 → 40 핀 헤더 물리 핀 번호
PHYSICAL_PIN = {2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 0: 27,
                5: 29, 6: 31, 13: 33, 19: 35, 26: 37, 14: 8, 15: 10, 18: 12, 23: 16, 24: 18,
                25: 22, 8: 24, 7: 26, 1: 28, 12: 32, 16: 36, 20: 38, 21: 40}
ANGLES = [0, 90, 180, 90, 0]   # 테스트 각도 순서
HOLD_SEC = 1.0                 # 각도마다 유지 시간

def testServo(pin, name):
    '''서보모터 하나를 ANGLES 순서대로 움직이고 결과를 출력합니다.'''
    print('\n[테스트] %s' % name)
    try:
        servo = AngularServo(pin, min_angle=0, max_angle=180)
    except Exception as e:
        print('  [오류] 초기화 실패: %s: %s' % (type(e).__name__, e))
        return
    try:
        for angle in ANGLES:
            servo.angle = angle
            print('  %3d도 명령 → 서보가 움직였는지 확인하세요' % angle)
            time.sleep(HOLD_SEC)
            checkPower('%s %d도 이동 후' % (name, angle))
    finally:
        servo.close()

def parsePins(args):
    '''커맨드 라인 인수를 GPIO(BCM) 번호 목록으로 변환합니다. 잘못된 번호면 안내 후 종료합니다.'''
    if not args:
        return DEFAULT_PINS
    try:
        pins = [int(a) for a in args]
    except ValueError:
        sys.exit('[오류] 핀 번호는 확장보드의 P 번호(숫자)로 입력하세요. 예: python3 script/servo_test.py 18 27')
    unknown = [p for p in pins if p not in PHYSICAL_PIN]
    if unknown:
        sys.exit('[오류] 확장보드에 없는 P 번호: %s (P0~P27 만 가능)' % unknown)
    return pins

if __name__ == '__main__':
    pins = parsePins(sys.argv[1:])
    print('서보모터 배선 점검을 시작합니다. (Ctrl+C: 중단)')
    print('확인: 빨강=5V, 갈색/검정=GND(라즈베리파이 GND 와 공통), 주황/노랑=신호 핀')
    for i, pin in enumerate(pins, 1):
        print('      서보모터 %d 노랑(신호)선 → 확장보드 P%d (물리 %d번 핀)' % (i, pin, PHYSICAL_PIN[pin]))
    print('      빨강 → +5.0V, 갈색 → GND (확장보드 글씨 기준)')
    checkPower('시작')
    try:
        for i, pin in enumerate(pins, 1):
            testServo(pin, 'servo%d(P%d)' % (i, pin))
    except KeyboardInterrupt:
        print('\n[중단] Ctrl+C')
    print('\n점검 종료')
