#!/usr/bin/env python3
"""
RSS 피드 테스트 스크립트
각 플랫폼이 실제로 데이터를 반환하는지 확인
"""
import feedparser
import urllib.parse
import requests
import config

def test_google_news():
    """Google News RSS 테스트"""
    print("\n" + "=" * 70)
    print("📡 [1] Google News RSS Test")
    print("=" * 70)
    
    for keyword in config.KEYWORDS_EN[:2]:  # 처음 2개만
        query = urllib.parse.quote(keyword)
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        print(f"\n검색어: {keyword}")
        print(f"URL: {url[:80]}...")
        
        feed = feedparser.parse(url)
        print(f"✅ 발견: {len(feed.entries)}개")
        
        if feed.entries:
            print(f"\n첫 3개 제목:")
            for i, entry in enumerate(feed.entries[:3], 1):
                print(f"  {i}. {entry.title[:70]}...")
        else:
            print("  ⚠️ No entries!")
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"  Error: {feed.bozo_exception}")


def test_bing_news():
    """Bing News RSS 테스트"""
    print("\n" + "=" * 70)
    print("📡 [2] Bing News RSS Test")
    print("=" * 70)
    
    keyword = config.KEYWORDS_EN[0]
    query = urllib.parse.quote(keyword)
    url = f"https://www.bing.com/news/search?q={query}&format=rss"
    print(f"\n검색어: {keyword}")
    print(f"URL: {url[:80]}...")
    
    feed = feedparser.parse(url)
    print(f"✅ 발견: {len(feed.entries)}개")
    
    if feed.entries:
        print(f"\n첫 3개 제목:")
        for i, entry in enumerate(feed.entries[:3], 1):
            print(f"  {i}. {entry.title[:70]}...")
    else:
        print("  ⚠️ No entries!")


def test_newsapi():
    """NewsAPI 테스트"""
    print("\n" + "=" * 70)
    print("📡 [3] NewsAPI Test")
    print("=" * 70)
    
    if not config.NEWSAPI_KEY:
        print("\n⚠️ NewsAPI 키가 설정되지 않았습니다.")
        print("  환경변수 NEWSAPI_KEY를 설정해주세요.")
        print("  무료 키 발급: https://newsapi.org/register")
        return
    
    keyword = config.KEYWORDS_EN[0]
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': keyword,
        'apiKey': config.NEWSAPI_KEY,
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': 5
    }
    
    print(f"\n검색어: {keyword}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            print(f"✅ 발견: {len(articles)}개")
            
            if articles:
                print(f"\n첫 3개 제목:")
                for i, article in enumerate(articles[:3], 1):
                    print(f"  {i}. [{article['source']['name']}] {article['title'][:60]}...")
        else:
            print(f"❌ API 오류: {data.get('message')}")
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 에러: {e.response.status_code}")
        if e.response.status_code == 401:
            print("  인증 실패: API 키를 확인해주세요.")
        elif e.response.status_code == 429:
            print("  할당량 초과: 무료는 하루 100회 제한")
    except Exception as e:
        print(f"❌ 에러: {e}")


def test_reddit_rss():
    """Reddit RSS 테스트"""
    print("\n" + "=" * 70)
    print("📡 [4] Reddit RSS Test")
    print("=" * 70)
    
    if not config.REDDIT_SOURCES:
        print("\n⚠️ Reddit 소스가 설정되지 않았습니다.")
        return
    
    url = config.REDDIT_SOURCES[0]
    print(f"\nURL: {url}")
    
    feed = feedparser.parse(url)
    print(f"✅ 발견: {len(feed.entries)}개")
    
    if feed.entries:
        print(f"\n첫 3개 게시물:")
        for i, entry in enumerate(feed.entries[:3], 1):
            print(f"  {i}. {entry.title[:70]}...")
    else:
        print("  ⚠️ No entries!")


def test_all():
    """모든 소스 테스트"""
    print("\n" + "=" * 70)
    print("🧪 RSS 피드 종합 테스트")
    print("=" * 70)
    
    test_google_news()
    test_bing_news()
    test_newsapi()
    test_reddit_rss()
    
    print("\n" + "=" * 70)
    print("✅ 모든 테스트 완료")
    print("=" * 70)
    print("\n💡 작동하지 않는 소스는 config.py에서 비활성화하세요.")
    print("   예: NEWS_SOURCES['bing']['enabled'] = False")


if __name__ == "__main__":
    test_all()
