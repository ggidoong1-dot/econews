#!/usr/bin/env python3
"""
메인 실행 스크립트
수집 → 분석 → 리포트 생성의 전체 파이프라인 실행
"""
import os
import sys
# 👇 [중요] .env 파일을 읽어오는 코드가 추가되었습니다!
from dotenv import load_dotenv
load_dotenv()

import argparse
import time
from datetime import datetime, timezone
import config
import database as db
import collector
import analyzer
import reporter

# 로거 설정
logger = config.setup_logger(__name__)

# ==============================================
# 전체 파이프라인
# ==============================================

def run_full_pipeline(force: bool = False):
    """
    전체 파이프라인 실행: 수집 → 분석 → 리포트
    
    Args:
        force: 수집 주기 무시하고 강제 실행
    """
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Well-Dying Archive 전체 파이프라인 시작")
    logger.info(f"   실행 시각: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    # 통계 수집
    pipeline_stats = {
        "collector": None,
        "analyzer": None,
        "reporter": None
    }
    
    try:
        # 1. 수집 주기 체크
        if not force:
            should_run = db.should_run_collector()
            if not should_run:
                logger.info("⏭️  수집 주기가 아니므로 종료합니다.")
                logger.info("   강제 실행하려면: python main.py --force")
                return
        else:
            logger.info("⚡ 강제 실행 모드")
        
        # 2. 뉴스 수집
        logger.info("\n" + "─" * 70)
        logger.info("📡 STEP 1: 뉴스 수집")
        logger.info("─" * 70)
        pipeline_stats["collector"] = collector.run_collector()
        
        # 3. AI 분석 (30초 대기 후)
        logger.info("\n" + "─" * 70)
        logger.info("🤖 STEP 2: AI 분석 (30초 후 시작)")
        logger.info("─" * 70)
        time.sleep(30)
        analyzer.run_analyzer(batch_size=20)
        
        # 4. 일일 리포트 생성 (선택사항)
        logger.info("\n" + "─" * 70)
        logger.info("📊 STEP 3: 일일 리포트 생성 (스킵 가능)")
        logger.info("─" * 70)
        
        # 하루에 한 번만 리포트 생성 (예: 오전 9시)
        current_hour = datetime.now(timezone.utc).hour
        if current_hour == 1 or force:  # UTC 1시 = 한국 10시
            reporter.run_reporter(hours=24)
        else:
            logger.info(f"   현재 시각: UTC {current_hour}시")
            logger.info("   리포트는 UTC 1시(한국 10시)에만 생성됩니다.")
            logger.info("   강제 생성하려면: python main.py report")
        
        # 5. 최종 통계 출력
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 70)
        logger.info("🎯 전체 파이프라인 최종 통계")
        logger.info("=" * 70)
        
        if pipeline_stats["collector"]:
            collector_stats = pipeline_stats["collector"]
            logger.info("\n📡 [수집 단계]")
            logger.info(f"   🌍 크롤링한 기사:    {collector_stats.get('total_crawled', 0):6d}개")
            logger.info(f"   ✅ INSERT 성공:      {collector_stats.get('insert_success', 0):6d}개")
            logger.info(f"   ❌ INSERT 실패:      {collector_stats.get('insert_failed', 0):6d}개")
            logger.info(f"   ⏭️  무시된 기사:      {collector_stats.get('insert_skipped', 0):6d}개")
            logger.info(f"      ├─ 중복:          {collector_stats.get('duplicates_removed', 0):6d}개")
            logger.info(f"      └─ 검증 실패:     {collector_stats.get('invalid_removed', 0):6d}개")
            
            total = collector_stats.get('total_crawled', 1)
            success_rate = (collector_stats.get('insert_success', 0) / total * 100)
            logger.info(f"   📈 성공률:           {success_rate:6.1f}%")
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ 전체 파이프라인 완료 (소요시간: {elapsed:.1f}초)")
        logger.info("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 파이프라인 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# ==============================================
# 개별 모듈 실행
# ==============================================

def run_collector_only():
    """수집만 실행"""
    logger.info("📡 수집기만 실행")
    stats = collector.run_collector()

    # 안전성: collector가 예외로 None을 반환하더라도 처리
    if not stats:
        logger.error("❌ 수집 작업 중 오류가 발생하여 통계 정보를 반환하지 못했습니다.")
        return

    # 통계 출력
    logger.info("\n" + "=" * 70)
    logger.info("📊 수집 작업 요약")
    logger.info("=" * 70)
    logger.info(f"🌍 크롤링한 기사:      {stats.get('total_crawled', 0):6d}개")
    logger.info(f"✅ INSERT 성공:        {stats.get('insert_success', 0):6d}개")
    logger.info(f"❌ INSERT 실패:        {stats.get('insert_failed', 0):6d}개")
    logger.info(f"⏭️  무시된 기사:        {stats.get('insert_skipped', 0):6d}개")
    logger.info(f"   ├─ 중복:            {stats.get('duplicates_removed', 0):6d}개")
    logger.info(f"   └─ 검증 실패:       {stats.get('invalid_removed', 0):6d}개")
    logger.info("=" * 70)


def run_analyzer_only(batch_size: int = 10):
    """분석만 실행"""
    logger.info(f"🤖 분석기만 실행 (배치 크기: {batch_size})")
    analyzer.run_analyzer(batch_size=batch_size)


def run_reporter_only(hours: int = 24):
    """리포트만 생성"""
    logger.info(f"📊 리포터만 실행 (최근 {hours}시간)")
    reporter.run_reporter(hours=hours)


def show_statistics():
    """통계 출력"""
    logger.info("\n" + "=" * 70)
    logger.info("📊 시스템 통계")
    logger.info("=" * 70)
    
    # 최근 7일 통계
    try:
        stats = db.get_statistics(days=7)
        
        print(f"\n[최근 7일 통계]")
        print(f"  총 기사: {stats['total_articles']}개")
        print(f"  처리 완료: {stats['processed_articles']}개")
        print(f"  미처리: {stats['unprocessed_articles']}개")
        print(f"  처리율: {stats['processing_rate']}%")
        
        # 소스별 통계
        if stats.get('sources'):
            print(f"\n[소스별 기사 수]")
            source_counts = {}
            for item in stats['sources']:
                source = item.get('source', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {source}: {count}개")
        
        # 설정 정보
        settings = db.get_settings()
        print(f"\n[수집 설정]")
        print(f"  수집 주기: {settings.get('interval_minutes')}분")
        print(f"  마지막 실행: {settings.get('last_run')}")
        
        should_run = db.should_run_collector()
        print(f"  다음 실행: {'가능' if should_run else '대기 중'}")

    except Exception as e:
        logger.error(f"통계 조회 중 오류: {e}")
    
    logger.info("=" * 70)


def test_connection():
    """DB 및 API 연결 테스트"""
    logger.info("\n" + "=" * 70)
    logger.info("🔌 연결 테스트")
    logger.info("=" * 70)
    
    # 1. Supabase 연결
    print("\n[Supabase]")
    try:
        db.ensure_connection()
        print("  ✅ 연결 성공")
        
        countries = db.get_countries()
        keywords = db.get_keywords()
        print(f"  - 국가: {len(countries)}개")
        print(f"  - 키워드: {len(keywords)}개")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
    
    # 2. Gemini API
    print("\n[Gemini API]")
    try:
        api_url = config.get_gemini_api_url()
        print(f"  ✅ API URL 생성 성공")
        print(f"  - 모델: {config.GEMINI_MODEL}")
        print(f"  - URL: {api_url[:80]}...")
    except Exception as e:
        print(f"  ❌ API 설정 오류: {e}")
    
    # 3. Telegram
    print("\n[Telegram]")
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        print("  ✅ 인증 정보 설정됨")
        print(f"  - 채팅 ID: {config.TELEGRAM_CHAT_ID}")
    else:
        print("  ⚠️ 인증 정보 없음 (선택사항)")
    
    # 4. NewsAPI
    print("\n[NewsAPI]")
    if config.NEWSAPI_KEY:
        print("  ✅ API 키 설정됨")
    else:
        print("  ⚠️ API 키 없음 (선택사항)")
        print("  무료 키 발급: https://newsapi.org/register")
    
    logger.info("\n" + "=" * 70)

# ==============================================
# CLI 인터페이스
# ==============================================

def main():
    parser = argparse.ArgumentParser(
        description='Well-Dying Archive - 글로벌 뉴스 수집 및 분석 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python main.py                    # 전체 파이프라인 실행
  python main.py --force            # 주기 무시하고 강제 실행
  python main.py collect            # 수집만 실행
  python main.py analyze            # 분석만 실행
  python main.py report             # 리포트만 생성
  python main.py stats              # 통계 확인
  python main.py test               # 연결 테스트
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['collect', 'analyze', 'report', 'stats', 'test'],
        help='실행할 명령'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='수집 주기 무시하고 강제 실행'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='분석 배치 크기 (기본: 10)'
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='리포트 시간 범위 (기본: 24)'
    )
    
    args = parser.parse_args()
    
    # 명령 실행
    if args.command == 'collect':
        run_collector_only()
    elif args.command == 'analyze':
        run_analyzer_only(batch_size=args.batch_size)
    elif args.command == 'report':
        run_reporter_only(hours=args.hours)
    elif args.command == 'stats':
        show_statistics()
    elif args.command == 'test':
        test_connection()
    else:
        # 기본: 전체 파이프라인
        run_full_pipeline(force=args.force)


if __name__ == "__main__":
    main()