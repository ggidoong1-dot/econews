"""
notifications.py 단위 테스트

알림 시스템의 핵심 함수들을 테스트합니다.
"""
import pytest
from unittest.mock import patch, MagicMock
from notifications import (
    send_slack_notification,
    send_slack_rich_message,
    send_high_impact_alert,
    notify_all
)


class TestSendSlackNotification:
    """Slack 알림 함수 테스트"""
    
    @patch('notifications.config')
    def test_disabled_returns_false(self, mock_config):
        """Slack 비활성화 시 False 반환"""
        mock_config.SLACK_ENABLED = False
        result = send_slack_notification("Test message")
        assert result is False
    
    @patch('notifications.config')
    @patch('notifications.requests.post')
    def test_successful_send(self, mock_post, mock_config):
        """성공적인 전송"""
        mock_config.SLACK_ENABLED = True
        mock_config.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        mock_post.return_value.status_code = 200
        
        result = send_slack_notification("Test message")
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch('notifications.config')
    @patch('notifications.requests.post')
    def test_failed_send(self, mock_post, mock_config):
        """실패한 전송"""
        mock_config.SLACK_ENABLED = True
        mock_config.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Bad Request"
        
        result = send_slack_notification("Test message")
        
        assert result is False
    
    @patch('notifications.config')
    @patch('notifications.requests.post')
    def test_request_exception(self, mock_post, mock_config):
        """요청 예외 처리"""
        import requests
        mock_config.SLACK_ENABLED = True
        mock_config.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        mock_post.side_effect = requests.RequestException("Connection error")
        
        result = send_slack_notification("Test message")
        
        assert result is False


class TestSendSlackRichMessage:
    """Slack 리치 메시지 테스트"""
    
    @patch('notifications.config')
    def test_disabled_returns_false(self, mock_config):
        """Slack 비활성화 시 False 반환"""
        mock_config.SLACK_ENABLED = False
        result = send_slack_rich_message("Title", "Text")
        assert result is False
    
    @patch('notifications.config')
    @patch('notifications.requests.post')
    def test_with_fields(self, mock_post, mock_config):
        """필드 포함 메시지"""
        mock_config.SLACK_ENABLED = True
        mock_config.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        mock_post.return_value.status_code = 200
        
        result = send_slack_rich_message(
            title="Test Title",
            text="Test Text",
            color="#36a64f",
            fields=[{"title": "Field1", "value": "Value1", "short": True}],
            footer="Footer text"
        )
        
        assert result is True


class TestSendHighImpactAlert:
    """고영향 뉴스 알림 테스트"""
    
    def test_low_relevance_skipped(self):
        """낮은 관련성은 스킵"""
        article = {
            "title": "Test",
            "korea_impact": {
                "korea_relevance": "low",
                "impact_direction": "neutral"
            }
        }
        result = send_high_impact_alert(article)
        assert result.get("skipped") is True
    
    def test_none_relevance_skipped(self):
        """관련 없음은 스킵"""
        article = {
            "title": "Test",
            "korea_impact": {
                "korea_relevance": "none"
            }
        }
        result = send_high_impact_alert(article)
        assert result.get("skipped") is True
    
    @patch('notifications.send_slack_rich_message')
    @patch('notifications.asyncio.run')
    def test_high_relevance_sends_alert(self, mock_async, mock_slack):
        """높은 관련성은 알림 전송"""
        mock_slack.return_value = True
        mock_async.return_value = True
        
        article = {
            "title": "Samsung Q4 profit drops",
            "link": "https://example.com/news",
            "source": "Reuters",
            "korea_impact": {
                "korea_relevance": "high",
                "impact_direction": "negative",
                "title_ko": "삼성 4분기 이익 감소",
                "affected_sectors": ["반도체"],
                "reasoning": "메모리 칩 수요 감소"
            }
        }
        
        result = send_high_impact_alert(article)
        
        assert result.get("skipped") is not True
        mock_slack.assert_called_once()


class TestNotifyAll:
    """통합 알림 함수 테스트"""
    
    @patch('notifications.config')
    @patch('notifications.send_slack_notification')
    @patch('notifications.asyncio.run')
    def test_all_channels_called(self, mock_async, mock_slack, mock_config):
        """모든 채널 호출"""
        mock_config.SLACK_ENABLED = True
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.TELEGRAM_CHAT_ID = "test_chat"
        mock_slack.return_value = True
        mock_async.return_value = True
        
        result = notify_all("Test message")
        
        assert "slack" in result
        assert "telegram" in result
    
    @patch('notifications.config')
    def test_disabled_channels(self, mock_config):
        """비활성화된 채널"""
        mock_config.SLACK_ENABLED = False
        mock_config.TELEGRAM_BOT_TOKEN = None
        mock_config.TELEGRAM_CHAT_ID = None
        
        result = notify_all("Test message")
        
        assert result.get("slack") is False
        assert result.get("telegram") is False
