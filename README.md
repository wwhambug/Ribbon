# Ribbon / 리본

Muse 가젯 연결을 웹 AI 리본으로 이어가기 위한 초기 실험 저장소.

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
