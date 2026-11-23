#############################################################################################
#
# <event_log.py>  이벤트 기록 (IF-10, 규칙 LOG-01)
#
# events/<YYYYMMDD>.jsonl  하루 1파일, 한 줄 = 이벤트 1건
# events/<YYYYMMDD>/<id>.jpg  대표 사진
# 기록에 실패해도 로봇을 멈추지 않습니다 (터미널에 원인만 출력).
#
# 자체 점검: python3 event_log.py
#
#############################################################################################
import json
import re
import threading
import time
from pathlib import Path

RESULTS = ('left', 'stayed', 'unknown', 'uncertain', 'person_stop')   # 이탈, 잔류, 관찰 불가, 불확실, 사람으로 중지
DATE_RE = re.compile(r'^\d{8}$')
ID_RE = re.compile(r'^(\d{8})-(\d{4})$')

class EventLog:
    def __init__(self, baseDir):
        self.dir = Path(baseDir) / 'events'
        self.lock = threading.Lock()

    def _dayFile(self, day):
        return self.dir / ('%s.jsonl' % day)

    def _readDay(self, day):
        '''하루 이벤트 목록 (파일 순서 = 오래된 것부터). 깨진 줄은 건너뜁니다.'''
        try:
            with open(str(self._dayFile(day)), encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []
        out = []
        for n, line in enumerate(lines, 1):
            try:
                out.append(json.loads(line))
            except ValueError:
                print('[기록 오류] %s %d번째 줄이 깨져서 건너뜁니다' % (self._dayFile(day).name, n))
        return out

    def _closeTail(self, day):
        '''마지막 줄이 줄바꿈 없이 끝났으면(쓰다 끊김) 줄바꿈을 붙여 그 줄을 따로 떼어 둡니다.'''
        f = self._dayFile(day)
        if not f.exists() or f.stat().st_size == 0:
            return
        with open(str(f), 'rb+') as fp:
            fp.seek(-1, 2)
            if fp.read(1) != b'\n':
                fp.write(b'\n')

    def _lineCount(self, day):
        try:
            with open(str(self._dayFile(day)), encoding='utf-8') as f:
                return sum(1 for line in f if line.strip())
        except FileNotFoundError:
            return 0

    def write(self, event, photo=None, now=None):
        '''
        event 에 id, time, photo 를 채워 저장하고 저장한 dict 를 돌려줍니다. 실패하면 None.
        event 필수: species(str), result(RESULTS 중 하나). 나머지(zone, max_conf, person, stimuli,
        responses, reobserve_sec)는 있으면 그대로 저장합니다. photo 는 OpenCV 영상(numpy) 또는 None.
        '''
        if event.get('result') not in RESULTS:
            print('[기록 오류] result 는 %s 중 하나여야 합니다: %r' % (', '.join(RESULTS), event.get('result')))
            return None
        now = time.time() if now is None else now
        day = time.strftime('%Y%m%d', time.localtime(now))
        with self.lock:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                self._closeTail(day)                                  # 쓰다 끊긴 마지막 줄에 붙여 쓰지 않게
                eid = '%s-%04d' % (day, self._lineCount(day) + 1)   # 깨진 줄도 세야 번호가 겹치지 않음
                rec = dict(event, id=eid, time=time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now)), photo=None)
                if photo is not None:
                    rec['photo'] = self._savePhoto(day, eid, photo)
                with open(str(self._dayFile(day)), 'a', encoding='utf-8') as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            except OSError as e:
                print('[기록 오류] 저장하지 못했습니다 (저장 공간, 폴더 권한 확인): %s' % e)
                return None
        print('[기록] %s %s %s' % (eid, rec.get('species'), rec['result']))
        return rec

    def _savePhoto(self, day, eid, photo):
        import cv2                         # 사진이 있을 때만 불러옵니다
        d = self.dir / day
        d.mkdir(exist_ok=True)
        name = '%s.jpg' % eid
        if not cv2.imwrite(str(d / name), photo):
            print('[기록 오류] 사진 저장 실패: %s' % (d / name))
            return None
        return '%s/%s' % (day, name)

    def listEvents(self, day, page=1, limit=20):
        '''(최신순 이벤트 목록, 전체 개수). day 는 YYYYMMDD.'''
        if not DATE_RE.match(day):
            raise ValueError('날짜 형식이 아닙니다')
        events = list(reversed(self._readDay(day)))
        start = (page - 1) * limit
        return events[start:start + limit], len(events)

    def getEvent(self, eid):
        m = ID_RE.match(eid)
        if not m:
            raise ValueError('이벤트 번호 형식이 아닙니다')
        return next((e for e in self._readDay(m.group(1)) if e.get('id') == eid), None)

    def photoPath(self, day, name):
        '''events/ 안의 사진 파일 경로. 형식이 틀리거나 밖을 가리키면 None (../ 차단).'''
        if not DATE_RE.match(day) or not re.match(r'^\d{8}-\d{4}\.jpg$', name):
            return None
        p = (self.dir / day / name).resolve()
        if self.dir.resolve() not in p.parents or not p.is_file():
            return None
        return p

if __name__ == '__main__':
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        log = EventLog(t)
        now = time.mktime((2026, 11, 23, 14, 5, 12, 0, 0, -1))
        assert log.write({'species': 'roe_deer', 'result': 'nope'}, now=now) is None    # 틀린 판정
        a = log.write({'species': 'roe_deer', 'result': 'left', 'zone': 2}, now=now)
        b = log.write({'species': 'person', 'result': 'person_stop'}, now=now + 60)
        assert a['id'] == '20261123-0001' and b['id'] == '20261123-0002' and a['time'] == '2026-11-23T14:05:12'
        items, total = log.listEvents('20261123', page=1, limit=1)
        assert total == 2 and items[0]['id'] == b['id']                                 # 최신순
        assert log.getEvent('20261123-0001')['zone'] == 2 and log.getEvent('20261123-0009') is None
        assert log.photoPath('20261123', '../../x.jpg') is None
        assert log.photoPath('20261123', '20261123-0001.jpg') is None                   # 사진 없음
        with open(str(log._dayFile('20261123')), 'a', encoding='utf-8') as f:
            f.write('{broken')                                                         # 쓰다 끊긴 줄 (줄바꿈 없음)
        assert log.listEvents('20261123')[1] == 2                                       # 깨진 줄 건너뜀
        c = log.write({'species': 'x', 'result': 'unknown'}, now=now)
        assert c['id'] == '20261123-0004' and log.getEvent(c['id'])['species'] == 'x'   # 번호 안 겹치고 읽힘
    print('event_log 자체 점검 통과')
