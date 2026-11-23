#############################################################################################
#
# <scenario.py>  시나리오 시험: 시퀀스를 이어서 정해진 순서대로 실행 (docs/scenarios/scenarios.md)
#
# 시나리오 = 시퀀스(큰 동작, 예: "동물을 탐지한다")를 순서대로 이은 것
# 시퀀스   = 세부 단계(예: "사진 찍기", "서보를 동물 쪽으로", "스피커: 빵 소리")의 목록
# 단계     = (설명, 동작, 다음 단계까지 기다리는 초). 설명의 {name} 은 시나리오 대상 이름으로 바뀝니다.
#
# 동작은 ar.py 가 실행합니다. None 이면 기다리기만 합니다 (탐지는 아직 AI 없이 "나타났다고 봄").
#   ('photo',)        지금 카메라 화면을 사진으로 잡아 둠 (기록할 때 이 사진을 씀)
#   ('aim',)          시나리오 대상 위치(x, y) 쪽으로 서보 조준
#   ('center',)       서보 가운데,  ('hold',) 서보 그 자리에서 멈춤
#   ('servo_to', 위아래, 좌우)  그 각도로 (도),  ('servo_by', 위아래, 좌우)  지금 각도에서 그만큼 더 (도, +/-)
#   ('sweep', 시작, 끝)  좌우 서보(2번)를 단계 시간 동안 시작 각도에서 끝 각도로 천천히 (한 번에 튀지 않게)
#                     둘 다 ar.py 가 설정의 서보 범위(AIM_TILT_MIN/MAX 등)로 잘라서 보냅니다
#   ('horn', on/off)  차의 부저 켜기/끄기 (ar.py [H] 경적과 같은 부저),  ('lamp', on/off) 전조등 켜기/끄기 ([L] 네오픽셀)
#   ('stim', kind)    자극 켜기 (sound_a 음향 A, sound_b 음향 B, sound_led 음향과 LED),  ('stim_stop',) 끄기
#   ('log', result)   기록 (left 이탈, stayed 잔류, unknown 관찰 불가, uncertain 불확실, person_stop 사람으로 중지)
# 실행 중 실제 탐지에 사람이 보이거나, 탐지가 멈추거나, [Space] / [중지] 를 누르면 ar.py 가 바로 멈춥니다.
#
# 새 시나리오를 만들려면 SEQUENCES 에서 골라 SCENARIOS 에 순서대로 적습니다.
# 시퀀스의 세부 단계는 설정 GUI "시퀀스 편집" 탭에서 고칠 수 있습니다 → runtime/sequences.json 에 저장.
# 파일이 있으면 아래 SEQUENCES(기본값) 대신 그 내용을 씁니다. ar.py 는 시나리오를 시작할 때마다 다시 읽습니다.
#
# 자체 점검: python3 scenario.py
#
#############################################################################################

from event_log import RESULTS
from settings import RUNTIME_DIR, readJson, writeJsonAtomic
from stimulus import KINDS

SEQ_FILE = RUNTIME_DIR / 'sequences.json'
MAX_STEP_SEC = 60                                          # 단계 하나가 기다리는 최대 시간
ANGLES = 'angles'                                          # 위아래, 좌우 각도 두 숫자를 받는 동작
ANGLE_RANGE = {'servo_to': (0, 180), 'servo_by': (-180, 180), 'sweep': (0, 180)}
ANGLE_LABELS = {'servo_to': ('위아래', '좌우'), 'servo_by': ('위아래', '좌우'), 'sweep': ('좌우 시작', '끝')}
# 고를 수 있는 동작: 이름 → (GUI 표시, 고를 값 / ANGLES / None)
ACTIONS = {'wait': ('기다리기', None), 'photo': ('사진 찍기', None), 'aim': ('대상 쪽으로 조준', None),
           'servo_to': ('서보 각도로', ANGLES), 'servo_by': ('서보 돌리기', ANGLES), 'sweep': ('서보 좌우로 쓸기', ANGLES),
           'center': ('서보 가운데', None), 'hold': ('서보 멈춤', None), 'stim': ('자극 켜기', KINDS),
           'stim_stop': ('자극 끄기', None), 'log': ('기록', RESULTS),
           'horn': ('부저 (경적)', ('on', 'off')), 'lamp': ('전조등 (LED)', ('on', 'off'))}

# 시퀀스: 이름 → (큰 동작, [세부 단계]) ------------------------------------------------------
# 쓰는 부품: 서보(카메라 방향), 스피커(빵 소리), LED. 바퀴는 시나리오 동안 세워 둠. 거리센서는 아직 안 씀
# 탐지는 아직 하지 않고 "동물이 있다"고 보고 기능을 규칙 순서대로 실행합니다.
SEQUENCES = {
    'scan':   ('서보를 돌리며 찾는다', [
        ('서보를 왼쪽으로', ('servo_to', 90, 45), 0.5),
        ('오른쪽으로 천천히 돌리기', ('sweep', 45, 120), 2)]),
    'found':  ('카메라에 잡힌다', [
        ('카메라에 {name}가 잡힘, 서보 멈춤', None, 0.3)]),
    'scare':  ('빵 소리와 LED 를 함께 켠다', [
        ('전조등 켜기', ('lamp', 'on'), 0),
        ('부저 빵', ('horn', 'on'), 0.5),
        ('부저 끄기', ('horn', 'off'), 2.5),
        ('전조등 끄기', ('lamp', 'off'), 0)]),
    'return': ('가운데로 돌아온다', [
        ('서보 가운데', ('center',), 1.5)]),
}

# 시나리오: 번호 → (제목, 대상, [시퀀스 순서]) ---------------------------------------------------
# 대상: name 표시 이름, species 기록 종류, x, y 화면 위치 (카메라 640x480, '대상 쪽으로 조준' 에서 씀), zone 구역
DEER = {'name': '노루', 'species': 'roe_deer', 'x': 480, 'y': 120, 'zone': 2}
SCENARIOS = {
    'S-02': ('서보로 찾고 빵 소리 + LED', DEER, ['scan', 'found', 'scare', 'return']),
}
# 그 밖의 시나리오(사람, 장애물 등)는 docs/scenarios/scenarios.md 에만 있습니다

# 편집한 시퀀스 읽고 쓰기 ----------------------------------------------------------------------
def checkStep(step):
    '''(설명, 동작, 초) 를 확인해 돌려줍니다. 틀리면 ValueError (GUI 에 그대로 보여 줄 문장).'''
    try:
        label, act, sec = step
    except (TypeError, ValueError):
        raise ValueError('단계 형식이 틀립니다: %r' % (step,))
    try:
        sec = float(sec)
    except (TypeError, ValueError):
        raise ValueError('%s: 기다리는 시간을 숫자로 넣어 주세요 (%r)' % (label, sec))
    if not isinstance(label, str) or not label.strip():
        raise ValueError('설명이 비어 있습니다')
    if not 0 <= sec <= MAX_STEP_SEC:
        raise ValueError('%s: 기다리는 시간은 0 ~ %d초여야 합니다' % (label, MAX_STEP_SEC))
    act = tuple(act) if act else None
    if act is not None:
        if act[0] not in ACTIONS or act[0] == 'wait':
            raise ValueError('%s: 모르는 동작 %r' % (label, act[0]))
        choices = ACTIONS[act[0]][1]
        if choices == ANGLES:
            lo, hi = ANGLE_RANGE[act[0]]
            try:
                act = (act[0], int(float(act[1])), int(float(act[2])))
            except (IndexError, TypeError, ValueError, OverflowError):
                raise ValueError('%s: 위아래, 좌우 각도를 숫자로 넣어 주세요' % label)
            if len(act) != 3 or not all(lo <= v <= hi for v in act[1:]):
                raise ValueError('%s: 각도는 %d ~ %d도여야 합니다' % (label, lo, hi))
        elif (choices is None) != (len(act) == 1) or (choices is not None and act[1] not in choices):
            raise ValueError('%s: %s 값이 틀립니다 %r' % (label, ACTIONS[act[0]][0], act))
    return (label.strip(), act, sec)

def loadSequences(path=SEQ_FILE):
    '''기본 SEQUENCES 에 편집한 파일을 덮어씁니다. 틀린 시퀀스는 그 시퀀스만 기본값으로 쓰고 알립니다.'''
    out = dict(SEQUENCES)
    saved = readJson(path) or {}
    for key, v in (saved.items() if isinstance(saved, dict) else ()):
        if key not in SEQUENCES:
            continue                                       # 시나리오가 쓰지 않는 이름은 무시
        try:
            out[key] = (str(v['title']).strip() or SEQUENCES[key][0], [checkStep(st) for st in v['steps']])
        except (KeyError, TypeError, ValueError) as e:
            print('[시퀀스 오류] %s: %s → 기본값 사용' % (key, e))
    return out

def saveSequences(seqs, path=SEQ_FILE):
    '''확인한 뒤 저장합니다. 틀리면 저장하지 않고 ValueError.'''
    data = {key: {'title': title, 'steps': [list(checkStep(st)) for st in steps]} for key, (title, steps) in seqs.items()}
    writeJsonAtomic(path, data)

def outline(sid, seqs=None):
    '''GUI 에 보여 줄 [(큰 동작, [세부 단계 설명])].'''
    seqs = seqs or loadSequences()
    _, target, order = SCENARIOS[sid]
    return [(seqs[q][0], [step[0].replace('{name}', target['name']) for step in seqs[q][1]]) for q in order]

class Player:
    '''ar.py 가 프레임마다 step() 을 불러, 때가 된 동작을 받아 실행합니다.'''
    def __init__(self, sid, now, sequences=None):
        if sid not in SCENARIOS:
            raise ValueError('모르는 시나리오: %s' % sid)
        sequences = sequences or loadSequences()          # GUI 에서 편집한 내용을 시작할 때마다 반영
        self.sid, (_, self.target, seqs) = sid, SCENARIOS[sid]
        # 시퀀스를 펼쳐 (몇 번째 시퀀스, 단계) 한 줄로 이음 → 끝나면 바로 다음 시퀀스로
        self.steps = [(n, step) for n, q in enumerate(seqs) for step in sequences[q][1]]
        self.seqTitles = [sequences[q][0] for q in seqs]
        self.index, self.nextAt, self.start, self.seq = 0, now, now, -1
        self.stimuli, self.done, self.history = [], not self.steps, []   # 단계를 다 지웠으면 바로 끝
        self.photo = None                                 # ('photo',) 로 잡은 화면 (ar.py 가 넣음)
        self.sweep, self.lastPan = None, None             # 진행 중인 '서보 좌우로 돌리기' (시작 시각, 시간, 시작, 끝)

    def _label(self, i):
        return self.steps[i][1][0].replace('{name}', self.target['name'])

    def step(self, now):
        '''이번 프레임에 실행할 동작 목록. aim 은 대상 위치를 붙여 ('aim', x, y),
        sweep 은 프레임마다 ('servo_pan', 각도) 로 조금씩 돌려줍니다.'''
        out = []
        if self.sweep and not self.done:
            t0, dur, a, b = self.sweep
            k = min(1.0, (now - t0) / dur) if dur > 0 else 1.0
            pan = int(round(a + (b - a) * k))
            if pan != self.lastPan:
                self.lastPan = pan
                out.append(('servo_pan', pan))
            if k >= 1.0:
                self.sweep = None
        while not self.done and now >= self.nextAt:
            n, (label, act, sec) = self.steps[self.index]
            if n != self.seq:
                self.seq = n
                self.history.append('%5.1f초 %d. %s' % (now - self.start, n + 1, self.seqTitles[n]))
            self.history.append('          - %s' % self._label(self.index))
            if act and act[0] == 'aim':
                act = ('aim', self.target['x'], self.target['y'])
            elif act and act[0] == 'sweep':
                self.sweep, self.lastPan = (now, sec, act[1], act[2]), act[1]
                act = ('servo_pan', act[1])
            elif act and act[0] == 'stim':
                self.stimuli.append(act[1])
            elif act and act[0] == 'log':
                act = ('log', {'scenario': self.sid, 'zone': self.target['zone'], 'species': self.target['species'],
                               'result': act[1], 'stimuli': list(self.stimuli), 'responses': len(self.stimuli)})
            if act:
                out.append(act)
            self.index += 1
            self.nextAt = now + sec
            self.done = self.index >= len(self.steps)
        return out

    def stop(self, now, why):
        '''사람, [Space], GUI [중지]. 자극 끄고 서보 그 자리.'''
        if self.done:
            return []
        self.done, self.sweep = True, None
        self.history.append('%5.1f초 중지: %s' % (now - self.start, why))
        return [('stim_stop',), ('horn', 'off'), ('lamp', 'off'), ('hold',)]

    def status(self, now=None):
        '''GUI 에 보여 줄 지금 단계: seq(몇 번째 시퀀스, 0부터), step(지금 세부 단계 설명),
        next(다음 세부 단계), nextIn(다음까지 남은 초, now 를 줄 때만).'''
        current = self.seqTitles[self.seq] if self.seq >= 0 else ''
        hasNext = not self.done and self.index < len(self.steps)
        return {'id': self.sid, 'done': self.done, 'seq': self.seq, 'seqCount': len(self.seqTitles),
                'sequence': '%d/%d %s' % (self.seq + 1, len(self.seqTitles), current),
                'step': self._label(self.index - 1) if self.index else '',
                'next': self._label(self.index) if hasNext else '',
                'nextIn': round(max(0.0, self.nextAt - now), 1) if hasNext and now is not None else None,
                'history': self.history[-14:]}

if __name__ == '__main__':
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'sequences.json'
        assert loadSequences(f) == SEQUENCES                                 # 파일 없음 → 기본값
        seqs = dict(SEQUENCES, scare=('빵 소리와 LED', [('삑 {name}', ('stim', 'sound_b'), 2.0)]))
        saveSequences(seqs, f)
        got = loadSequences(f)
        assert got['scare'] == ('빵 소리와 LED', [('삑 {name}', ('stim', 'sound_b'), 2.0)]) and got['scan'] == SEQUENCES['scan']
        p = Player('S-02', 0.0, got)
        acts = [a for t in range(0, 600) for a in p.step(t * 0.1)]
        assert ('stim', 'sound_b') in acts and '          - 삑 노루' in p.history        # 편집한 단계로 실행
        assert checkStep(('위로', ['servo_to', '100', 60.0], 1)) == ('위로', ('servo_to', 100, 60), 1.0)
        assert checkStep(('더', ('servo_by', -20, 15), 0))[1] == ('servo_by', -20, 15)
        assert checkStep(('쓸기', ('sweep', 30, 150), 2))[1] == ('sweep', 30, 150)
        for bad in (('', None, 1), ('x', ('stim', 'rm'), 1), ('x', ('aim', 'a'), 1), ('x', ('log',), 1),
                    ('x', None, 999), ('x', ('nope',), 1), ('x', None, 'abc'), ('x', ('servo_to', 200, 90), 1),
                    ('x', ('servo_to', 90), 1), ('x', ('servo_by', 'a', 1), 1), ('x', ('servo_by', -181, 0), 1),
                    ('x', ('sweep', -5, 90), 1)):
            try:
                checkStep(bad)
                raise AssertionError('통과하면 안 됨: %r' % (bad,))
            except ValueError:
                pass
        writeJsonAtomic(f, {'scare': {'title': 'x', 'steps': [['y', ['stim', 'rm'], 1]]}, 'scan': 5})
        assert loadSequences(f) == SEQUENCES                                 # 틀린 시퀀스는 기본값
        saveSequences({k: (t, []) for k, (t, _) in SEQUENCES.items()}, f)
        p = Player('S-02', 0.0, loadSequences(f))
        assert p.done and p.step(0) == []                                    # 단계를 다 지우면 바로 끝
    for sid, (_, _, seqs) in SCENARIOS.items():
        assert all(q in SEQUENCES for q in seqs), sid       # 없는 시퀀스 이름 방지
        p = Player(sid, 0.0)
        for t in range(0, 600):
            p.step(t * 0.1)
        assert p.done, sid                                   # 모두 끝까지 이어짐
    # 대표: 서보를 왼쪽으로 → 오른쪽으로 천천히 → 잡힘 → 빵 소리 + LED → 가운데
    p = Player('S-02', 0.0)
    acts = [a for t in range(0, 200) for a in p.step(t * 0.05)]
    pans = [a[1] for a in acts if a[0] == 'servo_pan']
    assert acts[0] == ('servo_to', 90, 45) and pans[0] == 45 and pans[-1] == 120
    assert pans == sorted(pans) and len(pans) > 20                      # 한 번에 튀지 않고 조금씩
    kinds = [a if a[0] in ('horn', 'lamp') else a[0] for a in acts if a[0] != 'servo_pan']
    assert kinds == ['servo_to', ('lamp', 'on'), ('horn', 'on'), ('horn', 'off'), ('lamp', 'off'), 'center'], kinds
    lastPan = max(i for i, a in enumerate(acts) if a[0] == 'servo_pan')
    assert acts.index(('lamp', 'on')) > lastPan and acts.index(('horn', 'on')) > lastPan     # 서보 쓸기가 끝난 뒤 빵 + 전조등
    p = Player('S-02', 0.0)
    p.step(0.0)
    assert p.status()['seq'] == 0 and p.status()['step'] == '서보를 왼쪽으로'
    st = p.status(0.2)
    assert st['next'] == '오른쪽으로 천천히 돌리기' and st['nextIn'] == 0.3      # 다음 단계까지 남은 시간
    p.step(0.5); p.step(2.6)
    st = p.status()
    assert st['seq'] == 1 and st['sequence'] == '2/4 카메라에 잡힌다' and st['step'] == '카메라에 노루가 잡힘, 서보 멈춤'
    assert p.stop(4.5, '[Space]') == [('stim_stop',), ('horn', 'off'), ('lamp', 'off'), ('hold',)]   # 멈추면 모두 끔
    assert p.step(99) == [] and p.stop(5, 'x') == []
    assert outline('S-02')[1] == ('카메라에 잡힌다', ['카메라에 노루가 잡힘, 서보 멈춤'])
    try:
        Player('S-11', 0)
        raise AssertionError('없는 시나리오')
    except ValueError:
        pass
    print('scenario 자체 점검 통과')
