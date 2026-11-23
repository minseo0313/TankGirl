#############################################################################################
#
# <aim.py>  서보 조준 (IF-08, 규칙 AIM-02 ~ AIM-06)
#
# 서보 1 = 위아래(tilt), 서보 2 = 좌우(pan). 각도는 도(0~180).
# 서보 핀은 ar.py 가 잡고 있으므로 이 모듈은 각도만 계산하고, 실제 이동은 ar.py 가 넘긴 함수로 합니다.
#
# 자체 점검: python3 aim.py  (서보 없이 각도 계산만 확인)
#
#############################################################################################
import time

FRAME_W, FRAME_H = 640, 480            # 탐지 박스 좌표 기준 (IF-01 카메라 화면)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def computeAim(box, current, s):
    '''
    박스 쪽을 향할 (tilt, pan) 을 돌려줍니다. 규칙 AIM-02 순서:
    목표 각도 → 서보 범위로 자르기 → 지금 각도에서 이동량을 AIM_MAX_STEP_DEG 로 자르기.
    box = (x1, y1, x2, y2, ...) 카메라 640x480 좌표, current = 지금 (tilt, pan), s = settings dict.
    '''
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    tilt, pan = current
    if s['AIM_CAMERA_ON_SERVO'] and abs(cx - FRAME_W / 2) <= s['AIM_DEADBAND_PX'] \
            and abs(cy - FRAME_H / 2) <= s['AIM_DEADBAND_PX']:
        return current                                    # 이미 화면 가운데 → 떨림 방지로 그대로
    errX = (cx - FRAME_W / 2) / (FRAME_W / 2)             # -1 왼쪽 끝 ~ +1 오른쪽 끝
    errY = (cy - FRAME_H / 2) / (FRAME_H / 2)             # -1 위 끝 ~ +1 아래 끝
    dPan = -errX * s['CAM_HFOV_DEG'] / 2 * s['SERVO_LEFT']
    dTilt = -errY * s['CAM_VFOV_DEG'] / 2 * s['SERVO_UP']
    if s['AIM_CAMERA_ON_SERVO']:
        targetTilt, targetPan = tilt + dTilt, pan + dPan  # 돌릴수록 대상이 가운데로 옴
    else:
        targetTilt, targetPan = s['SERVO_CENTER'] + dTilt, s['SERVO_CENTER'] + dPan  # 화면 위치 = 방향
    targetTilt = clamp(targetTilt, s['AIM_TILT_MIN'], s['AIM_TILT_MAX'])
    targetPan = clamp(targetPan, s['AIM_PAN_MIN'], s['AIM_PAN_MAX'])
    step = s['AIM_MAX_STEP_DEG']
    return (int(round(tilt + clamp(targetTilt - tilt, -step, step))),
            int(round(pan + clamp(targetPan - pan, -step, step))))

def clampAngles(tilt, pan, s):
    '''직접 지정한 각도를 서보 범위로 자릅니다 (규칙 AIM-03).'''
    return (int(clamp(tilt, s['AIM_TILT_MIN'], s['AIM_TILT_MAX'])),
            int(clamp(pan, s['AIM_PAN_MIN'], s['AIM_PAN_MAX'])))

def largestBox(boxes):
    '''여러 마리면 박스가 가장 큰(가까운) 것 (규칙 DET-05). 없으면 None.'''
    return max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), default=None)

class Aimer:
    '''
    getAngles() → 지금 (tilt, pan), move(tilt, pan) → 서보 이동, hold() → 그 자리에서 힘 풀기.
    세 함수는 ar.py 가 서보 코드로 만들어 넘깁니다.
    '''
    def __init__(self, getAngles, move, hold):
        self.getAngles = getAngles
        self.move = move
        self.holdFn = hold
        self.lastAim = 0.0           # 마지막 자동 조준 시각 (AIM_INTERVAL_SEC 간격)
        self.pausedUntil = 0.0       # 수동 조작 뒤 자동 조준을 쉬는 끝 시각 (AIM-06)

    def pause(self, sec, now=None):
        now = time.time() if now is None else now
        self.pausedUntil = max(self.pausedUntil, now + sec)

    def aimAt(self, box, s, now=None, force=False):
        '''자동 조준. 간격, 수동 조작 쉬는 시간 안이면 아무것도 안 합니다 (force 면 무시). 보낸 각도를 돌려줍니다.'''
        now = time.time() if now is None else now
        if not force and (now < self.pausedUntil or now - self.lastAim < s['AIM_INTERVAL_SEC']):
            return self.getAngles()
        self.lastAim = now
        current = self.getAngles()
        target = computeAim(box, current, s)
        if target != current:
            self.move(*target)
        return target

    def moveTo(self, tilt, pan, s):
        target = clampAngles(tilt, pan, s)
        self.move(*target)
        return target

    def aimCenter(self, s):
        return self.moveTo(s['SERVO_CENTER'], s['SERVO_CENTER'], s)

    def aimHold(self):
        '''매번 보냅니다. 사람이 보이는 동안 다른 곳(수동 키 등)에서 다시 움직인 서보도 프레임마다 멈춰야 하므로.'''
        self.holdFn()

if __name__ == '__main__':
    import settings
    s = settings.defaults()                                  # 카메라 고정, 중앙 90, 범위 tilt 60~120
    assert computeAim((300, 220, 340, 260), (90, 90), s) == (90, 90)        # 가운데 → 그대로
    assert computeAim((600, 220, 640, 260), (90, 90), s) == (90, 80)        # 오른쪽 끝 → 한 번에 10도만
    assert computeAim((600, 220, 640, 260), (90, 80), s) == (90, 70)        # 다음 번에 또 10도
    assert computeAim((600, 220, 640, 260), (90, 66), s) == (90, 65)        # 목표(약 65도)에서 멈춤
    assert computeAim((300, 0, 340, 20), (90, 90), dict(s, AIM_MAX_STEP_DEG=90)) == (110, 90)  # 위 → 범위 안
    assert computeAim((300, 0, 340, 20), (120, 90), dict(s, CAM_VFOV_DEG=180)) == (120, 90)    # 최대 120에서 자름
    assert computeAim((600, 220, 640, 260), (90, 90), dict(s, SERVO_LEFT=-1)) == (90, 100)     # 방향 반대
    cam = dict(s, AIM_CAMERA_ON_SERVO=True)
    assert computeAim((330, 230, 350, 250), (90, 50), cam) == (90, 50)      # 데드밴드 안 → 그대로
    assert computeAim((600, 220, 640, 260), (90, 50), cam) == (90, 40)      # 지금 각도 기준으로 더 돌림
    assert largestBox([(0, 0, 10, 10, 'a'), (0, 0, 20, 20, 'b')])[4] == 'b' and largestBox([]) is None
    sent = []
    a = Aimer(lambda: (90, 90), lambda t, p: sent.append((t, p)), lambda: sent.append('hold'))
    a.aimAt((600, 220, 640, 260), s, now=100.0)
    a.aimAt((600, 220, 640, 260), s, now=100.1)               # 간격 0.3초 안 → 안 보냄
    a.pause(5, now=100.0)
    a.aimAt((600, 220, 640, 260), s, now=101.0)               # 수동 쉬는 시간 → 안 보냄
    a.aimHold(); a.aimHold()                                  # 부를 때마다 보냄 (사람이 있는 동안 계속 멈춤)
    assert sent == [(90, 80), 'hold', 'hold'], sent
    assert a.moveTo(10, 200, s) == (60, 180)                  # 직접 지정도 범위로 자름
    print('aim 자체 점검 통과')
