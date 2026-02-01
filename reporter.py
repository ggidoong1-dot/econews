"""
일일 리포터 (v3.0)
Gemini API를 사용하여 일일 브리핑 생성 및 Telegram 전송
"""
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from telegram import Bot
import config
import database as db

# 로거 설정
logger = config.setup_logger(__name__)

# ==============================================
# AI 리포트 생성
# ==============================================

def generate_daily_report(articles: List[Dict]) -> Tuple[Optional[str], List[str]]:
    """
    Gemini API를 사용하여 일일 브리핑을 생성합니다.
    
    Args:
        articles: 지난 24시간 내 기사 리스트
        
    Returns:
        Tuple[Optional[str], List[str]]: (리포트 본문, 새로운 키워드 리스트)
    """
    if not articles:
        logger.warning("분석할 기사가 없습니다.")
        return None, []
    
    api_url = config.get_gemini_api_url()
    
    # 기사 정보 구성
    articles_text = ""
    for idx, article in enumerate(articles[:50], 1):  # 최대 50개만
        # 한글 제목이 있으면 사용, 없으면 원본
        title = article.get('title_ko') or article.get('title')
        source = article.get('source', 'Unknown')
        category = article.get('category', '')
        sentiment = article.get('sentiment', '')
        
        articles_text += f"{idx}. [{source}] {title}"
        if category:
            articles_text += f" ({category}, {sentiment})"
        articles_text += "\n"
    
    # 프롬프트 구성
    prompt = f"""
You are an expert analyst specializing in 'Well-Dying/Euthanasia/Death with Dignity' topics.

Below are news headlines from the last 24 hours:

{articles_text}

[Mission]
1. Summarize the major trends and developments in Korean (3-5 bullet points)
2. Analyze the overall sentiment distribution (Positive/Negative/Neutral percentages)
3. Identify 2-3 emerging keywords or topics that are gaining attention
4. Provide a brief outlook or implication for the field

[Output Format]
Start with: 📢 [일일 웰다잉 브리핑 - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}]

Write in Korean, professional but accessible tone.

End with a line: "KEYWORDS: keyword1, keyword2, keyword3"
"""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 1000
        }
    }
    
    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=config.API_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        
        # 응답 검증
        if 'candidates' not in data or not data['candidates']:
            logger.error(f"❌ 예상치 못한 API 응답: {data}")
            return None, []
        
        candidate = data['candidates'][0]
        
        # Safety filter 체크
        if candidate.get('finishReason') == 'SAFETY':
            logger.warning("⚠️ 안전 필터에 의해 차단됨")
            return None, []
        
        text = candidate['content']['parts'][0]['text']
        
        # 리포트 본문과 키워드 분리
        report_body = text
        new_keywords = []
        
        if "KEYWORDS:" in text:
            parts = text.split("KEYWORDS:")
            report_body = parts[0].strip()
            kw_str = parts[1].strip()
            new_keywords = [k.strip() for k in kw_str.split(',') if k.strip()]
        
        logger.info("✅ 일일 리포트 생성 완료")
        return report_body, new_keywords
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ API HTTP 에러: {e.response.status_code}")
        if hasattr(e, 'response'):
            logger.error(f"응답: {e.response.text[:200]}")
        return None, []
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ API 타임아웃 ({config.API_TIMEOUT}초)")
        return None, []
        
    except Exception as e:
        logger.error(f"❌ 리포트 생성 실패: {e}")
        return None, []

# ==============================================
# Telegram 전송
# ==============================================

async def send_telegram_message(message: str) -> bool:
    """
    Telegram Bot을 통해 메시지를 전송합니다.
    
    Args:
        message: 전송할 메시지
        
    Returns:
        bool: 전송 성공 여부
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram 인증 정보 없음, 전송 스킵")
        return False
    
    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        
        # Telegram 메시지 길이 제한: 4096자
        if len(message) > 4000:
            # 긴 메시지는 분할 전송
            logger.info("메시지가 길어 분할 전송합니다.")
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            
            for idx, chunk in enumerate(chunks, 1):
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHAT_ID,
                    text=f"[{idx}/{len(chunks)}]\n\n{chunk}",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(1)  # 연속 전송 간 대기
        else:
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )
        
        logger.info("✅ Telegram 전송 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ Telegram 전송 실패: {e}")
        return False

# ==============================================
# 메인 리포터 로직
# ==============================================

def run_reporter(hours: int = 24):
    """
    일일 리포터 실행
    
    Args:
        hours: 조회할 시간 범위 (기본: 24시간)
    """
    logger.info("=" * 60)
    logger.info(f"🎙️ 일일 리포터 시작 (최근 {hours}시간)")
    logger.info("=" * 60)
    
    # 1. 최근 기사 조회
    articles = db.get_recent_articles(hours=hours)
    
    if not articles:
        logger.info(f"📭 최근 {hours}시간 내 기사가 없습니다.")
        
        # 기사가 없어도 알림 전송 (선택사항)
        no_news_message = f"""
📢 [일일 웰다잉 브리핑 - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}]

최근 {hours}시간 동안 수집된 새로운 기사가 없습니다.

다음 브리핑을 기다려주세요.
"""
        asyncio.run(send_telegram_message(no_news_message))
        return
    
    logger.info(f"📊 분석 대상: {len(articles)}개 기사")
    
    # 2. 통계 정보
    processed_count = sum(1 for a in articles if a.get('is_processed'))
    sources = {}
    for article in articles:
        source = article.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
    
    logger.info(f"   처리 완료: {processed_count}/{len(articles)}개")
    logger.info(f"   소스별: {dict(list(sources.items())[:5])}")  # 상위 5개만
    
    # 3. AI 리포트 생성
    logger.info("🤖 AI 리포트 생성 중...")
    report, keywords = generate_daily_report(articles)
    
    if not report:
        logger.error("❌ 리포트 생성 실패")
        
        # 실패해도 기본 통계 전송
        fallback_message = f"""
📢 [일일 웰다잉 브리핑 - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}]

⚠️ AI 분석 중 오류가 발생했습니다.

기본 통계:
- 총 기사: {len(articles)}개
- 처리 완료: {processed_count}개
- 주요 소스: {', '.join(list(sources.keys())[:3])}

자세한 내용은 대시보드에서 확인해주세요.
"""
        asyncio.run(send_telegram_message(fallback_message))
        return
    
    # 4. 추가 통계 정보 덧붙이기
    enhanced_report = f"""{report}

━━━━━━━━━━━━━━━━━━━━
📈 통계 요약
• 총 기사: {len(articles)}개
• AI 분석 완료: {processed_count}개
• 주요 출처: {', '.join(list(sources.keys())[:3])}

#웰다잉 #존엄사 #WellDying
"""
    
    # 5. DB에 저장
    today = datetime.now(timezone.utc).date().isoformat()
    db.save_daily_report(today, report, keywords)
    
    # 6. Telegram 전송
    logger.info("📤 Telegram 전송 중...")
    asyncio.run(send_telegram_message(enhanced_report))
    
    # 7. 새로운 키워드 로깅
    if keywords:
        logger.info(f"🔑 새로운 트렌드 키워드: {', '.join(keywords)}")
    
    logger.info("=" * 60)
    logger.info("✅ 리포터 완료")
    logger.info("=" * 60)


def generate_weekly_summary():
    """
    주간 요약 리포트 생성 (향후 확장용)
    """
    logger.info("📅 주간 요약 리포트 (개발 예정)")
    # TODO: 주간 통계 및 트렌드 분석
    pass


if __name__ == "__main__":
    try:
        run_reporter()
    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"\n❌ 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
