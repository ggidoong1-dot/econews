import time
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import urllib.parse
import config
import collector_utils as utils

logger = config.setup_logger(__name__)


def fetch_naver_news(keywords: List[str]) -> List[Dict]:
    """
    Naver 뉴스를 스크래핑하여 수집합니다.
    """
    logger.info("📡 [Naver News] 수집 시작 (스크래핑)")
    all_articles = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for keyword in keywords:
        try:
            encoded = urllib.parse.quote(keyword)
            url = f"https://search.naver.com/search.naver?where=news&query={encoded}&sort=1"
            
            logger.debug(f"   검색어: {keyword}")
            response = requests.get(url, headers=headers, timeout=config.API_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            selectors = [
                'a.news_tit',
                '.news_area .news_tit',
                'div.news_wrap a.news_tit',
                'a[href*="n.news.naver.com"]'
            ]
            
            items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    logger.debug(f"   셀렉터 '{selector}' 사용")
                    break
            
            if not items:
                logger.warning(f"   ⚠️ 기사를 찾을 수 없습니다. HTML 구조가 변경되었을 수 있습니다.")
                with open(f'/home/claude/naver_debug_{keyword}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text[:5000])
                logger.debug(f"   디버그 HTML 저장: naver_debug_{keyword}.html")
                continue
            
            logger.debug(f"   발견: {len(items)}개")
            
            for item in items[:20]:
                try:
                    title = item.get_text(strip=True)
                    link = item.get('href', '')
                    
                    if not link or not title:
                        continue
                    
                    all_articles.append({
                        "title": title,
                        "link": link,
                        "description": "",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "source": "Naver News",
                        "country": "Korea"
                    })
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue
            
            time.sleep(1)
            
        except requests.exceptions.Timeout:
            logger.error(f"   ❌ 타임아웃 (30초)")
            continue
        except Exception as e:
            logger.error(f"   ❌ '{keyword}' 검색 실패: {e}")
            continue
    
    logger.info(f"   ✅ Naver News: {len(all_articles)}개 수집")
    return all_articles
