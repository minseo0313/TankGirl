#############################################################################################
#
# <settings_gui.py>  설정과 실험 창 (tkinter)
#
# $ python3 settings_gui.py        (aicar 폴더에서, VNC 데스크톱의 터미널)
#
# - ★ 표시 = 원본 aicar 에 처음부터 있던 값 (되도록 바꾸지 않음). 거의 안 바꾸는 값은 [고급 설정 보기]를 켜야 보임
# - 설정 탭: 값을 바꾸고 [저장] (Ctrl+S) → 실행 중인 ar.py 가 0.5초 안에 다시 읽어 바로 반영합니다.
#           "재시작 필요" 표시가 있는 항목만 ar.py 를 다시 켜야 반영됩니다.
# - 실험 탭: 서보 이동, 가상 위치 조준, 자극, 기록 시험. ar.py 가 실행 중일 때 ar.py 가 실행합니다.
# tkinter 가 없으면: sudo apt install python3-tk
#
#############################################################################################
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

import control
import settings
from event_log import RESULTS
from stimulus import KINDS

STATUS_REFRESH_MS = 1000
FONT_FAMILIES = ('Pretendard', 'Apple SD Gothic Neo', 'Noto Sans CJK KR', 'NanumGothic')
RESULT_LABELS = {'left': '이탈', 'stayed': '잔류', 'unknown': '관찰 불가', 'uncertain': '불확실', 'person_stop': '사람으로 중지'}

class SettingsApp:
    def __init__(self, root):
        self.root = root
        root.title('TankGirl 설정과 실험')
        root.minsize(620, 520)
        self._setFont()
        self.vars = {}
        self.advRows = []                    # "고급 설정 보기"를 켜야 보이는 줄의 위젯들
        self.values = settings.load()

        top = ttk.Frame(root, padding=(12, 8))
        top.pack(fill='x')
        self.connLabel = ttk.Label(top, text='ar.py 확인 중…')
        self.connLabel.pack(side='left')
        self.topmost = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text='항상 위', variable=self.topmost, command=self._applyTopmost).pack(side='right')
        self.showAdv = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text='고급 설정 보기', variable=self.showAdv, command=self._applyAdv).pack(side='right', padx=12)
        ttk.Label(top, text='★ 원본 aicar 값', foreground='#6E6E73').pack(side='right', padx=12)
        self._applyTopmost()

        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=12)
        groups = []
        for p in settings.SCHEMA:
            if p['group'] not in groups:
                groups.append(p['group'])
        for g in groups:
            nb.add(self._settingsTab(nb, g), text=g)
        nb.add(self._experimentTab(nb), text='실험')

        bottom = ttk.Frame(root, padding=(12, 8))
        bottom.pack(fill='x')
        ttk.Button(bottom, text='저장 (바로 반영)', command=self.save).pack(side='right')
        ttk.Button(bottom, text='다시 읽기', command=self.reload).pack(side='right', padx=6)
        ttk.Button(bottom, text='기본값', command=self.resetDefaults).pack(side='right')
        self.msg = ttk.Label(bottom, text='')
        self.msg.pack(side='left')
        root.bind('<Control-s>', lambda e: self.save())
        self._applyAdv()
        self.refreshStatus()

    def _setFont(self):
        have = set(tkfont.families())
        family = next((f for f in FONT_FAMILIES if f in have), None)
        if family:
            for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
                tkfont.nametofont(name).configure(family=family, size=12)

    def _applyTopmost(self):
        # ar.py 의 OpenCV 창이 전체 화면이라 이 창이 뒤로 숨지 않게 합니다
        self.root.attributes('-topmost', self.topmost.get())

    def _applyAdv(self):
        for widgets in self.advRows:
            for w in widgets:
                if self.showAdv.get():
                    w.grid()
                else:
                    w.grid_remove()

    # 고를 수 있는 값은 이름으로 보여 줌 (예: 1 → '그대로') -----------------------------------
    @staticmethod
    def _show(key, value):
        names = settings.BY_KEY[key]['names']
        return names.get(value, str(value)) if names else str(value)

    @staticmethod
    def _parse(key, text):
        names = settings.BY_KEY[key]['names']
        if names:
            for value, name in names.items():
                if name == text:
                    return value
        return text

    # 설정 탭 -------------------------------------------------------------------------------
    def _settingsTab(self, parent, group):
        f = ttk.Frame(parent, padding=12)
        f.columnconfigure(1, weight=1)
        row = 0
        items = [p for p in settings.SCHEMA if p['group'] == group]
        items.sort(key=lambda p: p['adv'])          # 기본 항목 먼저, 고급 항목은 아래로 (같은 묶음 안 순서는 유지)
        for p in items:
            if p['adv'] and not any(q['adv'] for q in items[:items.index(p)]):
                # 고급 항목 앞에 한 칸 띄우고 제목 (고급 설정 보기를 켰을 때만 보임)
                gap = ttk.Frame(f, height=16)
                gap.grid(row=row, column=0, columnspan=3)
                sep = ttk.Separator(f, orient='horizontal')
                sep.grid(row=row + 1, column=0, columnspan=3, sticky='ew', pady=(0, 4))
                title = ttk.Label(f, text='고급 설정', foreground='#6E6E73')
                title.grid(row=row + 2, column=0, sticky='w', pady=(0, 4))
                self.advRows.append((gap, sep, title))
                row += 3
            key, d = p['key'], p['default']
            # ★ = 원본 aicar 에 처음부터 있던 값 (되도록 바꾸지 않음)
            label = ('★ ' if p['origin'] else '') + p['label'] + ('  (재시작 필요)' if p['restart'] else '')
            lw = ttk.Label(f, text=label)
            lw.grid(row=row, column=0, sticky='w', pady=4)
            if isinstance(d, bool):
                var = tk.BooleanVar(value=self.values[key])
                w = ttk.Checkbutton(f, variable=var)
            elif p['choices'] is not None:
                var = tk.StringVar(value=self._show(key, self.values[key]))
                w = ttk.Combobox(f, textvariable=var, values=[self._show(key, c) for c in p['choices']],
                                 state='readonly', width=12)
            elif p['lo'] is not None:
                var = tk.StringVar(value=str(self.values[key]))
                inc = 1 if isinstance(d, int) else 0.05
                w = ttk.Spinbox(f, textvariable=var, from_=p['lo'], to=p['hi'], increment=inc, width=12)
            else:
                var = tk.StringVar(value=str(self.values[key]))
                w = ttk.Entry(f, textvariable=var, width=28)
            w.grid(row=row, column=1, sticky='w', padx=8)
            kw = ttk.Label(f, text='%s  %s' % (key, p['rule']), foreground='#6E6E73')
            kw.grid(row=row, column=2, sticky='w')
            if p['adv']:
                self.advRows.append((lw, w, kw))
            self.vars[key] = var
            row += 1
        return f

    def _collect(self):
        return {k: self._parse(k, v.get()) for k, v in self.vars.items()}

    def _setVars(self, values):
        for k, v in self.vars.items():
            v.set(values[k] if isinstance(values[k], bool) else self._show(k, values[k]))

    def save(self):
        try:
            self.values = settings.save(self._collect())
        except ValueError as e:
            messagebox.showerror('저장하지 않았습니다', str(e))
            return
        except OSError as e:
            messagebox.showerror('저장 실패', '파일을 쓰지 못했습니다: %s' % e)
            return
        self._setVars(self.values)
        self.msg.config(text='저장함 → ar.py 가 곧 반영합니다')

    def reload(self):
        self.values = settings.load()
        self._setVars(self.values)
        self.msg.config(text='저장된 값을 다시 읽음')

    def resetDefaults(self):
        if messagebox.askyesno('기본값', '모든 값을 parameters.md 초기값으로 되돌릴까요? (저장을 눌러야 반영)'):
            self._setVars(settings.defaults())
            self.msg.config(text='기본값으로 바꿈 (아직 저장 안 함)')

    # 실험 탭 -------------------------------------------------------------------------------
    def _experimentTab(self, parent):
        f = ttk.Frame(parent, padding=12)

        servo = ttk.LabelFrame(f, text='서보 (서보 1 위아래, 서보 2 좌우)', padding=8)
        servo.pack(fill='x', pady=4)
        self.tilt, self.pan = tk.StringVar(value='90'), tk.StringVar(value='90')
        ttk.Label(servo, text='위아래').grid(row=0, column=0)
        ttk.Spinbox(servo, textvariable=self.tilt, from_=0, to=180, increment=5, width=6).grid(row=0, column=1, padx=4)
        ttk.Label(servo, text='좌우').grid(row=0, column=2)
        ttk.Spinbox(servo, textvariable=self.pan, from_=0, to=180, increment=5, width=6).grid(row=0, column=3, padx=4)
        ttk.Button(servo, text='이 각도로', command=lambda: self._sendNums('aim_angle', tilt=self.tilt, pan=self.pan)).grid(row=0, column=4, padx=4)
        ttk.Button(servo, text='가운데로', command=lambda: self._send('aim_center')).grid(row=0, column=5, padx=4)
        ttk.Button(servo, text='힘 풀기', command=lambda: self._send('aim_hold')).grid(row=0, column=6, padx=4)

        point = ttk.LabelFrame(f, text='가상 위치로 조준 (카메라 640×480 좌표, 동물이 거기 있다고 보고 AIM-02 계산)', padding=8)
        point.pack(fill='x', pady=4)
        self.px, self.py = tk.StringVar(value='480'), tk.StringVar(value='120')
        ttk.Label(point, text='x').grid(row=0, column=0)
        ttk.Spinbox(point, textvariable=self.px, from_=0, to=639, increment=20, width=6).grid(row=0, column=1, padx=4)
        ttk.Label(point, text='y').grid(row=0, column=2)
        ttk.Spinbox(point, textvariable=self.py, from_=0, to=479, increment=20, width=6).grid(row=0, column=3, padx=4)
        ttk.Button(point, text='조준 1번', command=lambda: self._sendNums('aim_point', x=self.px, y=self.py)).grid(row=0, column=4, padx=4)

        stim = ttk.LabelFrame(f, text='자극 (사람이 보이면 ar.py 가 바로 끔)', padding=8)
        stim.pack(fill='x', pady=4)
        self.kind = tk.StringVar(value=KINDS[0])
        ttk.Combobox(stim, textvariable=self.kind, values=KINDS, state='readonly', width=12).grid(row=0, column=0, padx=4)
        ttk.Button(stim, text='시작', command=lambda: self._send('stim_start', kind=self.kind.get())).grid(row=0, column=1, padx=4)
        ttk.Button(stim, text='정지', command=lambda: self._send('stim_stop')).grid(row=0, column=2, padx=4)

        log = ttk.LabelFrame(f, text='기록 시험 (지금 카메라 화면을 사진으로 남김)', padding=8)
        log.pack(fill='x', pady=4)
        self.result = tk.StringVar(value=RESULTS[0])
        ttk.Combobox(log, textvariable=self.result, values=RESULTS, state='readonly', width=12).grid(row=0, column=0, padx=4)
        self.resultLabel = ttk.Label(log, text=RESULT_LABELS[RESULTS[0]])
        self.resultLabel.grid(row=0, column=1, padx=4)
        self.result.trace_add('write', lambda *a: self.resultLabel.config(text=RESULT_LABELS.get(self.result.get(), '')))
        ttk.Button(log, text='기록 남기기', command=lambda: self._send('log_test', result=self.result.get())).grid(row=0, column=2, padx=4)

        st = ttk.LabelFrame(f, text='ar.py 상태', padding=8)
        st.pack(fill='both', expand=True, pady=4)
        self.statusText = ttk.Label(st, text='', justify='left')
        self.statusText.pack(anchor='w')
        return f

    def _sendNums(self, cmd, **vars_):
        try:
            args = {k: int(float(v.get())) for k, v in vars_.items()}
        except ValueError:
            messagebox.showerror('보내지 않았습니다', '숫자를 넣어 주세요')
            return
        self._send(cmd, **args)

    def _send(self, cmd, **args):
        _, alive = control.readStatus()
        if not alive:
            messagebox.showwarning('ar.py 가 꺼져 있음', '실험 명령은 ar.py 가 실행 중일 때 동작합니다.\n'
                                   '다른 터미널에서 python3 ar.py <프로젝트> 를 먼저 실행하세요.')
            return
        try:
            control.send(cmd, **args)
        except (ValueError, OSError) as e:
            messagebox.showerror('보내지 못했습니다', str(e))
            return
        self.msg.config(text='보냄: %s' % cmd)

    def refreshStatus(self):
        s, alive = control.readStatus()
        if alive:
            self.connLabel.config(text='● ar.py 실행 중', foreground='#248A3D')
            lines = [
                '상태: %s   탐지: %s' % (s.get('state'), '켜짐' if s.get('detect_on') else '꺼짐'),
                '사람: %s   동물: %s' % ('보임' if s.get('person') else '-', '보임' if s.get('animal') else '-'),
                '서보: 위아래 %s°, 좌우 %s°   자동 조준: %s' % (s.get('tilt'), s.get('pan'), '켜짐' if s.get('aim_auto') else '꺼짐'),
                '자극: %s' % (s.get('stimulus') or '꺼짐'),
                '조회 서버: %s' % ('포트 %s' % s['server_port'] if s.get('server_port') else '꺼짐'),
                '마지막 명령: %s' % (s.get('last_command') or '-'),
            ]
            if s.get('detect_error'):
                lines.append('탐지 오류: %s' % s['detect_error'])
            if not s.get('detect_ok'):
                lines.append('※ 탐지가 꺼져 있어 사람을 확인할 수 없습니다. '
                             + ('[주의] 탐지 없이 실험 허용 중 (안전 탭 ALLOW_WITHOUT_DETECT)' if s.get('allow_without_detect')
                                else '자극, 서보 실험 명령은 거부됩니다 (안전 탭에서 허용 가능)'))
            self.statusText.config(text='\n'.join(lines))
        else:
            self.connLabel.config(text='○ ar.py 꺼짐 (설정 저장은 됨, 실험은 ar.py 를 켠 뒤)', foreground='#B25000')
            self.statusText.config(text='')
        self.root.after(STATUS_REFRESH_MS, self.refreshStatus)

def build(root):
    return SettingsApp(root)

if __name__ == '__main__':
    root = tk.Tk()
    build(root)
    root.mainloop()
