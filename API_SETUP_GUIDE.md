# 🔑 API 등록 가이드

전체 시스템을 작동시키기 위해 필요한 API 키 발급 방법을 단계별로 안내합니다.

## 📋 필수 API (반드시 등록)

### 1. Supabase 설정

**무료 플랜**: 500MB DB, 무제한 API 요청

#### 단계별 가이드

1. **회원가입**
   - https://supabase.com 접속
   - "Start your project" 클릭
   - GitHub, Google 등으로 가입

2. **프로젝트 생성**
   - "New Project" 클릭
   - Project name: `well-dying-archive` (원하는 이름)
   - Database Password: 안전한 비밀번호 생성
   - Region: `Northeast Asia (Seoul)` 선택 (한국 사용자)
   - "Create new project" 클릭 (1-2분 소요)

3. **API 키 복사**
   - 좌측 메뉴에서 ⚙️ Settings 클릭
   - API 섹션 선택
   - **Project URL** 복사 → `.env`의 `SUPABASE_URL`에 붙여넣기
   - **anon public** 키 복사 → `.env`의 `SUPABASE_KEY`에 붙여넣기

4. **테이블 생성**
   - 좌측 메뉴에서 🗃️ Table Editor 클릭
   - "New Table" → "SQL Editor" 클릭
   - README.md의 SQL 코드 복사 → 실행

✅ **완료 확인**: `python main.py test` 실행 시 "[Supabase] ✅ 연결 성공" 출력

---

### 2. Google Gemini API 설정

**무료 플랜**: 
- 분당 15회 요청
- 하루 1,500회 요청
- 월 100만 토큰

#### 단계별 가이드

1. **API 키 발급**
   - https://aistudio.google.com/app/apikey 접속
   - Google 계정으로 로그인
   - "Get API key" 클릭
   - "Create API key" 클릭
   - 새 프로젝트 생성 또는 기존 프로젝트 선택

2. **키 복사**
   - 생성된 API 키 복사
   - `.env`의 `GOOGLE_API_KEY`에 붙여넣기

3. **모델 선택 (선택사항)**
   - 기본: `gemini-2.5-flash` (빠르고 저렴)
   - 고급: `gemini-2.5-pro` (더 정확하지만 느림)
   - `.env`에서 `GEMINI_MODEL` 설정

✅ **완료 확인**: `python main.py test` 실행 시 "[Gemini API] ✅ API URL 생성 성공" 출력

---

## 🎯 선택 API (권장)

### 3. NewsAPI 설정

**무료 플랜**: 하루 100회 요청

#### 장점
- 15,000+ 글로벌 뉴스사이트 접근
- 최근 1개월 기사 검색
- 안정적인 구조화된 데이터

#### 단계별 가이드

1. **회원가입**
   - https://newsapi.org/register 접속
   - 이메일, 이름 입력
   - 용도: "Personal" 또는 "Education" 선택
   - 체크박스 동의 → "Submit" 클릭

2. **API 키 확인**
   - 가입 완료 페이지에 API 키 표시
   - 또는 이메일로 전송됨
   - 또는 https://newsapi.org/account 에서 확인

3. **키 등록**
   - API 키 복사
   - `.env`의 `NEWSAPI_KEY`에 붙여넣기

✅ **완료 확인**: `python test_rss.py` 실행 시 "[NewsAPI] ✅ 발견: N개" 출력

⚠️ **주의**: 무료 플랜은 하루 100회 제한. 초과 시 다음날까지 대기.

---

### 4. Telegram Bot 설정 (일일 알림용)

**무료**: 무제한 사용

#### 장점
- 일일 브리핑 자동 전송
- 실시간 알림
- 모바일에서 확인 가능

#### 단계별 가이드

1. **봇 생성**
   - Telegram 앱에서 `@BotFather` 검색
   - `/start` 입력
   - `/newbot` 입력
   - 봇 이름 입력 (예: "Well-Dying News")
   - 봇 사용자명 입력 (예: "welldying_news_bot")
   - **토큰 복사** (예: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Chat ID 확인**
   
   방법 1 (쉬움):
   - 생성한 봇과 대화 시작 (`/start` 메시지 전송)
   - https://api.telegram.org/bot`YOUR_TOKEN`/getUpdates 접속
     (YOUR_TOKEN을 실제 토큰으로 교체)
   - JSON에서 `"chat":{"id":123456789}` 찾기
   - 숫자 복사

   방법 2 (도구 사용):
   - `@userinfobot` 검색
   - `/start` 입력
   - "Id: 123456789" 확인

3. **키 등록**
   - `.env`의 `TELEGRAM_BOT_TOKEN`에 토큰 붙여넣기
   - `.env`의 `TELEGRAM_CHAT_ID`에 Chat ID 붙여넣기

✅ **완료 확인**: `python main.py report` 실행 시 Telegram으로 메시지 수신

---

## 🧪 전체 테스트

### 1. 환경변수 확인

`.env` 파일이 다음과 같이 설정되었는지 확인:

```bash
# 필수 (3개)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GOOGLE_API_KEY=AIzaSy...

# 선택사항
NEWSAPI_KEY=1234567890abcdef...
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=123456789
```

### 2. 연결 테스트

```bash
# 가상환경 활성화
source venv/bin/activate  # Windows: venv\Scripts\activate

# 테스트 실행
python main.py test
```

**기대 출력**:
```
🔌 연결 테스트
═══════════════════════════════════════

[Supabase]
  ✅ 연결 성공
  - 국가: 0개
  - 키워드: 0개

[Gemini API]
  ✅ API URL 생성 성공
  - 모델: gemini-2.5-flash

[Telegram]
  ✅ 인증 정보 설정됨  (또는 ⚠️ 인증 정보 없음)
  
[NewsAPI]
  ✅ API 키 설정됨  (또는 ⚠️ API 키 없음)
```

### 3. 첫 실행

```bash
# 뉴스 수집만 테스트
python main.py collect

# 정상 작동 시 전체 파이프라인 실행
python main.py --force
```

---

## ❓ 문제 해결

### Supabase 연결 실패
```
❌ Supabase 클라이언트가 초기화되지 않았습니다.
```

**해결**:
1. `.env` 파일 위치 확인 (프로젝트 루트에 있어야 함)
2. URL과 KEY에 따옴표 없는지 확인
3. URL이 `https://`로 시작하는지 확인

### Gemini API 404 에러
```
❌ API HTTP 에러: 404
```

**해결**:
1. API 키가 올바른지 확인
2. `config.py`에서 `GEMINI_MODEL` 확인
3. 2026년 기준 `gemini-2.5-flash` 사용

### NewsAPI 429 에러
```
❌ HTTP 에러: 429
할당량 초과: 무료는 하루 100회 제한
```

**해결**:
1. 다음날까지 대기
2. 또는 Pro 플랜 구독
3. 일시적으로 `config.py`에서 NewsAPI 비활성화:
   ```python
   NEWS_SOURCES['newsapi']['enabled'] = False
   ```

### Telegram 메시지 전송 실패
```
❌ Telegram 전송 실패
```

**해결**:
1. 봇과 먼저 대화를 시작했는지 확인 (`/start`)
2. Chat ID가 숫자만 포함하는지 확인 (따옴표 없음)
3. 토큰 형식 확인: `숫자:영문숫자조합`

---

## 🎉 완료!

모든 API가 정상적으로 등록되었다면:

```bash
# 통계 확인
python main.py stats

# 정기 실행 (cron 또는 스케줄러 설정)
# 예: 6시간마다
0 */6 * * * cd /path/to/project && python main.py
```

**추가 도움이 필요하면 이슈를 열어주세요!** 🙋‍♂️
