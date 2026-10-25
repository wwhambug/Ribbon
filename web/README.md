# 리본 웹

비공개 Sites 웹 작업실. 화면과 API는 단일 Worker이며 D1에 대화·작업·답변 이벤트를 보관한다. 공식 Sites의 소유자 전용 접근 경계를 전제로 한다. 공개 서비스나 여러 사용자 공유용 권한 모델은 구현하지 않았다.

`worker/index.js`에 화면과 API가 있다. 사용자 입력과 모델 답변은 DOM의 textContent로 표시한다. 모델이 만든 HTML/스크립트는 실행하지 않는다. Muse 인증 정보와 Sites 서비스 자격증명은 브라우저에 보내지 않는다.

필요한 런타임 비밀 값은 Sites의 `BRIDGE_TOKEN`이다. 연결 프로그램에는 추가로 Sites 서비스 접근 토큰이 필요하다. 비밀 값은 이 저장소나 hosting.json에 넣지 않는다.

Node 24 이상에서 로컬 검증·미리보기:

```bash
node --test tests/worker.test.mjs
node scripts/dev.mjs
node scripts/build.mjs
node scripts/validate-artifact.mjs
```

로컬 미리보기는 loopback에만 바인딩하고 로컬 개발용 identity를 부여한다. 배포된 Worker에서는 Sites 인증 헤더 또는 비밀 연결 토큰 없이는 API를 사용할 수 없다. 개발용 기본 토큰은 배포에 사용하지 않는다.

마이그레이션은 `db/schema.js`와 drizzle-kit으로 생성한다. 이미 적용한 SQL과 메타데이터를 수정하지 말고 다음 마이그레이션을 추가한다. 빌드 산출물:

```text
dist/
├── .openai/
│   └── hosting.json
│   └── drizzle/
└── server/
    └── index.js
```

Sites source helper로 정확히 푸시된 커밋에서 빌드·패키지한 뒤 소유자 전용 배포를 사용한다. 기존 프로젝트 ID와 비공개 접근 설정을 유지한다.
