import feedparser
from deep_translator import GoogleTranslator
from typing import List, Dict, Optional
import time
import re
import logging
from datetime import datetime
from functools import lru_cache
from dateutil import parser as date_parser
from supabase import create_client, Client
import streamlit as st
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 🔐 Supabase 설정
# ==========================================
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    else:
        SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
except FileNotFoundError:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Supabase Init Fail: {e}")

# ==========================================
# 🌍 수집 대상 국가 (더 많은 국가 추가)
# ==========================================
TARGET_REGIONS = [
    {"code": "US", "lang": "en", "name": "미국"},
    {"code": "KR", "lang": "ko", "name": "한국"},
    {"code": "CN", "lang": "zh-CN", "name": "중국"},
    {"code": "JP", "lang": "ja", "name": "일본"},
    {"code": "DE", "lang": "de", "name": "독일"},
    {"code": "FR", "lang": "fr", "name": "프랑스"},
    {"code": "GB", "lang": "en", "name": "영국"},
    {"code": "IN", "lang": "en", "name": "인도"},
    {"code": "TW", "lang": "zh-TW", "name": "대만"},
    {"code": "SG", "lang": "en", "name": "싱가포르"},  # 추가
    {"code": "HK", "lang": "zh-HK", "name": "홍콩"},    # 추가
    {"code": "CA", "lang": "en", "name": "캐나다"},     # 추가
]

# ==========================================
# 🔍 경제 카테고리 (자동 필터링용)
# 느슨한 필터: 경제 관련 단어가 하나라도 있으면 통과
# ==========================================
BROAD_ECONOMIC_KEYWORDS = {
    "en": [
        # 비즈니스 일반
        "business", "economy", "market", "stock", "trade", "industry", "company", 
        "corporate", "enterprise", "commercial", "finance", "investment",
        
        # 기술/산업
        "tech", "technology", "semiconductor", "chip", "AI", "electric", "battery",
        "energy", "oil", "gas", "automotive", "manufacturing",
        
        # 금융
        "bank", "fed", "rate", "inflation", "GDP", "currency", "dollar", "euro",
        "yen", "yuan", "crypto", "bitcoin", "bond", "debt",
        
        # 기업/경영
        "CEO", "earnings", "revenue", "profit", "loss", "merger", "acquisition",
        "IPO", "startup", "venture", "deal", "contract",
        
        # 무역/정책
        "export", "import", "tariff", "sanction", "regulation", "policy",
        "government", "tax", "subsidy"
    ],
    
    "ko": [
        "경제", "시장", "주식", "기업", "산업", "금융", "투자", "무역",
        "반도체", "배터리", "전기차", "기술", "금리", "환율", "달러",
        "삼성", "현대", "LG", "SK", "실적", "매출", "수출", "정책"
    ],
    
    "ja": [
        "経済", "市場", "株式", "企業", "産業", "金融", "投資", "貿易",
        "半導体", "電気", "技術", "金利", "為替", "ドル", "円",
        "トヨタ", "ソニー", "業績", "輸出"
    ],
    
    "zh": [
        "经济", "市场", "股票", "企业", "产业", "金融", "投资", "贸易",
        "半导体", "电池", "技术", "利率", "汇率", "美元", "人民币",
        "华为", "腾讯", "阿里", "业绩", "出口"
    ],
    
    "de": [
        "wirtschaft", "markt", "unternehmen", "industrie", "handel", "technologie",
        "finanzen", "börse", "politik"
    ],
    
    "fr": [
        "économie", "marché", "entreprise", "industrie", "commerce", "technologie",
        "finance", "bourse", "politique"
    ]
}

# ==========================================
# 번역 서비스 (속도 개선)
# ==========================================
class TranslationService:
    _instance = None
    _translator = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._translator = GoogleTranslator(source='auto', target='ko')
        return cls._instance

    @lru_cache(maxsize=5000)  # 캐시 크기 증가
    def translate(self, text: str) -> Optional[str]:
        try:
            time.sleep(0.15)  # 딜레이 감소 (0.2 -> 0.15)
            return self._translator.translate(text)
        except Exception:
            return None

# ==========================================
# 뉴스 모니터 엔진 (대폭 개선)
# ==========================================
class NewsMonitor:
    def __init__(self):
        self.translator = TranslationService()
        self.cjk_pattern = re.compile(r'[\u3131-\uD79D\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]')
        self.patterns = {}
        
        # 넓은 경제 필터 패턴 미리 컴파일
        self.broad_patterns = self._compile_broad_patterns()

    def _compile_broad_patterns(self):
        """경제 관련 넓은 필터 패턴 생성"""
        patterns = {}
        
        for lang, keywords in BROAD_ECONOMIC_KEYWORDS.items():
            patterns[lang] = []
            for keyword in keywords:
                # CJK는 단순 포함, 영문은 단어 경계
                if self._is_cjk(keyword):
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                else:
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                patterns[lang].append(pattern)
        
        return patterns

    def _is_cjk(self, text):
        """키워드에 한글/한자/일본어가 포함되어 있는지 확인"""
        return bool(self.cjk_pattern.search(text))

    def _is_economic_article(self, title: str, lang: str) -> bool:
        """
        [핵심 개선] 넓은 경제 필터
        - 경제 관련 단어가 하나라도 있으면 True
        - 빠른 사전 필터링으로 번역 전에 걸러냄
        """
        # 주 언어 패턴 체크
        if lang in self.broad_patterns:
            for pattern in self.broad_patterns[lang]:
                if pattern.search(title):
                    return True
        
        # 영어 패턴도 추가 체크 (다국어 기사 대비)
        if lang != "en" and "en" in self.broad_patterns:
            for pattern in self.broad_patterns["en"][:20]:  # 상위 20개만
                if pattern.search(title):
                    return True
        
        return False

    def load_keywords_from_db(self):
        """DB에서 사용자 정의 키워드 로드"""
        if not supabase:
            return {}
        
        try:
            response = supabase.table("search_keywords").select("*").execute()
            rows = response.data
            
            if not rows:
                return {}

            mapping = {}
            
            for row in rows:
                category = row['category']
                keyword = row['keyword']
                
                if self._is_cjk(keyword):
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                else:
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                
                mapping[pattern] = (category, keyword)
            
            self.patterns = mapping
            return mapping
            
        except Exception as e:
            logger.error(f"키워드 로딩 실패: {e}")
            return {}

    def analyze(self, text: str):
        """사용자 정의 키워드로 카테고리 분류"""
        found_cats = set()
        found_keys = set()
        
        if not self.patterns:
            self.load_keywords_from_db()

        for pattern, (cat, key) in self.patterns.items():
            if pattern.search(text):
                found_cats.add(cat)
                found_keys.add(key)
        
        # [개선] 키워드가 없어도 "일반 경제" 카테고리로 분류
        if not found_cats:
            found_cats.add("일반 경제")
                
        return list(found_keys), list(found_cats)

    def save_db(self, item):
        """DB 저장 (배치 처리 가능하도록 개선)"""
        if not supabase:
            return
        try:
            supabase.table("news_articles").upsert(item, on_conflict="link").execute()
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def fetch_by_region(self, region_config, max_articles=50):
        """
        [대폭 개선] 국가별 뉴스 수집
        - 더 많은 기사 스캔 (20 -> 100)
        - 넓은 경제 필터 적용
        - 번역 최소화
        """
        lang = region_config['lang']
        country = region_config['code']
        url = f"https://news.google.com/rss?hl={lang}&gl={country}&ceid={country}:{lang}"
        
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                logger.warning(f"{region_config['name']}: 기사 없음")
                return 0
        except Exception as e:
            logger.error(f"{region_config['name']} RSS 로드 실패: {e}")
            return 0

        count = 0
        processed = 0
        
        # [개선] 최대 100개까지 스캔 (기존 20개)
        for entry in feed.entries[:100]:
            title = entry.get('title', '').strip()
            if not title:
                continue
            
            link = entry.link
            processed += 1
            
            # === STEP 1: 넓은 경제 필터 (번역 전) ===
            # 언어 자동 감지
            detect_lang = lang
            if lang.startswith("zh"):
                detect_lang = "zh"
            
            # 경제 관련 아니면 스킵
            if not self._is_economic_article(title, detect_lang):
                continue
            
            # === STEP 2: 번역 (한국어가 아닐 때만) ===
            final_title = title
            if lang != 'ko' and not self._is_cjk(title):
                trans = self.translator.translate(title)
                if trans:
                    final_title = trans
            
            # === STEP 3: 키워드 분석 (번역 후) ===
            keywords, categories = self.analyze(final_title)
            
            # === STEP 4: 저장 ===
            try:
                pub_date = date_parser.parse(entry.get('published', '')).isoformat()
            except:
                pub_date = datetime.now().isoformat()

            data = {
                "title": final_title,
                "original_title": title,
                "link": link,
                "published_at": pub_date,
                "source": entry.get('source', {}).get('title', 'Unknown'),
                "keywords": keywords if keywords else ["경제"],
                "categories": categories,
                "country": region_config['name'],
                "language": lang
            }
            
            self.save_db(data)
            count += 1
            
            # [개선] 국가당 최대 수집 개수 제한
            if count >= max_articles:
                break
        
        logger.info(f"{region_config['name']}: {processed}개 스캔 → {count}개 저장")
        return count

monitor = NewsMonitor()

def run_global_batch():
    """
    [개선] 전 세계 배치 수집
    - 국가당 최소 20개 목표
    - 총 200개 이상 수집 목표
    """
    monitor.load_keywords_from_db()
    total_saved = 0
    logs = []
    
    logger.info("=" * 60)
    logger.info("🌍 글로벌 뉴스 배치 수집 시작")
    logger.info("=" * 60)
    
    for region in TARGET_REGIONS:
        try:
            # 국가당 30개까지 수집 (12개국 × 30 = 최대 360개)
            saved = monitor.fetch_by_region(region, max_articles=30)
            if saved > 0:
                total_saved += saved
                log_msg = f"✅ {region['name']}: {saved}개 저장"
                logs.append(log_msg)
                logger.info(log_msg)
            else:
                log_msg = f"⚠️ {region['name']}: 0개"
                logs.append(log_msg)
                logger.warning(log_msg)
        except Exception as e:
            log_msg = f"❌ {region['name']}: 오류 ({str(e)[:50]})"
            logs.append(log_msg)
            logger.error(log_msg)
    
    logger.info("=" * 60)
    logger.info(f"🎉 총 {total_saved}개 뉴스 수집 완료!")
    logger.info("=" * 60)
    
    return total_saved, logs

def add_keyword(category, keyword):
    """키워드 추가"""
    if supabase:
        supabase.table("search_keywords").insert({
            "category": category,
            "language": "AUTO",
            "keyword": keyword
        }).execute()

def delete_keyword(keyword_id):
    """키워드 삭제"""
    if supabase:
        supabase.table("search_keywords").delete().eq("id", keyword_id).execute()

def get_all_keywords():
    """모든 키워드 조회"""
    if supabase:
        return supabase.table("search_keywords").select("*").order("category").execute().data
    return []
