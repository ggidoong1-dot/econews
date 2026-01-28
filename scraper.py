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

# 수집 대상 국가 및 언어 설정 (이건 그대로 둠)
TARGET_REGIONS = [
    {"code": "US", "lang": "en", "name": "미국"},
    {"code": "KR", "lang": "ko", "name": "한국"},
    {"code": "JP", "lang": "ja", "name": "일본"},
    {"code": "CN", "lang": "zh-CN", "name": "중국"},
    {"code": "DE", "lang": "de", "name": "독일"},
    {"code": "ES", "lang": "es", "name": "스페인"},
]

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

    @lru_cache(maxsize=3000)
    def translate(self, text: str) -> Optional[str]:
        try:
            time.sleep(0.2)
            return self._translator.translate(text)
        except Exception:
            return None

# ==========================================
# 뉴스 모니터 엔진
# ==========================================
class NewsMonitor:
    def __init__(self):
        self.translator = TranslationService()
        self.patterns = {} # 초기화 시점에는 비워둠

    def load_keywords_from_db(self):
        """DB에서 키워드를 최신으로 불러와서 패턴 컴파일"""
        if not supabase: return {}
        
        try:
            # DB에서 모든 키워드 가져오기
            response = supabase.table("search_keywords").select("*").execute()
            rows = response.data
            
            if not rows:
                logger.warning("DB에 키워드가 없습니다.")
                return {}

            mapping = {}
            cjk_langs = ['ko', 'ja', 'zh', 'zh-CN']
            
            for row in rows:
                category = row['category']
                lang = row['language']
                keyword = row['keyword']
                
                # 정규식 생성
                if lang in cjk_langs:
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
        found_cats = set()
        found_keys = set()
        
        # 키워드가 비어있으면 DB에서 로딩 시도
        if not self.patterns:
            self.load_keywords_from_db()

        for pattern, (cat, key) in self.patterns.items():
            if pattern.search(text):
                found_cats.add(cat)
                found_keys.add(key)
                
        return list(found_keys), list(found_cats)

    def save_db(self, item):
        if not supabase: return
        try:
            supabase.table("news_articles").upsert(item, on_conflict="link").execute()
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def fetch_by_region(self, region_config):
        lang = region_config['lang']
        country = region_config['code']
        url = f"https://news.google.com/rss?hl={lang}&gl={country}&ceid={country}:{lang}"
        
        try:
            feed = feedparser.parse(url)
            if not feed.entries: return 0
        except:
            return 0

        count = 0
        for entry in feed.entries[:20]:
            title = entry.get('title', '')
            link = entry.link
            
            # 분석
            keywords, categories = self.analyze(title)
            
            if categories:
                final_title = title
                if lang != 'ko':
                    trans = self.translator.translate(title)
                    if trans: final_title = trans
                
                try:
                    pub_date = date_parser.parse(entry.get('published', '')).isoformat()
                except:
                    pub_date = datetime.now().isoformat()

                data = {
                    "title": final_title,
                    "original_title": title,
                    "link": link,
                    "published_at": pub_date,
                    "source": entry.get('source', {}).get('title', ''),
                    "keywords": keywords,
                    "categories": categories,
                    "country": region_config['name'],
                    "language": lang
                }
                
                self.save_db(data)
                count += 1
                
        return count

# 전역 인스턴스
monitor = NewsMonitor()

def run_global_batch():
    # 실행할 때마다 최신 키워드 반영을 위해 DB 다시 로드
    monitor.load_keywords_from_db()
    
    total_saved = 0
    logs = []
    
    for region in TARGET_REGIONS:
        saved = monitor.fetch_by_region(region)
        if saved > 0:
            total_saved += saved
            logs.append(f"✅ {region['name']}: {saved}개 저장")
    
    return total_saved, logs

# 키워드 관리용 함수 (main.py에서 사용)
def add_keyword(category, lang, keyword):
    if supabase:
        supabase.table("search_keywords").insert({
            "category": category,
            "language": lang,
            "keyword": keyword
        }).execute()

def delete_keyword(keyword_id):
    if supabase:
        supabase.table("search_keywords").delete().eq("id", keyword_id).execute()

def get_all_keywords():
    if supabase:
        return supabase.table("search_keywords").select("*").order("category").execute().data
    return []
