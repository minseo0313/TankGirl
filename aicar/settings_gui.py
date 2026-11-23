#############################################################################################
#
# <settings_gui.py>  설정과 실험 창 (tkinter)
#
# $ python3 settings_gui.py        (aicar 폴더에서, VNC 데스크톱의 터미널)
#
# - ★ 표시 = 원본 aicar 에 처음부터 있던 값 (되도록 바꾸지 않음). 거의 안 바꾸는 값은 [고급 설정 보기]를 켜야 보임
# - 설정 탭: 값을 바꾸고 [저장] (Ctrl+S) → 실행 중인 ar.py 가 0.5초 안에 다시 읽어 바로 반영합니다.
#           "재시작 필요" 표시가 있는 항목만 ar.py 를 다시 켜야 반영됩니다.
# - 시나리오 탭: 왼쪽에서 시나리오를 고르고 [실행] → ar.py 가 시퀀스(큰 동작)를 순서대로 이어 서보, 자극, 기록을 실행.
#               가운데에서 시퀀스 이름과 세부 단계(설명, 동작, 값, 기다리는 초)를 바로 고치고 추가, 삭제, 순서 바꾸기.
#               [저장] → runtime/sequences.json, ar.py 는 다음 실행부터 반영. 오른쪽에 진행 로그.
#               시나리오별 시퀀스 순서는 scenario.py SCENARIOS.
# - 실험 탭: 서보 이동, 가상 위치 조준, 자극, 기록 시험. ar.py 가 실행 중일 때 ar.py 가 실행합니다.
# tkinter 가 없으면: sudo apt install python3-tk
#
#############################################################################################
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

import control
import scenario as scn
import settings
from event_log import RESULTS
from stimulus import KINDS

# 창 빈 곳을 잡고 끌면 창이 움직임. 버튼, 입력 칸, 드롭다운, 스크롤바, 탭은 원래대로 동작하도록 뺌
DRAG_CLASSES = {'TFrame', 'Frame', 'TLabel', 'Label', 'TLabelframe', 'Labelframe', 'Canvas'}
STATUS_REFRESH_MS = 300          # 시나리오 지금 단계가 바로 보이도록 자주 확인
FONT_FAMILIES = ('Pretendard', 'Apple SD Gothic Neo', 'Noto Sans CJK KR', 'NanumGothic')
RESULT_LABELS = {'left': '이탈', 'stayed': '잔류', 'unknown': '관찰 불가', 'uncertain': '불확실', 'person_stop': '사람으로 중지'}

class SettingsApp:
    def __init__(self, root):
        self.root = root
        root.title('TankGirl 설정과 실험')
        # 라즈베리파이 VNC 화면은 작을 수 있어서 최소 크기를 작게, 글꼴도 화면에 맞춤 (잘림 방지)
        root.minsize(480, 360)
        self.small = root.winfo_screenheight() < 900
        self.fontSize = 10 if self.small else 12
        self._setFont()
        self.scrollCanvases = []
        for ev in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            root.bind_all(ev, self._wheel)
        self.dragFrom = None
        root.bind_all('<ButtonPress-1>', self._dragStart, add='+')
        root.bind_all('<B1-Motion>', self._dragMove, add='+')
        root.bind_all('<ButtonRelease-1>', lambda e: setattr(self, 'dragFrom', None), add='+')
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
        nb.pack(fill='both', expand=True, padx=8 if self.small else 12)
        self.seqs = self._editable(scn.loadSequences())   # 시나리오 탭에서 고치는 사본 (저장 전까지 ar.py 에 안 감)
        nb.add(self._scenarioTab(nb), text='시나리오')
        groups = []
        for p in settings.SCHEMA:
            if p['group'] not in groups:
                groups.append(p['group'])
        for g in groups:
            self._scrollTab(nb, lambda parent, g=g: self._settingsTab(parent, g), g)
        self._scrollTab(nb, self._experimentTab, '실험')

        bottom = ttk.Frame(root, padding=(12, 8))
        bottom.pack(fill='x')
        ttk.Button(bottom, text='저장 (바로 반영)', command=self.save).pack(side='right')
        ttk.Button(bottom, text='다시 읽기', command=self.reload).pack(side='right', padx=6)
        ttk.Button(bottom, text='기본값', command=self.resetDefaults).pack(side='right')
        self.msg = ttk.Label(bottom, text='')
        self.msg.pack(side='left')
        root.bind('<Control-s>', lambda e: self.save())
        self._applyAdv()
        self._placeWindow()
        self.refreshStatus()

    def _setFont(self):
        have = set(tkfont.families())
        family = next((f for f in FONT_FAMILIES if f in have), None)
        if family:
            for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
                tkfont.nametofont(name).configure(family=family, size=self.fontSize)

    def _scrollable(self, parent):
        '''(바깥 틀, 캔버스, 안쪽을 넣는 함수). 내용이 화면보다 길면 세로 스크롤.'''
        outer = ttk.Frame(parent)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)
        canvas = tk.Canvas(outer, highlightthickness=0, width=300, height=160)   # 작게 요청하고 창 크기만큼 늘어남
        bar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.grid(row=0, column=0, sticky='nsew')
        bar.grid(row=0, column=1, sticky='ns')
        self.scrollCanvases.append(canvas)

        def put(inner):
            win = canvas.create_window((0, 0), window=inner, anchor='nw')
            inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>', lambda e: canvas.itemconfigure(win, width=e.width))
        return outer, canvas, put

    def _scrollTab(self, nb, build, text):
        outer, canvas, put = self._scrollable(nb)
        put(build(canvas))
        nb.add(outer, text=text)

    def _dragStart(self, e):
        w = e.widget
        if isinstance(w, tk.Misc) and w.winfo_toplevel() is self.root and w.winfo_class() in DRAG_CLASSES:
            self.dragFrom = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())
        else:
            self.dragFrom = None

    def _dragMove(self, e):
        if self.dragFrom:
            self.root.geometry('+%d+%d' % (e.x_root - self.dragFrom[0], e.y_root - self.dragFrom[1]))

    def _wheel(self, e):
        '''마우스 휠: 포인터 아래에 있는 스크롤 영역만 움직임 (macOS/Windows 는 delta, 리눅스(Pi)는 Button-4/5).'''
        w = self.root.winfo_containing(e.x_root, e.y_root)
        while w is not None and w not in self.scrollCanvases:
            w = w.master
        if w is not None:
            w.yview_scroll(-1 if (getattr(e, 'num', 0) == 4 or e.delta > 0) else 1, 'units')

    def _placeWindow(self):
        '''화면 나누기(설정 SPLIT_SCREEN)면 ar.py 카메라 창 오른쪽 남은 자리에 맞춰 띄웁니다.'''
        if not self.values['SPLIT_SCREEN']:
            return
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        need = max(self.root.winfo_reqwidth(), *(self._innerWidth(c) + 40 for c in self.scrollCanvases))
        # 화면이 좁으면 내용이 잘리지 않게 카메라 창 오른쪽을 조금 덮더라도 필요한 폭만큼 왼쪽으로
        x = max(0, min(int(sw * self.values['SPLIT_RATIO']), sw - need))
        self.root.geometry('%dx%d+%d+0' % (sw - x, sh - 80, x))      # 아래 80px 는 작업 표시줄 자리

    @staticmethod
    def _innerWidth(canvas):
        return max((canvas.nametowidget(canvas.itemcget(i, 'window')).winfo_reqwidth()
                    for i in canvas.find_all() if canvas.type(i) == 'window'), default=0)

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
            lw = ttk.Label(f, text=label, wraplength=230)           # 화면 반쪽에 들어가게 줄바꿈
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
            kw = ttk.Label(f, text='%s  %s' % (key, p['rule']), foreground='#6E6E73', wraplength=150)
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

    # 시나리오 탭: 왼쪽 시나리오 목록, 가운데 시퀀스(큰 동작)와 세부 단계를 바로 고침, 오른쪽 진행 로그 --------
    VALUE_LABELS = {'sound_a': '음향 A (빵)', 'sound_b': '음향 B', 'sound_led': '소리와 LED', 'led': 'LED만', 'on': '켜기', 'off': '끄기', **RESULT_LABELS}
    ANGLE_DEFAULTS = {'servo_to': (90, 90), 'servo_by': (0, 0), 'sweep': (45, 120)}   # 동작을 처음 고를 때 넣는 각도
    ACCENT = '#0A84FF'                                               # 지금 단계 표시
    HINT = '#8E8E93'

    def _scenarioTab(self, parent):
        '''화면 반쪽(라즈베리파이 640px 안팎)에 들어가도록 한 줄로 쌓음: 고르기·실행 → 시퀀스 블록 → 저장 → 진행.'''
        f = ttk.Frame(parent, padding=6)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)
        family = tkfont.nametofont('TkDefaultFont').actual('family')
        self.boldFont = (family, self.fontSize + 1, 'bold')
        self.actNames = {v[0]: k for k, v in scn.ACTIONS.items()}       # 표시 이름 → 동작

        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(0, weight=1)
        self.scnIds = list(scn.SCENARIOS)
        self.scnPick = ttk.Combobox(top, state='readonly', width=28,
                                    values=['%s  %s' % (sid, scn.SCENARIOS[sid][0]) for sid in self.scnIds])
        self.scnPick.grid(row=0, column=0, sticky='ew')
        self.scnPick.bind('<<ComboboxSelected>>', lambda e: self._showScenario())
        ttk.Button(top, text='▶ 실행', width=6, command=self._runScenario).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(top, text='■ 중지', width=6, command=lambda: self._send('scenario_stop')).grid(row=0, column=2, padx=(4, 0))
        self.scnNow = ttk.Label(top, text='지금: 대기', font=self.boldFont, foreground=self.ACCENT)
        self.scnNow.grid(row=1, column=0, columnspan=3, sticky='w', pady=(6, 0))
        self.seqHeads = []                                 # 시퀀스 블록 번호 (지금 단계에 ▶ 표시)
        self.scnTitle = ttk.Label(f, text='', foreground=self.HINT)
        self.scnTitle.grid(row=1, column=0, sticky='w', pady=(4, 0))

        outer, canvas, put = self._scrollable(f)
        outer.grid(row=2, column=0, sticky='nsew', pady=4)
        self.seqBox = ttk.Frame(canvas)
        put(self.seqBox)

        bottom = ttk.Frame(f)
        bottom.grid(row=3, column=0, sticky='ew')
        ttk.Button(bottom, text='저장', command=self._saveSequences).pack(side='right')
        ttk.Button(bottom, text='기본값으로', command=self._resetScenario).pack(side='right', padx=4)
        self.seqMsg = ttk.Label(bottom, text='고친 뒤 [저장] → 다음 실행부터', foreground=self.HINT)
        self.seqMsg.pack(side='left')

        log = ttk.LabelFrame(f, text='진행', padding=4)
        log.grid(row=4, column=0, sticky='ew', pady=(4, 0))
        self.scnLog = tk.Text(log, height=5, width=40, wrap='word', relief='flat', state='disabled', font=(family, 10))
        self.scnLog.pack(fill='x')
        self.scnLogText = ''

        self.scnPick.current(0)                            # 맨 위 = 대표 시나리오 (S-02)
        self._showScenario()
        return f

    def _selectedScenario(self):
        i = self.scnPick.current()
        return self.scnIds[i] if i >= 0 else None

    def _runScenario(self):
        sid = self._selectedScenario()
        if sid is not None:
            if self.seqMsg.cget('text').startswith('고침'):
                self.msg.config(text='저장하지 않은 단계는 이번 실행에 들어가지 않습니다')
            self._send('scenario_start', id=sid)

    def _dirty(self):
        self.seqMsg.config(text='고침 (아직 저장 안 함)', foreground='#B25000')

    @staticmethod
    def _bindVar(var, setter, after):
        var.trace_add('write', lambda *a: (setter(var.get()), after()))

    def _showScenario(self):
        '''고른 시나리오의 시퀀스를 블록으로 다시 그립니다 (단계를 넣고 빼면 이걸로 새로 그림).'''
        sid = self._selectedScenario()
        if sid is None:
            return
        for w in self.seqBox.winfo_children():
            w.destroy()
        title, target, order = scn.SCENARIOS[sid]
        self.scnTitle.config(text='대상: %s · {name} 은 대상 이름으로 바뀜 · 같은 시퀀스를 쓰는 시나리오는 함께 바뀜'
                             % target['name'], wraplength=420)
        self.seqHeads = []
        for n, key in enumerate(order):
            head = ttk.Frame(self.seqBox)
            num = ttk.Label(head, text='%d.' % (n + 1), font=self.boldFont)
            num.pack(side='left')
            self.seqHeads.append(num)
            tv = tk.StringVar(value=self.seqs[key][0])
            self._bindVar(tv, lambda v, k=key: self.seqs[k].__setitem__(0, v), self._dirty)
            ttk.Entry(head, textvariable=tv, width=22, font=self.boldFont).pack(side='left', padx=4)
            box = ttk.LabelFrame(self.seqBox, labelwidget=head, padding=(6, 2))
            box.pack(fill='x', pady=(2, 4), padx=(0, 4))
            box.columnconfigure(0, weight=1)
            steps = self.seqs[key][1]
            for i, step in enumerate(steps):
                self._stepRow(box, key, i, step)
            ttk.Button(box, text='+ 단계 추가', command=lambda k=key: self._editSteps(k, 'add')).grid(
                row=2 * len(steps), column=0, sticky='w', pady=(2, 2))

    def _stepRow(self, box, key, i, step):
        '''단계 하나 = 두 줄. 1줄: 설명, 위·아래·삭제. 2줄: 동작, 값(자극 종류 / 기록 판정 / 위아래·좌우 각도), 기다리는 초.'''
        r = 2 * i
        lv = tk.StringVar(value=step[0])
        self._bindVar(lv, lambda v: step.__setitem__(0, v), self._dirty)
        ttk.Entry(box, textvariable=lv, width=20).grid(row=r, column=0, sticky='ew', pady=(4, 0))
        bf = ttk.Frame(box)
        bf.grid(row=r, column=1, sticky='e', padx=(4, 0), pady=(4, 0))
        for text, how in (('▲', 'up'), ('▼', 'down'), ('✕', 'del')):
            ttk.Button(bf, text=text, width=2, command=lambda h=how: self._editSteps(key, h, i)).pack(side='left')

        line = ttk.Frame(box)
        line.grid(row=r + 1, column=0, columnspan=2, sticky='w', padx=(12, 0), pady=(2, 0))
        act = step[1][0] if step[1] else 'wait'
        av = tk.StringVar(value=scn.ACTIONS[act][0])
        cb = ttk.Combobox(line, textvariable=av, values=list(self.actNames), state='readonly', width=12)
        cb.bind('<<ComboboxSelected>>', lambda e: self._changeAct(step, self.actNames[av.get()]))
        cb.pack(side='left')
        choices = scn.ACTIONS[act][1]
        if choices == scn.ANGLES:
            lo, hi = scn.ANGLE_RANGE[act]
            for idx, text in zip((1, 2), scn.ANGLE_LABELS[act]):
                ttk.Label(line, text=text).pack(side='left', padx=(6, 0))
                v = tk.StringVar(value=str(step[1][idx]))
                self._bindVar(v, lambda x, idx=idx: step[1].__setitem__(idx, x), self._dirty)
                ttk.Spinbox(line, textvariable=v, from_=lo, to=hi, increment=5, width=4).pack(side='left', padx=(2, 0))
        elif choices:
            labels = [self.VALUE_LABELS.get(c, c) for c in choices]
            v = tk.StringVar(value=self.VALUE_LABELS.get(step[1][1], step[1][1]))
            c2 = ttk.Combobox(line, textvariable=v, values=labels, state='readonly', width=11)
            c2.bind('<<ComboboxSelected>>', lambda e: (step[1].__setitem__(1, choices[labels.index(v.get())]), self._dirty()))
            c2.pack(side='left', padx=(6, 0))
        sv = tk.StringVar(value='%g' % float(step[2]) if self._isNumber(step[2]) else str(step[2]))
        self._bindVar(sv, lambda v: step.__setitem__(2, v), self._dirty)
        ttk.Spinbox(line, textvariable=sv, from_=0, to=scn.MAX_STEP_SEC, increment=0.5, width=4).pack(side='left', padx=(8, 0))
        ttk.Label(line, text='초').pack(side='left', padx=(2, 0))

    @staticmethod
    def _isNumber(v):
        try:
            float(v)
            return True
        except (TypeError, ValueError):
            return False

    def _changeAct(self, step, act):
        choices = scn.ACTIONS[act][1]
        if act == 'wait':
            step[1] = None
        elif choices == scn.ANGLES:
            step[1] = [act, *self.ANGLE_DEFAULTS[act]]
        else:
            step[1] = [act, choices[0]] if choices else [act]
        self._dirty()
        self._showScenario()                               # 값 칸 모양이 바뀌므로 다시 그림

    def _editSteps(self, key, how, i=None):
        steps = self.seqs[key][1]
        if how == 'add':
            steps.append(['새 단계', None, 1])
        elif how == 'del':
            del steps[i]
        else:
            j = i - 1 if how == 'up' else i + 1
            if not 0 <= j < len(steps):
                return
            steps[i], steps[j] = steps[j], steps[i]
        self._dirty()
        self._showScenario()

    @staticmethod
    def _editable(seqs):
        '''편집용 사본: {이름: [큰 동작, [[설명, [동작, 값...] 또는 None, 초], ...]]}.'''
        return {k: [t, [[l, list(a) if a else None, s] for l, a, s in steps]] for k, (t, steps) in seqs.items()}

    def _saveSequences(self):
        seqs = {k: (t.strip() or scn.SEQUENCES[k][0], [(l, tuple(a) if a else None, s) for l, a, s in steps])
                for k, (t, steps) in self.seqs.items()}
        try:
            scn.saveSequences(seqs)
        except ValueError as e:
            messagebox.showerror('저장하지 않았습니다', str(e))
            return
        except OSError as e:
            messagebox.showerror('저장 실패', '파일을 쓰지 못했습니다: %s' % e)
            return
        self.seqs = self._editable(scn.loadSequences())
        self._showScenario()
        self.seqMsg.config(text='저장함 → 다음 실행부터 반영', foreground='#248A3D')

    def _resetScenario(self):
        sid = self._selectedScenario()
        if sid and messagebox.askyesno('기본값', '%s 의 시퀀스를 모두 기본값으로 되돌릴까요?\n'
                                               '같은 시퀀스를 쓰는 다른 시나리오도 바뀝니다. (저장을 눌러야 반영)' % sid):
            defaults = self._editable(scn.SEQUENCES)
            for key in scn.SCENARIOS[sid][2]:
                self.seqs[key] = defaults[key]
            self._dirty()
            self._showScenario()

    def _showProgress(self, run):
        # 지금 단계: 위쪽 한 줄 + 고른 시나리오면 해당 시퀀스 블록 번호에 ▶
        if run['done']:
            stopped = next((h.split('중지:', 1)[1].strip() for h in run['history'] if '중지:' in h), None)
            self.scnNow.config(text='지금: %s %s' % (run['id'], '중지 (%s)' % stopped if stopped else '끝'))
        else:
            nxt = '\n다음: %s (%.1f초 뒤)' % (run['next'], run['nextIn']) if run.get('next') and run.get('nextIn') is not None else ''
            self.scnNow.config(text='지금: %s  %s → %s%s' % (run['id'], run.get('sequence', ''), run.get('step', ''), nxt))
        current = run.get('seq', -1) if run['id'] == self._selectedScenario() and not run['done'] else -1
        for i, num in enumerate(self.seqHeads):
            num.config(text=('▶ %d.' if i == current else '%d.') % (i + 1),
                       foreground=self.ACCENT if i == current else '')
        text = '%s %s\n시퀀스 %s\n\n%s' % (run['id'], '끝' if run['done'] else '실행 중', run['sequence'],
                                        '\n'.join(run['history']))
        if text != self.scnLogText:                        # 같으면 다시 쓰지 않음 (스크롤 유지)
            self.scnLogText = text
            self.scnLog.config(state='normal')
            self.scnLog.delete('1.0', 'end')
            self.scnLog.insert('end', text)
            self.scnLog.see('end')
            self.scnLog.config(state='disabled')

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
            if s.get('scenario'):
                self._showProgress(s['scenario'])
            if s.get('detect_error'):
                lines.append('탐지 오류: %s' % s['detect_error'])
            if not s.get('detect_ok'):
                lines.append('※ 탐지가 꺼져 있어 사람을 확인할 수 없습니다. '
                             + ('[주의] 탐지 없이 실험 허용 중 (안전 탭 ALLOW_WITHOUT_DETECT)' if s.get('allow_without_detect')
                                else '자극, 서보 실험 명령은 거부됩니다 (안전 탭에서 허용 가능)'))
            self.statusText.config(text='\n'.join(lines))
        else:
            self.connLabel.config(text='○ ar.py 꺼짐', foreground='#B25000')
            self.statusText.config(text='')
        self.root.after(STATUS_REFRESH_MS, self.refreshStatus)

def build(root):
    return SettingsApp(root)

if __name__ == '__main__':
    root = tk.Tk()
    build(root)
    root.mainloop()
