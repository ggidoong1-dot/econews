"""
글로벌 뉴스 수집기 (v3.1)
오케스트레이션 레이어: 여러 수집기 모듈을 호출하고 결과를 정제하여 DB에 저장합니다.
한국 주식시장 영향 분석을 위한 경제 뉴스 수집 기능 추가.
"""
import time
from typing import List, Dict
import config
import database as db

# 모듈화된 수집기/유틸 임포트
import collector_utils as utils
from collectors.rss import fetch_google_news, fetch_reddit_rss, fetch_direct_rss, fetch_newsapi
from collectors.scraper import fetch_naver_news
from collectors.finance_rss import fetch_finance_rss, fetch_finance_rss_all

# 로거 설정
logger = config.setup_logger(__name__)


# ==============================================
# 메인 수집 로직
# ==============================================

def run_collector():
    """메인 수집기 실행 - 통계 정보 반환"""
    logger.info("=" * 60)
    logger.info("🚀 글로벌 뉴스 수집기 시작 (v3.0)")
    logger.info("=" * 60)
    
    # 통계 변수
    stats = {
        "total_crawled": 0,      # 크롤링한 총 개수
        "duplicates_removed": 0,  # 중복 제거된 개수
        "invalid_removed": 0,     # 검증 실패한 개수
        "total_valid": 0,         # 유효한 기사 개수
        "insert_success": 0,      # INSERT 성공
        "insert_failed": 0,       # INSERT 실패
        "insert_skipped": 0       # INSERT 무시 (검증 실패 등)
    }
    
    # 1. 중복 체크용 기존 링크 로드
    existing_links = db.get_recent_links(config.COLLECTOR_LOOKBACK_DAYS)
    logger.info(f"📊 기존 링크: {len(existing_links)}개 (최근 {config.COLLECTOR_LOOKBACK_DAYS}일)")
    
    # 2. 금지어 로드
    ban_words = db.get_ban_words()
    logger.info(f"🚫 금지어: {len(ban_words)}개")
    
    # 3. 키워드 로드 (Supabase에서 동적으로 가져오기)
    all_keywords = db.get_keywords()
    
    # 한글/영문 자동 분류
    keywords_ko = [k for k in all_keywords if any('\uac00' <= c <= '\ud7a3' for c in k)]
    keywords_en = [k for k in all_keywords if k not in keywords_ko]
    
    # 기본값 폴백 (DB 키워드가 없을 경우)
    if not keywords_en:
        keywords_en = config.KEYWORDS_EN
    if not keywords_ko:
        keywords_ko = config.KEYWORDS_KO
    
    logger.info(f"🔑 검색 키워드: 영문 {len(keywords_en)}개, 한글 {len(keywords_ko)}개 (총 {len(all_keywords)}개)")
    
    # 4. 각 소스별 수집
    all_articles = []
    
    if config.NEWS_SOURCES['google']['enabled']:
        all_articles.extend(fetch_google_news(keywords_en))
    
    # Bing / NewsAPI may be optional implementations; call only if functions exist
    if config.NEWS_SOURCES.get('bing', {}).get('enabled'):
        if 'fetch_bing_news' in globals():
            all_articles.extend(fetch_bing_news(keywords_en))
        else:
            logger.warning("   ⚠️ Bing 뉴스 수집 함수가 구현되어 있지 않습니다. 생략합니다.")

    if config.NEWS_SOURCES.get('newsapi', {}).get('enabled'):
        all_articles.extend(fetch_newsapi(keywords_en))
    
    if config.NEWS_SOURCES['naver']['enabled']:
        all_articles.extend(fetch_naver_news(keywords_ko))
    
    # Reddit RSS
    if config.REDDIT_SOURCES:
        all_articles.extend(fetch_reddit_rss(config.REDDIT_SOURCES))
    
    # 직접 RSS
    if config.DIRECT_RSS_SOURCES:
        all_articles.extend(fetch_direct_rss(config.DIRECT_RSS_SOURCES, keywords_en))
    
    # 경제/금융 전문 뉴스 RSS (한국 시장 영향 분석용)
    if hasattr(config, 'FINANCE_RSS_SOURCES') and config.FINANCE_RSS_SOURCES:
        logger.info("📊 경제/금융 전문 뉴스 수집...")
        all_articles.extend(fetch_finance_rss_all())  # 전체 수집 후 AI가 필터링
    
    stats["total_crawled"] = len(all_articles)
    logger.info(f"\n📥 총 크롤링: {stats['total_crawled']}개")
    
    # 5. 필터링 및 정제
    logger.info("🔍 필터링 시작...")
    valid_articles = []
    
    for article in all_articles:
        # 중복 체크
        if article['link'] in existing_links:
            stats["duplicates_removed"] += 1
            continue
        
        # 유효성 검사
        if not utils.is_valid_article(article, ban_words):
            stats["invalid_removed"] += 1
            continue
        
        # 추가 필드 설정
        article['content_hash'] = utils.generate_content_hash(article['link'])
        article['is_processed'] = False
        
        valid_articles.append(article)
        existing_links.add(article['link'])  # 이번 실행 내 중복 방지
    
    stats["total_valid"] = len(valid_articles)
    stats["insert_skipped"] = stats["duplicates_removed"] + stats["invalid_removed"]
    
    logger.info(f"✅ 유효 기사: {stats['total_valid']}개")
    logger.info(f"   - 중복 제거: {stats['duplicates_removed']}개")
    logger.info(f"   - 검증 실패: {stats['invalid_removed']}개")
    
    # 6. DB 저장
    if valid_articles:
        saved_count = db.save_news_batch(valid_articles)
        stats["insert_success"] = saved_count
        stats["insert_failed"] = stats["total_valid"] - saved_count
        logger.info(f"💾 DB 저장 완료: {saved_count}개 성공, {stats['insert_failed']}개 실패")
    else:
        logger.info("📭 저장할 새 기사가 없습니다.")
        stats["insert_failed"] = 0
    
    # 7. 마지막 실행 시간 업데이트
    db.update_last_run()
    
    # 8. 최종 통계 로깅
    logger.info("\n" + "=" * 70)
    logger.info("📊 수집 작업 최종 통계")
    logger.info("=" * 70)
    logger.info(f"🌍 크롤링한 기사:        {stats['total_crawled']:6d}개")
    logger.info(f"✅ 유효한 기사:         {stats['total_valid']:6d}개")
    logger.info(f"   ├─ INSERT 성공:     {stats['insert_success']:6d}개")
    logger.info(f"   └─ INSERT 실패:     {stats['insert_failed']:6d}개")
    logger.info(f"❌ 무시된 기사:         {stats['insert_skipped']:6d}개")
    logger.info(f"   ├─ 중복 기사:       {stats['duplicates_removed']:6d}개")
    logger.info(f"   └─ 검증 실패:       {stats['invalid_removed']:6d}개")
    success_rate = (stats['insert_success'] / stats['total_crawled'] * 100) if stats['total_crawled'] > 0 else 0
    logger.info(f"📈 성공률:              {success_rate:6.1f}%")
    logger.info("=" * 70)
    
    # 실패한 경우 경고
    if stats['insert_failed'] > 0:
        logger.error(f"\n🚨 주의: {stats['insert_failed']}개 기사 INSERT 실패!")
        logger.error(f"   failed_articles.jsonl 파일 확인: logs/failed_articles.jsonl")
        logger.error(f"   분석 명령어: python log_analyzer.py analyze\n")
        import traceback
        traceback.print_exc()
    # 결과 반환
    return stats
