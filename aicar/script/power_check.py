#############################################################################################
#
# power_check.py : Raspberry Pi 전원(전압 부족) 상태 확인
#
#   `vcgencmd get_throttled` 로 Raspberry Pi 본체의 전압 부족·속도 제한 상태를 읽어
#   상태가 바뀔 때만 터미널에 경고를 출력합니다.
#
#   주의: Raspberry Pi 본체 전압만 확인합니다. 서보모터에 전원·GND 가 연결되지 않은 것은
#         서보모터가 신호를 돌려주지 않으므로 소프트웨어로 감지할 수 없습니다.
#
#############################################################################################
import subprocess

# get_throttled 비트 → (출력 메시지)
POWER_FLAGS = [
    (0x1,     '[전원 경고] 지금 Raspberry Pi 전압이 부족합니다 (약 4.63V 미만).'),
    (0x4,     '[전원 경고] 지금 전압 부족 또는 과열로 CPU 속도가 제한되고 있습니다.'),
    (0x10000, '[전원 경고] 부팅 이후 전압 부족이 발생한 적이 있습니다.'),
]
POWER_HINT = ('            → 서보모터를 Raspberry Pi 5V 대신 외부 5V 전원(GND 공통)으로 연결하거나 '
              '충분한 용량(5V 3A 이상)의 전원을 사용하세요.')

_NOT_CHECKED = object()        # 아직 한 번도 확인하지 않은 상태
_lastFlags = _NOT_CHECKED      # 마지막으로 출력한 상태 (같은 상태는 반복 출력하지 않음)

def readThrottled():
    '''get_throttled 값을 정수로 반환합니다. 읽을 수 없으면 None 을 반환합니다.'''
    try:
        out = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True,
                             text=True, timeout=1).stdout          # 예: throttled=0x50005
        return int(out.strip().split('=')[1], 16)
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return None

def checkPower(when=''):
    '''
    전원 상태를 확인하고, 이전과 달라졌을 때만 결과를 출력합니다.
    when 은 출력에 붙는 시점 설명입니다 (예: '시작', '서보 이동 후').
    '''
    global _lastFlags
    flags = readThrottled()
    if flags == _lastFlags:
        return
    _lastFlags = flags
    tag = ' (%s)' % when if when else ''
    if flags is None:
        print('[전원] 전압 상태를 읽을 수 없습니다 (vcgencmd get_throttled 실패)%s' % tag)
        return
    messages = [msg for bit, msg in POWER_FLAGS if flags & bit]
    if not messages:
        print('[전원] 정상 (전압 부족 기록 없음)%s' % tag)
        return
    for msg in messages:
        print(msg + tag)
    print(POWER_HINT)
