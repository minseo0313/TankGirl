#############################################################################################
#
# <stimulus.py>  기피 자극 출력 (IF-09, 규칙 STIM-01 ~ STIM-02, SAFE-06)
#
# 종류: sound_a (음향 A), sound_b (음향 B), sound_led (음향 A + LED 깜빡임), led (LED 깜빡임만, 소리 없음)
# 소리는 SOUND_PLAYER(aplay 등)로 파일을 재생하고, sec 초가 지나면 스스로 끕니다.
# 소리 파일이 sec 보다 짧으면 파일 길이만큼만 납니다.
# 장애물 경고 경적(부저, GPIO 23)은 자극이 아니므로 여기서 다루지 않습니다.
#
# 자체 점검: python3 stimulus.py  (소리, LED 없이 흐름만 확인)
#
#############################################################################################
import subprocess
import threading
from pathlib import Path

KINDS = ('sound_a', 'sound_b', 'sound_led', 'led')
# 다른 장치가 쓰는 핀 (README GPIO 표, 서보 17·27, I²C 2·3). 18·10 은 NEOPIXEL.py 설정을 확인하기 전이라 막아 둠
RESERVED_PINS = {2, 3, 5, 6, 10, 12, 13, 17, 18, 20, 21, 23, 24, 25, 26, 27}

def makeLed(pin):
    from gpiozero import LED                # Pi 에서만 있는 라이브러리라 쓸 때 불러옵니다
    return LED(pin)

class Stimulus:
    def __init__(self, baseDir, popen=subprocess.Popen, ledFactory=makeLed):
        self.baseDir = Path(baseDir)
        self.popen = popen
        self.ledFactory = ledFactory
        self.lock = threading.Lock()
        self.proc = None
        self.timer = None
        self.led = None
        self.ledPin = 0
        self.kind = None

    def _soundPath(self, kind, s):
        '''aicar/sounds/ 안의 파일만. 밖을 가리키면 None.'''
        name = s['SOUND_B_FILE'] if kind == 'sound_b' else s['SOUND_A_FILE']
        p = (self.baseDir / name).resolve()
        return p if (self.baseDir / 'sounds').resolve() in p.parents else None

    def _getLed(self, pin):
        if pin in RESERVED_PINS:
            print('[자극 오류] LED 핀 %d 은 다른 장치가 씁니다 → LED 없이 소리만' % pin)
            return None
        if self.led is not None and self.ledPin != pin:
            self.led.close()
            self.led = None
        if self.led is None:
            try:
                self.led = self.ledFactory(pin)
                self.ledPin = pin
            except Exception as e:           # gpiozero 가 없거나 핀을 못 열면 소리만 냅니다
                print('[자극 오류] LED(핀 %d)를 열지 못했습니다: %s: %s' % (pin, type(e).__name__, e))
                self.led = None
        return self.led

    def start(self, kind, sec, s):
        '''자극을 켭니다. 바로 돌아오고 sec 초 뒤 스스로 꺼집니다. 못 켜면 False 와 이유를 출력.'''
        if kind not in KINDS:
            print('[자극 오류] 모르는 종류: %r (%s 중 하나)' % (kind, ', '.join(KINDS)))
            return False
        self.stop()
        if kind == 'led':
            return self._startLedOnly(sec, s)
        path = self._soundPath(kind, s)
        if path is None:
            print('[자극 오류] 소리 파일은 aicar/sounds/ 안에 두어야 합니다 (설정 SOUND_A_FILE / SOUND_B_FILE)')
            return False
        if not path.is_file():
            print('[자극 오류] 소리 파일이 없습니다: %s (설정 SOUND_A_FILE / SOUND_B_FILE)' % path)
            return False
        with self.lock:
            try:
                self.proc = self.popen([s['SOUND_PLAYER'], str(path)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError as e:
                print('[자극 오류] %s 를 실행하지 못했습니다: %s' % (s['SOUND_PLAYER'], e))
                self.proc = None
                return False
            if kind == 'sound_led' and s['LED_PIN']:
                led = self._getLed(s['LED_PIN'])
                if led is not None:
                    led.blink(on_time=s['LED_BLINK_SEC'], off_time=s['LED_BLINK_SEC'])
            self.kind = kind
            self.timer = threading.Timer(sec, self.stop)
            self.timer.daemon = True
            self.timer.start()
        print('[자극] %s %.1f초' % (kind, sec))
        return True

    def _startLedOnly(self, sec, s):
        '''LED 만 sec 초 깜빡입니다. LED_PIN 이 '사용 안 함'이거나 LED 를 못 열면 False.'''
        if not s['LED_PIN']:
            print('[자극 오류] LED 핀이 "사용 안 함"입니다 (설정 GUI 자극 탭 LED_PIN)')
            return False
        with self.lock:
            led = self._getLed(s['LED_PIN'])
            if led is None:
                return False
            led.blink(on_time=s['LED_BLINK_SEC'], off_time=s['LED_BLINK_SEC'])
            self.kind = 'led'
            self.timer = threading.Timer(sec, self.stop)
            self.timer.daemon = True
            self.timer.start()
        print('[자극] led %.1f초' % sec)
        return True

    def stop(self):
        '''즉시 끕니다. 끄는 함수가 멈추면 안 되므로 오류는 출력만 합니다.'''
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            wasOn = self.kind is not None
            self.kind = None
            if self.proc is not None:
                try:
                    if self.proc.poll() is None:
                        self.proc.terminate()
                except OSError as e:
                    print('[자극 오류] 소리 끄기 실패: %s' % e)
                self.proc = None
            if self.led is not None:
                try:
                    self.led.off()
                except Exception as e:
                    print('[자극 오류] LED 끄기 실패: %s: %s' % (type(e).__name__, e))
        if wasOn:
            print('[자극] 끔')

    def active(self):
        with self.lock:
            return self.kind is not None

    def close(self):
        '''종료할 때. gpiozero 핀 해제(ar.py closePinFactory)보다 먼저 부릅니다.'''
        self.stop()
        if self.led is not None:
            self.led.close()
            self.led = None

if __name__ == '__main__':
    import tempfile
    import time
    import settings

    class FakeProc:
        def __init__(self): self.terminated = False
        def poll(self): return None
        def terminate(self): self.terminated = True

    class FakeLed:
        def __init__(self, pin): self.pin, self.state = pin, 'off'
        def blink(self, on_time, off_time): self.state = 'blink'
        def off(self): self.state = 'off'
        def close(self): self.state = 'closed'

    procs, leds = [], []
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / 'sounds').mkdir()
        (Path(t) / 'sounds' / 'a.wav').write_bytes(b'RIFF')
        (Path(t) / 'outside.wav').write_bytes(b'RIFF')
        s = dict(settings.defaults(), SOUND_A_FILE='sounds/a.wav', SOUND_B_FILE='sounds/none.wav', LED_PIN=16)
        st = Stimulus(t, popen=lambda *a, **k: procs.append(FakeProc()) or procs[-1],
                      ledFactory=lambda pin: leds.append(FakeLed(pin)) or leds[-1])
        assert st.start('nope', 1, s) is False                 # 모르는 종류
        assert st.start('sound_b', 1, s) is False              # 파일 없음
        assert st.start('sound_a', 1, dict(s, SOUND_A_FILE='outside.wav')) is False      # sounds/ 밖
        assert st.start('sound_a', 1, dict(s, SOUND_A_FILE='sounds/../outside.wav')) is False
        assert st.start('sound_led', 0.2, s) and st.active() and leds[0].state == 'blink'
        st.stop()
        assert not st.active() and procs[0].terminated and leds[0].state == 'off'
        assert st.start('sound_a', 0.1, s)
        time.sleep(0.3)
        assert not st.active() and procs[1].terminated         # 시간이 지나면 스스로 꺼짐
        st.start('sound_led', 1, dict(s, LED_PIN=23))          # 부저 핀 → LED 없이 소리만
        assert len(leds) == 1
        n = len(procs)
        assert st.start('led', 0.1, s) and st.active() and leds[0].state == 'blink' and len(procs) == n   # 소리 없이 LED 만
        time.sleep(0.3)
        assert not st.active() and leds[0].state == 'off'      # 시간이 지나면 LED 도 꺼짐
        assert st.start('led', 1, dict(s, LED_PIN=0)) is False  # LED 핀 사용 안 함
        st.close()
        assert leds[0].state == 'closed'
    print('stimulus 자체 점검 통과')
