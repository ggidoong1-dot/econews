"""
알림 시스템 모듈 (v1.0)
Slack 웹훅 및 Telegram 통합 알림 지원
고영향 뉴스 즉시 알림 기능 제공
"""
import asyncio
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone

import config

logger = config.setup_logger(__name__)


# ==============================================
# Slack 알림
# ==============================================
def send_slack_notification(
    message: str, 
    channel: Optional[str] = None,
    username: str = "EcoNews Bot",
    icon_emoji: str = ":chart_with_upwards_trend:"
) -> bool:
    """
    Slack 웹훅으로 알림을 전송합니다.
    
    Args:
        message: 전송할 메시지
        channel: 채널 (기본값: config에서 설정)
        username: 봇 이름
        icon_emoji: 봇 아이콘
        
    Returns:
        bool: 전송 성공 여부
    """
    if not config.SLACK_ENABLED:
        logger.debug("Slack이 활성화되지 않았습니다.")
        return False
    
    webhook_url = config.SLACK_WEBHOOK_URL
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL이 설정되지 않았습니다.")
        return False
    
    payload = {
        "text": message,
        "username": username,
        "icon_emoji": icon_emoji
    }
    
    if channel:
        payload["channel"] = channel
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ Slack 알림 전송 완료")
            return True
        else:
            logger.error(f"❌ Slack 알림 실패: {response.status_code} - {response.text}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"❌ Slack 요청 오류: {e}")
        return False


def send_slack_rich_message(
    title: str,
    text: str,
    color: str = "#36a64f",
    fields: Optional[List[Dict]] = None,
    footer: Optional[str] = None
) -> bool:
    """
    Slack 리치 메시지(Attachment)를 전송합니다.
    
    Args:
        title: 메시지 제목
        text: 메시지 본문
        color: 사이드바 색상 (hex)
        fields: 추가 필드 목록
        footer: 푸터 텍스트
        
    Returns:
        bool: 전송 성공 여부
    """
    if not config.SLACK_ENABLED:
        return False
    
    attachment = {
        "color": color,
        "title": title,
        "text": text,
        "ts": datetime.now(timezone.utc).timestamp()
    }
    
    if fields:
        attachment["fields"] = fields
    
    if footer:
        attachment["footer"] = footer
    
    payload = {
        "attachments": [attachment],
        "username": "EcoNews Bot",
        "icon_emoji": ":newspaper:"
    }
    
    try:
        response = requests.post(
            config.SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"❌ Slack 리치 메시지 오류: {e}")
        return False


# ==============================================
# Telegram 알림 (기존 시스템과 통합)
# ==============================================
async def send_telegram_notification(message: str) -> bool:
    """
    Telegram으로 알림을 전송합니다.
    
    Args:
        message: 전송할 메시지
        
    Returns:
        bool: 전송 성공 여부
    """
    try:
        from telegram import Bot
        
        token = config.TELEGRAM_BOT_TOKEN
        chat_id = config.TELEGRAM_CHAT_ID
        
        if not token or not chat_id:
            logger.debug("Telegram 설정이 없습니다.")
            return False
        
        bot = Bot(token=token)
        
        # 메시지 길이 제한 (4096자)
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await bot.send_message(
                    chat_id=chat_id,
                    text=part,
                    parse_mode='Markdown'
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
        
        logger.info("✅ Telegram 알림 전송 완료")
        return True
        
    except ImportError:
        logger.warning("python-telegram-bot 패키지가 설치되지 않았습니다.")
        return False
    except Exception as e:
        logger.error(f"❌ Telegram 전송 실패: {e}")
        return False


# ==============================================
# 고영향 뉴스 즉시 알림
# ==============================================
def send_high_impact_alert(article: Dict) -> Dict[str, bool]:
    """
    고영향 뉴스에 대해 모든 채널로 즉시 알림을 보냅니다.
    
    Args:
        article: 뉴스 기사 데이터 (korea_impact 포함)
        
    Returns:
        Dict[str, bool]: 채널별 전송 결과
    """
    impact = article.get("korea_impact", {})
    relevance = impact.get("korea_relevance", "none")
    direction = impact.get("impact_direction", "neutral")
    
    # 고영향 뉴스만 알림
    if relevance not in ["high"]:
        return {"skipped": True}
    
    # 방향에 따른 이모지
    emoji_map = {
        "positive": "🟢 📈",
        "negative": "🔴 📉",
        "neutral": "⚪ ➡️"
    }
    emoji = emoji_map.get(direction, "📰")
    
    # 메시지 구성
    title = article.get("title", "제목 없음")
    title_ko = impact.get("title_ko", title)
    sectors = ", ".join(impact.get("affected_sectors", [])[:3])
    reasoning = impact.get("reasoning", "")[:100]
    source = article.get("source", "Unknown")
    link = article.get("link", "")
    
    message = f"""
{emoji} *고영향 뉴스 알림*

📰 *{title_ko}*
원문: {title[:50]}...

🏭 영향 섹터: {sectors or "미확인"}
💡 분석: {reasoning or "분석 없음"}

📎 출처: {source}
🔗 {link}
"""
    
    results = {}
    
    # Slack 알림
    color = {"positive": "#36a64f", "negative": "#ff4444", "neutral": "#cccccc"}.get(direction, "#cccccc")
    results["slack"] = send_slack_rich_message(
        title=f"{emoji} 고영향 뉴스: {title_ko[:50]}",
        text=reasoning or "한국 시장에 영향을 미칠 수 있는 뉴스입니다.",
        color=color,
        fields=[
            {"title": "영향 섹터", "value": sectors or "미확인", "short": True},
            {"title": "출처", "value": source, "short": True}
        ],
        footer=f"📎 {link[:50]}..."
    )
    
    # Telegram 알림
    try:
        results["telegram"] = asyncio.run(send_telegram_notification(message))
    except Exception as e:
        logger.error(f"Telegram 알림 오류: {e}")
        results["telegram"] = False
    
    logger.info(f"🔔 고영향 알림 전송: Slack={results.get('slack')}, Telegram={results.get('telegram')}")
    return results


# ==============================================
# 통합 알림 함수
# ==============================================
def notify_all(message: str) -> Dict[str, bool]:
    """
    모든 설정된 채널로 알림을 보냅니다.
    
    Args:
        message: 전송할 메시지
        
    Returns:
        Dict[str, bool]: 채널별 전송 결과
    """
    results = {}
    
    # Slack
    if config.SLACK_ENABLED:
        results["slack"] = send_slack_notification(message)
    else:
        results["slack"] = False
    
    # Telegram
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            results["telegram"] = asyncio.run(send_telegram_notification(message))
        except Exception as e:
            logger.error(f"Telegram 오류: {e}")
            results["telegram"] = False
    else:
        results["telegram"] = False
    
    return results


# ==============================================
# CLI 테스트
# ==============================================
if __name__ == "__main__":
    print("🔔 알림 시스템 테스트")
    print(f"   Slack 활성화: {config.SLACK_ENABLED}")
    print(f"   Telegram 설정: {bool(config.TELEGRAM_BOT_TOKEN)}")
    
    # 테스트 메시지
    test_message = "🧪 테스트 알림입니다. (EcoNews)"
    
    if config.SLACK_ENABLED:
        result = send_slack_notification(test_message)
        print(f"   Slack 테스트: {'성공' if result else '실패'}")
    else:
        print("   Slack: 비활성화 상태")
