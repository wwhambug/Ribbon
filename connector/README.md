# 리본 연결 프로그램

공식 Muse Gadget SDK의 개인 계정 페어링을 사용한다. 모델 API 키는 필요하지 않다. 연결 정보와 토큰 갱신 상태는 영구 디렉터리에 보관해야 한다.

현재 웹은 비공개 Sites에 배포됐으며, 이 프로그램은 웹에 나가는 HTTPS 요청만 보낸다. 들어오는 포트나 PC 명령 실행 권한을 제공하지 않는다. 작업을 한 번 전송한 뒤 실패하거나 접수가 불명확해지면 자동 재전송하지 않는다.

## 상태 파일

`MUSEGADGET_STATE_DIR`(기본 `/var/lib/musegadget`)에 다음 파일이 필요하다. 파일 내용을 저장소에 커밋하거나 로그에 출력하지 않는다.

- `identity.json`: 공식 SDK 장치 identity.
- `pairing.json`: 공식 앱에서 발급한 장치 인증 정보와 갱신 토큰.
- `sdk_token`: 등록에 사용한 SDK 토큰.
- `ribbon-bridge.json`: `site_url`, `site_bearer`, `bridge_token`, `location` (`local` 또는 `cloud`).

Linux에서 상태 디렉터리는 0700, 파일은 0600으로 설정한다. 프로그램이 토큰을 갱신하므로 읽기 전용 마운트로 운영하지 않는다.

## 실행

SDK와 의존성이 준비된 Linux에서:

```bash
/opt/ribbon/venv/bin/python connector/ribbon_connector.py
```

컨테이너 실행(이미지 자체는 아직 실제 빌드 검증 전):

```bash
docker build -t ribbon-connector connector
docker run --name ribbon --restart unless-stopped -v /absolute/private/state:/data ribbon-connector
```

## 대화의 맥락

웹 대화는 D1에 저장한다. 엔진에는 작업마다 별도 Muse 세션을 만들고, 같은 웹 대화의 최근 완료된 6개 요청과 답변을 최대 약 32,000자 범위에서 전달한다. 이는 모든 과거 대화를 무제한 기억하는 방식이 아니다. PC 조작 도구는 등록하지 않으며 리본의 손은 현재 응답 전달 상태를 표시한다.

## 클라우드 이전 확인 순서

1. 이전할 클라우드 실행 환경과 영구 저장 위치를 확보한다.
2. 로컬 연결 프로그램을 중단한다. 같은 identity를 두 환경에서 동시에 실행하지 않는다.
3. 위 상태 파일을 인증된 암호화 통신으로 옮기고 `location`을 `cloud`로 바꾼다.
4. 클라우드에서 연결 프로그램을 시작한다.
5. PC의 WSL을 종료한 상태에서 웹 요청·답변 성공을 확인한다.
6. 사용자 PC를 완전히 종료한 상태에서도 폰 웹으로 확인한다.
7. 장치 토큰 갱신과 클라우드 재시작 뒤 복구도 별도로 확인한다.

현재 배포가 클라우드에서 돌아간다고 화면에 거짓 표시하지 않는다. `location` 표시는 실행 위치 설정이며, PC 종료 상태의 실제 성공 시험과는 별개다.
