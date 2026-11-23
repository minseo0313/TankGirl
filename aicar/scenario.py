#############################################################################################
#
# <scenario.py>  시나리오 시험: 시퀀스를 이어서 정해진 순서대로 실행 (docs/scenarios/scenarios.md)
#
# 시나리오 = 시퀀스(큰 동작, 예: "동물을 탐지한다")를 순서대로 이은 것
# 시퀀스   = 세부 단계(예: "카메라에 노루가 나타난다", "사진을 찍는다", "빵 소리를 낸다")의 목록
# 단계     = (설명, 동작, 다음 단계까지 기다리는 초). 설명의 {name} 은 시나리오 대상 이름으로 바뀝니다.
#
# 동작은 ar.py 가 실행합니다. None 이면 기다리기만 합니다 (탐지는 아직 AI 없이 "나타났다고 봄").
#   ('photo',)        지금 카메라 화면을 사진으로 잡아 둠 (기록할 때 이 사진을 씀)
#   ('aim',)          시나리오 대상 위치(x, y) 쪽으로 서보 조준
#   ('center',)       서보 가운데,  ('hold',) 서보 그 자리에서 멈춤
#   ('servo_to', 위아래, 좌우)  그 각도로 (도),  ('servo_by', 위아래, 좌우)  지금 각도에서 그만큼 더 (도, +/-)
#                     둘 다 ar.py 가 설정의 서보 범위(AIM_TILT_MIN/MAX 등)로 잘라서 보냅니다
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
ANGLE_RANGE = {'servo_to': (0, 180), 'servo_by': (-180, 180)}
# 고를 수 있는 동작: 이름 → (GUI 표시, 고를 값 / ANGLES / None)
ACTIONS = {'wait': ('기다리기', None), 'photo': ('사진 찍기', None), 'aim': ('대상 쪽으로 조준', None),
           'servo_to': ('서보 각도로', ANGLES), 'servo_by': ('서보 돌리기', ANGLES),
           'center': ('서보 가운데', None), 'hold': ('서보 멈춤', None), 'stim': ('자극 켜기', KINDS),
           'stim_stop': ('자극 끄기', None), 'log': ('기록', RESULTS)}

# 시퀀스: 이름 → (큰 동작, [세부 단계]) ------------------------------------------------------
# 쓰는 부품: 서보(카메라 방향), 스피커(빵 소리), LED, 바퀴(시나리오 동안 세워 둠). 거리센서는 아직 안 씀
SEQUENCES = {
    'stop':     ('멈춘다', [
        ('바퀴를 세우고 카메라(서보)를 가운데로', ('center',), 1.5)]),
    'look':     ('주변을 살핀다', [
        ('5초 동안 카메라로 본다', None, 5),
        ('아무것도 없다', None, 0)]),
    'detect':   ('동물을 탐지한다', [
        ('카메라에 {name}가 나타난다', None, 1),
        ('1초 동안 계속 보여 {name}로 확정한다', None, 0),
        ('사진을 찍는다', ('photo',), 0)]),
    'aim':      ('카메라를 동물 쪽으로 돌린다', [
        ('서보를 {name} 쪽으로 돌린다', ('aim',), 2)]),
    'bang':     ('빵 소리를 낸다', [
        ('스피커로 빵 소리 (음향 A)', ('stim', 'sound_a'), 1.5)]),
    'led':      ('LED 를 켠다', [
        ('LED 를 깜빡인다', ('stim', 'led'), 3),
        ('LED 를 끈다', ('stim_stop',), 0)]),
    'bang_led': ('소리와 LED 를 함께 낸다 (더 세게)', [
        ('빵 소리와 LED 깜빡임을 함께', ('stim', 'sound_led'), 3),
        ('소리와 LED 를 끈다', ('stim_stop',), 0)]),
    'person':   ('사람을 본다', [
        ('카메라에 사람이 나타난다', None, 0),
        ('사진을 찍는다', ('photo',), 0),
        ('서보를 멈추고 소리, LED 를 내지 않는다', ('hold',), 3),
        ('사람이 사라진다', None, 0)]),
    'cut_person': ('사람이 끼어든다', [
        ('소리를 내는 중에 사람이 들어온다', None, 0),
        ('소리와 LED 를 바로 끈다', ('stim_stop',), 0),
        ('서보를 멈춘다', ('hold',), 3)]),
    'watch_left': ('다시 지켜본다', [
        ('1초 쉰다 (카메라 고정)', None, 1),
        ('{name}가 화면 밖으로 나간다', None, 2),
        ('3초 더 봐도 다시 안 보인다 → 떠남', None, 3)]),
    'watch_stay': ('다시 지켜본다', [
        ('1초 쉰다 (카메라 고정)', None, 1),
        ('5초 동안 {name}가 그대로 있다 → 안 떠남', None, 5)]),
    'return':   ('복귀한다', [
        ('카메라(서보)를 가운데로', ('center',), 1.5),
        ('순찰을 다시 시작한다 (주행은 ar.py [G])', None, 0)]),
}
RESULT_NAMES = {'left': '이탈', 'stayed': '잔류, 확인 필요', 'unknown': '관찰 불가',
                'uncertain': '불확실', 'person_stop': '사람으로 중지'}
for _r, _label in RESULT_NAMES.items():                     # 'log_left' 등: 기록한다
    SEQUENCES['log_' + _r] = ('기록한다', [('%s (사진과 함께)' % _label, ('log', _r), 0)])

# 시나리오: 번호 → (제목, 대상, [시퀀스 순서]) ---------------------------------------------------
# 대상: name 표시 이름, species 기록 종류, x, y 화면 위치 (카메라 640x480), zone 구역 (None = 미정)
DEER = {'name': '노루', 'species': 'roe_deer', 'x': 480, 'y': 120, 'zone': 2}
SCENARIOS = {
    'S-02': ('동물이 나타나 빵 소리와 LED 로 쫓음', DEER,
             ['stop', 'detect', 'aim', 'bang', 'led', 'watch_left', 'log_left', 'return']),
    'S-03': ('동물이 떠나지 않아 한 번 더 (소리+LED)', dict(DEER, x=320, y=240),
             ['stop', 'detect', 'aim', 'bang', 'led', 'watch_stay', 'aim', 'bang_led', 'watch_stay', 'log_stayed', 'return']),
    'S-07': ('쫓는 도중 사람이 나타남', DEER,
             ['stop', 'detect', 'aim', 'bang', 'cut_person', 'log_person_stop', 'return']),
    'S-05': ('사람만 나타남', dict(DEER, name='사람', species='person', zone=1),
             ['stop', 'person', 'log_person_stop', 'return']),
    'S-01': ('아무것도 없음', DEER, ['stop', 'look', 'return']),
}
# 거리센서가 필요한 시나리오(S-11, S-12)와 그 밖의 시나리오는 docs/scenarios/scenarios.md 에만 있습니다

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

    def step(self, now):
        '''이번 프레임에 실행할 동작 목록. aim 은 대상 위치를 붙여 ('aim', x, y) 로 돌려줍니다.'''
        out = []
        while not self.done and now >= self.nextAt:
            n, (label, act, sec) = self.steps[self.index]
            if n != self.seq:
                self.seq = n
                self.history.append('%5.1f초 %d. %s' % (now - self.start, n + 1, self.seqTitles[n]))
            self.history.append('          - %s' % label.replace('{name}', self.target['name']))
            if act and act[0] == 'aim':
                act = ('aim', self.target['x'], self.target['y'])
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
        '''사람, 탐지 멈춤, [Space], GUI [중지]. 자극 끄고 서보 그 자리.'''
        if self.done:
            return []
        self.done = True
        self.history.append('%5.1f초 중지: %s' % (now - self.start, why))
        return [('stim_stop',), ('hold',)]

    def status(self):
        current = self.seqTitles[self.seq] if self.seq >= 0 else ''
        return {'id': self.sid, 'done': self.done, 'sequence': '%d/%d %s' % (self.seq + 1, len(self.seqTitles), current),
                'history': self.history[-14:]}

if __name__ == '__main__':
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'sequences.json'
        assert loadSequences(f) == SEQUENCES                                 # 파일 없음 → 기본값
        seqs = dict(SEQUENCES, bang=('빵 소리를 낸다', [('삑 {name}', ('stim', 'sound_b'), 2.0)]))
        saveSequences(seqs, f)
        got = loadSequences(f)
        assert got['bang'] == ('빵 소리를 낸다', [('삑 {name}', ('stim', 'sound_b'), 2.0)]) and got['aim'] == SEQUENCES['aim']
        p = Player('S-02', 0.0, got)
        acts = [a for t in range(0, 600) for a in p.step(t * 0.1)]
        assert ('stim', 'sound_b') in acts and '          - 삑 노루' in p.history        # 편집한 단계로 실행
        assert checkStep(('위로', ['servo_to', '100', 60.0], 1)) == ('위로', ('servo_to', 100, 60), 1.0)
        assert checkStep(('더', ('servo_by', -20, 15), 0))[1] == ('servo_by', -20, 15)
        for bad in (('', None, 1), ('x', ('stim', 'rm'), 1), ('x', ('aim', 'a'), 1), ('x', ('log',), 1),
                    ('x', None, 999), ('x', ('nope',), 1), ('x', None, 'abc'), ('x', ('servo_to', 200, 90), 1),
                    ('x', ('servo_to', 90), 1), ('x', ('servo_by', 'a', 1), 1), ('x', ('servo_by', -181, 0), 1)):
            try:
                checkStep(bad)
                raise AssertionError('통과하면 안 됨: %r' % (bad,))
            except ValueError:
                pass
        writeJsonAtomic(f, {'bang': {'title': 'x', 'steps': [['y', ['stim', 'rm'], 1]]}, 'aim': 5})
        assert loadSequences(f) == SEQUENCES                                 # 틀린 시퀀스는 기본값
        saveSequences(dict(SEQUENCES, stop=('멈춘다', [])), f)
        assert Player('S-01', 0.0, loadSequences(f)).step(0) == []           # 빈 시퀀스는 건너뜀
    for sid, (_, _, seqs) in SCENARIOS.items():
        assert all(q in SEQUENCES for q in seqs), sid       # 없는 시퀀스 이름 방지
        p = Player(sid, 0.0)
        acts = [a for t in range(0, 600) for a in p.step(t * 0.1)]
        assert p.done, sid                                   # 모두 끝까지 이어짐
        logs = [a for a in acts if a[0] == 'log']
        assert len(logs) == (0 if sid == 'S-01' else 1), sid
        for a in acts:                                       # 사진은 기록보다 먼저
            if a[0] == 'log' and sid != 'S-01':
                assert ('photo',) in acts[:acts.index(a)], sid
    p = Player('S-03', 0.0)
    acts = [a for t in range(0, 600) for a in p.step(t * 0.1)]
    assert [a[1] for a in acts if a[0] == 'stim'] == ['sound_a', 'led', 'sound_led']
    assert [a[1] for a in acts if a[0] == 'log'][0]['result'] == 'stayed' and ('aim', 320, 240) in acts
    p = Player('S-02', 0.0)                                              # 대표: 탐지 → 빵 소리 → LED
    acts = [a for t in range(0, 600) for a in p.step(t * 0.1)]
    order = [a[0] if a[0] != 'stim' else a[1] for a in acts if a[0] in ('photo', 'stim', 'log')]
    assert order == ['photo', 'sound_a', 'led', 'log'], order
    p = Player('S-02', 0.0)
    assert p.step(0.0) == [('center',)] and p.step(1.0) == []           # 멈추고 1.5초 기다림
    assert p.status()['sequence'] == '1/8 멈춘다'
    p.step(1.5)
    assert p.status()['sequence'] == '2/8 동물을 탐지한다'                  # 다음 시퀀스로 이어짐
    assert p.stop(2.0, '사람') == [('stim_stop',), ('hold',)] and p.step(99) == [] and p.stop(3, 'x') == []
    assert outline('S-02')[1] == ('동물을 탐지한다', ['카메라에 노루가 나타난다', '1초 동안 계속 보여 노루로 확정한다',
                                                   '사진을 찍는다'])
    try:
        Player('S-11', 0)
        raise AssertionError('S-11 은 키보드 시험')
    except ValueError:
        pass
    print('scenario 자체 점검 통과')
