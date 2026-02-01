# 🚀 완벽 설치 가이드 (처음부터 끝까지)

**소요 시간: 약 30분**

이 가이드는 GitHub에 저장소를 만드는 것부터 Streamlit Cloud 배포까지 모든 과정을 다룹니다.

---

## 📋 준비물 체크리스트

시작 전에 다음을 준비하세요:

- [ ] GitHub 계정 (없으면 https://github.com 에서 가입)
- [ ] 컴퓨터에 Git 설치 (https://git-scm.com/downloads)
- [ ] Python 3.11 설치 (https://www.python.org/downloads/)

---

## 🎯 PART 1: GitHub 저장소 생성 및 코드 업로드 (5분)

### Step 1-1: GitHub에 저장소 생성

1. GitHub에 로그인 → https://github.com
2. 오른쪽 위 **+** 버튼 → **New repository** 클릭
3. 다음 정보 입력:
   ```
   Repository name: global-well-dying-archive
   Description: AI-powered news monitoring system for well-dying topics
   Public (추천) 또는 Private
   ✅ Add a README file (체크)
   ```
4. **Create repository** 클릭

### Step 1-2: 저장소를 컴퓨터에 복제

터미널(Windows: Git Bash, Mac/Linux: Terminal) 실행:

```bash
# 작업할 폴더로 이동 (예: 바탕화면)
cd ~/Desktop

# 저장소 복제 (your-username을 실제 GitHub 유저명으로 변경!)
git clone https://github.com/your-username/global-well-dying-archive.git

# 폴더로 이동
cd global-well-dying-archive
```

### Step 1-3: 제공받은 파일들 복사

Claude가 만들어준 **모든 파일**을 이 폴더에 복사합니다:

```
global-well-dying-archive/
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml
├── config.py
├── database.py
├── collector.py
├── analyzer.py
├── reporter.py
├── main.py
├── app.py               ← 대시보드!
├── test_naver.py
├── test_rss.py
├── requirements.txt
├── runtime.txt
├── .env.example
├── README.md
├── QUICK_START.md
├── API_SETUP_GUIDE.md
└── GITHUB_ACTIONS_GUIDE.md
```

### Step 1-4: Git에 업로드

```bash
# 모든 파일 추가
git add .

# 커밋 (변경사항 저장)
git commit -m "Initial commit: Add all project files"

# GitHub에 업로드
git push origin main
```

**✅ 확인**: GitHub 저장소 페이지를 새로고침하면 파일들이 보여야 합니다!

---

## 🔑 PART 2: API 키 발급 (10분)

### Step 2-1: Supabase (필수)

1. https://supabase.com 접속 → 회원가입
2. **New Project** 클릭
3. 정보 입력:
   ```
   Project name: well-dying-archive
   Database Password: 안전한 비밀번호 (저장 필수!)
   Region: Northeast Asia (Seoul) ← 한국 사용자
   ```
4. **Create new project** → 1-2분 대기
5. 완료 후:
   - 좌측 **Settings** → **API**
   - **Project URL** 복사 → 메모장에 저장
   - **anon public** 키 복사 → 메모장에 저장

### Step 2-2: Gemini API (필수)

1. https://aistudio.google.com/app/apikey 접속
2. **Get API key** 클릭
3. **Create API key** 클릭
4. 키 복사 → 메모장에 저장

### Step 2-3: NewsAPI (선택, 권장)

1. https://newsapi.org/register 접속
2. 이메일, 이름 입력 → Submit
3. 화면에 표시된 API 키 복사 → 메모장에 저장

### Step 2-4: Telegram Bot (선택)

1. Telegram 앱 실행
2. **@BotFather** 검색
3. `/newbot` 입력
4. 봇 이름 입력 (예: Well-Dying News Bot)
5. 봇 사용자명 입력 (예: welldying_news_bot)
6. **토큰** 복사 → 메모장에 저장
7. 새로 만든 봇 검색 → `/start` 메시지 전송
8. 브라우저에서 접속:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   (YOUR_TOKEN을 실제 토큰으로 교체)
9. JSON에서 `"chat":{"id":123456789}` 찾기
10. **숫자** 복사 → 메모장에 저장

---

## 🗃️ PART 3: Supabase 데이터베이스 설정 (3분)

1. Supabase 프로젝트 접속
2. 좌측 메뉴 **SQL Editor** 클릭
3. 아래 SQL 코드 **전체 복사** → 붙여넣기 → **Run** 클릭

```sql
-- 뉴스 테이블
CREATE TABLE news (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    title_ko TEXT,
    link TEXT UNIQUE NOT NULL,
    description TEXT,
    published_at TIMESTAMPTZ,
    source TEXT,
    country TEXT,
    content_hash TEXT,
    summary_ai TEXT,
    category TEXT,
    sentiment TEXT,
    is_processed BOOLEAN DEFAULT false,
    quality_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 설정 테이블
CREATE TABLE settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    interval_minutes INTEGER DEFAULT 360,
    last_run TIMESTAMPTZ DEFAULT '2000-01-01T00:00:00+00:00',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 일일 리포트 테이블
CREATE TABLE daily_reports (
    id BIGSERIAL PRIMARY KEY,
    report_date DATE UNIQUE NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 키워드 테이블
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- 금지어 테이블
CREATE TABLE ban_words (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- 모니터링 사이트 테이블
CREATE TABLE monitored_sites (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    rss_url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성 (성능 향상)
CREATE INDEX idx_news_created_at ON news(created_at);
CREATE INDEX idx_news_is_processed ON news(is_processed);
CREATE INDEX idx_news_link ON news(link);
```

**✅ 확인**: 좌측 **Table Editor**에서 테이블들이 생성되었는지 확인

---

## ☁️ PART 4: Streamlit Cloud 배포 (7분)

### Step 4-1: Streamlit Cloud 가입

1. https://share.streamlit.io 접속
2. **Sign up with GitHub** 클릭
3. GitHub 계정으로 로그인
4. Streamlit에 권한 허용

### Step 4-2: 앱 배포

1. 우측 상단 **New app** 클릭
2. 정보 입력:
   ```
   Repository: your-username/global-well-dying-archive
   Branch: main
   Main file path: app.py
   App URL: welldying-archive (원하는 이름)
   ```
3. **Advanced settings** 클릭
4. Python version: **3.11** 선택

### Step 4-3: Secrets 설정 (중요!)

**Secrets** 섹션에 다음 내용을 **정확히** 복사하여 붙여넣기:

```toml
# Supabase (필수)
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."

# Gemini API (필수)
GOOGLE_API_KEY = "AIzaSy..."

# NewsAPI (선택)
NEWSAPI_KEY = "1234567890abcdef..."

# Telegram (선택)
TELEGRAM_BOT_TOKEN = "1234567890:ABC..."
TELEGRAM_CHAT_ID = "123456789"

# GitHub (대시보드에서 원격 실행용 - 선택)
GITHUB_PAT = "ghp_..."
GITHUB_OWNER = "your-username"
GITHUB_REPO = "global-well-dying-archive"
```

**⚠️ 주의사항**:
- **따옴표 유지** (제거하지 마세요!)
- **실제 값으로 교체** (xxxxx 부분)
- **줄바꿈 정확히** 입력

### Step 4-4: 배포 시작

1. **Deploy!** 클릭
2. 3-5분 대기 (커피 한 잔 ☕)
3. 배포 완료! 🎉

**✅ 확인**: 대시보드가 열리고 데이터가 보이는지 확인 (처음엔 비어있음)

---

## 🔄 PART 5: GitHub Actions 설정 (5분)

### Step 5-1: GitHub Secrets 설정

1. GitHub 저장소 페이지 접속
2. **Settings** 탭 클릭
3. 좌측 **Secrets and variables** → **Actions** 클릭
4. **New repository secret** 클릭

아래 Secrets를 **하나씩** 추가:

| Name | Value |
|------|-------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | `eyJhbGci...` |
| `GOOGLE_API_KEY` | `AIzaSy...` |
| `NEWSAPI_KEY` | `1234567...` (선택) |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABC...` (선택) |
| `TELEGRAM_CHAT_ID` | `123456789` (선택) |

**⚠️ 주의**: 
- **따옴표 없이** 값만 입력!
- 대소문자 정확히!

### Step 5-2: 워크플로우 수동 실행 (첫 테스트)

1. **Actions** 탭 클릭
2. 좌측 "Well-Dying Archive Pipeline" 선택
3. **Run workflow** 버튼 클릭
4. **Run workflow** 확인
5. 실행 시작! (노란색 점)

### Step 5-3: 로그 확인

1. 방금 시작한 워크플로우 클릭
2. "run-pipeline" 클릭
3. 각 단계 펼쳐서 로그 확인:
   ```
   ✅ Test connections
   ✅ Collect news
   ✅ Analyze articles
   ...
   ```

**✅ 확인**: 모든 단계가 초록색 체크로 완료되어야 함

---

## 🎉 완료! 시스템 확인

### 1. Supabase에서 데이터 확인

1. Supabase → **Table Editor** → **news** 테이블
2. 수집된 기사들이 보여야 함

### 2. Streamlit 대시보드 확인

1. 배포된 URL 접속 (예: https://welldying-archive.streamlit.app)
2. **News Feed** 탭에서 기사 확인
3. **Management** 탭에서 키워드 추가 테스트

### 3. Telegram 알림 확인 (설정했다면)

- 매일 한국 시간 오전 10시에 브리핑 수신

---

## ❓ 문제 해결

### Streamlit 배포 실패

**증상**: "ModuleNotFoundError" 또는 빨간 에러
**해결**:
1. `requirements.txt`에 패키지가 모두 있는지 확인
2. `runtime.txt`가 `python-3.11`인지 확인
3. Secrets 형식이 정확한지 확인 (따옴표 필수!)

### GitHub Actions 실패

**증상**: 빨간 X 표시
**해결**:
1. Secrets 이름 대소문자 확인
2. Secrets 값에 공백 없는지 확인
3. 로그에서 정확한 에러 메시지 확인

### Supabase 연결 실패

**증상**: "Supabase 클라이언트가 초기화되지 않았습니다"
**해결**:
1. URL이 `https://`로 시작하는지 확인
2. Key가 `eyJ`로 시작하는지 확인
3. Secrets/환경변수 이름 확인

### 기사가 수집되지 않음

**증상**: 테이블이 비어있음
**해결**:
1. GitHub Actions가 정상 실행되었는지 확인
2. `python test_rss.py` 실행하여 RSS 소스 확인
3. Naver가 실패했다면 `python test_naver.py` 실행

---

## 📱 일상적인 사용 방법

### 매일 하는 것
- **없음!** 자동으로 6시간마다 수집됨

### 일주일에 한 번
- 대시보드 접속하여 기사 확인
- 필요시 키워드 추가/삭제

### 한 달에 한 번
- Supabase Storage 용량 확인 (무료: 500MB)
- GitHub Actions 사용량 확인 (Public은 무제한)

---

## 🎯 다음 단계

1. **키워드 커스터마이징**
   - 대시보드 → Management → Keywords
   - 관심있는 키워드 추가

2. **Telegram 브리핑 확인**
   - 매일 오전 10시 한국 시간
   - 트렌드 및 인사이트 확인

3. **데이터 분석**
   - AI Insights 탭에서 감정 분석 확인
   - Daily Reports에서 과거 브리핑 확인

---

**🎉 축하합니다! 모든 설정이 완료되었습니다!**

**질문이나 문제가 있으면 GitHub Issues에 남겨주세요.**
