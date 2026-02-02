"""
새벽 전문 뉴스 수집기
한국 시간 0시~7시 사이 발생하는 글로벌 뉴스를 수집합니다.

주요 수집 대상:
- 미국 장 마감 뉴스 (한국시간 6시~7시)
- 유럽 경제 뉴스 (한국시간 0시~4시)
- 아시아 선물 시장 동향 (한국시간 5시~7시)
"""
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import feedparser
import requests

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = config.setup_logger(__name__)

# User-Agent 헤더 (RSS 차단 방지)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==============================================
# 새벽 시간대 전용 뉴스 소스
# ==============================================
NIGHT_RSS_SOURCES = [
    # ============ 미국 메인 뉴스 ============
    {
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "name": "WSJ Markets",
        "country": "US",
        "category": "markets",
        "priority": "high"
    },
    {
        "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "name": "WSJ Business",
        "country": "US",
        "category": "finance",
        "priority": "high"
    },
    {
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "name": "WSJ World",
        "country": "US",
        "category": "world",
        "priority": "medium"
    },
    # ============ CNBC (미국 증시 핵심) ============
    {
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "name": "CNBC Top News",
        "country": "US",
        "category": "markets",
        "priority": "high"
    },
    {
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "name": "CNBC Pre-Markets",
        "country": "US",
        "category": "markets",
        "priority": "high"
    },
    {
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "name": "CNBC US Markets",
        "country": "US",
        "category": "markets",
        "priority": "high"
    },
    # ============ Reuters ============
    {
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "name": "Reuters Business",
        "country": "Global",
        "category": "finance",
        "priority": "high"
    },
    # ============ BBC/NPR ============
    {
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "name": "BBC Business",
        "country": "UK",
        "category": "finance",
        "priority": "medium"
    },
    {
        "url": "https://feeds.npr.org/1006/rss.xml",
        "name": "NPR Business",
        "country": "US",
        "category": "finance",
        "priority": "medium"
    },
    # ============ 테크/반도체 ============
    {
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "name": "BBC Technology",
        "country": "UK",
        "category": "tech",
        "priority": "medium"
    },
    {
        "url": "https://www.theverge.com/rss/index.xml",
        "name": "The Verge",
        "country": "US",
        "category": "tech",
        "priority": "low"
    },
    # ============ 아시아 뉴스 ============
    {
        "url": "https://www3.nhk.or.jp/rss/news/cat5.xml",
        "name": "NHK Business",
        "country": "Japan",
        "category": "finance",
        "priority": "medium"
    },
    {
        "url": "https://www.scmp.com/rss/91/feed",
        "name": "SCMP Business",
        "country": "China/HK",
        "category": "finance",
        "priority": "medium"
    },
    # ============ 원자재/에너지 ============
    {
        "url": "https://oilprice.com/rss/main",
        "name": "OilPrice",
        "country": "Global",
        "category": "commodities",
        "priority": "medium"
    },
]

# 한국 시장 영향 키워드 (빠른 필터링용)
KOREA_IMPACT_KEYWORDS = [
    # 직접 관련
    "korea", "korean", "samsung", "sk hynix", "hyundai", "kia", "lg",
    "kospi", "kosdaq", "won", "krw", "seoul",
    # 반도체
    "semiconductor", "chip", "nvidia", "tsmc", "intel", "amd", 
    "memory", "dram", "nand", "hbm", "ai chip",
    # 2차전지/EV
    "battery", "ev", "electric vehicle", "tesla", "lithium",
    # 통화/금리
    "fed", "federal reserve", "interest rate", "inflation",
    "fomc", "powell", "rate cut", "rate hike",
    # 빅테크
    "apple", "google", "microsoft", "amazon", "meta", "nvidia",
    # 무역/지정학
    "china", "trade war", "tariff", "sanction", "export",
    # 원자재
    "oil", "crude", "gold", "copper",
    # 시장 지표
    "s&p", "nasdaq", "dow", "treasury", "yield", "vix",
]


def _fetch_feed(url: str, timeout: int = 15) -> feedparser.FeedParserDict:
    """RSS 피드를 User-Agent 헤더와 함께 가져옵니다."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except requests.RequestException as e:
        logger.debug(f"   요청 실패, feedparser로 재시도: {e}")
        return feedparser.parse(url)


def _is_night_time_kst() -> bool:
    """현재 시간이 한국 기준 새벽 시간대(0시~7시)인지 확인합니다."""
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    return 0 <= now_kst.hour < 7


def _get_hours_ago(hours: int) -> datetime:
    """지정된 시간 전의 datetime 반환"""
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _quick_filter_relevant(title: str, description: str) -> bool:
    """한국 시장 관련 뉴스인지 빠르게 필터링 (키워드 기반)"""
    text = f"{title} {description}".lower()
    return any(kw in text for kw in KOREA_IMPACT_KEYWORDS)


def collect_night_news(
    hours_back: int = 8,
    filter_korea_relevant: bool = True,
    priority_filter: Optional[List[str]] = None
) -> List[Dict]:
    """
    새벽 시간대 글로벌 뉴스를 수집합니다.
    
    Args:
        hours_back: 몇 시간 전까지 수집할지 (기본 8시간)
        filter_korea_relevant: 한국 시장 관련 뉴스만 필터링할지
        priority_filter: 수집할 우선순위 목록 (예: ["high", "medium"])
        
    Returns:
        List[Dict]: 수집된 뉴스 목록
    """
    logger.info("=" * 60)
    logger.info("🌙 새벽 뉴스 수집 시작")
    logger.info(f"   수집 범위: 최근 {hours_back}시간")
    logger.info(f"   한국 관련 필터: {'ON' if filter_korea_relevant else 'OFF'}")
    logger.info("=" * 60)
    
    if priority_filter is None:
        priority_filter = ["high", "medium", "low"]
    
    all_articles = []
    cutoff_time = _get_hours_ago(hours_back)
    
    # 활성 소스 필터링
    active_sources = [
        s for s in NIGHT_RSS_SOURCES 
        if s.get("priority", "low") in priority_filter
    ]
    
    logger.info(f"📡 활성 뉴스 소스: {len(active_sources)}개")
    
    for source in active_sources:
        try:
            url = source['url']
            name = source['name']
            country = source.get('country', 'Global')
            category = source.get('category', 'general')
            priority = source.get('priority', 'low')
            
            logger.debug(f"   [{priority.upper()}] {name}: {url}")
            feed = _fetch_feed(url)
            
            # 피드 상태 확인
            if hasattr(feed, 'bozo') and feed.bozo:
                logger.warning(f"   ⚠️ {name}: 피드 파싱 문제 발생")
            
            source_count = 0
            for entry in feed.entries[:40]:  # 소스당 최대 40개
                try:
                    title = getattr(entry, 'title', '')
                    link = getattr(entry, 'link', '')
                    
                    if not title or not link:
                        continue
                    
                    # 발행일 파싱 (없으면 현재 시간으로)
                    published = getattr(entry, 'published_parsed', None)
                    if published:
                        pub_datetime = datetime(*published[:6], tzinfo=timezone.utc)
                        # 시간 범위 체크
                        if pub_datetime < cutoff_time:
                            continue
                    else:
                        pub_datetime = datetime.now(timezone.utc)
                    
                    summary = getattr(entry, 'summary', '') or ''
                    
                    # 한국 관련 빠른 필터링
                    if filter_korea_relevant:
                        if not _quick_filter_relevant(title, summary):
                            continue
                    
                    article = {
                        "title": title,
                        "link": link,
                        "description": summary[:500],  # 길이 제한
                        "published_at": pub_datetime.isoformat(),
                        "source": name,
                        "country": country,
                        "category": category,
                        "priority": priority,
                        "collected_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    all_articles.append(article)
                    source_count += 1
                    
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue
            
            if source_count > 0:
                logger.info(f"   ✅ {name}: {source_count}개 수집")
            
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            logger.error(f"   ❌ {source.get('name', 'Unknown')} 수집 실패: {e}")
            continue
    
    # 중복 제거 (링크 기준)
    seen_links = set()
    unique_articles = []
    for article in all_articles:
        if article['link'] not in seen_links:
            seen_links.add(article['link'])
            unique_articles.append(article)
    
    # 발행일순 정렬 (최신 먼저)
    unique_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    logger.info("=" * 60)
    logger.info(f"🌙 새벽 뉴스 수집 완료: 총 {len(unique_articles)}개")
    logger.info("=" * 60)
    
    return unique_articles


def collect_priority_news(hours_back: int = 4) -> List[Dict]:
    """
    우선순위 높은 뉴스만 빠르게 수집 (긴급 알림용)
    
    Args:
        hours_back: 몇 시간 전까지 수집할지
        
    Returns:
        List[Dict]: 수집된 뉴스 목록
    """
    return collect_night_news(
        hours_back=hours_back,
        filter_korea_relevant=True,
        priority_filter=["high"]
    )


def get_night_summary_stats(articles: List[Dict]) -> Dict:
    """
    새벽 뉴스 수집 통계 요약
    
    Args:
        articles: 수집된 기사 목록
        
    Returns:
        Dict: 통계 요약
    """
    if not articles:
        return {"total": 0, "by_country": {}, "by_category": {}, "by_priority": {}}
    
    stats = {
        "total": len(articles),
        "by_country": {},
        "by_category": {},
        "by_priority": {},
        "time_range": {
            "earliest": None,
            "latest": None
        }
    }
    
    for article in articles:
        # 국가별
        country = article.get('country', 'Unknown')
        stats["by_country"][country] = stats["by_country"].get(country, 0) + 1
        
        # 카테고리별
        category = article.get('category', 'general')
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # 우선순위별
        priority = article.get('priority', 'low')
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        # 시간 범위
        pub_at = article.get('published_at', '')
        if pub_at:
            if stats["time_range"]["earliest"] is None or pub_at < stats["time_range"]["earliest"]:
                stats["time_range"]["earliest"] = pub_at
            if stats["time_range"]["latest"] is None or pub_at > stats["time_range"]["latest"]:
                stats["time_range"]["latest"] = pub_at
    
    return stats


# ==============================================
# 테스트
# ==============================================
if __name__ == "__main__":
    print("=" * 60)
    print("새벽 뉴스 수집기 테스트")
    print("=" * 60)
    
    # 한국 시간대 확인
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    print(f"\n현재 시간 (KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"새벽 시간대 여부: {_is_night_time_kst()}")
    
    # 뉴스 수집 테스트
    print("\n📰 뉴스 수집 테스트 (최근 4시간, 한국 관련만)...")
    articles = collect_night_news(hours_back=4, filter_korea_relevant=True)
    
    # 통계
    stats = get_night_summary_stats(articles)
    print(f"\n📊 수집 통계:")
    print(f"   총 기사: {stats['total']}개")
    print(f"   국가별: {stats['by_country']}")
    print(f"   카테고리별: {stats['by_category']}")
    print(f"   우선순위별: {stats['by_priority']}")
    
    # 상위 5개 기사 출력
    print("\n📰 수집된 기사 (상위 5개):")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. [{article['source']}] {article['title'][:60]}...")
        print(f"   발행: {article.get('published_at', 'N/A')[:19]}")
