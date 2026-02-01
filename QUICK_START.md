# ⚡ 빠른 설치 가이드 (5분)

## 📦 1. 프로젝트 설치 (1분)

```bash
# 저장소 클론
git clone [your-repo-url]
cd global-well-dying-archive

# 가상환경 생성 (권장)
python -m venv venv

# 활성화
source venv/bin/activate  # Mac/Linux
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

## 🔑 2. API 키 설정 (3분)

```bash
# 환경변수 파일 생성
cp .env.example .env
```

`.env` 파일을 열고 다음을 입력:

### 필수 (2개)

1. **Supabase** (1분)
   - https://supabase.com → 가입 → 프로젝트 생성
   - Settings → API → URL과 Key 복사
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGci...
   ```

2. **Gemini API** (1분)
   - https://aistudio.google.com/app/apikey
   - "Get API key" 클릭 → 키 복사
   ```
   GOOGLE_API_KEY=AIzaSy...
   ```

### 선택사항 (나중에 추가 가능)

3. **NewsAPI** (30초)
   - https://newsapi.org/register
   ```
   NEWSAPI_KEY=1234567...
   ```

4. **Telegram** (1분)
   - Telegram에서 @BotFather 검색 → `/newbot`
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
   TELEGRAM_CHAT_ID=123456789
   ```

## 🗃️ 3. 데이터베이스 설정 (1분)

Supabase 콘솔에서:

1. 좌측 메뉴 → SQL Editor
2. 아래 코드 복사 → 붙여넣기 → Run

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

-- 일일 리포트
CREATE TABLE daily_reports (
    id BIGSERIAL PRIMARY KEY,
    report_date DATE UNIQUE NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_news_created_at ON news(created_at);
CREATE INDEX idx_news_is_processed ON news(is_processed);
CREATE INDEX idx_news_link ON news(link);
```

## ✅ 4. 테스트 실행 (30초)

```bash
# 연결 테스트
python main.py test
```

**기대 출력**:
```
[Supabase]
  ✅ 연결 성공

[Gemini API]
  ✅ API URL 생성 성공
```

## 🚀 5. 첫 실행 (바로 시작!)

```bash
# 뉴스 수집 테스트
python main.py collect

# 성공하면 전체 파이프라인 실행
python main.py --force
```

---

## 📋 주요 명령어 치트시트

```bash
# 전체 실행 (자동)
python main.py

# 강제 실행 (주기 무시)
python main.py --force

# 개별 모듈
python main.py collect   # 수집만
python main.py analyze   # 분석만
python main.py report    # 리포트만

# 모니터링
python main.py stats     # 통계
python main.py test      # 연결 테스트

# 디버깅
python test_rss.py       # RSS 테스트
python test_naver.py     # Naver 구조 확인
```

---

## ❗ 문제 발생 시

### 1. 모듈을 찾을 수 없음
```bash
pip install -r requirements.txt
```

### 2. Supabase 연결 실패
- `.env` 파일이 프로젝트 루트에 있는지 확인
- URL이 `https://`로 시작하는지 확인

### 3. Gemini API 404
- 2026년 기준 `gemini-2.5-flash` 모델 사용
- API 키가 올바른지 확인

### 4. Naver 스크래핑 실패
```bash
python test_naver.py
# HTML 구조 변경 시 collector.py 수정 필요
```

---

## 🎯 다음 단계

1. **정기 실행 설정** (Cron, Task Scheduler)
   ```bash
   # Linux/Mac: crontab -e
   0 */6 * * * cd /path/to/project && /path/to/venv/bin/python main.py
   ```

2. **대시보드 확인**
   - Supabase 콘솔에서 데이터 확인
   - 또는 Streamlit 대시보드 실행 (별도 개발 필요)

3. **커스터마이징**
   - `config.py`: 키워드, 수집 주기 등
   - 추가 뉴스 소스 등록

---

**🎉 설치 완료! 자동으로 글로벌 웰다잉 뉴스가 수집됩니다.**

**자세한 설명은 `README.md`와 `API_SETUP_GUIDE.md`를 참고하세요.**
