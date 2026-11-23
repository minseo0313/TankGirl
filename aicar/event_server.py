#############################################################################################
#
# <event_server.py>  원격 조회 HTTP API (IF-11, 규칙 LOG-02)
#
# 조회만 합니다. 로봇을 움직이는 요청은 만들지 않습니다.
# 핫스팟 안에서만 씁니다. 인터넷(공유기 포트 포워딩 등)에 열지 않습니다.
#
#   GET /api/events?date=2026-11-23&page=1&limit=20   그날 이벤트, 최신순
#   GET /api/events/<id>                               이벤트 1건
#   GET /api/status                                    지금 상태
#   GET /photos/<YYYYMMDD>/<id>.jpg                    사진
#
# 응답: {"success": bool, "data": ..., "error": str|null, "page": {...}|null}
#
# 자체 점검: python3 event_server.py  (빈 포트로 잠깐 띄워 요청해 봄)
#
#############################################################################################
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_LIMIT = 100

def makeHandler(log, statusFn):
    class Handler(BaseHTTPRequestHandler):
        timeout = 5                            # 연결만 열고 보내지 않는 기기가 스레드를 붙잡지 않게

        def log_message(self, fmt, *args):     # 요청마다 터미널에 찍지 않음
            pass

        def _json(self, code, data=None, error=None, page=None):
            body = json.dumps({'success': error is None, 'data': data, 'error': error, 'page': page},
                              ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                self._route()
            except Exception as e:              # 원인은 터미널에만, 응답에는 내부 정보를 넣지 않음
                print('[조회 서버 오류] %s %s: %s: %s' % (self.command, self.path, type(e).__name__, e))
                self._json(500, error='서버 오류')

        def _route(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == '/api/events':
                return self._events(q)
            m = re.match(r'^/api/events/([0-9-]+)$', u.path)
            if m:
                try:
                    e = log.getEvent(m.group(1))
                except ValueError as err:
                    return self._json(400, error=str(err))
                return self._json(200, e) if e else self._json(404, error='없는 이벤트')
            if u.path == '/api/status':
                return self._json(200, statusFn())
            m = re.match(r'^/photos/([^/]+)/([^/]+)$', u.path)
            if m:
                return self._photo(m.group(1), m.group(2))
            self._json(404, error='없는 주소')

        def _events(self, q):
            date = q.get('date', [time.strftime('%Y-%m-%d')])[0]
            try:
                page = int(q.get('page', ['1'])[0])
                limit = int(q.get('limit', ['20'])[0])
                if page < 1 or not (1 <= limit <= MAX_LIMIT):
                    raise ValueError
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
                    raise ValueError
            except ValueError:
                return self._json(400, error='date=YYYY-MM-DD, page>=1, limit=1~%d' % MAX_LIMIT)
            items, total = log.listEvents(date.replace('-', ''), page, limit)
            self._json(200, items, page={'total': total, 'page': page, 'limit': limit})

        def _photo(self, day, name):
            p = log.photoPath(day, name)
            if p is None:
                return self._json(404, error='없는 사진')
            body = p.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler

def start(log, port, statusFn, host='0.0.0.0'):
    '''백그라운드 스레드로 서버를 띄우고 서버 객체를 돌려줍니다. 포트를 쓰고 있으면 OSError.'''
    server = ThreadingHTTPServer((host, port), makeHandler(log, statusFn))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print('[조회 서버] http://<파이 주소>:%d/api/events' % server.server_address[1])
    return server

if __name__ == '__main__':
    import tempfile
    import urllib.error
    import urllib.request
    from event_log import EventLog

    def get(url):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    with tempfile.TemporaryDirectory() as t:
        log = EventLog(t)
        now = time.mktime((2026, 11, 23, 14, 5, 12, 0, 0, -1))
        log.write({'species': 'roe_deer', 'result': 'left'}, now=now)
        log.write({'species': 'wild_boar', 'result': 'stayed'}, now=now + 1)
        srv = start(log, 0, lambda: {'state': '정지'}, host='127.0.0.1')
        base = 'http://127.0.0.1:%d' % srv.server_address[1]
        code, body = get(base + '/api/events?date=2026-11-23&limit=1')
        r = json.loads(body)
        assert code == 200 and r['success'] and r['data'][0]['species'] == 'wild_boar' and r['page']['total'] == 2
        assert get(base + '/api/events?limit=1000')[0] == 400
        assert get(base + '/api/events?date=../../etc')[0] == 400
        assert get(base + '/api/events/20261123-0001')[0] == 200
        assert get(base + '/api/events/20261123-0099')[0] == 404
        assert get(base + '/api/status')[0] == 200
        assert get(base + '/photos/20261123/..%2F..%2Fx.jpg')[0] == 404
        assert get(base + '/nothing')[0] == 404
        srv.shutdown()
    print('event_server 자체 점검 통과')
