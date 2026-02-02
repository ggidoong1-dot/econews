"""
투자 리포트 수집기 (v1.0)
- 해외 투자은행/기관 리포트 (RSS)
- 국내 증권사 리포트 (네이버 증권)
- 경제지표 캘린더
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import feedparser
import re

import config

logger = config.setup_logger(__name__)


# ==============================================
# 해외 투자은행 리포트 RSS 소스
# ==============================================
IB_REPORT_SOURCES = [
    # Bloomberg
    {
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "name": "Bloomberg Markets",
        "category": "IB",
        "country": "US"
    },
    # Reuters
    {
        "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
        "name": "Reuters Analysis",
        "category": "IB",
        "country": "US"
    },
    # CNBC
    {
        "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "name": "CNBC Investing",
        "category": "IB",
        "country": "US"
    },
    # Financial Times
    {
        "url": "https://www.ft.com/markets?format=rss",
        "name": "FT Markets",
        "category": "IB",
        "country": "UK"
    },
    # MarketWatch
    {
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "name": "MarketWatch",
        "category": "IB",
        "country": "US"
    }
]

# 리포트 관련 키워드 (필터링용)
REPORT_KEYWORDS = [
    # 영문
    "upgrade", "downgrade", "target price", "price target", "rating",
    "buy", "sell", "hold", "outperform", "underperform",
    "analyst", "forecast", "outlook", "earnings", "guidance",
    "goldman", "morgan", "jp morgan", "citi", "ubs", "hsbc",
    "merrill", "barclays", "credit suisse", "deutsche bank",
    # 한글
    "목표가", "투자의견", "매수", "매도", "중립", "비중확대", "비중축소",
    "상향", "하향", "리포트", "애널리스트", "전망"
]


def fetch_ib_reports(hours: int = 24) -> List[Dict]:
    """
    해외 투자은행/기관 리포트 관련 뉴스 수집
    
    Args:
        hours: 수집 기간 (시간)
        
    Returns:
        List[Dict]: 리포트 뉴스 목록
    """
    logger.info("📊 해외 투자은행 리포트 수집 시작...")
    reports = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    for source in IB_REPORT_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            
            for entry in feed.entries[:20]:  # 소스당 최대 20개
                title = entry.get("title", "")
                description = entry.get("description", entry.get("summary", ""))
                
                # 리포트 관련 키워드 필터링
                content = f"{title} {description}".lower()
                if not any(kw.lower() in content for kw in REPORT_KEYWORDS):
                    continue
                
                # 날짜 파싱
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                
                if pub_date and pub_date < cutoff:
                    continue
                
                reports.append({
                    "title": title,
                    "description": description[:500],
                    "link": entry.get("link", ""),
                    "source": source["name"],
                    "category": source["category"],
                    "country": source["country"],
                    "published_at": pub_date.isoformat() if pub_date else None,
                    "type": "IB_REPORT"
                })
                
            logger.info(f"   ✅ {source['name']}: 수집 완료")
            
        except Exception as e:
            logger.warning(f"   ⚠️ {source['name']} 실패: {e}")
    
    logger.info(f"📊 해외 리포트 총 {len(reports)}건 수집")
    return reports


def fetch_naver_reports(limit: int = 20) -> List[Dict]:
    """
    네이버 증권 리서치 리포트 수집
    
    Args:
        limit: 최대 수집 개수
        
    Returns:
        List[Dict]: 국내 증권사 리포트 목록
    """
    logger.info("📈 네이버 증권 리포트 수집 시작...")
    reports = []
    
    # 네이버 증권 리서치 페이지들
    pages = [
        ("https://finance.naver.com/research/company_list.naver", "종목분석"),
        ("https://finance.naver.com/research/market_info_list.naver", "시장분석"),
        ("https://finance.naver.com/research/economy_list.naver", "경제분석"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for url, category in pages:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 리포트 테이블 찾기
            table = soup.find('table', class_='type_1')
            if not table:
                continue
            
            rows = table.find_all('tr')[2:]  # 헤더 제외
            
            for row in rows[:limit // len(pages)]:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                # 제목과 링크
                title_tag = cols[0].find('a')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://finance.naver.com/research/{link}"
                
                # 증권사
                firm = cols[1].get_text(strip=True) if len(cols) > 1 else "Unknown"
                
                # 날짜
                date_str = cols[-1].get_text(strip=True) if cols else ""
                
                reports.append({
                    "title": title,
                    "description": f"[{firm}] {title}",
                    "link": link,
                    "source": firm,
                    "category": category,
                    "country": "KR",
                    "published_at": date_str,
                    "type": "KR_REPORT"
                })
            
            logger.info(f"   ✅ {category}: 수집 완료")
            
        except Exception as e:
            logger.warning(f"   ⚠️ {category} 실패: {e}")
    
    logger.info(f"📈 국내 리포트 총 {len(reports)}건 수집")
    return reports


def fetch_hankyung_consensus(limit: int = 10) -> List[Dict]:
    """
    한경 컨센서스 리포트 수집
    
    Args:
        limit: 최대 수집 개수
        
    Returns:
        List[Dict]: 컨센서스 리포트 목록
    """
    logger.info("📊 한경 컨센서스 수집 시작...")
    reports = []
    
    url = "https://consensus.hankyung.com/apps.analysis/analysis.list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 리포트 리스트 찾기
        items = soup.find_all('div', class_='item')[:limit]
        
        for item in items:
            title_tag = item.find('a')
            if not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)
            link = title_tag.get('href', '')
            if link and not link.startswith('http'):
                link = f"https://consensus.hankyung.com{link}"
            
            # 증권사 정보
            firm_tag = item.find('span', class_='firm')
            firm = firm_tag.get_text(strip=True) if firm_tag else "Unknown"
            
            reports.append({
                "title": title,
                "description": f"[{firm}] {title}",
                "link": link,
                "source": firm,
                "category": "컨센서스",
                "country": "KR",
                "type": "KR_CONSENSUS"
            })
        
        logger.info(f"   ✅ 한경 컨센서스: {len(reports)}건")
        
    except Exception as e:
        logger.warning(f"   ⚠️ 한경 컨센서스 실패: {e}")
    
    return reports


def fetch_economic_calendar(days: int = 1) -> List[Dict]:
    """
    주요 경제지표 일정 수집 (Investing.com 스타일)
    
    Args:
        days: 수집 기간 (일)
        
    Returns:
        List[Dict]: 경제지표 일정 목록
    """
    logger.info("📅 경제지표 캘린더 수집 시작...")
    
    # 주요 경제지표 (수동 정의 - API가 제한적이므로)
    # 실제로는 Investing.com 크롤링 또는 FRED API 사용 권장
    indicators = [
        {"name": "미국 CPI (소비자물가지수)", "importance": "high"},
        {"name": "미국 FOMC 금리결정", "importance": "high"},
        {"name": "미국 고용지표 (Non-Farm Payroll)", "importance": "high"},
        {"name": "미국 GDP 성장률", "importance": "high"},
        {"name": "한국 수출입 동향", "importance": "medium"},
        {"name": "중국 PMI (제조업구매관리자지수)", "importance": "medium"},
    ]
    
    logger.info(f"   ✅ 주요 지표 {len(indicators)}개 로드")
    return indicators


def collect_all_reports() -> Dict[str, List[Dict]]:
    """
    모든 리포트 수집 통합 함수
    
    Returns:
        Dict: 카테고리별 리포트 목록
    """
    logger.info("=" * 60)
    logger.info("🔍 투자 리포트 종합 수집 시작")
    logger.info("=" * 60)
    
    result = {
        "ib_reports": fetch_ib_reports(hours=24),
        "kr_reports": fetch_naver_reports(limit=20),
        "consensus": fetch_hankyung_consensus(limit=10),
        "economic_calendar": fetch_economic_calendar(days=1)
    }
    
    total = sum(len(v) for v in result.values())
    logger.info(f"📊 총 {total}건 수집 완료")
    
    return result


def format_reports_for_briefing(reports: Dict[str, List[Dict]]) -> str:
    """
    브리핑용 리포트 요약 포맷팅
    
    Args:
        reports: collect_all_reports() 결과
        
    Returns:
        str: 마크다운 형식의 리포트 요약
    """
    sections = []
    
    # 해외 IB 리포트
    ib = reports.get("ib_reports", [])
    if ib:
        ib_section = "## 📊 해외 투자은행 리포트\n\n"
        for r in ib[:5]:  # 상위 5개
            ib_section += f"- **{r['source']}**: {r['title'][:60]}...\n"
        sections.append(ib_section)
    
    # 국내 증권사 리포트
    kr = reports.get("kr_reports", [])
    if kr:
        kr_section = "## 📈 국내 증권사 리포트\n\n"
        for r in kr[:5]:
            kr_section += f"- **[{r['source']}]** {r['title'][:50]}...\n"
        sections.append(kr_section)
    
    # 컨센서스
    consensus = reports.get("consensus", [])
    if consensus:
        con_section = "## 🎯 한경 컨센서스\n\n"
        for r in consensus[:3]:
            con_section += f"- {r['title'][:60]}...\n"
        sections.append(con_section)
    
    return "\n".join(sections) if sections else "리포트 정보 없음"


# ==============================================
# CLI 테스트
# ==============================================
if __name__ == "__main__":
    print("🔍 리포트 수집 테스트")
    
    # 해외 IB 리포트
    ib = fetch_ib_reports(hours=24)
    print(f"\n해외 IB 리포트: {len(ib)}건")
    for r in ib[:3]:
        print(f"  - [{r['source']}] {r['title'][:50]}...")
    
    # 국내 리포트
    kr = fetch_naver_reports(limit=10)
    print(f"\n국내 증권사 리포트: {len(kr)}건")
    for r in kr[:3]:
        print(f"  - [{r['source']}] {r['title'][:40]}...")
