# Ribbon / 리본

Muse 가젯 연결을 웹 AI 리본으로 이어가기 위한 초기 실험 저장소.

## Windows 연결 사전 검사

Windows PowerShell 5.1에서 실행:

```powershell
powershell.exe -NoProfile -File scripts/Test-Bluetooth.ps1
```

이 검사는 Windows Bluetooth API로 기본 어댑터의 BLE peripheral 지원을 확인하고 공식 Muse 서비스 UUID로 GATT 서비스 생성을 시도한다. 광고를 시작하거나 인증 정보를 요청하지 않는다. 정상 통과 시 종료 코드 0, 어댑터 미발견 시 2, 기능 또는 서비스 생성 미지원 시 3을 반환한다. 실행 호스트가 오류 코드를 다르게 표시할 수 있으므로 JSON 결과를 함께 확인한다.

## 2026-10-25 현재 PC의 실측 결과

- Windows 11 Home, Intel Wireless Bluetooth (USB VID 8087 / PID 0A2A).
- BLE central 지원: true.
- BLE peripheral 지원: false.
- Muse UUID의 GATT 서비스 생성: RadioNotAvailable.
- 따라서 현재 Windows 드라이버/어댑터 상태에서는 가젯으로 광고하고 휴대폰 연결을 받는 실험을 진행할 수 없었다. 실제 Muse 앱 페어링은 수행하지 않았다.

Bluetooth 이어폰 연결 기능과 가젯 서버 기능은 다르다. 이 결과만으로 하드웨어가 모든 운영체제에서 불가능하다고 판정하지 않는다. 다른 드라이버/운영체제 또는 Windows BLE peripheral 지원이 확인된 어댑터에서 재검사해야 한다. Linux 설치만으로 해결된다고 보장하지 않는다.

다음 단계는 사용 가능한 어댑터에서 peripheral 기능을 확인한 후 Windows GATT 전송부를 구현하고 공식 SDK의 SetupController 및 PairingSession에 연결하는 것이다. 앱이 발급하는 실제 장치 인증 정보가 필요하며 단순히 연결 완료 상태만 만드는 것으로 대체할 수 없다.

## 공식 근거

- [Microsoft peripheral 지원 속성](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothadapter.isperipheralrolesupported)
- [Muse Linux SDK](https://github.com/facebookincubator/muse-gadget-sdk/tree/c9354b7a765cfb7dd3c4f1945a9ca838d871630c/linux)
- [Muse SDK 토큰 이용 범위](https://gadgets.muse.ai/sdk-terms)

SDK 토큰, pairing.json, 인증 정보는 저장소에 올리지 않는다.
