import feedparser
from deep_translator import GoogleTranslator
from typing import List, Dict, Optional, Tuple, Set
import time
import re
import logging
from datetime import datetime
from functools import lru_cache
from dateutil import parser as date_parser
from supabase import create_client, Client
import streamlit as st
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 🔐 [보안 설정] Supabase 연결
# 깃허브에 키가 노출되지 않도록 st.secrets에서 가져옵니다.
# ==========================================
try:
    # 1. Streamlit Cloud (배포환경) 또는 로컬 .streamlit/secrets.toml 확인
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    else:
        # 2. 환경변수 확인 (Docker 등 다른 환경 대비)
        SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
except FileNotFoundError:
    # 로컬에서 secrets.toml이 없을 경우
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

# 클라이언트 생성
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Supabase 연결 초기화 실패: {e}")

# ==========================================
# 1. 키워드 설정 (관리 포인트)
# ==========================================
WATCH_KEYWORDS = {
    "반도체": {
        "ko": ["반도체", "HBM", "SK하이닉스", "삼성전자"],
        "en": ["semiconductor", "chip", "foundry", "HBM", "SK Hynix", "Samsung Electronics", "TSMC", "Nvidia", "ASML"]
    },
    "금융": {
        "ko": ["금리", "연준", "기준금리", "인플레이션"],
        "en": ["Fed", "Federal Reserve", "interest rate", "CPI", "FOMC", "inflation", "rate hike", "monetary policy"]
    },
    "전기차": {
        "ko": ["전기차", "배터리", "테슬라"],
        "en": ["EV", "electric vehicle", "battery", "Tesla", "CATL", "BYD", "Rivian", "lithium"]
    },
    "AI/기술": {
        "ko": ["AI", "인공지능", "챗GPT"],
        "en": ["AI", "artificial intelligence", "LLM", "OpenAI", "GPT", "Claude", "ChatGPT", "Gemini", "machine learning"]
    },
    "환율": {
        "ko": ["엔화", "달러", "환율", "원화"],
        "en": ["yen", "dollar", "exchange rate", "currency", "forex", "won"]
    }
}

# ==========================================
# 2. 번역 서비스 (Singleton + LRU)
# ==========================================
class TranslationService:
    _instance = None
    _translator = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._translator = GoogleTranslator(source='auto', target='ko')
        return cls._instance

    @lru_cache(maxsize=2000)
    def translate(self, text: str, rate_limit: float = 0.3) -> Optional[str]:
        try:
            time.sleep(rate_limit)
            return self._translator.translate(text)
        except Exception as e:
            logger.error(f"번역 실패: {str(e)[:100]}")
            return None
    
    @classmethod
    def clear_cache(cls):
        if cls._instance:
            cls._instance.translate.cache_clear()

# ==========================================
# 3. 뉴스 모니터 & DB 저장
# ==========================================
class NewsMonitor:
    def __init__(self):
        self.translator = TranslationService()
        self.hangul_pattern = re.compile(r'[가-힣]')
        self.eng_pattern_map = self._compile_english_patterns()
        self.korean_keywords = self._extract_korean_keywords()

    def _compile_english_patterns(self):
        mapping = {}
        for category, lang_keywords in WATCH_KEYWORDS.items():
            if "en" in lang_keywords:
                for keyword in lang_keywords["en"]:
                    # 영어는 단어 경계(\b) 체크
                    pattern = re.compile(r'\b' + re.escape(keyword.lower()) + r'\b', re.IGNORECASE)
                    mapping[pattern] = (category, keyword)
        return mapping

    def _extract_korean_keywords(self):
        ko_keywords = {}
        for category, lang_keywords in WATCH_KEYWORDS.items():
            if "ko" in lang_keywords:
                ko_keywords[category] = lang_keywords["ko"]
        return ko_keywords

    def _is_korean_fast(self, text):
        return bool(self.hangul_pattern.search(text))

    def analyze_content(self, text, is_korean_mode):
        found_k, found_c = set(), set()
        text_lower = text.lower()
        
        if is_korean_mode:
            for cat, keywords in self.korean_keywords.items():
                for k in keywords:
                    if k in text:
                        found_k.add(k)
                        found_c.add(cat)
        else:
            for pattern, (cat, k) in self.eng_pattern_map.items():
                if pattern.search(text_lower):
                    found_k.add(k)
                    found_c.add(cat)
        return len(found_c) > 0, list(found_k), list(found_c)

    def save_to_supabase(self, article_data: Dict):
        """DB 저장 (Upsert)"""
        if not supabase:
            # 로컬에서 키 설정 안하고 돌릴 때 에러 방지
            logger.warning("⚠️ Supabase 설정이 없어 DB 저장을 건너뜁니다.")
            return

        try:
            data = {
                "title": article_data["title"],
                "original_title": article_data["original"],
                "link": article_data["link"],
                "published_at": article_data["date"],
                "source": article_data["source"],
                "keywords": article_data["keywords"],
                "categories": article_data["categories"],
                "country": article_data["country"],
                "language": article_data["language"]
            }
            # 링크가 같으면 덮어쓰기(upsert)
            supabase.table("news_articles").upsert(data, on_conflict="link").execute()
            logger.info(f"💾 Saved: {article_data['title'][:20]}...")
            
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")

    def fetch_and_save(self, query="", lang_code="en", country_code="US", max_results=10):
        if query:
            url = f"https://news.google.com/rss/search?q={query}&hl={lang_code}&gl={country_code}&ceid={country_code}:{lang_code}"
        else:
            url = f"https://news.google.com/rss?hl={lang_code}&gl={country_code}&ceid={country_code}:{lang_code}"
        
        try:
            feed = feedparser.parse(url)
            if not feed.entries: return 0
        except Exception as e:
            logger.error(f"RSS 에러: {e}")
            return 0

        saved_count = 0
        scan_limit = min(max_results * 3, len(feed.entries))

        for entry in feed.entries[:scan_limit]:
            original_title = entry.get('title', '').strip()
            if not original_title: continue

            is_kr = (country_code == "KR" or lang_code == "ko" or self._is_korean_fast(original_title))
            
            final_title = original_title
            keywords, categories = [], []
            should_save = False

            if is_kr:
                match, k, c = self.analyze_content(original_title, True)
                if match:
                    keywords, categories = k, c
                    should_save = True
            else:
                # 1. 영문 필터
                match, k, c = self.analyze_content(original_title, False)
                if match:
                    # 2. 번역
                    translated = self.translator.translate(original_title)
                    if translated:
                        final_title = translated
                        # 3. 한글 2차 필터
                        _, k2, c2 = self.analyze_content(translated, True)
                        keywords = list(set(k + k2))
                        categories = list(set(c + c2))
                        should_save = True

            if should_save:
                try:
                    pub_date = date_parser.parse(entry.get('published', ''))
                    pub_date_iso = pub_date.isoformat()
                except:
                    pub_date_iso = datetime.now().isoformat()

                article_data = {
                    "title": final_title,
                    "original": original_title,
                    "link": entry.link,
                    "date": pub_date_iso,
                    "source": entry.get('source', {}).get('title', 'Unknown'),
                    "keywords": keywords,
                    "categories": categories,
                    "country": country_code,
                    "language": lang_code
                }
                
                self.save_to_supabase(article_data)
                saved_count += 1
                
                if saved_count >= max_results:
                    break
        
        return saved_count

# 전역 인스턴스
monitor = NewsMonitor()

# 외부 호출용 함수
def run_collector(query, lang, country):
    return monitor.fetch_and_save(query, lang, country)

# 뷰어용: DB 데이터 가져오기 함수
def get_db_data(limit=100):
    if not supabase: return []
    try:
        response = supabase.table("news_articles")\
            .select("*")\
            .order("published_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"데이터 조회 실패: {e}")
        return []