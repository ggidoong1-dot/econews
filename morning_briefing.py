"""
모닝 브리핑 생성기 (v2.0)
오전 8시 30분에 실행되어 전날 미국 마감 후 뉴스와
투자 리포트를 분석하고 한국 주식시장 영향 브리핑을 생성합니다.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import config

logger = config.setup_logger(__name__)

# 모듈 임포트
from collectors.finance_rss import fetch_finance_rss_all
from collectors.market_indicators import get_key_indicators, get_risk_level, format_market_summary
from collectors.report_collector import (
    collect_all_reports,
    format_reports_for_briefing
)
from korea_market_analyzer import (
    analyze_news_batch,
    filter_high_impact_news,
    get_recommended_stocks,
    format_impact_report
)


def generate_morning_briefing() -> str:
    """
    모닝 브리핑을 생성합니다.
    
    Returns:
        str: 완성된 브리핑 텍스트
    """
    logger.info("=" * 60)
    logger.info("🌅 모닝 브리핑 생성 시작")
    logger.info("=" * 60)
    
    now = datetime.now(timezone(timedelta(hours=9)))  # KST
    date_str = now.strftime("%Y-%m-%d")
    
    sections = []
    
    # 헤더
    sections.append(f"📊 **[{date_str}] 오늘의 시장 브리핑**\n")
    
    # 1. 글로벌 시장 지표
    logger.info("📈 글로벌 시장 지표 수집...")
    try:
        indicators = get_key_indicators()
        if indicators:
            sections.append(format_market_summary(indicators))
            
            # 리스크 레벨
            risk = get_risk_level(indicators)
            sections.append(f"\n{risk['emoji']} **리스크 레벨**: {risk['level'].upper()}")
            sections.append(f"_{risk['description']}_")
            
            if risk['warnings']:
                sections.append("\n**⚠️ 주의사항**")
                for w in risk['warnings']:
                    sections.append(f"  • {w}")
        else:
            sections.append("\n⚠️ 시장 지표 수집 실패")
    except Exception as e:
        logger.error(f"시장 지표 수집 오류: {e}")
        sections.append("\n⚠️ 시장 지표 수집 중 오류 발생")
    
    sections.append("\n---\n")
    
    # 2. 투자 리포트 수집
    logger.info("📊 투자 리포트 수집...")
    try:
        reports = collect_all_reports()
        report_section = format_reports_for_briefing(reports)
        if report_section and report_section != "리포트 정보 없음":
            sections.append(report_section)
        else:
            sections.append("\n⚠️ 리포트 수집 정보 없음")
    except Exception as e:
        logger.error(f"리포트 수집 오류: {e}")
        sections.append("\n⚠️ 리포트 수집 중 오류 발생")
    
    sections.append("\n---\n")
    
    # 3. 경제 뉴스 수집 및 분석
    logger.info("📰 경제 뉴스 수집...")
    try:
        articles = fetch_finance_rss_all()
        logger.info(f"   수집된 기사: {len(articles)}개")
        
        if articles:
            # 한국 시장 영향 분석 (규칙 기반으로 빠르게)
            logger.info("🔍 한국 시장 영향 분석...")
            analyzed = analyze_news_batch(articles[:50])  # 상위 50개만 분석
            high_impact = filter_high_impact_news(analyzed)
            
            if high_impact:
                sections.append(format_impact_report(analyzed))
                
                # 오늘의 추천 종목 요약
                all_recommendations = []
                for article in high_impact[:5]:
                    recs = article.get("recommended_stocks", [])
                    all_recommendations.extend(recs)
                
                if all_recommendations:
                    # 중복 제거 및 빈도순 정렬
                    stock_counts = {}
                    for rec in all_recommendations:
                        name = rec["name"]
                        if name not in stock_counts:
                            stock_counts[name] = {"count": 0, "direction": rec["direction"], "sectors": set()}
                        stock_counts[name]["count"] += 1
                        stock_counts[name]["sectors"].add(rec["sector"])
                    
                    sorted_stocks = sorted(stock_counts.items(), key=lambda x: x[1]["count"], reverse=True)
                    
                    sections.append("\n---\n")
                    sections.append("💡 **오늘의 관심 종목**")
                    sections.append("")
                    
                    for name, info in sorted_stocks[:5]:
                        direction = info["direction"]
                        emoji = {"positive": "⬆️", "negative": "⬇️", "neutral": "➡️"}.get(direction, "➡️")
                        sectors = ", ".join(info["sectors"])
                        sections.append(f"  {emoji} **{name}** ({sectors})")
            else:
                sections.append("📭 한국 시장에 직접적인 영향을 미치는 뉴스가 없습니다.")
        else:
            sections.append("⚠️ 뉴스 수집 실패")
            
    except Exception as e:
        logger.error(f"뉴스 분석 오류: {e}")
        sections.append("⚠️ 뉴스 분석 중 오류 발생")
    
    # 푸터
    sections.append("\n---")
    sections.append(f"_생성 시간: {now.strftime('%Y-%m-%d %H:%M')} KST_")
    
    briefing = "\n".join(sections)
    
    logger.info("=" * 60)
    logger.info("✅ 모닝 브리핑 생성 완료")
    logger.info("=" * 60)
    
    return briefing


async def send_telegram_briefing(briefing: str) -> bool:
    """
    Telegram으로 브리핑을 전송합니다.
    """
    try:
        from telegram import Bot
        
        token = config.TELEGRAM_BOT_TOKEN
        chat_id = config.TELEGRAM_CHAT_ID
        
        if not token or not chat_id:
            logger.warning("Telegram 설정 누락")
            return False
        
        bot = Bot(token=token)
        
        # 메시지 길이 제한 (4096자)
        if len(briefing) > 4000:
            # 분할 전송
            parts = [briefing[i:i+4000] for i in range(0, len(briefing), 4000)]
            for part in parts:
                await bot.send_message(
                    chat_id=chat_id,
                    text=part,
                    parse_mode='Markdown'
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=briefing,
                parse_mode='Markdown'
            )
        
        logger.info("📤 Telegram 전송 완료")
        return True
        
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")
        return False


def run_morning_briefing(send_telegram: bool = True) -> str:
    """
    모닝 브리핑을 실행합니다.
    
    Args:
        send_telegram: Telegram으로 전송할지 여부
        
    Returns:
        str: 생성된 브리핑
    """
    briefing = generate_morning_briefing()
    
    # 콘솔 출력
    print("\n" + "=" * 60)
    print(briefing)
    print("=" * 60 + "\n")
    
    # Telegram 전송
    if send_telegram:
        try:
            asyncio.run(send_telegram_briefing(briefing))
        except Exception as e:
            logger.error(f"Telegram 전송 오류: {e}")
    
    return briefing


# CLI 실행
if __name__ == "__main__":
    import sys
    
    # --no-telegram 옵션으로 Telegram 전송 없이 실행 가능
    send_telegram = "--no-telegram" not in sys.argv
    
    run_morning_briefing(send_telegram=send_telegram)
