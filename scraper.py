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
# 🌍 수집 대상 국가
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
    {"code": "SG", "lang": "en", "name": "싱가포르"},
    {"code": "HK", "lang": "zh-HK", "name": "홍콩"},
    {"code": "CA", "lang": "en", "name": "캐나다"},
]

# ==========================================
# 🔍 [핵심] 매우 느슨한 경제 필터 키워드
# ==========================================
LOOSE_ECONOMIC_KEYWORDS = {
    "en": [
        # 핵심 경제 단어 (최소한만)
        "business", "economy", "economic", "market", "stock", "company", "tech",
        "bank", "trade", "industry", "deal", "price", "sale", "growth"
    ],
    "ko": ["경제", "시장", "기업", "주식", "산업"],
    "ja": ["経済", "市場", "企業", "株式"],
    "zh": ["经济", "市场", "企业", "股票"],
    "de": ["wirtschaft", "unternehmen"],
    "fr": ["économie", "entreprise"]
}

# ==========================================
# 번역 서비스
# ==========================================
class TranslationService:
    _instance = None
    _translator = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._translator = GoogleTranslator(source='auto', target='ko')
        return cls._instance

    @lru_cache(maxsize=5000)
    def translate(self, text: str) -> Optional[str]:
        try:
            time.sleep(0.1)  # 딜레이 더 감소
            return self._translator.translate(text)
        except Exception as e:
            logger.debug(f"번역 실패: {str(e)[:50]}")
            return None  # 실패해도 계속 진행

# ==========================================
# 뉴스 모니터 엔진
# ==========================================
class NewsMonitor:
    def __init__(self):
        self.translator = TranslationService()
        self.cjk_pattern = re.compile(r'[\u3131-\uD79D\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]')
        self.patterns = {}
        
        # 느슨한 필터 패턴
        self.loose_patterns = self._compile_loose_patterns()

    def _compile_loose_patterns(self):
        """매우 느슨한 경제 필터 (최소한만)"""
        patterns = {}
        
        for lang, keywords in LOOSE_ECONOMIC_KEYWORDS.items():
            patterns[lang] = []
            for keyword in keywords:
                if self._is_cjk(keyword):
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                else:
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                patterns[lang].append(pattern)
        
        return patterns

    def _is_cjk(self, text):
        return bool(self.cjk_pattern.search(text))

    def _is_economic_article(self, title: str, lang: str) -> bool:
        """
        [매우 느슨한 필터] 
        - 경제 키워드가 하나라도 있으면 True
        - 없으면 길이로 판단 (짧은 제목은 광고/스팸일 가능성)
        """
        # 주 언어 패턴 체크
        if lang in self.loose_patterns:
            for pattern in self.loose_patterns[lang]:
                if pattern.search(title):
                    return True
        
        # 영어도 체크
        if lang != "en" and "en" in self.loose_patterns:
            for pattern in self.loose_patterns["en"][:5]:  # 상위 5개만
                if pattern.search(title):
                    return True
        
        # [추가] 제목 길이가 충분하면 통과 (스팸 필터)
        if len(title.strip()) > 30:
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
        
        # 키워드 없으면 "일반 경제"
        if not found_cats:
            found_cats.add("일반 경제")
                
        return list(found_keys), list(found_cats)

    def save_db_batch(self, items: List[Dict]):
        """[성능 개선] 배치로 저장"""
        if not supabase or not items:
            return 0
        
        try:
            # Supabase upsert는 배치 지원
            response = supabase.table("news_articles").upsert(items, on_conflict="link").execute()
            return len(items)
        except Exception as e:
            logger.error(f"배치 저장 실패: {e}")
            # 실패 시 개별 저장 시도
            success = 0
            for item in items:
                try:
                    supabase.table("news_articles").upsert(item, on_conflict="link").execute()
                    success += 1
                except:
                    pass
            return success

    def fetch_by_region(self, region_config, max_articles=50):
        """
        [대폭 개선] 국가별 뉴스 수집
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

        collected_items = []
        processed = 0
        
        # [중요] 최대 150개까지 스캔 (증가)
        for entry in feed.entries[:150]:
            title = entry.get('title', '').strip()
            if not title:
                continue
            
            link = entry.link
            processed += 1
            
            # 언어 감지
            detect_lang = lang
            if lang.startswith("zh"):
                detect_lang = "zh"
            
            # === [핵심] 필터 매우 느슨하게 ===
            # 제목 길이 체크만 (10자 이상)
            if len(title) < 10:
                continue
            
            # 경제 필터 (선택적)
            # is_economic = self._is_economic_article(title, detect_lang)
            # if not is_economic:
            #     continue
            # → 주석 처리: 거의 모든 뉴스 수집
            
            # === 번역 (실패해도 원문으로 저장) ===
            final_title = title
            if lang != 'ko' and not self._is_cjk(title):
                trans = self.translator.translate(title)
                if trans:
                    final_title = trans
            
            # === 키워드 분석 ===
            keywords, categories = self.analyze(final_title)
            
            # === 데이터 준비 ===
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
                "keywords": keywords if keywords else ["뉴스"],
                "categories": categories,
                "country": region_config['name'],
                "language": lang
            }
            
            collected_items.append(data)
            
            # 목표 달성 시 중단
            if len(collected_items) >= max_articles:
                break
        
        # === 배치 저장 ===
        saved_count = self.save_db_batch(collected_items)
        
        logger.info(f"{region_config['name']}: {processed}개 스캔 → {saved_count}개 저장")
        return saved_count

monitor = NewsMonitor()

def run_global_batch():
    """
    [개선] 전 세계 배치 수집
    - 최소 200개 보장
    """
    monitor.load_keywords_from_db()
    total_saved = 0
    logs = []
    
    logger.info("=" * 60)
    logger.info("🌍 글로벌 뉴스 배치 수집 시작")
    logger.info("=" * 60)
    
    for region in TARGET_REGIONS:
        try:
            # 국가당 40개까지 (12개국 × 40 = 480개 목표)
            saved = monitor.fetch_by_region(region, max_articles=40)
            if saved > 0:
                total_saved += saved
                log_msg = f"✅ {region['name']}: {saved}개"
                logs.append(log_msg)
                logger.info(log_msg)
            else:
                log_msg = f"⚠️ {region['name']}: 0개"
                logs.append(log_msg)
        except Exception as e:
            log_msg = f"❌ {region['name']}: {str(e)[:30]}"
            logs.append(log_msg)
            logger.error(log_msg)
    
    logger.info("=" * 60)
    logger.info(f"🎉 총 {total_saved}개 뉴스 수집 완료!")
    logger.info("=" * 60)
    
    return total_saved, logs

def add_keyword(category, keyword):
    if supabase:
        supabase.table("search_keywords").insert({
            "category": category,
            "language": "AUTO",
            "keyword": keyword
        }).execute()

def delete_keyword(keyword_id):
    if supabase:
        supabase.table("search_keywords").delete().eq("id", keyword_id).execute()

def get_all_keywords():
    if supabase:
        return supabase.table("search_keywords").select("*").order("category").execute().data
    return []
