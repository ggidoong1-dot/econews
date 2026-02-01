"""
경제/금융 전문 뉴스 수집기
WSJ, BBC Business, NPR 등 경제 뉴스를 수집합니다.
"""
import time
import urllib.parse
import requests
from typing import List, Dict
import feedparser
from datetime import datetime, timezone
import config
import collector_utils as utils

logger = config.setup_logger(__name__)

# User-Agent 헤더 (RSS 차단 방지)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """RSS 피드를 User-Agent 헤더와 함께 가져옵니다."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except requests.RequestException as e:
        logger.debug(f"   요청 실패, feedparser로 재시도: {e}")
        return feedparser.parse(url)


def fetch_finance_rss() -> List[Dict]:
    """
    경제/금융 전문 RSS 피드에서 뉴스를 수집합니다.
    한국 시장 영향 분석용 키워드로 필터링합니다.
    """
    logger.info("📡 [Finance RSS] 수집 시작")
    all_articles = []
    
    # 경제/금융 키워드로 필터링
    keywords_lower = [k.lower() for k in config.KEYWORDS_FINANCE_EN]
    
    for source in config.FINANCE_RSS_SOURCES:
        try:
            url = source['url']
            name = source['name']
            country = source.get('country', 'Global')
            category = source.get('category', 'finance')
            
            logger.debug(f"   {name}: {url}")
            feed = _fetch_feed(url)
            
            # 피드 상태 확인
            if hasattr(feed, 'bozo') and feed.bozo:
                logger.warning(f"   ⚠️ {name}: 피드 파싱 문제 발생")
            
            filtered_count = 0
            for entry in feed.entries[:50]:  # 소스당 최대 50개
                try:
                    title = getattr(entry, 'title', '')
                    link = getattr(entry, 'link', '')
                    
                    if not title or not link:
                        continue
                    
                    title_lower = title.lower()
                    summary = getattr(entry, 'summary', '') or ''
                    summary_lower = summary.lower()
                    
                    # 한국 시장 관련 키워드 필터링
                    if any(kw in title_lower or kw in summary_lower for kw in keywords_lower):
                        all_articles.append({
                            "title": title,
                            "link": link,
                            "description": summary,
                            "published_at": utils.clean_date(getattr(entry, 'published', '')),
                            "source": name,
                            "country": country,
                            "category": category
                        })
                        filtered_count += 1
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue
            
            logger.debug(f"   {name}: {len(feed.entries)}개 중 {filtered_count}개 관련")
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            logger.error(f"   ❌ {source.get('name', 'Unknown')} 수집 실패: {e}")
            continue
    
    logger.info(f"   ✅ Finance RSS: {len(all_articles)}개 수집")
    return all_articles


def fetch_finance_rss_all() -> List[Dict]:
    """
    경제/금융 전문 RSS에서 모든 뉴스 수집 (필터링 없이).
    AI 분석 단계에서 한국 시장 영향을 판단합니다.
    """
    logger.info("📡 [Finance RSS ALL] 수집 시작")
    all_articles = []
    
    for source in config.FINANCE_RSS_SOURCES:
        try:
            url = source['url']
            name = source['name']
            country = source.get('country', 'Global')
            category = source.get('category', 'finance')
            
            logger.debug(f"   {name}: {url}")
            feed = _fetch_feed(url)
            
            if hasattr(feed, 'bozo') and feed.bozo:
                logger.warning(f"   ⚠️ {name}: 피드 파싱 문제 발생")
            
            for entry in feed.entries[:30]:  # 소스당 최대 30개 (전체 수집이므로 제한)
                try:
                    title = getattr(entry, 'title', '')
                    link = getattr(entry, 'link', '')
                    
                    if not title or not link:
                        continue
                    
                    all_articles.append({
                        "title": title,
                        "link": link,
                        "description": getattr(entry, 'summary', '') or '',
                        "published_at": utils.clean_date(getattr(entry, 'published', '')),
                        "source": name,
                        "country": country,
                        "category": category
                    })
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue
            
            logger.debug(f"   {name}: {len(feed.entries)}개 수집")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"   ❌ {source.get('name', 'Unknown')} 수집 실패: {e}")
            continue
    
    logger.info(f"   ✅ Finance RSS ALL: {len(all_articles)}개 수집")
    return all_articles


def detect_affected_sectors(title: str, description: str = "") -> List[str]:
    """
    뉴스 제목과 내용에서 영향받는 한국 시장 섹터를 감지합니다.
    
    Args:
        title: 뉴스 제목
        description: 뉴스 내용/요약
        
    Returns:
        List[str]: 영향받는 섹터 목록
    """
    text = f"{title} {description}".lower()
    affected_sectors = []
    
    for sector, keywords in config.SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                if sector not in affected_sectors:
                    affected_sectors.append(sector)
                break  # 하나만 매칭되면 해당 섹터 추가
    
    return affected_sectors


def calculate_korea_relevance(title: str, description: str = "") -> str:
    """
    뉴스의 한국 시장 관련성을 계산합니다.
    
    Returns:
        str: 'high', 'medium', 'low', 'none'
    """
    text = f"{title} {description}".lower()
    
    # 직접 관련 키워드
    direct_keywords = [
        "korea", "korean", "samsung", "sk hynix", "hyundai", "kia",
        "lg", "kospi", "kosdaq", "won", "krw", "seoul"
    ]
    
    # 간접 관련 키워드 (글로벌 영향)
    indirect_keywords = [
        "semiconductor", "chip", "battery", "ev", "fed", "interest rate",
        "china", "japan", "trade", "tariff", "oil", "nvidia", "tsmc"
    ]
    
    direct_count = sum(1 for kw in direct_keywords if kw in text)
    indirect_count = sum(1 for kw in indirect_keywords if kw in text)
    
    if direct_count >= 2:
        return "high"
    elif direct_count >= 1:
        return "medium"
    elif indirect_count >= 3:
        return "medium"
    elif indirect_count >= 1:
        return "low"
    else:
        return "none"


# 테스트용
if __name__ == "__main__":
    print("경제 뉴스 수집 테스트...")
    articles = fetch_finance_rss()
    print(f"\n수집된 기사: {len(articles)}개")
    
    for article in articles[:5]:
        sectors = detect_affected_sectors(article['title'], article['description'])
        relevance = calculate_korea_relevance(article['title'], article['description'])
        print(f"\n제목: {article['title'][:60]}...")
        print(f"소스: {article['source']}")
        print(f"한국 관련성: {relevance}")
        print(f"영향 섹터: {sectors}")
