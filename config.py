"""
중앙 설정 파일
모든 API 엔드포인트와 모델명을 여기서 관리합니다.
"""
import os
import logging
from dotenv import load_dotenv  # 👈 [핵심] .env 파일을 읽는 도구 추가

# ==============================================
# 환경 변수 로드 (가장 먼저 실행)
# ==============================================
load_dotenv()  # 👈 [핵심] .env 파일 강제 로드

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")  # 선택사항

# ==============================================
# Groq API 설정 (NEW - 새벽 뉴스 분석용)
# ==============================================
# Groq API 키 (https://console.groq.com 에서 발급)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq 모델 설정
# - llama-3.3-70b-versatile: 심층 분석용 (280 TPS, 정확)
# - llama-3.1-8b-instant: 빠른 필터링용 (560 TPS, 저렴)
GROQ_MODEL_DEEP = os.getenv("GROQ_MODEL_DEEP", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

# Groq Rate Limit 설정 (Free tier: 30 RPM, 14,400 RPD)
GROQ_RATE_LIMIT_DELAY_FAST = 2.0  # 8b 모델 호출 간 대기 (초)
GROQ_RATE_LIMIT_DELAY_DEEP = 4.0  # 70b 모델 호출 간 대기 (초)

# AI 분석 모드 선택
# "groq": Groq API 사용 (새벽 대량 분석에 추천)
# "gemini": Google Gemini 사용 (기존 방식)
# "auto": Groq 우선, 실패 시 Gemini 폴백
AI_ANALYZER_MODE = os.getenv("AI_ANALYZER_MODE", "auto")

# ==============================================
# Gemini API 설정 (2026년 최신 버전)
# ==============================================
# ✅ gemini-2.5-flash: 2026년 안정 버전 (빠르고 저렴)
# 대안: gemini-2.5-pro (더 강력하지만 느리고 비쌈)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_VERSION = "v1"  # v1 사용 (v1beta는 불안정)

def get_gemini_api_url():
    """Gemini API URL 생성"""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
    return f"https://generativelanguage.googleapis.com/{GEMINI_API_VERSION}/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"

# ==============================================
# 검색 키워드 설정
# ==============================================
# 영문 키워드 (Google, Bing, Yahoo 등)
KEYWORDS_EN = [
    "Euthanasia",
    "Assisted Suicide", 
    "Death with Dignity",
    "Medical Assistance in Dying",
    "MAID",
    "Right to Die"
]

# 한글 키워드 (Naver)
KEYWORDS_KO = [
    "웰다잉",
    "조력존엄사",
    "안락사",
    "존엄사",
    "의사조력자살"
]

# ==============================================
# 일본어 키워드 (일본 경제 뉴스)
# ==============================================
KEYWORDS_JA = [
    # 경제/금융
    "経済", "株式", "金利", "日銀", "円安", "円高",
    "インフレ", "デフレ", "景気",
    # 산업
    "半導体", "電気自動車", "バッテリー", "AI", "人工知能",
    # 무역/한국 관련
    "輸出", "輸入", "貿易", "関税",
    "韓国", "サムスン", "現代自動車", "韓国経済"
]

# ==============================================
# 중국어 키워드 (중국 경제 뉴스)
# ==============================================
KEYWORDS_ZH = [
    # 경제/금융
    "经济", "股市", "股票", "利率", "人民币", "通胀",
    # 산업
    "半导体", "芯片", "电动汽车", "电池", "新能源",
    "人工智能",
    # 무역/한국 관련
    "贸易", "关税", "出口", "进口",
    "韩国", "三星", "现代汽车", "SK海力士"
]

# ==============================================
# 뉴스 수집 설정
# ==============================================
COLLECTOR_BATCH_SIZE = 50  # DB 저장 시 배치 크기
COLLECTOR_LOOKBACK_DAYS = 2  # 중복 체크 기간 (일)
COLLECTOR_MAX_ARTICLES_PER_SOURCE = 100  # 소스당 최대 수집 개수

# 수집 주기 설정 (분)
DEFAULT_COLLECTION_INTERVAL = 360  # 6시간 (권장: 12시간)

# ==============================================
# API 타임아웃 및 재시도 설정
# ==============================================
API_TIMEOUT = 30  # 초
# 재시도 관련: 무료 플랜을 고려해 기본 대기 시간을 늘립니다.
API_RETRY_DELAY = 10  # 초 (기본 2초 → 10초로 증가)
API_MAX_RETRIES = 3  # 최대 재시도 횟수

# ==============================================
# 로깅 설정
# ==============================================
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "./logs")

def setup_logger(name, enable_file_logging=True):
    """로거 설정 헬퍼 함수
    
    Args:
        name: 로거 이름
        enable_file_logging: 파일 로깅 활성화 여부 (기본값: True)
    
    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    if not logger.handlers:
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)
        
        # 파일 핸들러 (enable_file_logging=True일 때)
        if enable_file_logging:
            try:
                os.makedirs(LOG_DIR, exist_ok=True)
                log_file = os.path.join(LOG_DIR, f"{name.replace('.', '_')}.log")
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"파일 로깅 설정 실패: {e}")
    
    return logger

# ==============================================
# 뉴스 소스 URL 설정
# ==============================================
NEWS_SOURCES = {
    "google": {
        "enabled": True,
        "url_template": "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
        "name": "Google News"
    },
    "bing": {
        "enabled": True,
        "url_template": "https://www.bing.com/news/search?q={query}&format=rss",
        "name": "Bing News"
    },
    "yahoo": {
        "enabled": False,  # Yahoo RSS는 2026년 현재 비활성
        "url_template": "https://news.yahoo.com/rss/search?p={query}",
        "name": "Yahoo News"
    },
    "naver": {
        "enabled": True,
        "url_template": "https://search.naver.com/search.naver?where=news&query={query}&sort=1",
        "name": "Naver News"
    },
    "newsapi": {
        "enabled": bool(NEWSAPI_KEY),  # API 키가 있을 때만 활성화
        "url_template": "https://newsapi.org/v2/everything?q={query}&apiKey={api_key}&language=en&sortBy=publishedAt",
        "name": "NewsAPI"
    }
}

# ==============================================
# Reddit RSS 소스 (커뮤니티 반응)
# ==============================================
REDDIT_SOURCES = [
    "https://www.reddit.com/r/euthanasia/.rss",
    "https://www.reddit.com/r/RightToDie/.rss",
    "https://www.reddit.com/r/deathwithdignity/.rss"
]

# ==============================================
# 직접 뉴스사이트 RSS
# ==============================================
DIRECT_RSS_SOURCES = [
    {
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "name": "BBC News",
        "country": "UK"
    },
    {
        "url": "https://www.theguardian.com/world/rss",
        "name": "The Guardian",
        "country": "UK"
    },
    {
        "url": "https://www.reuters.com/rssFeed/worldNews",
        "name": "Reuters World",
        "country": "Global"
    }
]

# ==============================================
# 경제/금융 전문 뉴스 RSS (신규)
# ==============================================
FINANCE_RSS_SOURCES = [
    # 미국/글로벌 경제 전문 (작동 확인됨)
    {
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "name": "WSJ World News",
        "country": "US",
        "category": "finance"
    },
    {
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "name": "WSJ Markets",
        "country": "US",
        "category": "markets"
    },
    {
        "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "name": "WSJ US Business",
        "country": "US",
        "category": "finance"
    },
    {
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "name": "BBC Business",
        "country": "UK",
        "category": "finance"
    },
    {
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "name": "BBC Technology",
        "country": "UK",
        "category": "tech"
    },
    {
        "url": "https://feeds.npr.org/1006/rss.xml",
        "name": "NPR Business",
        "country": "US",
        "category": "finance"
    },
    {
        "url": "https://feeds.npr.org/1019/rss.xml",
        "name": "NPR Technology",
        "country": "US",
        "category": "tech"
    },
    # 아시아 뉴스 (확장)
    {
        "url": "https://www3.nhk.or.jp/rss/news/cat5.xml",
        "name": "NHK Business",
        "country": "Japan",
        "category": "finance",
        "lang": "ja"
    },
    {
        "url": "https://www.scmp.com/rss/91/feed",
        "name": "SCMP Business",
        "country": "China/HK",
        "category": "finance",
        "lang": "en"  # 영문 제공
    },
    {
        "url": "https://www.scmp.com/rss/5/feed",
        "name": "SCMP China",
        "country": "China",
        "category": "economy",
        "lang": "en"
    },
    {
        "url": "https://asia.nikkei.com/rss/feed/nar",
        "name": "Nikkei Asia",
        "country": "Japan",
        "category": "finance",
        "lang": "en"
    },
    {
        "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
        "name": "CNA Business",
        "country": "Singapore",
        "category": "finance",
        "lang": "en"
    },
]

# ==============================================
# Slack 알림 설정
# ==============================================
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_ENABLED = bool(SLACK_WEBHOOK_URL)
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_CHANNEL", "#news-alerts")

# ==============================================
# 한국 시장 영향 분석용 키워드 (신규)
# ==============================================
# 경제/금융 영향 키워드 (영문)
KEYWORDS_FINANCE_EN = [
    # 금리/통화정책
    "Federal Reserve", "Fed rate", "interest rate", "inflation", "CPI",
    "Jerome Powell", "FOMC", "monetary policy", "rate hike", "rate cut",
    # 반도체
    "semiconductor", "chip", "NVIDIA", "TSMC", "Intel", "AMD",
    "memory chip", "DRAM", "NAND", "HBM", "AI chip",
    # 2차전지/전기차
    "electric vehicle", "EV", "Tesla", "battery", "lithium",
    "cathode", "anode", "EV battery", "charging",
    # 자동차
    "Hyundai", "Kia", "Toyota", "auto sales", "car market",
    # 빅테크
    "Apple", "Google", "Microsoft", "Amazon", "Meta",
    "AI", "artificial intelligence", "ChatGPT", "OpenAI",
    # 무역/관세
    "tariff", "trade war", "export", "import", "sanction",
    "China trade", "trade restriction",
    # 원자재
    "oil price", "crude oil", "gold", "copper", "natural gas",
    # 한국 직접 관련
    "South Korea", "Korean", "Samsung", "SK Hynix", "LG",
    "KOSPI", "won", "KRW",
]

# 한국 시장 영향 분석용 섹터 키워드 매핑
SECTOR_KEYWORDS = {
    "반도체": ["semiconductor", "chip", "NVIDIA", "TSMC", "Intel", "AMD", "memory", "DRAM", "NAND", "HBM", "AI chip", "Samsung Electronics", "SK Hynix"],
    "2차전지": ["battery", "EV battery", "lithium", "cathode", "anode", "Tesla", "electric vehicle", "LG Energy", "Samsung SDI"],
    "자동차": ["Hyundai", "Kia", "Toyota", "auto", "car sales", "EV", "electric vehicle", "Genesis"],
    "바이오": ["biotech", "pharmaceutical", "drug", "FDA", "clinical trial", "vaccine"],
    "IT/인터넷": ["Apple", "Google", "Microsoft", "Amazon", "Meta", "AI", "cloud", "Naver", "Kakao"],
    "금융": ["interest rate", "Fed", "bank", "financial", "credit", "loan"],
    "조선": ["shipbuilding", "LNG carrier", "container ship", "offshore"],
    "화학/정유": ["oil", "crude", "refinery", "petrochemical", "LG Chem"],
    "철강": ["steel", "iron ore", "POSCO"],
    "방산": ["defense", "military", "weapon", "missile", "Korea defense"],
    "원자력": ["nuclear", "uranium", "reactor", "nuclear power"],
    "엔터": ["K-pop", "BTS", "HYBE", "entertainment", "drama", "Netflix Korea"],
}

# ==============================================
# 품질 점수 가중치
# ==============================================
QUALITY_WEIGHTS = {
    "title_translation": 30,  # 제목 번역 품질
    "summary_completeness": 40,  # 요약 완성도
    "category_accuracy": 15,  # 카테고리 정확도
    "sentiment_analysis": 15   # 감정 분석
}

# 유효한 카테고리
VALID_CATEGORIES = [
    "Law/Policy",
    "Medical",
    "Social/Ethics",
    "Tech/Industry",
    "Research",
    "Personal Story"
]

# 유효한 감정
VALID_SENTIMENTS = [
    "Positive",
    "Negative",
    "Neutral"
]

# ==============================================
# 설정 검증
# ==============================================
def validate_config():
    """필수 환경변수 검증"""
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "GOOGLE_API_KEY": GOOGLE_API_KEY
    }
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        raise ValueError(f"❌ 필수 환경변수 누락: {', '.join(missing)}")
    
    return True

# 모듈 import 시 자동 검증 (선택사항)
if __name__ == "__main__":
    try:
        validate_config()
        print("✅ 설정 검증 완료")
        print(f"   - Gemini API URL: {get_gemini_api_url()[:80]}...")
        print(f"   - 활성 뉴스 소스: {sum(1 for s in NEWS_SOURCES.values() if s['enabled'])}개")
    except Exception as e:
        print(f"❌ 설정 오류: {e}")