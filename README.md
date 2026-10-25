# Ribbon / 리본

Muse 가젯 연결을 사용하는 개인 AI 웹 작업실. 별도 모델 API 키 없이 공식 가젯 프로토콜로 실제 답변과 공개 진행 상태를 받아온다.

**웹:** https://ribbon-hambug.hambugi-ricecale.chatgpt.site (소유자만 접근, ChatGPT 로그인 필요)

현재 구현: 대화별 기록 저장, 최근 맥락 전달, 실제 Muse 답변 및 진행 상태, 연결 상태·실행 위치 표시, 중복 요청 ID 처리, 연결 중단 시 자동 재전송 방지. PC 조작 도구나 실제 화면 클릭 좌표는 아직 연결하지 않았다.

현재 실행 위치: 웹과 데이터는 Sites 클라우드. 로컬 WSL에서 웹 전체 왕복 시험에 성공한 뒤 로컬 연결 프로그램을 중단하고, 인증 정보를 일회용 X25519/AES-GCM 암호화로 사용자 자신의 Muse 클라우드 VM에 이전했다. 그곳에서 systemd 서비스 설치·시작까지 확인했지만, 웹 접속 오류의 원인을 진단하는 명령이 Muse의 `needs_approval` 상태라 사용자 앱 승인을 기다리고 있다. 현재 클라우드 답변 및 PC 종료 시험은 미완료다.

- `web/`: Cloudflare Worker 웹/API와 D1 스키마, 테스트.
- `connector/`: Linux용 Muse 연결 프로그램과 이전 안내.
- `scripts/`: Bluetooth·페어링·메시지 왕복 검증 도구.

아래는 연결 검증 과정의 기록이다.

## 개발 검증 및 다음 작업

- 개인용 웹/API 배포 성공. Sites 소유자 전용 접근 유지.
- 실제 웹 요청 → 로컬 연결 프로그램 → Muse → 웹 답변 저장 성공. 응답: `리본 웹 연결 성공`.
- 웹 인증·중복 요청·단일 작업 점유·중단 시 재전송 방지·출력 스크립트 검사 5개 통과.
- 암호화 이전 테스트: 암호문 변조/다른 수신자 키 거부, 0600/0700 권한, 일회용 키 제거 및 재사용 거부 확인.
- Muse 클라우드에 프로그램과 비공개 상태 파일 설치 완료. 아직 네트워크 연결 검증을 통과하지 못했다.
- `Run-DirectMuseTask.py --resume`은 마지막 접수된 진단 작업을 구독만 하며 새 요청을 전송하지 않는다. 사용자 승인 후 이 경로로 결과를 이어서 확인할 수 있다.
- `Test-CloudWithoutWsl.mjs`는 Windows에서 WSL 종료 상태를 앞뒤로 확인하고 클라우드 답변을 검증하는 도구다. 아직 성공 판정 전이며, 자격증명은 숨김 표준입력으로만 받는다.
- 최종 PC 전원 종료·폰 웹 시험, 장치 토큰 갱신, 클라우드 재시작 복구는 별도 확인이 필요하다.

같은 장치 identity를 로컬과 클라우드에서 동시에 실행하지 않는다. 클라우드 이전 뒤 로컬 상태 파일은 자동 동기화되지 않는다.

## Windows 연결 사전 검사

Windows PowerShell 5.1에서 실행:

```powershell
powershell.exe -NoProfile -File scripts/Test-Bluetooth.ps1
```

이 검사는 Windows Bluetooth API로 기본 어댑터의 BLE peripheral 지원을 확인하고 공식 Muse 서비스 UUID로 GATT 서비스 생성 및 임시 광고를 시도한다. 광고가 시작되면 3초 후 중단하며 인증 정보를 요청하지 않는다. 정상 통과 시 종료 코드 0, 어댑터 미발견 시 2, 서비스 또는 광고 실패 시 3을 반환한다. 실행 호스트가 오류 코드를 다르게 표시할 수 있으므로 JSON 결과를 함께 확인한다.

## 2026-10-25 현재 PC의 실측 결과

- Windows 11 Home, Intel Wireless Bluetooth (USB VID 8087 / PID 0A2A).
- BLE central 지원: true.
- BLE peripheral 지원: false.
- Bluetooth가 꺼진 최초 검사에서는 GATT 서비스 생성: RadioNotAvailable.
- Bluetooth를 켠 재검사에서는 GATT 서비스 생성: Success.
- 실제 광고 시작 시도: 실패. Windows 오류 0x8007013C (The device does not support the command feature).
- 따라서 현재 Windows 드라이버/어댑터 상태에서는 가젯으로 광고하고 휴대폰 연결을 받는 실험을 진행할 수 없었다. 실제 Muse 앱 페어링은 수행하지 않았다.

Bluetooth 이어폰 연결 기능과 가젯 서버 기능은 다르다. 이 결과만으로 하드웨어가 모든 운영체제에서 불가능하다고 판정하지 않는다. 다른 드라이버/운영체제 또는 Windows BLE peripheral 지원이 확인된 어댑터에서 재검사해야 한다. Linux 설치만으로 해결된다고 보장하지 않는다.

다음 단계는 사용 가능한 어댑터에서 peripheral 기능을 확인한 후 Windows GATT 전송부를 구현하고 공식 SDK의 SetupController 및 PairingSession에 연결하는 것이다. 앱이 발급하는 실제 장치 인증 정보가 필요하며 단순히 연결 완료 상태만 만드는 것으로 대체할 수 없다.

## 공식 근거

- [Microsoft peripheral 지원 속성](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothadapter.isperipheralrolesupported)
- [Muse Linux SDK](https://github.com/facebookincubator/muse-gadget-sdk/tree/c9354b7a765cfb7dd3c4f1945a9ca838d871630c/linux)
- [Muse SDK 토큰 이용 범위](https://gadgets.muse.ai/sdk-terms)

SDK 토큰, pairing.json, 인증 정보는 저장소에 올리지 않는다.

## WSL 우회 경로: 실측 성공 (2026-10-25)

동일한 Intel Bluetooth 장치를 usbipd-win으로 Ubuntu에 전달한 경우 Linux에서는 central/peripheral 역할 및 advertising이 지원됐다.

- WSL 3.0.3 / kernel 6.18.54.1 / Ubuntu 24.04, 배포 이름 `Ribbon-Ubuntu`.
- usbipd-win 5.3.0 설치 및 Intel USB 장치 전달 성공.
- `hci0` 인식, BlueZ peripheral 역할 및 광고 인스턴스 지원 확인.
- 공식 SDK `BleServer`로 Muse GATT 서비스 등록 성공, 12초 임시 광고 성공.
- BlueZ의 `ActiveInstances > 0` 확인: `ACTIVE_ADVERTISEMENT_VERIFIED=True`.
- 공식 SDK 페어링 암호화·BLE setup·응답 추적 테스트 98개 통과.
- 검사 후 장치를 Windows로 돌려놓음. 휴대폰 검색·실제 Muse 계정 페어링은 아직 미실시.

이는 Windows의 미지원 표시가 이 장치의 모든 환경에서의 불가능을 뜻하지 않음을 실측으로 확인한 것이다. 현재 PC에서는 ESP32 없이 기존 Bluetooth를 사용해 다음 페어링 시험을 진행할 수 있다.

Linux 도구 준비(새 환경에서 root로 실행):

```bash
bash scripts/Prepare-Linux.sh
```

설치되는 SDK 커밋은 위의 고정 버전이다. 이 스크립트는 Muse 명령 실행 서비스를 활성화하거나 계정 페어링을 수행하지 않는다.

Bluetooth가 WSL에 전달된 동안 임시 광고 검사:

```bash
/opt/ribbon/venv/bin/python scripts/Test-LinuxAdvertisement.py
```

임시 광고는 등록·광고 경로만 검증하며 앱의 등록 요청에는 응답하지 않는다. 실제 페어링 시에는 휴대폰 Muse 앱, 유효한 SDK 토큰, 공식 pairing 흐름이 필요하다. SDK 토큰만으로 크레딧 차감 방식이나 클라우드 이전 성공이 보장되지는 않는다.

## 실제 계정 연결 성공 (2026-10-25)

휴대폰 Muse 앱과의 페어링에서 `auth_ok`, `setup complete`, `Paired.` 확인.
이후 저장된 장치 인증 정보를 사용한 별도 인터넷 연결 시험에서 다음을 확인했다.

- VM 조회 성공.
- 암호화 Noise 세션 연결 성공.
- `link.register` 서버 접수 성공: `registered with the Muse`.
- `MUSE_CONNECTION_REGISTERED=True`.

`scripts/Test-MuseConnection.py`는 명령을 전혀 등록하지 않고 채팅도 보내지 않는 연결 전용 검사다. 이 검사에서는 계정 크레딧 차감 방식, 답변 구독, 클라우드 이전을 검증하지 않았다. 페어링 완료 후 Bluetooth 장치는 Windows로 반환했다.

SDK 토큰은 `scripts/Start-Pairing.ps1`의 숨김 입력으로 받아 Linux 전용 상태 디렉터리에 저장한다. 이 도우미는 현재 로컬 작업 경로와 `Ribbon-Ubuntu` 배포 이름에 맞춘 실험용 스크립트다.

## 실제 문자 왕복 성공 (2026-10-25)

`scripts/Test-MuseChat.py`로 별도 대화에 고유 문자열 반환 요청을 보내고 실제 답변을 수신했다.

- 최종 시험에서 `received_bound_reply: true`, `nonce_matched: true`.
- 요청 접수부터 완료 확인까지 2.72초.
- working / responding / online 공개 상태 이벤트도 수신.
- Muse에 PC 명령은 등록하지 않음.

중요한 서버 동작: 아직 만들어지지 않은 session_id로 `/chat/subscribe`를 호출하면 HTTP 404가 반환됐다. 전체 구독은 열렸지만 별도 대화 답변을 받지 못해 첫 메시지 시험은 120초 후 종료됐다. 두 번째 메시지 시험에서는 전송 접수 후 생성된 session_id를 직접 구독해 답변을 받았다. 실제 메시지 전송은 총 두 번이며, 응답을 못 받은 첫 요청도 사용량이 발생했을 수 있다.

현재 스크립트는 실행할 때마다 테스트 메시지 한 번을 보낸다. 자동 재전송하지 않는다. 마지막 요청 식별 정보와 접수 결과는 Linux의 비공개 상태 디렉터리 `ribbon_probe.json`에 저장한다. 새 대화 전송 후 구독 사이의 이벤트 재생 및 연결 복구 보장은 아직 검증하지 않았다.

이로써 가젯 연결 프로그램에서 전송·진행 상태·답변 수신이 가능함을 실계정으로 확인했다. 웹 브라우저 연결, 기존 크레딧의 정확한 차감, 클라우드 이전, PC 종료 상태에서의 동작은 다음 검증 대상이다.
