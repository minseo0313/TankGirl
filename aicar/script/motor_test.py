#############################################################################################
#
# motor_test.py : DC 모터 점검 (카메라·화면 없이 모터만 동작)
#
#   실행: cd ~/aicar && python3 script/motor_test.py
#   왼쪽·오른쪽 모터를 하나씩, 그다음 둘 다 전진·후진·회전시키며 단계마다 이름을 출력합니다.
#   단계마다 바퀴(궤도)가 어떻게 도는지 보고 기록하세요. Ctrl+C 로 중단합니다.
#   차체를 들어 궤도가 바닥에 닿지 않게 한 상태에서 시험하세요.
#
#############################################################################################
import time
import RPi.GPIO as GPIO
from power_check import checkPower   # Raspberry Pi 전압 부족 경고

# gi.py / gi_servo.py 와 같은 핀 (GPIO BCM 번호)
MOTOR_L_PWM, MOTOR_L_DIR = 12, 5
MOTOR_R_PWM, MOTOR_R_DIR = 13, 6
SPEED = 70        # 시험 속도 (PWM 0~100)
RUN_SEC = 2.0     # 단계마다 도는 시간
PAUSE_SEC = 1.0   # 단계 사이 정지 시간

# (단계 이름, 왼쪽 값, 오른쪽 값)  + 전진 / - 후진 / 0 정지
STEPS = [
    ('왼쪽 모터만 전진',   SPEED, 0),
    ('왼쪽 모터만 후진',  -SPEED, 0),
    ('오른쪽 모터만 전진', 0,  SPEED),
    ('오른쪽 모터만 후진', 0, -SPEED),
    ('둘 다 전진 (직진)',  SPEED,  SPEED),
    ('둘 다 후진',        -SPEED, -SPEED),
    ('제자리 좌회전',     -SPEED,  SPEED),
    ('제자리 우회전',      SPEED, -SPEED),
]

def setMotor(pwm, dirPin, value):
    '''value 부호로 방향 핀(HIGH 전진 / LOW 후진), 절댓값으로 PWM 을 정합니다 (gi.py motorRun 과 같은 방식).'''
    GPIO.output(dirPin, GPIO.HIGH if value >= 0 else GPIO.LOW)
    pwm.ChangeDutyCycle(abs(value))

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in (MOTOR_L_PWM, MOTOR_L_DIR, MOTOR_R_PWM, MOTOR_R_DIR):
        GPIO.setup(pin, GPIO.OUT)
    left = GPIO.PWM(MOTOR_L_PWM, 500)    # gi.py 와 같은 500Hz
    right = GPIO.PWM(MOTOR_R_PWM, 500)
    left.start(0)
    right.start(0)
    print('DC 모터 점검: 왼쪽 PWM=GPIO%d 방향=GPIO%d, 오른쪽 PWM=GPIO%d 방향=GPIO%d'
          % (MOTOR_L_PWM, MOTOR_L_DIR, MOTOR_R_PWM, MOTOR_R_DIR))
    checkPower('시작')
    try:
        for i, (name, l, r) in enumerate(STEPS, 1):
            print('\n[%d/%d] %s  (왼쪽 %+d, 오른쪽 %+d) → 궤도가 어떻게 도는지 보세요' % (i, len(STEPS), name, l, r))
            setMotor(left, MOTOR_L_DIR, l)
            setMotor(right, MOTOR_R_DIR, r)
            time.sleep(RUN_SEC)
            checkPower(name)
            setMotor(left, MOTOR_L_DIR, 0)
            setMotor(right, MOTOR_R_DIR, 0)
            time.sleep(PAUSE_SEC)
    except KeyboardInterrupt:
        print('\n[중단] Ctrl+C')
    finally:
        left.stop()
        right.stop()
        GPIO.cleanup()
    print('\n점검 종료')
