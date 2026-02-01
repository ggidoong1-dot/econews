# 🌍 Global Well-Dying Archive

글로벌 웰다잉/안락사/존엄사 뉴스를 자동 수집하고 AI로 분석하는 시스템

## 📋 주요 기능

### 1. 🔍 다중 소스 뉴스 수집
- **Google News**: 글로벌 뉴스 검색
- **Bing News**: 대체 뉴스 소스
- **NewsAPI**: 15,000+ 뉴스사이트 (선택사항)
- **Naver News**: 한국 뉴스 스크래핑
- **Reddit RSS**: 커뮤니티 반응
- **Direct RSS**: BBC, Guardian, Reuters 등

### 2. 🤖 AI 기반 분석
- **Gemini 2.5 Flash** 사용
- 한글 제목 자동 번역
- 3줄 요약 생성
- 카테고리 분류 (법/정책, 의료, 사회/윤리, 기술/산업)
- 감정 분석 (찬성/반대/중립)
- 품질 점수 계산

### 3. 📊 일일 브리핑
- 트렌드 요약
- 감정 분포 분석
- 신규 키워드 추출
- Telegram 자동 전송

### 4. 💾 Supabase 통합
- 실시간 데이터베이스
- 중복 제거
- 통계 및 분석

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone [your-repo-url]
cd global-well-dying-archive

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어서 API 키 입력
```

### 2. 필수 API 키 발급

#### Supabase (필수)
1. https://supabase.com 가입
2. 새 프로젝트 생성
3. Settings → API → URL과 anon key 복사
4. `.env`에 입력

#### Google Gemini API (필수)
1. https://aistudio.google.com/app/apikey 접속
2. "Get API key" 클릭
3. `.env`에 입력

#### NewsAPI (선택사항)
1. https://newsapi.org/register 가입
2. 무료: 100 requests/day
3. `.env`에 입력

#### Telegram Bot (선택사항)
1. Telegram에서 @BotFather 검색
2. `/newbot` 명령으로 봇 생성
3. 토큰 복사 → `.env`에 입력
4. 봇과 대화 시작 후 Chat ID 확인
   ```bash
   # Chat ID 확인 방법
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```

### 3. 데이터베이스 테이블 생성

Supabase에서 다음 SQL 실행:

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

-- 키워드 테이블 (선택사항)
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- 국가 테이블 (선택사항)
CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- 금지어 테이블 (선택사항)
CREATE TABLE ban_words (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- 인덱스 생성
CREATE INDEX idx_news_created_at ON news(created_at);
CREATE INDEX idx_news_is_processed ON news(is_processed);
CREATE INDEX idx_news_source ON news(source);
CREATE INDEX idx_news_link ON news(link);
```

### 4. 실행

```bash
# 연결 테스트
python main.py test

# 전체 파이프라인 실행
python main.py

# 강제 실행 (주기 무시)
python main.py --force

# 개별 모듈 실행
python main.py collect   # 수집만
python main.py analyze   # 분석만
python main.py report    # 리포트만

# 통계 확인
python main.py stats
```

## 🛠️ 문제 해결

### Naver 스크래핑 실패

```bash
# HTML 구조 분석
python test_naver.py

# 생성된 파일 확인
cat naver_sample.html
```

### RSS 피드 테스트

```bash
python test_rss.py
```

### API 연결 오류

```bash
# 환경변수 확인
python -c "import config; config.validate_config()"

# 개별 테스트
python database.py  # DB 연결
python main.py test  # 전체 연결
```

## 📊 시스템 구조

```
global-well-dying-archive/
├── config.py           # 중앙 설정 관리
├── database.py         # Supabase 연동
├── collector.py        # 뉴스 수집기
├── analyzer.py         # AI 분석기
├── reporter.py         # 일일 리포터
├── main.py            # 통합 실행 스크립트
├── test_naver.py      # Naver 디버그 도구
├── test_rss.py        # RSS 테스트 도구
├── requirements.txt   # Python 패키지
├── .env.example       # 환경변수 템플릿
└── README.md          # 이 파일
```

## 🔧 설정 커스터마이징

### `config.py`에서 설정 가능:

```python
# 수집 주기 (분)
DEFAULT_COLLECTION_INTERVAL = 360  # 6시간

# 중복 체크 기간 (일)
COLLECTOR_LOOKBACK_DAYS = 2

# 키워드 추가/수정
KEYWORDS_EN = ["Euthanasia", "Assisted Suicide", ...]
KEYWORDS_KO = ["웰다잉", "조력존엄사", ...]

# 뉴스 소스 활성화/비활성화
NEWS_SOURCES = {
    "google": {"enabled": True},
    "bing": {"enabled": True},
    "newsapi": {"enabled": bool(NEWSAPI_KEY)},
    "naver": {"enabled": True}
}
```

## 📈 성능 최적화

### 1. API 레이트 리밋
- Gemini Free: 15 RPM
- NewsAPI Free: 100 requests/day
- `config.py`에서 대기 시간 조정

### 2. 배치 처리
```bash
# 분석 배치 크기 조정
python main.py analyze --batch-size 20
```

### 3. 수집 최적화
- 키워드 단순화 (OR 연산자 제거)
- 개별 키워드로 여러 번 검색
- 작동하지 않는 소스 비활성화

## 🐛 알려진 이슈

### 1. Naver 스크래핑
- **문제**: HTML 구조 변경 시 실패
- **해결**: `test_naver.py` 실행 후 selector 업데이트

### 2. Yahoo RSS
- **문제**: 2026년 현재 비활성
- **해결**: `config.py`에서 비활성화됨

### 3. 중복 기사
- **문제**: Google RSS는 최근 100개만 제공
- **해결**: 다양한 소스 추가 (NewsAPI, Reddit 등)

## 🚀 향후 계획

- [ ] 본문 스크래핑 기능 (newspaper3k)
- [ ] 주간 요약 리포트
- [ ] 대시보드 UI (Streamlit)
- [ ] 키워드 트렌드 분석
- [ ] 다국어 지원 확대
- [ ] 이메일 알림

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 풀 리퀘스트를 환영합니다!

## 📧 문의

프로젝트 이슈 페이지에 질문을 남겨주세요.

---

**Made with ❤️ for Well-Dying Research**
