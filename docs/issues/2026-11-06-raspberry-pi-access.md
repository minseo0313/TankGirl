# 라즈베리파이 핫스팟 연결 및 SSH 접속 기록

이슈 분류: SD 카드 Wi-Fi 설정, 핫스팟 연결, SSH 접속, VNC 화면 생성.

관련 이슈: [OV5647 카메라 인식 설정](2026-11-06-ov5647-camera.md), [전체 화면 흰 여백](2026-11-06-gi-fullscreen.md).

작성일: 2026-11-06

## 1. 환경과 확인된 결과

- PC: Windows, 모바일 핫스팟 사용
- SD 카드: USB 리더기로 PC에 연결, `bootfs (D:)`로 표시
- 이미지 정보: `Raspberry Pi reference 2023-05-03`, pi-gen stage4
- OS는 이미지 날짜상 Bullseye 계열로 추정. 정확한 배포판 버전은 미확인
- 핫스팟 이름(SSID): `<핫스팟 이름>`
- 핫스팟 밴드: 2.4GHz
- 라즈베리파이 호스트 이름: `raspberrypi`
- 로그인 계정: `pi`
- 연결 후 확인한 IP: `<Pi IP>` (재연결 시 변경될 수 있음)
- 부팅, 핫스팟 연결, SSH 로그인 성공 확인
- VNC 데스크톱 표시 문제는 아직 해결 확인 전

비밀번호는 이 문서에 기록하지 않는다.

## 2. Windows 핫스팟 설정

1. 설정 → 네트워크 및 인터넷 → 모바일 핫스팟으로 이동한다.
2. 핫스팟을 잠시 끄고 속성 → 편집을 연다.
3. 네트워크 밴드를 2.4GHz로 저장한다.
4. 모바일 핫스팟을 켠다.

Wi-Fi 연결에는 핫스팟 이름과 비밀번호가 필요하며, IP 주소는 연결 후 자동으로 할당받았다.

## 3. SD 카드에 Wi-Fi 설정 저장

SD 카드를 PC에 연결했을 때 Windows의 검사 안내가 표시되어, 우선 '스캔 없이 계속'으로 열었다. 이 선택은 카드의 정상 여부를 검사한 결과가 아니다. 포맷은 하지 않았다.

이번 구형 Raspberry Pi OS에서는 `bootfs (D:)`의 최상위에 `wpa_supplicant.conf`를 저장하는 방식을 사용했다. Bookworm 이후 OS에는 이 부팅 파티션 가져오기 방식을 그대로 적용할 수 없다.

메모장에 다음 내용을 작성한다. 비밀번호 자리에는 실제 핫스팟 비밀번호를 입력한다.

```conf
country=KR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="<핫스팟 이름>"
    psk="실제 핫스팟 비밀번호"
}
```

저장 옵션:

- 위치: `D:\`
- 파일 이름: `wpa_supplicant.conf`
- 파일 형식: 모든 파일
- 인코딩: UTF-8

처음 사진에서 파일 이름이 `wpa_supplicant.con.txt`로 확인됐다. 이 이름으로는 Wi-Fi 설정으로 가져오지 않는다. 탐색기 → 보기 → 표시 → 파일 확장명을 켜고, F2로 전체 이름을 정확히 `wpa_supplicant.conf`로 변경해야 한다. 끝에 `.txt`가 없어야 한다.

주의: 이 방식은 기존 Wi-Fi 설정을 대체할 수 있다. 기존 연결을 유지해야 한다면 기존 설정을 먼저 확보해야 한다.

## 4. SD 카드 삽입과 부팅

1. PC에서 SD 카드를 안전하게 제거한다.
2. 라즈베리파이 전원이 꺼진 상태에서 SD 카드를 끝까지 꽂는다.
3. 핫스팟을 켜둔 채 라즈베리파이 전원을 연결한다.
4. 약 1~2분 기다린다.

이번에는 전원이 켜진 상태에서 SD 카드를 꽂았다는 사실을 확인했다. SD 카드가 꽂힌 상태로 전원을 다시 연결한 뒤 초록 LED의 활동이 관찰됐으며, 이후 핫스팟 목록에 장치가 나타났다.

빨간 LED는 보통 전원 표시이고 초록 LED는 SD 카드 활동을 나타낸다. LED만으로 정상 부팅이나 Wi-Fi 연결 성공을 확정할 수 없다. 전원이 켜진 상태에서 SD 카드를 빼지 않는다. 종료가 가능하면 정상 종료를 사용한다.

## 5. 네트워크 연결 확인

아래 명령은 Windows PowerShell에서 실행했다. 문서의 명령 블록 표기는 요청에 따라 bash로 통일했다.

```bash
ping raspberrypi.local
```

결과: '호스트를 찾을 수 없습니다.' 이름으로 IP를 찾지 못한 것으로, 이 결과만으로 Wi-Fi 연결 실패를 확정할 수 없다.

Windows 모바일 핫스팟 → 연결된 장치에서 다음 정보를 직접 확인했다.

- 장치 이름: `raspberrypi`
- IP 주소: `<Pi IP>`

이 IP로 통신을 확인할 수 있다. 아래 IP ping 명령의 실행 결과는 이번 기록에서 확인하지 않았다.

```bash
ping <Pi IP>
```

## 6. SSH 접속 성공

Windows PowerShell에서 실행한다.

```bash
ssh pi@<Pi IP>
```

첫 연결 시 호스트 키 확인 질문이 나왔다. 출력에는 같은 키가 이전 주소 `<Pi IP>`에도 등록되어 있다고 표시됐다. 이번에는 확인 질문에 다음을 입력한 후 로그인 비밀번호를 입력했다.

```text
yes
```

새 연결의 호스트 키 확인은 접속 대상이 본인 장치인지 확인한 뒤 진행한다. 비밀번호 입력 중 문자가 표시되지 않는 것은 정상이다. 로그인 비밀번호는 핫스팟 비밀번호와 별개다.

접속 성공 후 프롬프트:

```text
pi@raspberrypi:~ $
```

커널 정보는 `Linux raspberrypi 6.1.21-v8+`, 아키텍처는 `aarch64`로 표시됐다. SSH 로그인 성공으로 해당 시점의 부팅과 네트워크 통신을 확인했다.

## 7. 기본 비밀번호 경고

로그인 시 `pi` 계정의 기본 비밀번호가 변경되지 않았다는 경고가 표시됐다. 다음 명령은 SSH 로그인 후 라즈베리파이에서 실행한다.

```bash
passwd
```

현재 비밀번호와 새 비밀번호를 안내에 따라 입력한다. 비밀번호 변경 완료 여부는 아직 확인하지 않았다.

## 8. VNC 오류와 설정 시도

VNC 접속 시 다음 메시지가 표시됐다.

```text
Cannot currently show the desktop
```

VNC가 표시할 데스크톱을 제공하지 못한 상태다. 모니터 없는 환경의 해상도 설정 또는 데스크톱 세션 상태 등을 확인해야 하며, 정확한 원인은 아직 미확인이다.

SSH에서 다음 명령을 실행했다.

```bash
sudo raspi-config
```

안내한 설정 절차는 다음과 같다. 실제 메뉴 선택 및 적용 완료는 확인되지 않았다.

1. Display Options → VNC Resolution
2. 1280×720 등 해상도 선택
3. Finish로 종료
4. 재부팅 안내에 따라 재부팅

필요 시 라즈베리파이에서 직접 재부팅한다. SSH가 끊기는 것은 재부팅 시 정상이다.

```bash
sudo reboot
```

## 9. 마지막 상태: SSH 연결 끊김

`sudo raspi-config` 입력 후 사용자에게서 다음 결과가 전달됐다.

```text
client_loop: send disconnect: Connection reset
PS C:\Users\남민서>
```

이는 SSH 연결이 끊겼다는 뜻이다. 이 메시지만으로 재부팅, 설정 적용 완료 또는 단절 원인을 확정할 수 없다. 기본 비밀번호 경고가 단절 원인이라는 증거도 없다.

다음 확인 순서:

1. 재부팅 중일 가능성을 고려해 1~2분 기다린다.
2. Windows 핫스팟의 연결된 장치 목록에서 현재 IP를 확인한다.
3. IP가 그대로라면 아래 명령으로 재접속한다. 바뀌었다면 새 IP로 바꾼다.

```bash
ssh pi@<Pi IP>
```

4. 재접속되면 필요 시 `sudo raspi-config`를 다시 실행해 위 해상도 설정을 진행한다.
5. 재부팅 후 현재 IP로 VNC를 다시 연결한다.

## 10. 그래픽 서비스 확인 및 raspi-config 화면

SSH 재접속 후 다음 명령을 실행했다.

```bash
systemctl get-default
systemctl status display-manager --no-pager -l
```

각 명령의 용도:

- `systemctl get-default`: 기본 부팅 대상을 확인한다. 결과 `graphical.target`은 그래픽 환경을 시작하도록 설정돼 있다는 뜻이다.
- `systemctl status display-manager --no-pager -l`: 그래픽 로그인 서비스를 확인한다. `--no-pager`는 별도 페이지 화면 없이 출력하고, `-l`은 긴 줄을 생략하지 않는다.

실제 출력에서 `lightdm.service`가 `active (running)`이었고, 하위 프로세스로 `Xorg`가 실행 중이었다. 그래픽 부팅 설정과 서비스 실행은 확인했지만, 이것만으로 VNC에서 표시할 데스크톱이 정상이라고 판단할 수는 없다. 사용자 목록을 가져오지 못했다는 Accounts 서비스 경고도 있었으나, VNC 오류와의 인과관계는 확인되지 않았다.

### Raspberry Pi 설정 도구 열기

라즈베리파이에 SSH로 접속한 터미널에서 실행한다.

```bash
sudo raspi-config
```

`raspi-config`는 Raspberry Pi OS의 시스템 설정을 텍스트 메뉴로 변경하는 도구다. `sudo`는 시스템 설정 변경에 필요한 관리자 권한으로 실행한다. 도구를 여는 것만으로 설정이 바뀌지는 않는다.

사용자가 전달한 화면에서 설정 도구가 정상적으로 열린 것을 확인했다. 화면 상단의 하드웨어 정보는 `Raspberry Pi 4 Model B Rev 1.5`다.

첫 화면 메뉴:

| 메뉴 | 용도 |
| --- | --- |
| 1 System Options | 네트워크, 사용자, 부팅 방식 등 시스템 설정 |
| 2 Display Options | 해상도 등 화면 관련 설정 |
| 3 Interface Options | SSH, VNC, 주변 장치 인터페이스 등의 활성화 설정 |
| 4 Performance Options | 성능 관련 설정 |
| 5 Localisation Options | 시간대, 언어, 키보드, 무선 국가 등 지역 설정 |
| 6 Advanced Options | 고급 시스템 설정 |
| 8 Update | raspi-config 도구 업데이트 |
| 9 About raspi-config | 도구 정보 확인 |

키보드 조작:

- 위·아래 방향키: 메뉴 이동
- Enter: 선택한 메뉴 열기 또는 확인
- Tab: 하단의 Select, Back, Finish 등 버튼으로 이동
- Esc: 이전 화면으로 돌아가기 또는 취소

### 지금 진행할 VNC 해상도 설정

현재 첫 화면에서 `1 System Options`가 선택돼 있다.

1. 아래 방향키를 한 번 눌러 **2 Display Options**를 선택하고 Enter를 누른다.
2. 다음 화면에 **VNC Resolution**이 있으면 선택한다.
3. 해상도 **1280×720**을 선택한다. 모니터 없이 사용할 화면 크기를 지정하기 위한 설정이다.
4. 첫 화면으로 돌아와 Tab으로 **Finish**를 선택하고 Enter를 누른다.
5. 재부팅 질문이 나오면 Yes를 선택한다. 질문이 없으면 셸로 돌아온 뒤 아래 명령을 실행한다.

```bash
sudo reboot
```

재부팅하면 SSH 연결이 끊긴다. 1~2분 후 Windows 핫스팟의 현재 IP를 확인하고 VNC로 다시 접속한다. `VNC Resolution` 메뉴가 없다면 다른 항목을 임의로 바꾸지 말고 메뉴 내용을 확인한다.

현재 확인된 것은 raspi-config 첫 화면이 열린 상태까지다. 해상도 선택, 재부팅, VNC 화면 복구는 아직 확인되지 않았다.

## 11. 모니터 없이 VNC 화면을 만들기 위한 HDMI 설정 변경

### 왜 변경했나?

Wi-Fi와 SSH는 정상 연결됐지만, VNC에는 `Cannot currently show the desktop`이 표시됐다. LightDM 로그에서는 X 서버가 종료 코드 1로 종료되고 재시작되는 상황이 반복됐다.

커널 로그에는 다음 메시지가 있었다.

```text
[drm] No displays found. Consider forcing hotplug if HDMI is attached
```

`/boot/config.txt` 확인 결과 Pi 4 구간에 `dtoverlay=vc4-fkms-v3d`가 활성화되어 있었고, 기존 `hdmi_force_hotplug` 설정은 주석 처리돼 있었다. 따라서 현재 FKMS 환경에서 **모니터가 없어도 HDMI 화면을 생성하도록 강제하고, 화면 해상도를 지정하는 변경**을 시도했다. 이는 VNC에 제공할 화면을 만들기 위한 조치이며, SSH 단절 원인까지 해결된다는 뜻은 아니다.

저장 공간은 `/`에 약 17GB, `/boot`에 약 222MB가 남아 있어 공간 부족 상태는 아니었다. `vcgencmd get_throttled` 결과는 `0x0`으로, 해당 부팅에서 기록된 저전압·스로틀링 플래그는 없었다. 이전 부팅의 전원 문제까지 배제하는 결과는 아니다.

### 로그를 보고 어떻게 판단했나?

아래 로그는 사용자가 SSH 터미널에서 실행해 전달한 실제 출력의 발췌다. 로그 시각은 라즈베리파이의 시스템 시각이며, 실제 작업일과 달랐다. 따라서 날짜 자체보다 메시지 내용과 부팅 후 경과 시간을 중심으로 판단했다.

#### 1. 그래픽 부팅은 설정돼 있지만 화면 정상 여부는 별개

확인 명령:

```bash
systemctl get-default
systemctl status display-manager --no-pager -l
```

실제 출력 발췌:

```text
graphical.target
● lightdm.service - Light Display Manager
     Active: active (running)
             ├─554 /usr/sbin/lightdm
             └─865 /usr/lib/xorg/Xorg ...
```

**판단:** 텍스트 전용으로 부팅하도록 설정된 상태는 아니고, 그래픽 로그인 관리자인 LightDM도 실행 중이다. 다만 관리 프로세스가 살아 있는 것과 화면 서버가 정상적으로 유지되는 것은 다르므로, VNC 정상 동작까지 확인한 결과는 아니다.

#### 2. VNC 오류가 반복되고 X 서버 프로세스가 계속 바뀜

확인 명령:

```bash
sudo journalctl -b -1 -n 40 --no-pager
```

실제 출력 발췌:

```text
10월 22 17:31:26 raspberrypi vncserver-x11[562]: ConsoleDisplay: Found running X server (pid=1050, binary=/usr/lib/xorg/Xorg)
10월 22 17:31:26 raspberrypi vncserver-x11[562]: AgentInitCheck: agent comms failure
10월 22 17:31:31 raspberrypi vncserver-x11[562]: ConsoleDisplay: Found running X server (pid=1061, binary=/usr/lib/xorg/Xorg)
10월 22 17:31:31 raspberrypi vncserver-x11[562]: AgentInitCheck: agent comms failure
```

**판단:** VNC와 화면 서버 사이의 통신이 실패하고 있다. X 서버의 PID가 짧은 간격으로 바뀌어 X 서버의 반복 재시작을 의심했다. 이 로그만으로 종료 이유까지 알 수는 없다.

#### 3. LightDM 로그에서 X 서버 시작 실패와 재시도 확인

확인 명령:

```bash
sudo tail -n 60 /var/log/lightdm/lightdm.log
```

실제 출력 발췌:

```text
[+89.60s] DEBUG: Process 935 exited with return value 1
[+89.60s] DEBUG: XServer 0: X server stopped
[+89.60s] DEBUG: Seat seat0: Failed to start display server - trying to restart
[+89.60s] DEBUG: XServer 0: Launching X Server
[+90.11s] DEBUG: Process 936 exited with return value 1
[+90.11s] DEBUG: XServer 0: X server stopped
```

**판단:** 화면 서버가 종료 코드 1로 실패하고 LightDM이 다시 시작하려는 상황은 확인됐다. 따라서 VNC 프로그램만의 연결 문제로 보기는 어렵다. 다만 이것이 SSH 단절이나 보드 재부팅까지 설명하는 것은 아니다.

#### 4. Xorg 로그의 오류 한 줄만으로 원인을 확정하지 않음

확인 명령:

```bash
sudo tail -n 60 /var/log/lightdm/x-0.log
sudo tail -n 100 /var/log/Xorg.0.log
```

`x-0.log`가 상세 로그 위치 `/var/log/Xorg.0.log`를 알려주어 해당 파일을 추가 확인했다.

실제 출력 발췌:

```text
[   177.213] (II) modeset(0): using drv /dev/dri/card1
[   177.214] (EE) open /dev/fb0: No such file or directory
[   177.214] (II) modeset(0): Creating default Display subsection in Screen section
[   177.214] (II) Loading sub module "glamoregl"
[   177.222] (II) Module glamoregl: vendor="X.Org Foundation"
```

**판단:** `/dev/fb0` 오류 뒤에도 modesetting 드라이버 초기화가 진행됐다. 따라서 `/dev/fb0`가 없다는 한 줄만으로 실패 원인을 확정하지 않았다. 전달된 로그가 그래픽 가속 모듈을 불러오는 부근에서 끝났다는 사실도 해당 모듈이 원인이라는 증거는 아니다.

#### 5. 커널 로그에서 모니터 미감지와 FKMS 사용 확인

확인 명령:

```bash
sudo journalctl -b -k -n 100 --no-pager
```

실제 출력 발췌:

```text
10월 22 17:38:38 raspberrypi kernel: [drm] No displays found. Consider forcing hotplug if HDMI is attached
10월 22 17:38:38 raspberrypi kernel: vc4-drm gpu: bound fe600000.firmwarekms (ops vc4_fkms_ops [vc4])
10월 22 17:38:38 raspberrypi kernel: [drm] Initialized vc4 0.0.0 20140616 for gpu on minor 1
```

**판단:** 그래픽 출력 장치가 모니터를 감지하지 못했고, FKMS 방식이 사용 중이다. 사용자가 실제 HDMI 모니터를 연결하지 않았다고 확인한 점과 일치한다. 따라서 모니터 없는 환경에서 화면 생성이 되도록 HDMI 강제 인식과 해상도 지정부터 시도하기로 했다. 이 로그는 모니터 미감지의 증거이며, X 서버 실패의 유일한 원인을 확정하는 증거는 아니다.

FKMS는 라즈베리파이의 화면 출력 방식 중 하나로, 리눅스 드라이버와 펌웨어가 화면 출력을 나눠 담당한다. 실제 모니터가 없어도 화면 데이터를 메모리에 생성할 수 있으며, VNC는 생성된 화면을 원격으로 전달할 수 있다. 이번 변경은 FKMS를 새로 켜거나 다른 방식으로 바꾼 것이 아니다.

#### 6. 기존 설정에서 강제 인식이 꺼져 있음을 확인

확인 명령:

```bash
grep -nE '^\[|hdmi_|dtoverlay=vc4|framebuffer_' /boot/config.txt
```

실제 출력 발췌:

```text
21:#hdmi_force_hotplug=1
24:#hdmi_group=1
25:#hdmi_mode=1
62:#dtoverlay=vc4-kms-v3d
79:[pi4]
80:dtoverlay=vc4-fkms-v3d
84:[all]
```

**판단:** `#`로 시작하는 HDMI 설정과 KMS 설정은 주석이므로 비활성이다. 반면 `[pi4]` 구간의 FKMS 설정은 활성이다. 이 구성에 맞춰 파일 맨 아래 `[all]` 구간에 HDMI0 강제 인식과 해상도 설정을 추가하도록 안내했다.

#### 7. 저장 공간과 전압 상태도 함께 확인

확인 명령:

```bash
df -h / /boot
vcgencmd get_throttled
uptime
```

실제 출력 발췌:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/root        29G   11G   17G  40% /
/dev/mmcblk0p1  253M   31M  222M  13% /boot
throttled=0x0
17:39:01 up 0 min,  2 users,  load average: 1.90, 0.50, 0.17
```

**판단:** 저장 공간 부족은 확인되지 않았다. 해당 부팅에서 저전압·스로틀링 플래그도 없었다. `up 0 min`은 막 부팅한 상태라는 뜻이며, 왜 재부팅됐는지는 알려주지 않는다. 이전 부팅의 전원 문제, SD 카드 문제, SSH 단절 원인 전체를 배제한 것은 아니다.

### 판단에서 변경으로 이어진 흐름

**VNC 화면 없음 → X 서버 시작 실패 확인 → 모니터 미감지 확인 → 기존 FKMS 및 HDMI 설정 확인 → 모니터 없이 HDMI 화면을 생성하도록 세 줄 추가 → 재부팅 후 VNC로 검증 예정**

현재 단계는 원인을 완전히 확정하고 해결을 확인한 상태가 아니라, 로그와 현재 구성에 맞는 작은 설정 변경을 시도한 상태다. 화면이 복구되지 않으면 저장된 설정과 새로운 Xorg 로그를 확인해야 한다.

### 무엇을 추가했나?

변경 파일: **`/boot/config.txt`**

파일 맨 아래의 기존 `[all]` 구간에 다음 세 줄을 추가하도록 안내했다. 사용자가 편집 중 전달한 내용은 아래와 같다.

```ini
[all]
gpu_mem=128

hdmi_force_hotplug:0=1
hdmi_group:0=2
hdmi_mode:0=85
```

| 항목 | 의미 | 추가 이유 |
| --- | --- | --- |
| `[all]` | 이후 설정을 모든 보드 모델에 적용하는 구간 | 기존 파일 맨 아래 구간을 사용. 현재 장치는 Pi 4 |
| `gpu_mem=128` | GPU용 메모리 128MB 지정 | 기존 값으로 유지했으며, 이번에 새로 추가한 설정이 아님 |
| `hdmi_force_hotplug:0=1` | 첫 번째 HDMI 출력에 모니터가 연결된 것으로 강제 인식 | 실제 모니터 없이도 화면 출력을 생성하도록 시도 |
| `hdmi_group:0=2` | 첫 번째 HDMI 출력에 DMT 해상도 규격 사용 | 아래 해상도 번호를 DMT 기준으로 해석하도록 지정 |
| `hdmi_mode:0=85` | DMT 모드 85, 1280×720·60Hz 지정 | VNC에 사용할 화면 크기와 주사율 지정 |

`:0`은 첫 번째 HDMI 출력인 HDMI0를 뜻한다. 이 세 줄은 **Wi-Fi 이름, 비밀번호, IP 또는 SSH 설정을 변경하지 않는다.** 여기서는 구형 Raspberry Pi OS의 FKMS 구성을 기준으로 적용했으며, 최신 KMS 환경에 그대로 적용하는 절차는 아니다.

### 실행한 명령과 용도

라즈베리파이 SSH 터미널에서 실행했다.

```bash
sudo cp -n /boot/config.txt /boot/config.txt.before-vnc
```

변경 전 설정 파일을 백업한다. `-n`은 같은 이름의 백업이 이미 있으면 덮어쓰지 않는다. 따라서 이 파일이 항상 가장 최근 편집 직전 상태라는 보장은 없다.

```bash
sudo nano /boot/config.txt
```

관리자 권한으로 설정 파일을 편집한다. nano에서 위 설정을 입력한 뒤 **Ctrl+O → Enter**로 저장하고 **Ctrl+X**로 종료하도록 안내했다.

```bash
sudo reboot
```

부팅 시 읽는 HDMI 설정을 적용하기 위해 재부팅한다. 실제 출력에서 SSH 연결이 원격 호스트에 의해 종료된 것을 확인했다. 재부팅 명령은 전달됐지만, 이후 정상 부팅과 VNC 복구는 아직 확인 전이다.

편집 후 셸에서 나온 `$'\177': 명령어를 찾을 수 없음`은 삭제 키에 해당하는 문자가 명령으로 입력됐을 때의 오류다. 이 메시지는 설정 파일 저장 성공 여부를 알려주지 않으며, 이후 `sudo reboot` 실행은 진행됐다.

### 재부팅 후 확인할 것

1. 약 2분 뒤 Windows 핫스팟의 연결된 장치에서 현재 IP를 확인한다.
2. VNC로 현재 IP에 접속해 데스크톱이 표시되는지 확인한다.
3. 화면이 표시되지 않으면 SSH로 접속해 파일 저장 여부를 먼저 확인한다.

```bash
ssh pi@<Pi IP>
```

위 주소가 바뀌었다면 현재 IP로 바꿔 실행한다. 접속 후 다음 명령으로 파일 마지막 부분을 확인한다.

```bash
tail -n 12 /boot/config.txt
```

세 HDMI 설정이 마지막 `[all]` 구간에 저장됐는지 확인한다. 파일에 값이 있는 것만으로 화면 생성 성공까지 확인되는 것은 아니다.

### 문제가 생기면 되돌리는 방법

아래는 **복원이 필요할 때만** 실행한다. 이번 작업에서는 아직 실행하지 않았다. 백업 이후 다른 설정도 변경했다면 해당 변경까지 되돌아가므로 먼저 백업 내용을 확인한다.

```bash
cat /boot/config.txt.before-vnc
```

백업이 되돌릴 상태가 맞으면 복원하고 재부팅한다.

```bash
sudo cp /boot/config.txt.before-vnc /boot/config.txt
sudo reboot
```

**현재 상태:** 백업·편집 명령 및 재부팅 명령 실행은 전달받았다. 최종 파일 저장 상태, 재부팅 후 접속, VNC 화면 복구는 아직 확인하지 못했다.

## 12. 접속 후 추가 확인 명령

다음은 필요할 때 라즈베리파이 SSH 터미널에서 실행할 수 있는 확인 명령이다. 이번 대화에서는 결과를 아직 확인하지 않았다.

현재 Wi-Fi 이름 확인:

```bash
iwgetid -r
```

할당된 IP 확인:

```bash
hostname -I
```

정확한 OS 버전 확인:

```bash
cat /etc/os-release
```

정상 종료:

```bash
sudo shutdown -h now
```

종료 명령 후 충분히 기다려 종료된 것을 확인하고 전원을 분리한다.
