import time
import urllib.parse
from typing import List, Dict
import feedparser
from datetime import datetime, timezone
import config
import collector_utils as utils

logger = config.setup_logger(__name__)


def fetch_google_news(keywords: List[str]) -> List[Dict]:
    """
    Google News RSS에서 기사를 수집합니다.
    """
    logger.info("📡 [Google News] 수집 시작")
    all_articles: List[Dict] = []

    for keyword in keywords:
        try:
            encoded = urllib.parse.quote(keyword)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

            logger.debug(f"   검색어: {keyword}")
            feed = feedparser.parse(url)

            # 피드 상태 확인
            if hasattr(feed, 'status') and feed.status != 200:
                logger.warning(f"   ⚠️ HTTP {feed.status}")
                continue

            logger.debug(f"   발견: {len(feed.entries)}개")

            # 최대 20개 항목만 처리
            for entry in feed.entries[:20]:
                try:
                    title = entry.get('title', '') if hasattr(entry, 'get') else getattr(entry, 'title', '')
                    link = entry.get('link', '') if hasattr(entry, 'get') else getattr(entry, 'link', '')
                    if not title or not link:
                        continue

                    published = utils.clean_date(entry.get('published', '') if hasattr(entry, 'get') else getattr(entry, 'published', ''))
                    description = entry.get('summary', '') if hasattr(entry, 'get') else getattr(entry, 'summary', '')

                    all_articles.append({
                        "title": title,
                        "link": link,
                        "description": description,
                        "published_at": published,
                        "source": "Google News",
                        "country": "Global"
                    })
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue

            time.sleep(1)

        except Exception as e:
            logger.error(f"   ❌ '{keyword}' 검색 실패: {e}")
            continue

    logger.info(f"   ✅ Google News: {len(all_articles)}개 수집")
    return all_articles


def fetch_reddit_rss(subreddit_urls: List[str]) -> List[Dict]:
    """Reddit RSS 피드에서 게시물을 수집합니다."""
    logger.info("📡 [Reddit] 수집 시작")
    all_articles = []
    
    for url in subreddit_urls:
        try:
            logger.debug(f"   URL: {url}")
            feed = feedparser.parse(url)
            
            logger.debug(f"   발견: {len(feed.entries)}개")
            
            for entry in feed.entries:
                all_articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "description": entry.get('summary', ''),
                    "published_at": utils.clean_date(entry.get('published', '')),
                    "source": "Reddit",
                    "country": "Global"
                })
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"   ❌ {url} 수집 실패: {e}")
            continue
    
    logger.info(f"   ✅ Reddit: {len(all_articles)}개 수집")
    return all_articles


def fetch_direct_rss(rss_sources: List[Dict], keywords: List[str] = None) -> List[Dict]:
    """직접 뉴스사이트 RSS를 수집합니다."""
    logger.info("📡 [Direct RSS] 수집 시작")
    all_articles = []
    
    # 키워드가 전달되지 않으면 config 기본값 사용
    if keywords is None:
        keywords = config.KEYWORDS_EN
    
    for source in rss_sources:
        try:
            url = source['url']
            name = source['name']
            country = source.get('country', 'Global')
            
            logger.debug(f"   {name}: {url}")
            feed = feedparser.parse(url)
            
            # 키워드 필터링 (모든 기사가 아닌 관련 기사만)
            keywords_lower = [k.lower() for k in keywords]
            
            filtered_count = 0
            for entry in feed.entries:
                title = entry.title.lower()
                summary = entry.get('summary', '').lower()
                
                # 키워드 포함 여부 확인
                if any(keyword in title or keyword in summary for keyword in keywords_lower):
                    all_articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "description": entry.get('summary', ''),
                        "published_at": utils.clean_date(entry.get('published', '')),
                        "source": name,
                        "country": country
                    })
                    filtered_count += 1
            
            logger.debug(f"   발견: {len(feed.entries)}개 중 {filtered_count}개 관련")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"   ❌ {source.get('name', 'Unknown')} 수집 실패: {e}")
            continue
    
    logger.info(f"   ✅ Direct RSS: {len(all_articles)}개 수집")
    return all_articles


def fetch_bing_news(keywords: List[str]) -> List[Dict]:
    """Bing News용 임시 스텁. 실제 구현이 없을 때 오류를 피하기 위해 빈 리스트 반환."""
    logger.warning("Bing News 수집기는 아직 구현되지 않았습니다. 빈 결과 반환합니다.")
    return []


def fetch_newsapi(keywords: List[str]) -> List[Dict]:
    """NewsAPI에서 뉴스를 수집합니다."""
    import requests
    
    api_key = config.NEWSAPI_KEY
    if not api_key:
        logger.warning("   ⚠️ NEWSAPI_KEY가 설정되지 않았습니다. 스킵합니다.")
        return []
    
    logger.info("📡 [NewsAPI] 수집 시작")
    all_articles = []
    
    for keyword in keywords:
        try:
            encoded = urllib.parse.quote(keyword)
            url = f"https://newsapi.org/v2/everything?q={encoded}&language=en&sortBy=publishedAt&pageSize=20&apiKey={api_key}"
            
            logger.debug(f"   검색어: {keyword}")
            response = requests.get(url, timeout=config.API_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.warning(f"   ⚠️ API 응답 오류: {data.get('message', 'Unknown error')}")
                continue
            
            articles = data.get('articles', [])
            logger.debug(f"   발견: {len(articles)}개")
            
            for article in articles[:20]:
                try:
                    title = article.get('title', '')
                    link = article.get('url', '')
                    
                    if not title or not link or title == '[Removed]':
                        continue
                    
                    # 날짜 처리
                    pub_date = article.get('publishedAt', '')
                    if pub_date:
                        pub_date = utils.clean_date(pub_date)
                    else:
                        pub_date = datetime.now(timezone.utc).isoformat()
                    
                    all_articles.append({
                        "title": title,
                        "link": link,
                        "description": article.get('description', '') or '',
                        "published_at": pub_date,
                        "source": f"NewsAPI/{article.get('source', {}).get('name', 'Unknown')}",
                        "country": "Global"
                    })
                except Exception as e:
                    logger.debug(f"   항목 파싱 실패: {e}")
                    continue
            
            time.sleep(1)  # Rate limit 방지
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 426:
                logger.error("   ❌ NewsAPI 무료 플랜은 HTTPS만 지원합니다. 유료 플랜이 필요할 수 있습니다.")
            elif e.response.status_code == 401:
                logger.error("   ❌ NewsAPI 키가 유효하지 않습니다.")
            elif e.response.status_code == 429:
                logger.error("   ❌ NewsAPI 요청 한도 초과. 잠시 후 다시 시도하세요.")
            else:
                logger.error(f"   ❌ HTTP 오류: {e}")
            break  # API 오류 시 더 이상 시도하지 않음
        except Exception as e:
            logger.error(f"   ❌ '{keyword}' 검색 실패: {e}")
            continue
    
    logger.info(f"   ✅ NewsAPI: {len(all_articles)}개 수집")
    return all_articles
