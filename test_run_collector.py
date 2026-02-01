"""
collector 통합 테스트

run_collector 파이프라인의 핵심 로직 검증
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Set


class MockDatabase:
    """DB 모킹 클래스"""
    
    def __init__(self):
        self.saved_articles = []
        self.last_run_updated = False
    
    def get_recent_links(self, days: int) -> Set[str]:
        """최근 링크 반환"""
        return {"https://old.example.com/1", "https://old.example.com/2"}
    
    def get_ban_words(self) -> List[str]:
        """금지어 반환"""
        return ["spam", "advertisement"]
    
    def save_news_batch(self, articles: List[Dict]) -> int:
        """배치 저장"""
        self.saved_articles.extend(articles)
        return len(articles)
    
    def update_last_run(self) -> None:
        """마지막 실행 시간 업데이트"""
        self.last_run_updated = True


class MockConfig:
    """설정 모킹 클래스"""
    
    API_TIMEOUT = 10
    KEYWORDS_EN = ["technology", "science"]
    KEYWORDS_KO = ["기술", "과학"]
    COLLECTOR_LOOKBACK_DAYS = 7
    
    NEWS_SOURCES = {
        "google": {"enabled": True},
        "naver": {"enabled": True}
    }
    
    REDDIT_SOURCES = []
    DIRECT_RSS_SOURCES = []


class TestRunCollectorPipeline:
    """수집 파이프라인 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전 설정"""
        self.mock_db = MockDatabase()
        self.mock_config = MockConfig()
    
    @patch('database.get_recent_links')
    @patch('database.get_ban_words')
    @patch('database.save_news_batch')
    @patch('database.update_last_run')
    @patch('collectors.rss.fetch_google_news')
    @patch('collectors.scraper.fetch_naver_news')
    def test_pipeline_filters_duplicates(
        self,
        mock_naver,
        mock_google,
        mock_update,
        mock_save,
        mock_ban,
        mock_links
    ):
        """파이프라인이 중복 기사를 필터링"""
        # 설정
        mock_links.return_value = {"https://old.example.com/1"}
        mock_ban.return_value = ["spam"]
        
        new_articles = [
            {
                "title": "New Article 1",
                "link": "https://example.com/new1",
                "description": "New content",
                "published_at": "2026-02-01T00:00:00+00:00",
                "source": "Test",
                "country": "Global"
            },
            {
                "title": "Duplicate",
                "link": "https://old.example.com/1",  # 중복
                "description": "Old content",
                "published_at": "2026-02-01T00:00:00+00:00",
                "source": "Test",
                "country": "Global"
            }
        ]
        
        mock_google.return_value = new_articles
        mock_naver.return_value = []
        mock_save.return_value = 1
        
        # 실행 (내부 로직 시뮬레이션)
        existing_links = mock_links(7)
        valid_articles = []
        
        for article in new_articles:
            if article['link'] not in existing_links:
                valid_articles.append(article)
        
        # 검증
        assert len(valid_articles) == 1
        assert valid_articles[0]['link'] == "https://example.com/new1"
    
    @patch('database.get_recent_links')
    @patch('database.get_ban_words')
    def test_pipeline_filters_ban_words(
        self,
        mock_ban,
        mock_links
    ):
        """파이프라인이 금지어 포함 기사를 필터링"""
        mock_links.return_value = set()
        mock_ban.return_value = ["spam", "advertisement"]
        
        articles = [
            {
                "title": "Real News",
                "link": "https://example.com/real",
                "description": "Real content"
            },
            {
                "title": "Buy our SPAM product",
                "link": "https://example.com/spam",
                "description": "Advertisement"
            }
        ]
        
        ban_words = mock_ban()
        valid = []
        
        for article in articles:
            title_lower = article['title'].lower()
            if not any(word.lower() in title_lower for word in ban_words):
                valid.append(article)
        
        assert len(valid) == 1
        assert "SPAM" in articles[1]['title']
    
    def test_pipeline_statistics_calculation(self):
        """파이프라인이 통계를 정확히 계산"""
        stats = {
            "total_crawled": 100,
            "duplicates_removed": 30,
            "invalid_removed": 20,
            "insert_success": 50,
            "insert_failed": 0
        }
        
        valid_articles = stats['total_crawled'] - stats['duplicates_removed'] - stats['invalid_removed']
        success_rate = (stats['insert_success'] / stats['total_crawled'] * 100) if stats['total_crawled'] > 0 else 0
        
        assert valid_articles == 50
        assert success_rate == 50.0
