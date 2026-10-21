# 둘 AI 기능 (LLM)

앱은 정적 페이지라서 API 키를 넣을 수 없어요. 그래서 **AI 서버(`server/`)를 따로 켜고, 앱이 그 서버의 `/api/...`를 부르는** 구조예요.
LLM은 Claude API(기본) 또는 내 컴퓨터의 Ollama 중에서 고를 수 있어요.

```
브라우저(앱) ──POST /api/...──▶ AI 서버 (server/main.py, FastAPI)
                                 ├─ llm.py     Claude API 또는 Ollama (JSON 스키마로 답 모양 고정)
                                 └─ places.py  카카오 로컬 / Google Places (데이트 코스의 실제 장소)
```

## 기능과 위치

| 기능 | 앱 화면 | API | 하는 일 |
|---|---|---|---|
| AI 맞춤형 매칭 | 프로필 상세 → **AI 궁합 분석** | `match-insight` | 매칭 엔진이 계산한 근거 + 두 프로필(성향·연애 가치관·연락 빈도·생활 패턴)로 잘 맞는 점, 서로 다른 점, 알아 가기 좋은 질문을 자연어로 설명 |
| AI 대화 코치 | 채팅 입력창 옆 **AI** → 답장 추천 | `chat-coach` | 최근 대화 30개와 고른 말투(다정/유쾌/차분/담백)로 답장 후보 3개 + 끊겼을 때 이어 갈 질문 2개. 고르면 입력창에 들어감(자동 전송 안 함) |
| 첫 만남 대화 주제 | 채팅 → AI → 첫 만남 대화 주제 | `first-meet` | 공통 관심사로 주제 3~4개와 질문, 대화 흐름, 피할 질문 |
| AI 프로필 작성 도우미 | 내 정보 → 자기소개 아래 | `profile-bio` | 키워드·경험을 분위기가 다른 자기소개 후보 3개로 (120자 제한에 맞춤) |
| AI 대화 안전 점검 | 채팅 → AI → 안전 점검 / 위험 표현 알림 | `safety` | 아래 참고 |
| AI 데이트 플래너 | 채팅 → 데이트 코스 추천 → **AI 맞춤 코스 짜기** | `date-plan` | 예산·날짜·시간대·바라는 점으로 중간 지점 근처 실제 장소를 골라 2~4단계 일정, 영업시간, 이동 시간, 길찾기 링크 |

**매칭 순위는 그대로 매칭 엔진(점수 계산)이 정해요.** LLM은 "왜 잘 맞는지"를 설명하는 역할이에요. 점수는 매번 같고 설명할 수 있어야 하고(개발자 화면), 500명 전원을 LLM에 넣으면 느리고 비싸기 때문이에요.

### 안전 점검이 동작하는 방식

1. **기기 안 1차 확인 (자동)**: 상대 메시지에 금전 요구, 투자 권유, 협박, 개인정보 요구 같은 단어가 있으면 입력창 위에 알림. 대화는 밖으로 나가지 않아요. (`app_template.html`의 `RISK`에서 단어 수정)
2. **AI 점검 (회원이 누를 때만)**: 대화와 1차 결과를 LLM에 보내 위험 수준(괜찮음/주의/위험), 문제 부분, 대응 방법을 받음.
3. **신고·차단은 회원이 직접**: 결과 아래 버튼으로 신고 화면(사유와 AI 요약이 미리 채워짐)이나 차단 메뉴를 열어요. AI는 상대를 사기꾼이라고 단정하지 않도록 프롬프트로 막았고, 자동 제재는 하지 않아요.

## 내 컴퓨터에서 실행 (시연판 + AI)

필요한 것: Python 3.10 이상

```bash
cd server
copy .env.example .env        # Mac/Linux: cp .env.example .env
# .env 에 ANTHROPIC_API_KEY 채우기 (또는 LLM_BACKEND=ollama)
run_ai.bat                    # Mac/Linux: ./run_ai.sh
```

`run_ai`는 패키지 설치 → 시연판 빌드(`src/build_app.py`) → AI 서버 실행을 차례로 해요.
브라우저에서 **http://localhost:8000** 을 열고 가상 회원(`user001` / `1234`)으로 로그인하세요.
자동 매칭된 상대와 채팅해 보려면 로그아웃 후 상대 아이디로 로그인해서 답장하면 돼요 (새로고침하면 대화는 사라져요).

서버 상태 확인: http://localhost:8000/api/health → 백엔드, 모델, 장소 검색 종류

### .env 설정

| 이름 | 설명 |
|---|---|
| `LLM_BACKEND` | `anthropic`(Claude API) 또는 `ollama` |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | 기본 모델 `claude-opus-5-5`. 비용을 줄이려면 `claude-sonnet-5-5`나 `claude-haiku-5-5` |
| `ANTHROPIC_EFFORT` | 생각 깊이 `low`~`max`. 짧은 추천 위주라 기본 `low` |
| `OLLAMA_MODEL` / `OLLAMA_URL` | 무료로 쓸 때. 한국어는 `qwen2.5:7b` 이상 권장 (`ollama pull qwen2.5:7b`). RTX 3060 노트북 기준 한 번에 10~25초. qwen이 가끔 중국어로 답하면 서버가 알아서 다시 생성해요 |
| `KAKAO_REST_API_KEY` | 데이트 플래너 장소 검색 (카카오 디벨로퍼스 → 앱 → REST API 키). 영업시간은 장소 링크에서 확인 |
| `GOOGLE_PLACES_API_KEY` | 카카오 대신 Google Places (New). 영업시간까지 받아 옴, 결제 계정 필요 |
| `PLACES_PROVIDER` | `kakao` / `google` / `none`. 비우면 키가 있는 쪽 |
| `FIREBASE_PROJECT_ID` | 배포판용. 넣으면 로그인한 회원의 요청만 받음 |
| `ALLOWED_ORIGINS` | 배포판 주소 (CORS). 예: `https://dul-app.web.app` |
| `AI_RATE_LIMIT` | 한 사람이 10분에 쓸 수 있는 요청 수 (기본 40) |

장소 키가 없어도 데이트 플래너는 동작해요. 이때는 LLM이 장소 종류를 정하고 지도 검색 링크를 붙여요.

## 배포판(Firebase)에 붙이기

1. AI 서버를 인터넷에 올려요 (Cloud Run, Render, 개인 서버 등). 예: Cloud Run
   ```bash
   cd server
   gcloud run deploy dul-ai --source . --region asia-northeast3 --allow-unauthenticated \
     --set-env-vars LLM_BACKEND=anthropic,FIREBASE_PROJECT_ID=<프로젝트ID>,ALLOWED_ORIGINS=https://<프로젝트ID>.web.app \
     --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest
   ```
   (시작 명령은 `server/Procfile`에 들어 있어요)
2. `FIREBASE_PROJECT_ID`를 꼭 넣어요. 그래야 로그인한 회원만 AI를 쓸 수 있어요 (앱이 Firebase 로그인 토큰을 같이 보냄).
3. 서버 주소를 넣어 배포판을 다시 빌드해요.
   ```bash
   cd src
   DUL_AI_URL=https://dul-ai-xxxx.run.app python3 build_deploy.py ..     # Windows PowerShell: $env:DUL_AI_URL="..."; python build_deploy.py ..
   cd .. && firebase deploy --only hosting
   ```

## 개인정보

- AI 버튼을 직접 누를 때만 그 기능에 필요한 정보가 서버로 가요: 두 사람의 공개 프로필(닉네임, 나이, 구 단위 지역, 직업, 자기소개, 관심사, 생활 패턴), 해당 대화의 최근 메시지, 고른 예산·날짜.
- 보내지 않는 것: 아이디, 생년월일, 사진, 종교, 외모 정보, 정확한 위치.
- 서버는 받은 내용을 저장하지 않아요. 개인정보 처리방침 2-1에 같은 내용이 있어요.

## 고치는 곳

- 프롬프트·답 모양: `server/main.py` (기능별 함수 안 `prompt`, `schema`)
- LLM 연결: `server/llm.py`
- 장소 검색·이동 시간: `server/places.py`
- 화면: `src/app_template.html`의 `// ---------------- AI 기능` 구역
