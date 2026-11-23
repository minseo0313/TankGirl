#############################################################################################
#
# <control.py>  설정 GUI ↔ ar.py 실험 명령과 상태 (IF-12)
#
# 서보 핀은 ar.py 가 잡고 있으므로 GUI 는 직접 움직이지 않고 runtime/control.json 에 명령을 씁니다.
# ar.py 는 프레임마다 새 명령이 있는지 보고 실행한 뒤, 1초마다 runtime/status.json 에 상태를 씁니다.
#
# 자체 점검: python3 control.py
#
#############################################################################################
import time
from settings import RUNTIME_DIR, readJson, writeJsonAtomic

CONTROL_FILE = RUNTIME_DIR / 'control.json'
STATUS_FILE = RUNTIME_DIR / 'status.json'
COMMAND_MAX_AGE_SEC = 5.0     # 이보다 오래된 명령은 실행하지 않음 (ar.py 를 늦게 켰을 때 옛 명령 방지)
STATUS_ALIVE_SEC = 3.0        # 상태가 이보다 오래되면 GUI 는 ar.py 가 꺼진 것으로 봄

# 명령: 필요한 인자
COMMANDS = {
    'aim_center': (),
    'aim_angle': ('tilt', 'pan'),
    'aim_point': ('x', 'y'),
    'aim_hold': (),
    'stim_start': ('kind',),
    'stim_stop': (),
    'log_test': ('result',),
    'scenario_start': ('id',),           # 시나리오 시험: 정해진 순서대로 실행 (scenario.py)
    'scenario_stop': (),
}

def send(cmd, path=CONTROL_FILE, **args):
    '''GUI 에서 부릅니다. 명령 번호를 돌려줍니다.'''
    if cmd not in COMMANDS:
        raise ValueError('모르는 명령: %s' % cmd)
    missing = [a for a in COMMANDS[cmd] if a not in args]
    if missing:
        raise ValueError('%s 에 필요한 값: %s' % (cmd, ', '.join(missing)))
    cid = int(time.time() * 1000)
    writeJsonAtomic(path, {'id': cid, 'cmd': cmd, 'args': args, 'time': time.time()})
    return cid

class CommandReader:
    '''ar.py 에서 프레임마다 poll(). 새 명령이 있으면 dict, 없으면 None.'''
    def __init__(self, path=CONTROL_FILE):
        self.path = path
        old = readJson(path) or {}
        self.lastId = old.get('id')           # 시작 전에 있던 명령은 실행하지 않음
        self.mtime = self._mtime()

    def _mtime(self):
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def poll(self, now=None):
        m = self._mtime()
        if m == self.mtime:
            return None
        self.mtime = m
        c = readJson(self.path)
        now = time.time() if now is None else now
        if not isinstance(c, dict) or c.get('id') == self.lastId or c.get('cmd') not in COMMANDS:
            return None                       # 손으로 고쳐 형식이 틀린 파일은 무시 (메인 루프를 멈추지 않게)
        self.lastId = c.get('id')
        try:
            age = now - float(c.get('time', 0))
        except (TypeError, ValueError):
            return None
        if age > COMMAND_MAX_AGE_SEC or not isinstance(c.get('args', {}), dict):
            return None
        return c

def writeStatus(status, path=STATUS_FILE):
    writeJsonAtomic(path, dict(status, time=time.time()))

def readStatus(path=STATUS_FILE, now=None):
    '''(상태 dict 또는 None, ar.py 가 살아 있나).'''
    s = readJson(path)
    now = time.time() if now is None else now
    return s, bool(s) and now - float(s.get('time', 0)) < STATUS_ALIVE_SEC

if __name__ == '__main__':
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as t:
        cf, sf = Path(t) / 'control.json', Path(t) / 'status.json'
        send('aim_center', path=cf)                       # ar.py 를 켜기 전에 보낸 명령
        r = CommandReader(cf)
        assert r.poll() is None                           # 무시
        time.sleep(0.01)
        send('aim_angle', path=cf, tilt=80, pan=100)
        c = r.poll()
        assert c['cmd'] == 'aim_angle' and c['args'] == {'tilt': 80, 'pan': 100}
        assert r.poll() is None                           # 같은 명령은 한 번만
        for broken in ([1], {'id': 9, 'cmd': 'aim_hold', 'time': 'x'}, {'id': 10, 'cmd': 'aim_hold', 'time': time.time(), 'args': [1]}):
            time.sleep(0.01)
            writeJsonAtomic(cf, broken)
            assert r.poll() is None                       # 깨진 형식은 예외 없이 무시
        for bad in (lambda: send('rm', path=cf), lambda: send('aim_angle', path=cf, tilt=1)):
            try:
                bad()
                raise AssertionError('통과하면 안 됨')
            except ValueError:
                pass
        assert readStatus(sf) == (None, False)
        writeStatus({'state': '정지'}, path=sf)
        assert readStatus(sf)[1] and not readStatus(sf, now=time.time() + 10)[1]
    print('control 자체 점검 통과')
