#############################################################################################
#                                                               
# Auto Drive Car  V1.0                                                          <ar.py>
#
# PyTorch 딥러닝 프레임 웍에서 학습된 모델파일에 의하여 자유주행 합니다.
#
# $ python ar.py <이미지 디렉터리>
# 
#
# G, [Home]: 자율 주행을 시작합니다.
# X, [Esc]: 주행을 종료하고 시스템(Command Window)으로 복귀합니다.
# C: 화면의 보여지는 정보를 최소화 하거나 최대로 보여 줍니다.
# D: ToF 거리감지 센서의 동작을 선택하거나 해지 합니다.
# H: 경적 소리 나게 합니다.
# L: 전조등(Neopixel)의 동작 상태를 선택합니다.
#    ON, Off, Police 1, Police 2, Police 3, Ambulance, Fire Truck, Patrol
#        gi.py 에서 Lamp = On 설정하면 On 으로 동작합니다.
# A: 전조등이 자동으로 점등 하거나 수동으로 점등 하도록 선택합니다. 
#        gi.py 에서 Auto = True 설정하면 자동 점등 모드로 동작합니다.
#        자동 모드에서 CdS 빛감지 센서에 의하여 어두우면 전조등 On 밝으면 전조등 Off 됩니다.
# [End]: 자율주행 종료합니다.
# [Up]: 전진
# [Left]: 제자리 좌회전
# [Right]: 제자리 우회전
# [Down]: 후진
# O: YOLO 동물·사람 탐지를 켜거나 끕니다 (<프로젝트>/ 안에 탐지 모델이 있을 때).
#        사람이 보이면 정지(적색 신호와 같음), 사람 없이 노루·멧돼지만 보이면 경적을 울립니다.
#
#
#                                                               
# 학습 모델파일(*.pt)을 지정하지 않거나 없으면 차량은 수동 조작만 가능합니다.
#
# Control Key
# 80: Home
# 81: Left Arrow
# 82: Up Arrow
# 83: Right Arrow
# 84: Down Arrow
# 85: Page Up
# 86: Page Down                                                               
# 87: End
#                                                               
# 파이토치 최신 버젼에서 view 함수가 reshape 로 변경
#
# FEB 2 2022
#
# SAMPLE Electronics co.                                        
# http://www.ArduinoPLUS.cc                                     
#                                                               
#############################################################################################
HORN_DISTANCE = 350                   # 경적이 울리는 거리
STOP_DISTANCE = 110                   # 차량 정지 거리 (차량 정지, 자율 주행과 수동 전진에서 해당)
RUN_SPEED = 70                        # 60, 70, 80, 90  차량 주행 속도(speed)
ANGLE_GAIN = 0.8                      # 0.7, 0.8, 0.9, 1.0, 1.1  조향각 이득(gain)
downLoads = 'Downloads'               # 디폴트 Down Load 폴더
#--------------------------------------------------------------------------------------------
imageDir = ''                         # 기본 디렉토리 이름
modelName = '_model_check.pt'         # 모델 파일 
model = None                          # 딥러닝 모델
modelFile = None                      # 딥러닝 생성 모델 파일 이름
MODEL_FILE = False                    # 딥러닝 모델 파일
lightMode = 'MANU'                    # Head Light 동작모드 Auto:자동, Manual:수동 
lightCar = ' '                        # 자동차 종류(램프 동작)
#--------------------------------------------------------------------------------------------
RED     =   0,  0,255                 # Red
GREEN   =   0,255,  0                 # Green
BLUE    = 255,  0,  0                 # Blue
MAGENTA = 255,  0,255                 # Magenta(Pink)
CYAN    = 255,255,  0                 # CYAN(Sky Blue)
YELLOW  =   0,255,255                 # Yellow
WHITE   = 255,255,255                 # White
BLACK   =   0,  0,  0                 # Black
GRAY    = 128,128,128                 # Gray
#--------------------------------------------------------------------------------------------
import VL53L0X                        # ToF Ranger Library
import ts                             # Traffic Signal Library
import NEOPIXEL as nx                 # Adafruit Neopixel Library
import yolo_detect as yd              # YOLO 동물·사람 탐지 (aicar/yolo_detect.py)
import settings as cfg                # 실험 설정값 (settings_gui.py 로 실행 중에 바꿈)
import aim                            # 서보 조준 (IF-08)
import stimulus as stim               # 기피 자극 (IF-09)
import event_log                      # 이벤트 기록 (IF-10)
import event_server                   # 원격 조회 API (IF-11)
import control                        # 설정 GUI 의 실험 명령과 상태 (IF-12)
#--------------------------------------------------------------------------------------------
import os                             # File 읽기(Read) 쓰기(Write)와 관련된 라이브러리
import sys                            # 커맨드 라인 처리를 위한 라이브러리
import time                           # 시간(시계) 정보 라이브러리
import glob                           # 검사조건을 통과한 화일 이름 리스트 생성 라이브러리
import pickle                         # 파이썬 객채 저장과 읽기 라이브러리
import cv2 as cv                      # OpenCV 그래픽 라이브러리 version 4.5.1
import numpy as np                    # OpenCV의 이미지 데이터 저장 배열변수 라이브러리
import RPi.GPIO as GPIO               # Raspberry Pi GPIO 핀 라이브러리
from picamera2 import Picamera2       # CSI 카메라 라이브러리
import traceback                      # 오류 발생 위치 확인 라이브러리
import warnings                       # 라이브러리 경고 메시지 제어
import threading                      # 서보모터를 정해진 시간만 돌리고 멈추는 타이머
from gpiozero import AngularServo, Device
from script.power_check import checkPower  # Raspberry Pi 전압 부족 경고 (aicar/script/)
# gpiozero 의 소프트웨어 PWM 경고는 아래 서보모터 초기화에서 한국어 안내로 대신 출력합니다.
warnings.filterwarnings('ignore', message='To reduce servo jitter')
import torch                          # Pytorch
import torch.nn as nn                 # Torch CNN
# Traffic Signal Parameter ------------------------------------------------------------------
TSWIN_XL = 0                                # [0]
TSWIN_XR = 639                              # [1]
TSWIN_YU = 30                               # [2]
TSWIN_YD = 180                              # [3]
maxRadius = 9                               # [4] 원 검출 조건(최대 반지름)
minRadius = 8                               # [5] 원 검출 조건(최소 반지름)
lineLeadAngGREEN = 200                      # [6] 시작(Lead) 라인 각도(/360)
lineTailAngGREEN = 90                       # [7] 종료(Tail) 라인 각도(/360)
lineLeadAngRED = 40                         # [8] 시작(Lead) 라인 각도(/360)
lineTailAngRED = 300                        # [9] 종료(Tail) 라인 각도(/360)
saturationHalfGREEN = 50                    # [10] Saturation 반지름 값 (/128)
saturationHalfRED = 50                      # [11] Saturation 반지름 값 (/128)
HSV_valueGREEN = 50                         # [12] 0~255 이며 작은수에서 가로가 크게 된다. OL:7
HSV_valueRED = 50                           # [13] 0~255 이며 작은수에서 가로가 크게 된다. OL:6
THRESH_GREEN = 50                           # [14] 0~255 이며 큰 수에서 세로가 높아 진다. OL:7
THRESH_RED = 50                             # [15] 0~255 이며 큰 수에서 세로가 높아 진다. OL:6
# Green -------------------------------------------------------------------------------------
lineLeadGREENX = 0                          # 시작(Lead) 라인과 외곽 원 교차 X 좌표
lineLeadGREENY = 0                          # 시작(Lead) 라인과 외곽 원 교차 Y 좌표
lineTailGREENX = 0                          # 종료(Tail) 라인과 외곽 원 교차 X 좌표
lineTailGREENY = 0                          # 종료(Tail) 라인과 외곽 원 교차 Y 좌표
HSV_hueLeadGREEN = int(lineLeadAngGREEN/2)  # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
HSV_hueTailGREEN = int(lineTailAngGREEN/2)  # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
HSV_saturationGREEN = saturationHalfGREEN*2 # HSV 색상 좌표계에서 Saturation(/256)
centerHueGREEN = 60
# Red ----------------------------------------------------------------------------------------
lineLeadREDX = 0                            # 시작(Lead) 라인과 외곽 원 교차 X 좌표
lineLeadREDY = 0                            # 시작(Lead) 라인과 외곽 원 교차 Y 좌표
lineTailREDX = 0                            # 종료(Tail) 라인과 외곽 원 교차 X 좌표
lineTailREDY = 0                            # 종료(Tail) 라인과 외곽 원 교차 Y 좌표
HSV_hueLeadRED = int(lineLeadAngRED/2)      # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
HSV_hueTailRED = int(lineTailAngRED/2)      # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
HSV_saturationRED = saturationHalfRED*2     # HSV 색상 좌표계에서 Saturation(/256)
centerHueRED = 0
#--------------------------------------------------------------------------------------------
# 차선 감지 영역 
WIN_XL = 0                            # [0] 제어 윈도우 왼쪽 X 값
WIN_XR = 639                          # [1] 제어 윈도우 오른쪽 X 값
WIN_YU = 246                          # [2] 제어 윈도우 위쪽 Y 값
WIN_YD = 459                          # [3] 제어 윈도우 아래쪽 Y값
#--------------------------------------------------------------------------------------------
# Raspberry Pi GPIO Pin Number
MOTOR_L_PWM = 12                      # GPIO.12    왼쪽 모터 펄스폭 변조
MOTOR_L_DIR = 5                       # GPIO.5     원쪽 모터 방향
MOTOR_R_PWM = 13                      # GPIO.13    오른쪽 모터 펄스폭 변조
MOTOR_R_DIR = 6                       # GPIO.6     오른쪽 모터 방향
BUZZER = 23                           # GPIO.23    경적
MUSIC = 24                            # GPIO.24    후진 사운드
LAMP_R_YELLOW = 20                    # Right Yellow Lamp
LAMP_L_YELLOW = 26                    # Left Yellow Lamp
LAMP_BRAKE = 21                       # 브레이크 Lamp
LIGHT_SENSOR = 25                     # 빛 감지 센서(CdS)
SERVO1_PIN = 17                       # GPIO.17  서보모터 1 신호: 확장보드 P17 = 물리 11번 핀
SERVO2_PIN = 27                       # GPIO.27  서보모터 2 신호: 확장보드 P27 = 물리 13번 핀
# Raspberry Pi GPIO Pin 설정
GPIO.setwarnings(False)               # GPIO 관련 경고 메시지 출력 금지
GPIO.setmode(GPIO.BCM)                # BCM 핀 번호
GPIO.setup(MOTOR_L_DIR,GPIO.OUT)      # 왼쪽 모터 방향
GPIO.setup(MOTOR_R_DIR,GPIO.OUT)      # 오른쪽 모터 방향
GPIO.setup(BUZZER,GPIO.OUT)           # 경적 
GPIO.setup(MUSIC,GPIO.OUT)            # 후진 사운드 
GPIO.setup(LAMP_R_YELLOW,GPIO.OUT)    # 우회전 깜빡이 램프
GPIO.setup(LAMP_L_YELLOW,GPIO.OUT)    # 좌회전 깜빡이 램프
GPIO.setup(LAMP_BRAKE,GPIO.OUT)       # 브레이크 램프
GPIO.setup(LIGHT_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP) # 빛감지 센서(CdS) 입력, 풀-업 모드
# DC Motor 설정 ------------------------------------------------------------------------------
class NoMotor:
    '''서보모터에 핀을 넘겨준 모터 자리에 쓰는 빈 모터 (PWM 명령을 무시합니다).'''
    def start(self, duty): pass
    def stop(self): pass
    def ChangeDutyCycle(self, duty): pass

def motorInit(pin, name):
    '''
    모터 PWM 을 500Hz 로 시작합니다.
    서보모터가 같은 핀을 쓰면 모터 PWM 을 만들지 않고 NoMotor 를 반환합니다.
    (같은 핀에 PWM 을 두 번 만들면 RPi.GPIO 가 RuntimeError 를 냅니다.)
    '''
    if pin in (SERVO1_PIN, SERVO2_PIN):
        print('[모터] %s PWM(P%d) 은 서보모터가 사용하므로 끕니다 → 이 모터는 동작하지 않습니다.' % (name, pin))
        return NoMotor()
    GPIO.setup(pin, GPIO.OUT)          # 모터 PWM 신호 출력 핀
    motor = GPIO.PWM(pin, 500)         # 모터 PWM 주파수 500Hz
    motor.start(0)                     # 펄스폭 변조(PWM)값 0 으로 시작
    return motor

MOTOR_L = motorInit(MOTOR_L_PWM, '왼쪽 모터')
MOTOR_R = motorInit(MOTOR_R_PWM, '오른쪽 모터')
#--------------------------------------------------------------------------------------------
tof = VL53L0X.VL53L0X()               # 거리 감지 센서 객체 설정
# ==============================
# 서보모터 초기화
# ==============================
SERVO_MIN = 0           # 서보모터 최소 각도
SERVO_MAX = 180         # 서보모터 최대 각도
SERVO_CENTER = 90       # 처음 움직일 때 기준 각도 (프로그램 시작 직후에는 서보 위치를 알 수 없음)
SERVO_STEP = 10         # "10도" 키 1회 회전량 (도)
SERVO_SWEEP_STEP = 2    # "계속" 키를 누른 뒤 화면 1장(루프 1회)마다 움직이는 각도 (약 1초에 60도)
SERVO_LEFT = 1          # 왼쪽 = 각도 증가. 실제로 왼쪽·오른쪽이 반대로 돌면 -1 로 바꾸세요.
# 이동 후 이 시간이 지나면 신호를 끊어 힘을 풉니다. 신호를 계속 주면 서보가 위치를 못 잡고 버티며 떨기 때문입니다.
# 너무 짧으면 목표에 닿기 전에 끊겨 "가다가 멈춥니다" (0.5초에서 시작 키 90도 이동이 중간에 멈췄음, 2026-10-29 영상).
SERVO_HOLD_SEC = 1.5
# 펄스 폭: 0도 ~ 180도에 해당하는 신호 길이(초). MG90S 데이터시트 값은 0.5ms ~ 2.5ms 이지만
# 이 서보는 2.5ms 에서 끝에 닿아 버티므로(끼익) 안쪽으로 줄였습니다. 아직 끝에서 버티면 더 줄이세요.
SERVO_MIN_PULSE = 0.0006
SERVO_MAX_PULSE = 0.0024

def servoInit(pin, name):
    '''
    서보모터를 생성합니다. 신호를 보내지 않으므로 이동 키를 누르기 전까지 움직이지 않습니다.
    실패하면 원인을 출력하고 None 을 반환하며, 서보모터 없이 주행·이미지 수집은 계속됩니다.
    '''
    try:
        servo = AngularServo(pin, initial_angle=None, min_angle=SERVO_MIN, max_angle=SERVO_MAX,
                             min_pulse_width=SERVO_MIN_PULSE, max_pulse_width=SERVO_MAX_PULSE)
        print('[서보] %s 준비 완료 (정지, 이동 키를 누르면 움직입니다)' % name)
        return servo
    except Exception as e:
        print('[서보 오류] %s 초기화 실패 → 이 서보모터는 사용하지 않습니다.' % name)
        print('            원인: %s: %s' % (type(e).__name__, e))
        print('            확인: gpiozero 설치, P%d 를 다른 장치가 쓰고 있지 않은지' % pin)
        return None

SERVO1_NAME = 'servo1(P%d)' % SERVO1_PIN      # 터미널 출력용 이름 (확장보드 글씨와 동일)
SERVO2_NAME = 'servo2(P%d)' % SERVO2_PIN
servo1 = servoInit(SERVO1_PIN, SERVO1_NAME)
servo2 = servoInit(SERVO2_PIN, SERVO2_NAME)
servoAngle = {SERVO1_NAME: SERVO_CENTER, SERVO2_NAME: SERVO_CENTER}  # 마지막으로 보낸 각도. 신호를 끊어도 기억합니다.
servoTimer = {SERVO1_NAME: None, SERVO2_NAME: None}    # 이동 후 신호를 끊을 타이머
servoSweep = {SERVO1_NAME: 0, SERVO2_NAME: 0}          # "계속" 방향 (+1 왼쪽 / -1 오른쪽, 0 = 안 함)
print('[서보] 소프트웨어 PWM 사용 중: 서보가 조금 떨릴 수 있습니다 (pigpio 사용 시 개선).')
checkPower('시작')
POWER_CHECK_PERIOD = 1.0  # 주행 중 전원 상태 확인 간격 (초)
#--------------------------------------------------------------------------------------------
# 설정, 조준, 자극, 기록 (settings_gui.py 로 실행 중에 바꾸고 시험합니다) -------------------------
SETTINGS = cfg.load()                 # 값은 applySettings() 로 아래 상수와 탐지 모듈에 들어갑니다
settingsWatcher = cfg.Watcher()       # runtime/settings.json 이 바뀌면 메인 루프에서 다시 읽음
commands = control.CommandReader()    # 설정 GUI 의 실험 명령
STATUS = {}                           # 설정 GUI 와 조회 서버(/api/status)에 보여 줄 상태
STATUS_PERIOD = 1.0                   # 상태 파일 쓰는 간격 (초)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
eventServer = None                    # 원격 조회 서버 (EVENT_SERVER_ON 일 때 __main__ 에서 켬)
# 서보 키 (숫자열, 숫자 키패드, 소문자). 누르면 자동 조준을 MANUAL_OVERRIDE_SEC 동안 쉼 (AIM-06)
SERVO_MANUAL_KEYS = {ord(c) for c in '123450qwert'} | {0x80 + ord(c) for c in '123450'}

def aimMove(tilt, pan):
    '''서보 1 = 위아래(tilt), 서보 2 = 좌우(pan). SERVO_HOLD_SEC 뒤 힘을 풉니다.
    servoAngle 이 같아도 보냅니다: 시작 직후에는 실제 위치를 모르는데 servoAngle 은 SERVO_CENTER 로 되어 있으므로.'''
    for servo, name, angle in ((servo1, SERVO1_NAME, tilt), (servo2, SERVO2_NAME, pan)):
        servoSweep[name] = 0
        servoMoveTo(servo, name, angle, '')

def aimHold():
    '''두 서보를 그 자리에서 힘 풀기 (사람이 보일 때 프레임마다, 실험 [힘 풀기]).'''
    for servo, name in ((servo1, SERVO1_NAME), (servo2, SERVO2_NAME)):
        servoSweep[name] = 0
        servoCancelTimer(name)
        if servo is not None:            # 없는 서보는 조용히 건너뜀 (프레임마다 오류 출력 방지)
            servoSet(servo, name, None, '')

aimer = aim.Aimer(lambda: (servoAngle[SERVO1_NAME], servoAngle[SERVO2_NAME]), aimMove, aimHold)
stimulus = stim.Stimulus(BASE_DIR)
eventLog = event_log.EventLog(BASE_DIR)

def applySettings(s):
    '''설정값을 이 파일의 상수와 탐지 모듈에 넣습니다. 시작할 때와 settings.json 이 바뀔 때 부릅니다.'''
    global SETTINGS, RUN_SPEED, ANGLE_GAIN, HORN_DISTANCE, STOP_DISTANCE, SERVO_CENTER, SERVO_LEFT, SERVO_HOLD_SEC
    global SERVO_STEP, SERVO_SWEEP_STEP
    SETTINGS = s
    RUN_SPEED, ANGLE_GAIN = s['RUN_SPEED'], s['ANGLE_GAIN']
    HORN_DISTANCE, STOP_DISTANCE = s['HORN_DISTANCE'], s['STOP_DISTANCE']
    SERVO_CENTER, SERVO_LEFT, SERVO_HOLD_SEC = s['SERVO_CENTER'], s['SERVO_LEFT'], s['SERVO_HOLD_SEC']
    SERVO_STEP, SERVO_SWEEP_STEP = s['SERVO_STEP'], s['SERVO_SWEEP_STEP']   # 키보드 서보 속도
    if detector is not None:
        detector.conf, detector.hold = s['DETECT_CONF'], s['DETECT_HOLD_SEC']

def handleCommand(c, frame, personSeen, detectOk):
    '''설정 GUI 실험 명령을 실행하고 결과 문장을 돌려줍니다.'''
    name, a, s = c['cmd'], c.get('args') or {}, SETTINGS
    moves = ('aim_center', 'aim_angle', 'aim_point', 'stim_start')
    try:
        if name in moves and not detectOk and not s['ALLOW_WITHOUT_DETECT']:
            return '탐지가 꺼져 있어 사람을 확인할 수 없음 → 거부 (SAFE-08, 설정 안전 탭에서 허용 가능)'
        if name in ('aim_center', 'aim_angle', 'aim_point') and personSeen:
            return '사람이 보여서 서보를 움직이지 않음 (SAFE-06)'
        if name.startswith('aim_'):
            aimer.pause(s['MANUAL_OVERRIDE_SEC'])       # 시험하는 동안 자동 조준이 덮어쓰지 않게
        if name == 'aim_center':
            return '가운데로 → 위아래 %d, 좌우 %d' % aimer.aimCenter(s)
        if name == 'aim_angle':
            return '각도 → 위아래 %d, 좌우 %d' % aimer.moveTo(int(a['tilt']), int(a['pan']), s)
        if name == 'aim_point':
            x, y = int(a['x']), int(a['y'])
            t = aimer.aimAt((x - 20, y - 20, x + 20, y + 20), s, force=True)
            return '(%d, %d) 조준 → 위아래 %d, 좌우 %d' % (x, y, t[0], t[1])
        if name == 'aim_hold':
            aimer.aimHold()
            return '힘 풀기'
        if name == 'stim_start':
            if personSeen:
                return '사람이 보여서 자극하지 않음 (SAFE-06)'
            ok = stimulus.start(a['kind'], s['STIMULUS_SEC'], s)
            return '%s %s' % (a['kind'], '시작' if ok else '실패 (터미널 확인)')
        if name == 'stim_stop':
            stimulus.stop()
            return '자극 정지'
        if name == 'log_test':
            rec = eventLog.write({'species': 'test', 'result': a['result'], 'zone': None}, photo=frame)
            return '기록 %s' % rec['id'] if rec else '기록 실패 (터미널 확인)'
    except (KeyError, TypeError, ValueError, OverflowError) as e:
        return '명령 오류: %s' % e
    return '모르는 명령'

def publicStatus():
    '''조회 서버(/api/status)용 상태. 내부 오류 문장은 빼고, 메인 루프가 고치는 중인 dict 대신 복사본.'''
    s = dict(STATUS)
    s['detect_error'] = bool(s.get('detect_error'))
    s.pop('last_command', None)
    return s
#--------------------------------------------------------------------------------------------
viewWin = np.zeros((480,800,3),np.uint8)  # 표시되는 윈도우 가로, 세로, 컬러층, 8비트
msgBoxL = cv.imread('./_IMAGE/armL.png',cv.IMREAD_COLOR)
msgBoxR = cv.imread('./_IMAGE/armR.png',cv.IMREAD_COLOR)
#--------------------------------------------------------------------------------------------
cv.namedWindow('Out', cv.WINDOW_NORMAL | cv.WINDOW_FREERATIO)
cv.setWindowProperty('Out', cv.WND_PROP_ASPECT_RATIO, cv.WINDOW_FREERATIO)
cv.setWindowProperty('Out', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
# 화면 해상도로 늘려 표시하고(흰 여백 제거) 저장·제어 좌표는 800x480을 유지한다.
import re
import subprocess
display_info = subprocess.check_output(['xrandr', '--current'], text=True)
display_match = re.search(r'current\s+(\d+)\s+x\s+(\d+)', display_info)
if display_match is None:
    raise RuntimeError('xrandr에서 현재 화면 해상도를 확인하지 못했습니다.')
DISPLAY_X, DISPLAY_Y = map(int, display_match.groups())
if DISPLAY_X <= 0 or DISPLAY_Y <= 0:
    raise RuntimeError('화면 해상도는 양수여야 합니다.')

#--------------------------------------------------------------------------------------------
# CSI 카메라는 libcamera 기반이라 cv.VideoCapture(V4L)로는 영상이 None 으로 온다
camera = Picamera2()                  # 카메라 객체 생성 (종료 처리 cleanup() 에서 닫음)
# RGB888은 Picamera2에서 OpenCV에 맞는 BGR 바이트 순서로 반환된다.
camera.configure(camera.create_video_configuration(main={"size": (640, 480), "format": "RGB888"}))
camera.start()
#--------------------------------------------------------------------------------------------
fileList = []             # os.listdir(dataDir)  # 데이터 디렉토리 내의 이미지 파일 이름을 리스트로 반환
#--------------------------------------------------------------------------------------------
class NvidiaModel(nn.Module):
    def __init__(self):
        super(NvidiaModel, self).__init__()
        # elu=Expenential Linear Unit, similar to leaky Relu
        # skipping 1st hiddel layer (nomralization layer), as we have normalized the data
        # Convolution Layers
        self.layer1 = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=24, kernel_size=(5, 5), stride=(2, 2)),
            nn.ELU(inplace=True),
            nn.Conv2d(in_channels=24, out_channels=36, kernel_size=(5, 5), stride=(2, 2)),
            nn.ELU(inplace=True),
            nn.Conv2d(in_channels=36, out_channels=48, kernel_size=(5, 5), stride=(2, 2)),
            nn.ELU(inplace=True),
            nn.Conv2d(in_channels=48, out_channels=64, kernel_size=(3, 3)),
            nn.ELU(inplace=True),
            nn.Dropout(0.2),
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3)),
            nn.ELU(inplace=True)
        )
        # Fully Connected Layers
        self.layer2 = nn.Sequential(
            # nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(in_features=18 * 64, out_features=100),
            nn.ELU(inplace=True),
            nn.Linear(in_features=100, out_features=50),
            nn.ELU(inplace=True),
            nn.Linear(in_features=50, out_features=10),
            nn.ELU(inplace=True)
        )
        # Output Layer
        self.layer3 = nn.Sequential(
            nn.Linear(in_features=10, out_features=1)
        )
    def forward(self, x):
        x = self.layer1(x)
        #x = x.view(x.shape[0], -1)
        x = x.reshape(x.shape[0], -1)
        x = self.layer2(x)
        x = self.layer3(x)
        return x
# Motor Run Function ------------------------------------------------------------------------
def motorRun(leftMotor, rightMotor):
    '''
    왼쪽 모터와 오른쪽 모터에 PWM 값을 설정합니다.
    부호가 음수(-)이면 후진, 양수(+)이면 전진합니다.
    PWM 값의 범위는 0~100 까지 입니다.
    '''
    amotorL = abs(leftMotor)                   # 왼쪽 모터 PWM 절대값
    if amotorL>100:                            # PWM 값이 100 보다 크면 100 으로 조정
        amotorL = 100
    amotorR = abs(rightMotor)                  # 오른쪽 모터 PWM 절대값
    if amotorR>100:                            # PWM 값이 100 보다 크면 100 으로 조정
        amotorR = 100
    #----------------------------------------------------------------------------------------
    if leftMotor >= 0:                         # 왼쪽 모터의 방향 설정
        GPIO.output(MOTOR_L_DIR,GPIO.HIGH)     # 왼쪽 모터 전진
    else:
        GPIO.output(MOTOR_L_DIR,GPIO.LOW)      # 왼쪽 모터 후진
    MOTOR_L.ChangeDutyCycle(amotorL)           # 왼쪽 모터 PWM 값 설정

    if rightMotor >= 0:                        # 오른쪽 모터의 방향 설정
        GPIO.output(MOTOR_R_DIR,GPIO.HIGH)     # 오른쪽 모터 전진
    else:
        GPIO.output(MOTOR_R_DIR,GPIO.LOW)      # 오른쪽 모터 후진
    MOTOR_R.ChangeDutyCycle(amotorR)           # 오른쪽 모터 PWM 값 설정
# Servo Move Function -----------------------------------------------------------------------
def servoSet(servo, name, angle, label):
    '''
    서보모터에 값을 보내고 label 을 출력합니다. angle 이 None 이면 신호를 끕니다(정지).
    서보모터가 없거나 오류가 나도 프로그램을 멈추지 않고 원인만 출력하며, 성공하면 True 를 반환합니다.
    '''
    if servo is None:
        print('[서보] %s 는 초기화에 실패해서 사용할 수 없습니다.' % name)
        return False
    try:
        servo.angle = angle
    except Exception as e:
        print('[서보 오류] %s %s 실패: %s: %s' % (name, label, type(e).__name__, e))
        return False
    if label: print('[서보] %s %s' % (name, label))
    return True

def servoCancelTimer(name):
    '''진행 중인 "신호 끊기" 타이머를 취소합니다.'''
    if servoTimer[name] is not None:
        servoTimer[name].cancel()
        servoTimer[name] = None

def servoMoveTo(servo, name, angle, label, release=True):
    '''angle 로 이동합니다. release 이면 SERVO_HOLD_SEC 뒤 신호를 끊어 그 자리에서 힘을 풉니다.'''
    servoCancelTimer(name)
    if not servoSet(servo, name, angle, label):
        servoSweep[name] = 0
        return
    servoAngle[name] = angle
    if release:
        servoTimer[name] = threading.Timer(SERVO_HOLD_SEC, servoSet, (servo, name, None, ''))
        servoTimer[name].daemon = True
        servoTimer[name].start()

def servoStop(servo, name):
    '''"계속"을 멈추고 신호를 바로 끊습니다. 이동 키는 바로 다시 쓸 수 있습니다.'''
    servoSweep[name] = 0
    servoCancelTimer(name)
    servoSet(servo, name, None, '정지 (%d도)' % servoAngle[name])

def servoNext(name, direction, step):
    '''마지막 각도에서 direction(+1 왼쪽 / -1 오른쪽) 으로 step 도 간 각도. 범위 끝에서 자릅니다.'''
    return max(SERVO_MIN, min(SERVO_MAX, servoAngle[name] + direction * SERVO_LEFT * step))

def servoTurn(servo, name, direction):
    '''"10도" 키: SERVO_STEP 도 간 뒤 멈춥니다. 범위 끝에서는 더 가지 않습니다.'''
    servoSweep[name] = 0
    target = servoNext(name, direction, SERVO_STEP)
    if target == servoAngle[name]:
        print('[서보] %s %d도 (범위 끝이라 더 움직이지 않음)' % (name, target))
        return
    servoMoveTo(servo, name, target, '%s %d도' % ('왼쪽' if direction > 0 else '오른쪽', target))

def servoKeepTurning(servo, name, direction):
    '''"계속" 키: 정지 키를 누르거나 끝에 닿을 때까지 direction 쪽으로 움직입니다 (servoSweepStep 이 움직임).
    같은 방향으로 움직이는 중에 같은 키를 한 번 더 누르면 멈춥니다.'''
    if servoSweep[name] == direction:
        servoStop(servo, name)
        return
    servoSweep[name] = direction
    print('[서보] %s %s으로 계속 (같은 키를 한 번 더 누르거나 정지 키로 멈춤)' % (name, '왼쪽' if direction > 0 else '오른쪽'))

def servoSweepStep(servo, name):
    '''메인 루프에서 화면 1장마다 부릅니다. "계속" 중이면 SERVO_SWEEP_STEP 만큼 움직이고, 끝에 닿으면 멈춥니다.'''
    if not servoSweep[name]:
        return
    target = servoNext(name, servoSweep[name], SERVO_SWEEP_STEP)
    if target == servoAngle[name]:
        servoSweep[name] = 0
        servoMoveTo(servo, name, target, '%d도 (범위 끝이라 멈춤)' % target)
        return
    servoMoveTo(servo, name, target, '', release=False)
# Cleanup Function --------------------------------------------------------------------------
def closePinFactory():
    '''
    gpiozero 가 잡고 있는 서보모터 핀(SERVO1_PIN, SERVO2_PIN)을 GPIO.cleanup() 보다 먼저 해제합니다.
    servo.close() 만으로는 핀이 gpiozero 내부 목록에 남아 있어서, 프로그램이 끝날 때
    gpiozero 가 GPIO.cleanup(핀번호) 를 다시 호출합니다. 이때 GPIO.cleanup() 으로 핀 번호
    방식(BCM)이 이미 지워져 있으면 RuntimeError(setmode) 가 납니다.
    핀을 먼저 해제하고 pin_factory 를 비워 두면 종료 시 gpiozero 가 다시 정리하지 않습니다.
    '''
    if Device.pin_factory is not None:
        Device.pin_factory.close()
        Device.pin_factory = None

def cleanup():
    '''
    프로그램 종료 시 장치를 정리합니다. 정상 종료와 오류 종료 모두 호출됩니다.
    한 단계가 실패해도 나머지 단계는 계속 진행합니다.
    서보모터는 GPIO.cleanup() 보다 먼저 해제해야 종료 시 RuntimeError 가 나지 않습니다.
    '''
    steps = [('모터 정지',         lambda: motorRun(0, 0)),
             ('전조등 끄기',       lambda: nx.lamp(0,0,0)),
             ('왼쪽 모터 정지',    MOTOR_L.stop),
             ('오른쪽 모터 정지',  MOTOR_R.stop),
             ('서보모터 1 해제',   lambda: servo1 and servo1.close()),
             ('서보모터 2 해제',   lambda: servo2 and servo2.close()),
             ('자극 끄기',         stimulus.close),
             ('조회 서버 끄기',    lambda: eventServer and eventServer.shutdown()),
             ('gpiozero 핀 해제',  closePinFactory),
             ('GPIO 초기화',       GPIO.cleanup),
             ('카메라 반납',       camera.close),
             ('윈도우 닫기',       cv.destroyAllWindows)]
    for name, step in steps:
        try:
            step()
        except Exception as e:
            print('[종료 처리 오류] %s 실패: %s: %s' % (name, type(e).__name__, e))

# Error Report Function ---------------------------------------------------------------------
def reportError(e):
    '''
    예기치 않은 오류를 읽기 쉽게 출력합니다.
    요약(종류·내용·이 파일의 발생 위치)을 먼저 보여주고, 상세 Traceback 은 아래에 붙입니다.
    '''
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename.endswith('ar.py')]
    print('\n' + '=' * 70)
    print('[오류] 프로그램이 오류로 종료되었습니다.')
    print('  종류: %s' % type(e).__name__)
    print('  내용: %s' % e)
    if frames:
        f = frames[-1]
        print('  위치: ar.py %d번 줄 (%s 함수)' % (f.lineno, f.name))
        print('  코드: %s' % f.line)
    print('  → 아래 상세 로그와 함께 위 내용을 공유해 주세요.')
    print('=' * 70)
    print('[상세 로그]')
    traceback.print_exception(type(e), e, e.__traceback__)

#============================================================================================
def main():

    global lightMode, lightCar

    # 상수 값 설정
    RESTART_NUM = 33             # Red 신호 유지 시간(frame단위)
    YM = 240                     # 모터 바 그래프 중앙 위치 (왼쪽, 오른쪽 공통 적용)
    nx.lamp(0,0,0)               # 전조등 끄기
    # 변수 초기 설정
    VIEW_FLAG = True             # 화면 표시 모드
    autoRun = False              # 자동차 동작 상태 (True:자율주행 False:정지)
    BLINK_LEFT = False           # 왼쪽 깜빡이
    BLINK_RIGHT = False          # 오른쪽 깜빡이
    TOF_FLAG = False             # 거리 감지 센서 동작 상태
    YUV = False                  # NVIDIA Cell 디스프레이 모드
    CDS = 'NIGHT'                # CdS 의 상태기록 Day:밝음, Night:어두움 
    preKey = ord(' ')            # 차량 초기 상태를 정지 상태로 설정
    PWM_COLOR = GREEN            # 모터 PWM 그래프 색상, GREEN: 수동 조작, RED: 자율 주행
    mL = 0                       # 왼쪽 모터 속도, PWM 값 -100 ~ 0 ~ +100
    mR = 0                       # 오른쪽 모터 속도, PWM 값 -100 ~ 0 ~ +100
    signRedDelay = 0             # 적색 신호가 감지 됬을 때 0 보다 큰 수로 설정, 0 이면 주행 
    angle = 0                    # 조향 각도
    timeCycle = 0                # 실행 주기 시간 (카메라 frame) 
    horn = 0                     # 경적 유지 시간
    blinkCount = 0               # 깜빡이 카운트
    powerTime = time.time()      # 마지막 전원 상태 확인 시각
    DETECT_ON = detector is not None  # YOLO 탐지 동작 상태 ([O] 키로 전환)
    statusTime = 0.0             # 마지막으로 상태 파일을 쓴 시각
    lastCommand = ''             # 마지막 실험 명령 결과 (설정 GUI 에 표시)

    #----------------------------------------------------------------------------------------
    while True:
        startCycle = time.time()                       # 프레임 시작 시각
        if startCycle - powerTime >= POWER_CHECK_PERIOD:
            powerTime = startCycle
            checkPower('주행 중')                       # 상태가 바뀔 때만 출력
        newSettings = settingsWatcher.poll()           # 설정 GUI 에서 저장하면 바로 반영
        if newSettings:
            applySettings(newSettings)
            print('[설정] 바뀐 값을 반영했습니다')
        if GPIO.input(LIGHT_SENSOR): CDS = 'NIGHT'     # 빛 감지 센서 
        else: CDS = 'DAY'
        if lightMode == 'AUTO' and CDS == 'NIGHT': nx.lamp(255,255,255)  # 전조등 자동 On
        elif lightCar == 'ON':  nx.lamp(255,255,255)   # 전조등 수동 On
        elif lightCar == 'POLICE 1': nx.policeCar1()   # Police Car 1
        elif lightCar == 'POLICE 2': nx.policeCar2()   # Police Car 2
        elif lightCar == 'POLICE 3': nx.policeCar3()   # Police Car 3
        elif lightCar == 'AMBULANCE': nx.ambulance()   # Ambulance Car
        elif lightCar == 'FIRE TRUCK': nx.fireTruck()  # Fire Truck
        elif lightCar == 'PATROL': nx.patrol()         # Patrol Car
        elif lightCar == 'OFF' or lightCar == ' ': nx.lamp(0,0,0)        # 전조등 Off
        # 경적 -------------------------------------------------------------------------------
        if horn: 
            GPIO.output(BUZZER,GPIO.HIGH)
            horn -= 1                                  # 경적 유지 시간 감소
        else: 
            GPIO.output(BUZZER,GPIO.LOW)               # 경적 끄기
        # 카메라로 부터 1 프레임 영상 가져오기 ---------------------------------------------------
        frame = camera.capture_array("main") #frame = cv.flip(frame,-1) # 입력 이미지를 필요하면 상하 반전
        if frame is None or frame.shape != (480, 640, 3):
            raise RuntimeError("카메라에서 640x480 컬러 영상을 받지 못했습니다.")
        viewWin[0:480,80:720] = frame[0:480,0:640]     # 480 x 640 VGA
        viewWin[0:480,0:0+80] = msgBoxL                # 왼쪽 메시지 박스
        viewWin[0:480,720:720+80] = msgBoxR            # 오른쪽 메시지 박스
        if DETECT_ON: detector.submit(frame)           # 탐지 스레드에 최신 화면 전달 (기다리지 않음)
        image = viewWin[WIN_YU:WIN_YD,WIN_XL+80:WIN_XR+80]   # 트랙 이미지
        image = cv.resize(image,(200,66))              # NVIDEA Image 포맷 (X:200, Y:66)
        imageYUV = cv.cvtColor(image, cv.COLOR_BGR2YUV)# RGB 색상을 YUV 색상으로 변환
        imageYUVG = cv.GaussianBlur(imageYUV, (3,3), 0) # Gauss 노이즈 제거
        procImg = imageYUVG/255            # 0-255 범위(정수)를 0.000-0.999 범위(유리수)로 변환
        # 신호등 인식 -------------------------------------------------------------------------
        # 적색 신호등이 인식되면 signRedDelay 에 non zero(RESTART_NUM) 를 저장한다.
        # signRedDelay 이 0 이 아니면 차량은 정지하고 0 이 되면 주행 시작한다.
        # signRedDelay 은 1 프레임 에서 1 씩 감소하여 0 이 된다. 
        v = ts.trafficSign(viewWin,          # Y480 x X800 전체 LCD 스크린
                        VIEW_FLAG,            # 신호등 데이터 디스프레이
                        TSWIN_XL,             # 카메라 영역 X 축 Left  0~640 
                        TSWIN_YU,             # 카메라 영역 Y 축 Up    0~480 
                        TSWIN_XR,             # 카메라 영역 X 축 Right 0~640 
                        TSWIN_YD,             # 카메라 영역 Y 축 Down  0~480
                        minRadius,            # 신호등 최소 반지름      >8
                        maxRadius,            # 신호등 최대 반지름      <40
                        HSV_hueLeadGREEN,     # Green 시작각
                        HSV_hueTailGREEN,     # Green 종료각
                        HSV_hueLeadRED,       # Red 시작각
                        HSV_hueTailRED,       # Red 종료각
                        HSV_saturationGREEN,  # Green Saturation
                        HSV_saturationRED,    # Red Saturation
                        HSV_valueGREEN,       # Green Value
                        HSV_valueRED,         # Red Value
                        THRESH_GREEN*10,      # Green Threshold
                        THRESH_RED*10         # Red Threshold
                        )

        if v == 'G': signRedDelay = 0                  # 녹색 신호등
        if v == 'R' and preKey == 80: 
            signRedDelay = RESTART_NUM                 # 자율 주행 모드에서 적색 신호등이면 정지
        if signRedDelay > 0:                           # 적색 신호등 이후에 일정시간 지나면 
            signRedDelay -= 1                          # 녹색 신호등이 없어도 주행 시작
        if signRedDelay > 0:                           # 적색 신호등 소등 이후 카운트 표시
            cv.putText(viewWin,f'{signRedDelay:2d}',(750,110),cv.FONT_HERSHEY_PLAIN,1,YELLOW)
        # 방향 지시등 -------------------------------------------------------------------------
        blinkCount += 1
        blinkCount %= 10                               # 10 frame 주기
        if blinkCount > 5:
            if BLINK_LEFT: GPIO.output(LAMP_L_YELLOW,GPIO.HIGH); viewWin[350:380,10:70] = YELLOW
            if BLINK_RIGHT: GPIO.output(LAMP_R_YELLOW,GPIO.HIGH); viewWin[350:380,730:790] = YELLOW
        else:
            GPIO.output(LAMP_R_YELLOW,GPIO.LOW); GPIO.output(LAMP_L_YELLOW,GPIO.LOW) # 노란색 끄기
        # 전방 거리 측정, 경적 발생, 차량 정지 ---------------------------------------------------
        if TOF_FLAG: 
            distance = tof.get_distance()                # VL53L0X TOF 거리 센서 측정 값 가져오기
            if VIEW_FLAG:
                if distance < 2000:
                    cv.putText(viewWin, f'{distance:3d} MM', (320,165),cv.FONT_HERSHEY_COMPLEX_SMALL,2,WHITE)
                else:
                    cv.putText(viewWin, f'--- MM', (320,165),cv.FONT_HERSHEY_COMPLEX_SMALL,2,WHITE)
            # 경적 구간에 들어오면 스크린에 정지 표시하고 경적 소리 출력 -----------------------------
            if distance < HORN_DISTANCE:
                cv.circle(viewWin, (400,160), 100, RED, 25)  # 정지 표시
                cv.line(viewWin, (400+70,160-70), (400-70,160+70), RED, 25)
                GPIO.output(LAMP_BRAKE,GPIO.HIGH)        # 브레이크 적색 램프 점등
                if preKey == 80 or preKey == 82:         # 자율 주행(G, Home) 또는 전진(Arrow Up)
                    horn = True                              
                if distance < STOP_DISTANCE:             # 정지 거리
                    horn = False                         # 경적 Off
                    if (preKey == 80 or preKey == 82):   # 자율 주행(80) 또는 수동 주행(82) 확인
                        signRedDelay = RESTART_NUM       # 주행 정지
                        BLINK_LEFT = True; BLINK_RIGHT = True
            else: 
                GPIO.output(LAMP_BRAKE,GPIO.LOW)         # 브레이크 적색 램프 끄기
        # 동물·사람 탐지 (YOLO) ---------------------------------------------------------------
        # 사람이 보이면 정지하고 자극(경적)을 내지 않습니다. 사람 없이 노루·멧돼지만 보이면 경적.
        personSeen = False
        animalSeen = False
        boxes = []
        if DETECT_ON:
            personSeen, animalSeen, boxes, inferMs = detector.state()
            if animalSeen and not personSeen:
                horn = 5                                 # 5 프레임 동안 경적 (보이는 동안 계속)
            if VIEW_FLAG:
                for x1, y1, x2, y2, name, conf in boxes:
                    color = YELLOW if name == 'person' else RED
                    cv.rectangle(viewWin, (x1+80, y1), (x2+80, y2), color, 2)
                    cv.putText(viewWin, f'{name} {conf:.2f}', (x1+80, max(y1-5, 12)), cv.FONT_HERSHEY_PLAIN, 1, color)
                if detector.error:
                    cv.putText(viewWin, 'YOLO ERROR', (560,20), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, RED)
                else:
                    cv.putText(viewWin, f'YOLO {inferMs:4d} mS', (560,20), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, WHITE)
                if personSeen:
                    cv.putText(viewWin, 'PERSON STOP', (300,250), cv.FONT_HERSHEY_COMPLEX_SMALL, 2, YELLOW)
        # 사람이 보이면 자극 끄고 서보 멈춤 (SAFE-06 일부). 멈춰 있을 때만 동물 쪽 자동 조준 (AIM-02) ----
        # 탐지가 꺼졌거나 오류로 멈추면 사람을 확인할 수 없으므로 자극을 끔 (SAFE-08 일부)
        detectOk = DETECT_ON and detector is not None and detector.error is None
        if not detectOk and not SETTINGS['ALLOW_WITHOUT_DETECT']:
            stimulus.stop()
        if personSeen:
            stimulus.stop()
            aimer.aimHold()
        elif SETTINGS['AIM_AUTO'] and animalSeen and not autoRun and mL == 0 and mR == 0:
            target = aim.largestBox([b for b in boxes if b[4] in yd.ANIMAL_NAMES])
            if target is not None:
                aimer.aimAt(target, SETTINGS)
        # 설정 GUI 실험 명령 -------------------------------------------------------------------
        c = commands.poll()
        if c:
            lastCommand = '%s → %s' % (c['cmd'], handleCommand(c, frame, personSeen, detectOk))
            print('[실험]', lastCommand)
        #------------------------------------------------------------------------------------
        if VIEW_FLAG:
            if MODEL_FILE: 
                cv.putText(viewWin, f'{imageDir}',(90,20),cv.FONT_HERSHEY_COMPLEX_SMALL,1,MAGENTA)
            cv.putText(viewWin, f'{timeCycle:4d} mS',(340,20),cv.FONT_HERSHEY_COMPLEX_SMALL,1,WHITE)
            cv.putText(viewWin, f'{lightMode} {CDS} {lightCar}',(510,475),cv.FONT_HERSHEY_PLAIN,1,GREEN)
            cv.putText(viewWin, 'Lane Detect Area', (WIN_XL+90,WIN_YU+18),cv.FONT_HERSHEY_PLAIN,1,YELLOW)
            cv.rectangle(viewWin,(WIN_XL+80,WIN_YU),(WIN_XR+80,WIN_YD),YELLOW,1)  # 차선 검색 영역 표시
            cv.putText(viewWin, 'Traffic Siginal Area', (TSWIN_XL+90,TSWIN_YU+18),cv.FONT_HERSHEY_PLAIN,1,CYAN)
            cv.rectangle(viewWin,(TSWIN_XL+80,TSWIN_YU),(TSWIN_XR+80,TSWIN_YD),CYAN,1)  # 신호등 검색 영역 표시

            if YUV:
                viewWin[407:407+66,300:300+200] = imageYUVG
            else:
                viewWin[407:407+66,300:300+200] = image
            if (lightMode == 'AUTO' and CDS == 'NIGHT') or lightCar == 'ON':  
                cv.rectangle(viewWin,(300-2,407-2),(300+200+2,407+66+2),WHITE,3)  # Lamp On
        # 자율 주행 모드 조향 각도 검출 ---------------------------------------------------------
        if MODEL_FILE and autoRun:    # 학습 파일이 존재하고 자율주행 모드일 때 실행
            X = np.asarray([procImg])
            X = torch.Tensor(X).permute(0, 3, 1, 2)
            angle = 0
            model.eval()
            with torch.no_grad():
                angle = int(model(X)[0] * ANGLE_GAIN)
            if VIEW_FLAG: 
                cv.putText(viewWin, f'{angle:3d}', (260,380),cv.FONT_HERSHEY_COMPLEX_SMALL,6,WHITE)
            mL = RUN_SPEED + angle     # 왼쪽 모터 속도 값(PWM)
            mR = RUN_SPEED - angle     # 오른쪽 모터 속도 값(PWM) 
        # 왼쪽 모터와 오른쪽 모터의 속도 크가 값(PWM)을 바 그래프로 표시 -----------------------------
        if autoRun: 
            PWM_COLOR = RED            # 자율 주행에서 그래프 색상
        else: 
            PWM_COLOR = GREEN          # 수동 조정에서 그래프 색상
        # 왼쪽 모터 PWM 그래프 ------------------------------------------------------------------
        if mL >= 0: 
            ys = YM - mL
            ye = YM
        else: 
            ys = YM
            ye = YM - mL  
        cv.rectangle(viewWin,(30,ys),(50,ye),PWM_COLOR,-1)
        # 오른쪽 모터 PWM 그래프 ----------------------------------------------------------------
        if mR >= 0: 
            ys = YM - mR
            ye = YM
        else: 
            ys = YM
            ye = YM - mR  
        cv.rectangle(viewWin,(750,ys),(770,ye),PWM_COLOR,-1)
        # 모터 PWM 값 표시 --------------------------------------------------------------------
        cv.putText(viewWin, f'{mL:3d}', (15,340),cv.FONT_HERSHEY_COMPLEX_SMALL,1,WHITE)
        cv.putText(viewWin, f'{mR:3d}', (735,340),cv.FONT_HERSHEY_COMPLEX_SMALL,1,WHITE)
        # 자율 주행 모드에서 Red 신호(0 보다 큰 수)이거나 사람이 보이면 정지 -------------------------
        if signRedDelay > 0 or personSeen:
            if autoRun or preKey == 82:           # 자율주행 모드일 또는 커서 Up 키
                mL = 0; mR = 0
        # 왼쪽 모터, 오른쪽 모터 동작 -----------------------------------------------------------
        motorRun(mL, mR)                          # PWM 값 지정 
        # 깜빡이 설정 -------------------------------------------------------------------------
        if preKey == 84: pass                     # Backward Key
        else:
            if abs(mL - mR) > 9:
                if (mL - mR) > 0: 
                    BLINK_LEFT = False; BLINK_RIGHT = True
                else: 
                    BLINK_LEFT = True; BLINK_RIGHT = False 
            else: 
                BLINK_LEFT = False; BLINK_RIGHT = False
        # 윈도우 디스프레이 --------------------------------------------------------------------
        cv.imshow('Out', cv.resize(viewWin, (DISPLAY_X, DISPLAY_Y)))
        # 수동 조작 모드, 파라메터 설정 ---------------------------------------------------------
        keyBoard = cv.waitKey(1)                              # 1 mSec 시간 지연하고 키값 읽기 
        # print(hex(keyBoard), keyBoard)
        if keyBoard == 0x1B or keyBoard == 0x09 or keyBoard == ord('x') or keyBoard == ord('X'):
            break                                             # ESC, TAB, X 프로그램 종료
        elif keyBoard == 80 or keyBoard == ord('g') or keyBoard == ord('G'): # Home, G 자율 주행 시작
            autoRun = True; signRedDelay = 0; preKey = 80
        elif keyBoard == ord('c') or keyBoard == ord('C'):    # 카메라, 신호등 영역 표시
            VIEW_FLAG = not VIEW_FLAG
        elif keyBoard == ord('h') or keyBoard == ord('H'):    # 경적
            horn = 5                                          # 5 프레임 동안 경적 울림
        elif keyBoard == ord('l') or keyBoard == ord('L'):    # 전조등 매뉴얼 모드
            if lightCar == ' ': lightCar = 'ON'
            elif lightCar == 'ON': lightCar = 'OFF'
            elif lightCar == 'OFF': lightCar = 'POLICE 1'
            elif lightCar == 'POLICE 1': lightCar = 'POLICE 2'
            elif lightCar == 'POLICE 2': lightCar = 'POLICE 3'
            elif lightCar == 'POLICE 3': lightCar = 'AMBULANCE'
            elif lightCar == 'AMBULANCE': lightCar = 'FIRE TRUCK'
            elif lightCar == 'FIRE TRUCK': lightCar = 'PATROL'
            elif lightCar == 'PATROL': lightCar = ' '
        elif keyBoard == ord('a') or keyBoard == ord('A'):    # 전조등 점등 모드
            if lightMode == 'MANU': 
                lightMode = 'AUTO'                            # 전조등 자동 점등 
            elif lightMode == 'AUTO': 
                lightMode = 'MANU'                            # 전조등 수동 점등
        elif keyBoard == ord('d') or keyBoard == ord('D'):    # ToF Range Sensor
            TOF_FLAG = not TOF_FLAG
            if TOF_FLAG: 
                tof.start_ranging(VL53L0X.VL53L0X_HIGH_SPEED_MODE) # 거리센서 동작 시작
            else: 
                tof.stop_ranging()                            # 거리 센서 정지
        elif keyBoard == ord('y') or keyBoard == ord('Y'):    # NVIDIA YUV 디스프레이
            YUV = not YUV                                     # RGB <-> YUV 전환
        elif keyBoard == ord('o') or keyBoard == ord('O'):    # YOLO 탐지 On/Off
            if detector is None:
                print('[탐지] 탐지 모델이 없어 켤 수 없습니다.')
            else:
                DETECT_ON = not DETECT_ON
                print('[탐지] %s' % ('켬' if DETECT_ON else '끔'))
        # 수동 차량 조정 ----------------------------------------------------------------------
        elif keyBoard == 82:                                  # 전진 Arrow Up(82)
            autoRun = False 
            if preKey == ord(' '): 
                mL = 80; mR = 80; signRedDelay = 0; preKey = keyBoard
            else: 
                preKey = ord(' '); mL = 0; mR = 0; GPIO.output(MUSIC,GPIO.LOW)
        elif keyBoard == 84:                                  # 후진 Arrow Down(84)
            autoRun = False 
            if preKey == ord(' '): 
                mL = -70; mR = -70; signRedDelay = 0; preKey = keyBoard
                GPIO.output(MUSIC,GPIO.HIGH)                  # 후진 멜로디
                BLINK_LEFT = True; BLINK_RIGHT = True         # 비상등
            else: 
                preKey = ord(' '); mL = 0; mR = 0; GPIO.output(MUSIC,GPIO.LOW)
        elif keyBoard == 81:                                  # 좌회전 Left(81)
            autoRun = False 
            if preKey == ord(' '): 
                mL = -70; mR = 70; signRedDelay = 0; preKey = keyBoard
            else: 
                preKey = ord(' '); mL = 0; mR = 0; GPIO.output(MUSIC,GPIO.LOW)
        elif keyBoard == 83:                                  # 우회전 Right(83)
            autoRun = False 
            if preKey == ord(' '): 
                mL = 70; mR = -70; signRedDelay = 0; preKey = keyBoard
            else: 
                preKey = ord(' '); mL = 0; mR = 0; GPIO.output(MUSIC,GPIO.LOW)
        elif keyBoard == ord(' ') or keyBoard == 87:          # [Spacd] [End]
            autoRun = False; preKey = ord(' '); mL = 0; mR = 0; GPIO.output(MUSIC,GPIO.LOW)
            stimulus.stop(); horn = 0                         # 수동 정지는 자극, 경적도 끔 (SAFE-09 일부)
            
        # 서보모터 조작 (servo1 = 숫자 1~5, servo2 = Q~T) -------------------------------------
        # 숫자 키패드(NumLock)는 0xB0~0xB9 로 입력되므로 숫자열 키와 함께 확인합니다.
        servoKey = keyBoard & 0xFF                # ar.py 는 키 값을 거르지 않으므로 하위 8비트만 비교
        if personSeen and servoKey in SERVO_MANUAL_KEYS:  # 사람 보호가 수동 서보 조작보다 먼저 (우선순위 3위 > 4위)
            print('[서보] 사람이 보여서 움직이지 않습니다 (SAFE-06)')
            servoKey = -1
        for servo, name, keys in ((servo1, SERVO1_NAME, ('1', '2', '3', '4', '5')),
                                  (servo2, SERVO2_NAME, ('q', 'w', 'e', 'r', 't'))):
            servoSweepStep(servo, name)
            # 문자 키는 소문자만: OpenCV 는 방향키를 대문자와 같은 값(←81=Q ↑82=R ↓84=T End87=W)으로 돌려줍니다.
            k = [(ord(c), 0x80 + ord(c)) if c.isdigit() else (ord(c),) for c in keys]
            if servoKey in k[0]: servoKeepTurning(servo, name, 1)    # 왼쪽으로 계속
            if servoKey in k[1]: servoKeepTurning(servo, name, -1)   # 오른쪽으로 계속
            if servoKey in k[2]: servoTurn(servo, name, 1)           # 왼쪽으로 SERVO_STEP 도
            if servoKey in k[3]: servoTurn(servo, name, -1)          # 오른쪽으로 SERVO_STEP 도
            if servoKey in k[4]: servoStop(servo, name)              # 정지
        if servoKey in (ord('0'), 0xB0):                     # 서보모터 1, 2 모두 정지
            servoStop(servo1, SERVO1_NAME)
            servoStop(servo2, SERVO2_NAME)
        if servoKey in SERVO_MANUAL_KEYS:                     # 수동 조작이 자동 조준보다 먼저 (AIM-06)
            aimer.pause(SETTINGS['MANUAL_OVERRIDE_SEC'])
        # 설정 GUI, 조회 서버에 보여 줄 상태 ------------------------------------------------------
        if startCycle - statusTime >= STATUS_PERIOD:
            statusTime = startCycle
            STATUS.update(state='자율주행' if autoRun else ('수동 주행' if (mL or mR) else '정지'),
                          detect_on=DETECT_ON, person=personSeen, animal=animalSeen,
                          detect_error=str(detector.error) if detector is not None and detector.error else None,
                          tilt=servoAngle[SERVO1_NAME], pan=servoAngle[SERVO2_NAME], aim_auto=SETTINGS['AIM_AUTO'],
                          stimulus=stimulus.kind, last_command=lastCommand, detect_ok=detectOk,
                          allow_without_detect=SETTINGS['ALLOW_WITHOUT_DETECT'],
                          server_port=SETTINGS['EVENT_SERVER_PORT'] if eventServer else None)
            try:
                control.writeStatus(STATUS)
            except OSError as e:
                print('[상태 오류] runtime/status.json 을 쓰지 못했습니다: %s' % e)
        endCycle = time.time()                                # 프레임 종료 시각
        timeCycle = int((endCycle - startCycle)*1000)         # 프레임 소요 시간
    #----------------------------------------------------------------------------------------
    if TOF_FLAG: 
        tof.stop_ranging()            # 거리센서 사용중이면 사용정지
    # 모터·서보·GPIO·카메라 정리는 __main__ 의 cleanup() 에서 합니다.
#============================================================================================
if __name__ == '__main__':

    print('\n')
    print('Python Version:     ', sys.version)
    print('OpenCV Version:     ', cv.__version__)
    print('Pytorch Version:    ', torch.__version__)
    print('\n')

    if len(sys.argv) >= 2:
        imageDir = sys.argv[1]        # Track Image 저장 디렉토리
    
    print('imageDir', imageDir)

    ################################################################
    # 사용자 이름
    username = os.getlogin()
    # Downloads 안에 있는 모델 *.pt 파일 리스트 생성
    file_listD = glob.glob(f'/home/{username}/{downLoads}/_{imageDir}_*.pt')
    current_directory = os.getcwd()  # 현재 작업 디렉토리
    # 프로젝트 디렉토리에 있는 모델 *.pt 파일 리스트 생성
    file_listC = glob.glob(os.path.join(current_directory,f'{imageDir}/_{imageDir}_*.pt'))
    # Downloads 디렉토리의 파일과 프로젝트 디렉토리 내의 화일을 병합
    file_list = file_listD + file_listC
    # 파일의 수정 시간을 가져와서 (파일 경로, 수정 시간) 형태로 저장
    file_times = [(file, os.path.getmtime(file)) for file in file_list]
    # 수정 시간을 기준으로 파일을 정렬 - 최근 만들어진 파일이 마지막에 오도록 정열한다.
    sorted_files = sorted(file_times, key=lambda x: x[1], reverse=False)
    # 파일을 LCD 에 디스프레이 한다. ------------------------------------------------------------
    def listingFile(sorted_files, startN, count, cline):
        viewWin[:,:] = BLACK
        i = 0
        while count:
            color = GRAY
            if i == cline:
                color = YELLOW
            cv.putText(viewWin, f'{startN+1:2d}: {sorted_files[startN][0]}',(10,20+20*i),cv.FONT_HERSHEY_COMPLEX_SMALL,1,color)
            startN += 1
            count -= 1
            i += 1
        cv.imshow('Out', cv.resize(viewWin, (DISPLAY_X, DISPLAY_Y)))
    #----------------------------------------------------------------------------------------
    c = len(sorted_files)               # 전체 파일(프로젝트 디렉토리 + Downloads 디렉토리) 개수
    if c:
        maxRows = 15                    # 화면에 리스팅되는 최대 파일 개수 설정
        startN = 0
        cline = 0
        if c >= maxRows:
            startN = c - maxRows 
            count = maxRows
            cline = maxRows - 1
        else:
            startN = 0 
            count = c
            cline = c - 1

        while True:
            if c==1:                # 프로젝트 디렉토리 또는 Downloads 디렉토리에 1 개의 모델파일이 
                break               # 존재하면 즉시 실행한다.

            listingFile(sorted_files, startN, count, cline)
            keyBoard = cv.waitKey(0) & 0xFF                       # 1 mSec 시간 지연하고 키값 읽기 
            if keyBoard == 13:                                    # Enter Key
                break
            elif keyBoard == 82:                                  # Arrow Up(82)
                if c > startN+cline:
                    if cline > 0:
                        cline -= 1
                    else:
                        if startN > 0:
                            startN -= 1
            elif keyBoard == 84:                                  # Arrow Down(84)
                if c <= maxRows:                                  #
                    if (cline+1) < c:
                        cline += 1
                else:
                    if (cline+1) < maxRows:
                        cline += 1
                    elif startN+maxRows < c:
                        startN += 1

        modelFile = sorted_files[startN+cline][0]    # 선택한 모델파일
        model = NvidiaModel()
        model.load_state_dict(torch.load(modelFile, map_location=torch.device('cpu')))

        MODEL_FILE = True
        print('\n학습 모델 파일 ', modelFile, ' 을 읽었습니다.\n')
    else:
        print('\n학습 모델 파일 ', modelFile, ' 이 없습니다.\n')
        modelFile = 'Manual Mode'
    # YOLO 탐지 모델 (train_all.ipynb 가 만든 zip 을 풀면 <프로젝트>/ 안에 놓임) ----------------
    detector = None
    yoloDir = os.path.join(current_directory, imageDir)
    if yd.hasModels(yoloDir):
        try:
            detector = yd.Detector(yoloDir)
            print('[탐지] YOLO 모델을 읽었습니다:', yoloDir)
        except (ImportError, OSError, ValueError, RuntimeError) as e:
            print('[탐지 오류] YOLO 모델을 읽지 못했습니다 → 탐지 없이 주행만 합니다.')
            print('  원인: %s: %s' % (type(e).__name__, e))
            print('  확인: pip install ultralytics ncnn, 모델 폴더에 model.ncnn.param·bin 이 있는지')
    else:
        print('[탐지] %s 안에 %s, %s 폴더가 없어 탐지 없이 주행만 합니다.' % (yoloDir, yd.PERSON_DIR, yd.ANIMAL_DIR))
    # 실험 설정값 적용, 원격 조회 서버 ------------------------------------------------------------
    applySettings(SETTINGS)
    print('[설정] %s 를 읽었습니다 (settings_gui.py 로 바꾸면 바로 반영)' % cfg.SETTINGS_FILE)
    if SETTINGS['EVENT_SERVER_ON']:
        try:
            eventServer = event_server.start(eventLog, SETTINGS['EVENT_SERVER_PORT'], publicStatus)
        except OSError as e:
            print('[조회 서버 오류] 포트 %d 를 열지 못했습니다 → 서버 없이 주행: %s' % (SETTINGS['EVENT_SERVER_PORT'], e))
    # 트랙 윈도우 파일
    t = './'+imageDir+'/_'+imageDir+'_track.pickle'
    if os.path.exists(t):
        with open(t, 'rb') as f:
            d = pickle.load(f)
            WIN_XL = d[0]; WIN_XR = d[1]; WIN_YU = d[2]; WIN_YD = d[3]  # 800 x 480 스크린 모드
            if d[4]: 
                lightMode = 'AUTO'
            elif d[5]: 
                lightCar = 'ON'
        print('WIN_XL:',WIN_XL,'WIN_XR:',WIN_XR, 'WIN_YU:',WIN_YU,'WIN_YD:', WIN_YD)
        print('트랙 윈도우 파일', t, ' 을 읽었습니다.')
    else:
        print('트랙 윈도우 파일', t, ' 이 없습니다.')

    # 신호등 파라메터 읽기
    fn = './'+imageDir+'/_'+imageDir+'_TS.pickle'
    if os.path.exists(fn):
        with open(fn, 'rb') as fr:
            d = pickle.load(fr)

            TSWIN_XL = d[0];             # 카메라 영역 X 축 Left  0~640 
            TSWIN_YU = d[1];             # 카메라 영역 Y 축 Up    0~480 
            TSWIN_XR = d[2];             # 카메라 영역 X 축 Right 0~640 
            TSWIN_YD = d[3];             # 카메라 영역 Y 축 Down  0~480
            minRadius = d[4];            # 신호등 최소 반지름      >8
            maxRadius = d[5];            # 신호등 최대 반지름      <40
            lineLeadAngGREEN = d[6];     # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
            lineTailAngGREEN = d[7];     # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
            lineLeadAngRED = d[8];       # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
            lineTailAngRED = d[9];       # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
            saturationHalfGREEN = d[10]; # Green Saturation
            saturationHalfRED = d[11];   # Red Saturation
            HSV_valueGREEN = d[12];      # Green Value
            HSV_valueRED = d[13];        # Red Value
            THRESH_GREEN = d[14];        # Green Threshold
            THRESH_RED = d[15];          # Red Threshold

        HSV_hueLeadGREEN = int(lineLeadAngGREEN/2)  # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
        HSV_hueTailGREEN = int(lineTailAngGREEN/2)  # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
        HSV_hueLeadRED = int(lineLeadAngRED/2)      # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
        HSV_hueTailRED = int(lineTailAngRED/2)      # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
        HSV_saturationGREEN = saturationHalfGREEN*2 # HSV 색상 좌표계에서 Saturation(/256)
        HSV_saturationRED = saturationHalfRED*2     # HSV 색상 좌표계에서 Saturation(/256)

        print('\n신호등 데이터 파일을 읽었습니다.:', fn, '\n')
    else:
        print('\n신호등 데이터 파일이 없습니다.')
    try:
        main()                                         # 자율 주행 프로그램 실행
    except KeyboardInterrupt:
        print('\n[종료] Ctrl+C 로 프로그램을 중단했습니다.')
    except Exception as e:
        reportError(e)                                 # 오류 요약 + 상세 로그 출력
        cleanup()
        sys.exit(1)
    cleanup()                                          # 모터·서보·GPIO·카메라 정리

#############################################################################################

'''
    #----------------------------------------------------------------------------------------
    if len(sys.argv) >= 2:
        t = sys.argv[1]         # 이미지 저장 디렉토리
        DIRECTORY_FLAG = True   # 디렉토리(프로젝트 이름)가 입력되었음 
        if not os.path.exists(t):
            print(f'이미지 저장 디렉터리 {t} 가 없습니다.')
            b = input('새로 생성 할까요? < Y: Yes>  <Any Key: No>')
            if b == 'y' or b == 'Y':
                os.mkdir(t)                # 디렉토리 생성 Sudo 모드로 생성
                # 생성한 디렉토리가 root 이므로 사용자 계정 pi 로 전환한다.
                # log in 사용자 계정을 가져온다.
                current_user = os.getlogin()
                user_name = current_user
                group_name = current_user
                # 사용자의 UID 가져오기
                uid = pwd.getpwnam(user_name).pw_uid
                # 그룹의 GID 가져오기
                gid = pwd.getpwnam(group_name).pw_gid
                # 파일의 소유자 변경
                os.chown(t, uid, gid)

                imageDir = t
            else:
                DIRECTORY_FLAG = False
        else:
            imageDir = t

    fn = './'+imageDir+'/_'+imageDir+'_TS.pickle'
    if DIRECTORY_FLAG and os.path.exists(fn):
        with open(fn, 'rb') as fr:
            d = pickle.load(fr)

            TSWIN_XL = d[0];             # 카메라 영역 X 축 Left  0~640 
            TSWIN_YU = d[1];             # 카메라 영역 Y 축 Up    0~480 
            TSWIN_XR = d[2];             # 카메라 영역 X 축 Right 0~640 
            TSWIN_YD = d[3];             # 카메라 영역 Y 축 Down  0~480
            minRadius = d[4];            # 신호등 최소 반지름      >8
            maxRadius = d[5];            # 신호등 최대 반지름      <40
            lineLeadAngGREEN = d[6];     # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
            lineTailAngGREEN = d[7];     # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
            lineLeadAngRED = d[8];       # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
            lineTailAngRED = d[9];       # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
            saturationHalfGREEN = d[10]; # Green Saturation
            saturationHalfRED = d[11];   # Red Saturation
            HSV_valueGREEN = d[12];      # Green Value
            HSV_valueRED = d[13];        # Red Value
            THRESH_GREEN = d[14];        # Green Threshold
            THRESH_RED = d[15];          # Red Threshold

        HSV_hueLeadGREEN = int(lineLeadAngGREEN/2)  # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
        HSV_hueTailGREEN = int(lineTailAngGREEN/2)  # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
        HSV_hueLeadRED = int(lineLeadAngRED/2)      # HSV 색상 좌표계에서 시작(Lead) 라인 각도(/180)
        HSV_hueTailRED = int(lineTailAngRED/2)      # HSV 색상 좌표계에서 종료(Tail) 라인 각도(/180)
        HSV_saturationGREEN = saturationHalfGREEN*2 # HSV 색상 좌표계에서 Saturation(/256)
        HSV_saturationRED = saturationHalfRED*2     # HSV 색상 좌표계에서 Saturation(/256)

        print('\n신호등 데이터 파일을 읽었습니다.:', fn, '\n')



'''
