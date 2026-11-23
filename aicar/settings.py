#############################################################################################
#
# <settings.py>  실험으로 바꾸는 설정값 한 곳
#
# 기본값은 docs/business-rules/parameters.md 의 초기값입니다.
# settings_gui.py 가 runtime/settings.json 에 저장하면, 실행 중인 ar.py 가 프레임마다 확인해 바로 반영합니다.
# runtime/ 은 실험 기록이라 git 에 넣지 않습니다 (.gitignore 의 aicar/*/).
#
# 자체 점검: python3 settings.py
#
#############################################################################################
import json
import math
import os
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / 'runtime'
SETTINGS_FILE = RUNTIME_DIR / 'settings.json'
RELOAD_CHECK_SEC = 0.5          # 설정 파일이 바뀌었는지 확인하는 간격

def P(key, default, group, label, lo=None, hi=None, choices=None, rule='', restart=False, origin=False,
      adv=False, names=None):
    '''설정 항목 하나.
    lo~hi 숫자 범위, choices 고를 수 있는 값, names 는 choices 를 GUI 에 보여 줄 이름 (예: 1 → '그대로'),
    restart 는 ar.py 재시작이 필요한 항목, origin 은 원본 aicar 에 처음부터 있던 값 (GUI 에 ★ 표시),
    adv 는 거의 안 바꾸는 값 (GUI 에서 "고급 설정 보기"를 켜야 보임).'''
    return {'key': key, 'default': default, 'group': group, 'label': label, 'lo': lo, 'hi': hi,
            'choices': choices, 'names': names, 'rule': rule, 'restart': restart, 'origin': origin, 'adv': adv}

DIRECTION = {1: '그대로', -1: '반대로'}

SCHEMA = [
    P('RUN_SPEED', 70, '주행', '자율주행 속도 (PWM, 클수록 빠름)', 0, 100, rule='DRV-01', origin=True),
    P('ANGLE_GAIN', 0.8, '주행', '조향 세기 (클수록 많이 꺾음)', 0.1, 3.0, rule='DRV-01', origin=True),
    P('HORN_DISTANCE', 350, '안전', '경적 거리 (mm)', 50, 2000, rule='SAFE-01', origin=True),
    P('STOP_DISTANCE', 110, '안전', '정지 거리 (mm), 목표 200', 30, 1000, rule='SAFE-02', origin=True),
    P('ALLOW_WITHOUT_DETECT', False, '안전', '탐지가 꺼져도 자극, 서보 실험 허용 (사람 확인 안 됨, 시험용)', rule='SAFE-08'),
    P('DETECT_CONF', 0.25, '탐지', '탐지 기준 (클수록 확실한 것만)', 0.05, 0.95, rule='DET-01'),
    P('DETECT_HOLD_SEC', 1.0, '탐지', '마지막으로 본 뒤 "있음" 유지 시간 (초)', 0.1, 5.0, rule='DET-01', adv=True),
    P('AIM_AUTO', False, '서보 조준', '동물 쪽으로 자동 조준 (차가 멈춰 있을 때만)', rule='AIM-02'),
    P('AIM_CAMERA_ON_SERVO', False, '서보 조준', '카메라를 서보에 달았음', rule='AIM-02'),
    P('SERVO_LEFT', 1, '서보 조준', '좌우 서보(2번) 방향 (반대로 돌면 바꾸기)', choices=(1, -1), names=DIRECTION, rule='AIM-01'),
    P('SERVO_UP', 1, '서보 조준', '위아래 서보(1번) 방향 (반대로 돌면 바꾸기)', choices=(1, -1), names=DIRECTION, rule='AIM-02'),
    P('AIM_MAX_STEP_DEG', 10, '서보 조준', '자동 조준 속도 (한 번에 도는 각도, 클수록 빠름)', 1, 90, rule='AIM-02'),
    P('SERVO_SWEEP_STEP', 2, '서보 조준', '키보드 "계속" 속도 (화면 1장마다 각도, 클수록 빠름)', 1, 20, rule='AIM-01'),
    P('SERVO_STEP', 10, '서보 조준', '키보드 한 번 누를 때 각도', 1, 90, rule='AIM-01', adv=True),
    P('SERVO_CENTER', 90, '서보 조준', '정면 각도 (도)', 0, 180, rule='AIM-05', adv=True),
    P('AIM_TILT_MIN', 60, '서보 조준', '위아래 최소 각도 (차체에 안 닿게)', 0, 180, rule='AIM-03', adv=True),
    P('AIM_TILT_MAX', 120, '서보 조준', '위아래 최대 각도 (차체에 안 닿게)', 0, 180, rule='AIM-03', adv=True),
    P('AIM_PAN_MIN', 0, '서보 조준', '좌우 최소 각도', 0, 180, rule='AIM-03', adv=True),
    P('AIM_PAN_MAX', 180, '서보 조준', '좌우 최대 각도', 0, 180, rule='AIM-03', adv=True),
    P('CAM_HFOV_DEG', 53.5, '서보 조준', '카메라 가로 화각 (도, 실측값)', 10.0, 180.0, rule='AIM-02', adv=True),
    P('CAM_VFOV_DEG', 41.4, '서보 조준', '카메라 세로 화각 (도, 실측값)', 10.0, 180.0, rule='AIM-02', adv=True),
    P('AIM_DEADBAND_PX', 40, '서보 조준', '떨림 방지: 가운데에서 이 픽셀 안이면 안 움직임', 0, 320, rule='AIM-02', adv=True),
    P('AIM_INTERVAL_SEC', 0.3, '서보 조준', '자동 조준 간격 (초)', 0.05, 5.0, rule='AIM-02', adv=True),
    P('SERVO_HOLD_SEC', 1.5, '서보 조준', '떨림 방지: 이동 뒤 힘 푸는 시간 (초)', 0.3, 5.0, rule='AIM-01', adv=True),
    P('MANUAL_OVERRIDE_SEC', 5.0, '서보 조준', '키보드 조작 뒤 자동 조준 쉬는 시간 (초)', 0.0, 60.0, rule='AIM-06', adv=True),
    P('STIMULUS_SEC', 3.0, '자극', '자극 시간 (초)', 0.5, 30.0, rule='STIM-02'),
    P('SOUND_A_FILE', 'sounds/sound_a.wav', '자극', '음향 A 파일 (aicar/ 기준)', rule='STIM-01'),
    P('SOUND_B_FILE', 'sounds/sound_b.wav', '자극', '음향 B 파일 (aicar/ 기준)', rule='STIM-01'),
    # 다른 장치, 시리얼 콘솔(14, 15), SPI, HAT EEPROM 핀을 피한 빈 핀만 허용
    P('LED_PIN', 0, '자극', '기피 LED 핀 (BCM)', choices=(0, 4, 16, 19, 22),
      names={0: '사용 안 함', 4: '4', 16: '16', 19: '19', 22: '22'}, rule='STIM-01'),
    P('SOUND_PLAYER', 'aplay', '자극', '소리 재생 프로그램', choices=('aplay', 'paplay', 'mpg123'), rule='STIM-02', adv=True),
    P('LED_BLINK_SEC', 0.2, '자극', 'LED 깜빡임 간격 (초)', 0.05, 2.0, rule='STIM-01', adv=True),
    P('EVENT_SERVER_ON', False, '기록', '원격 조회 서버 켜기', rule='LOG-02', restart=True),
    P('EVENT_SERVER_PORT', 8000, '기록', '원격 조회 서버 포트', 1024, 65535, rule='LOG-02', restart=True, adv=True),
]
BY_KEY = {p['key']: p for p in SCHEMA}
RANGE_PAIRS = (('AIM_PAN_MIN', 'AIM_PAN_MAX'), ('AIM_TILT_MIN', 'AIM_TILT_MAX'))

def defaults():
    return {p['key']: p['default'] for p in SCHEMA}

def coerce(key, value):
    '''value 를 key 의 형식으로 바꾸고 범위를 확인합니다. 맞지 않으면 ValueError (GUI 에 그대로 보여 줄 문장).'''
    p = BY_KEY[key]
    d = p['default']
    try:
        if isinstance(d, bool):
            if isinstance(value, str):
                value = value.strip().lower() in ('1', 'true', 'yes', 'on')
            v = bool(value)
        elif isinstance(d, int):
            v = int(float(value)) if not isinstance(value, bool) else int(value)
        elif isinstance(d, float):
            v = float(value)
        else:
            v = str(value).strip()
    except (TypeError, ValueError, OverflowError):        # OverflowError: int(float('inf'))
        raise ValueError('%s: 숫자가 아닙니다 (%r)' % (p['label'], value))
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError('%s: 숫자가 아닙니다 (%r)' % (p['label'], value))
    if p['choices'] is not None and v not in p['choices']:
        raise ValueError('%s: %s 중 하나여야 합니다' % (p['label'], ', '.join(map(str, p['choices']))))
    if p['lo'] is not None and not (p['lo'] <= v <= p['hi']):
        raise ValueError('%s: %s ~ %s 사이여야 합니다' % (p['label'], p['lo'], p['hi']))
    if isinstance(d, str) and not isinstance(d, bool) and not v:
        raise ValueError('%s: 비어 있습니다' % p['label'])
    return v

def validate(values):
    '''전체 값을 확인해 새 dict 를 돌려줍니다. 하나라도 틀리면 ValueError.'''
    out = {key: coerce(key, values.get(key, BY_KEY[key]['default'])) for key in BY_KEY}
    for lo, hi in RANGE_PAIRS:
        if out[lo] >= out[hi]:
            raise ValueError('%s 는 %s 보다 작아야 합니다' % (BY_KEY[lo]['label'], BY_KEY[hi]['label']))
    # ar.py 는 경적 거리 안에서만 정지 거리를 확인하므로, 정지 거리가 더 크면 정지가 늦어짐 (SAFE-01, SAFE-02)
    if out['STOP_DISTANCE'] >= out['HORN_DISTANCE']:
        raise ValueError('정지 거리는 경적 거리보다 작아야 합니다')
    return out

def sudoUser():
    '''sudo 로 실행 중이면 원래 사용자의 (uid, gid), 아니면 None.'''
    if not hasattr(os, 'geteuid') or os.geteuid() != 0:
        return None
    try:
        return int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID'])
    except (KeyError, ValueError):
        return None

def writeJsonAtomic(path, data):
    '''읽는 쪽이 반쯤 쓴 파일을 보지 않도록 임시 파일에 쓴 뒤 바꿔 넣습니다.
    ar.py 는 sudo(root)로, settings_gui.py 는 일반 사용자로 실행하므로, root 가 쓴 폴더와 파일은
    원래 사용자 소유로 돌려 둡니다 (안 그러면 GUI 가 status.json 을 못 읽고 control.json 을 못 씀).'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = sudoUser()
    if owner:
        os.chown(str(path.parent), *owner)          # 예전에 root 로 만든 runtime/ 도 여기서 바로잡힘
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if owner:
            os.chown(tmp, *owner)
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

def readJson(path):
    '''JSON 파일을 읽습니다. 없거나 깨졌으면 None.'''
    try:
        with open(str(path), encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        print('[설정 오류] %s 를 읽지 못했습니다: %s' % (path, e))
        return None

def load(path=SETTINGS_FILE):
    '''저장된 설정을 읽습니다. 파일이 없으면 기본값, 틀린 항목은 그 항목만 기본값으로 쓰고 알립니다.'''
    saved = readJson(path) or {}
    out = defaults()
    for key in BY_KEY:
        if key in saved:
            try:
                out[key] = coerce(key, saved[key])
            except ValueError as e:
                print('[설정 오류] %s → 기본값 %r 사용' % (e, out[key]))
    try:
        return validate(out)
    except ValueError as e:
        print('[설정 오류] %s → 전체 기본값 사용' % e)
        return defaults()

def save(values, path=SETTINGS_FILE):
    '''확인한 뒤 저장합니다. 틀리면 저장하지 않고 ValueError.'''
    v = validate(values)
    writeJsonAtomic(path, v)
    return v

class Watcher:
    '''설정 파일이 바뀌었는지 RELOAD_CHECK_SEC 마다 확인합니다. ar.py 메인 루프에서 프레임마다 poll().'''
    def __init__(self, path=SETTINGS_FILE):
        self.path = Path(path)
        self.mtime = self._mtime()
        self.checked = 0.0

    def _mtime(self):
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def poll(self, now=None):
        '''바뀌었으면 새 설정 dict, 아니면 None.'''
        now = time.time() if now is None else now
        if now - self.checked < RELOAD_CHECK_SEC:
            return None
        self.checked = now
        m = self._mtime()
        if m == self.mtime:
            return None
        self.mtime = m
        return load(self.path)

if __name__ == '__main__':
    d = defaults()
    assert validate(d) == d
    assert coerce('RUN_SPEED', '75') == 75 and coerce('AIM_AUTO', 'true') is True
    for key, bad in (('RUN_SPEED', 101), ('SERVO_LEFT', 0), ('SOUND_PLAYER', 'rm'), ('RUN_SPEED', 'abc'),
                     ('RUN_SPEED', float('inf')), ('ANGLE_GAIN', float('nan')), ('LED_PIN', 14)):
        try:
            coerce(key, bad)
            raise AssertionError('통과하면 안 됨: %s=%r' % (key, bad))
        except ValueError:
            pass
    for bad in (dict(d, AIM_TILT_MIN=130), dict(d, STOP_DISTANCE=1000, HORN_DISTANCE=50)):
        try:
            validate(bad)
            raise AssertionError('통과하면 안 됨 (최소 >= 최대, 정지 >= 경적)')
        except ValueError:
            pass
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'settings.json'
        assert load(f) == d                                     # 파일 없음 → 기본값
        w = Watcher(f)
        save(dict(d, RUN_SPEED=80), f)
        assert w.poll(now=time.time() + 1)['RUN_SPEED'] == 80   # 바뀜 → 새 값
        assert w.poll(now=time.time() + 2) is None              # 그대로 → None
        writeJsonAtomic(f, dict(d, RUN_SPEED=999))
        assert load(f)['RUN_SPEED'] == 70                       # 틀린 항목만 기본값
    # sudo 로 실행하면 runtime 파일을 원래 사용자 소유로 (root 가 아닐 때는 건드리지 않음)
    import unittest.mock as mock
    with tempfile.TemporaryDirectory() as t, mock.patch('os.geteuid', return_value=0, create=True), \
            mock.patch.dict(os.environ, {'SUDO_UID': '1000', 'SUDO_GID': '1000'}), mock.patch('os.chown') as chown:
        writeJsonAtomic(Path(t) / 'runtime' / 'status.json', {'a': 1})
        owners = {c.args[1:] for c in chown.call_args_list}
        assert chown.call_count == 2 and owners == {(1000, 1000)}          # 폴더와 파일
    with tempfile.TemporaryDirectory() as t, mock.patch('os.geteuid', return_value=1000, create=True), \
            mock.patch('os.chown') as chown:
        writeJsonAtomic(Path(t) / 'x.json', {})
        assert chown.call_count == 0
    print('settings 자체 점검 통과')
