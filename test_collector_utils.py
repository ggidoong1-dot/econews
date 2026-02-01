"""
collector_utils 단위 테스트

공통 유틸 함수들(날짜 정규화, 해시, 유효성 검사) 검증
"""
import pytest
from datetime import datetime, timezone
from collector_utils import (
    generate_content_hash,
    clean_date,
    is_valid_article
)


class TestGenerateContentHash:
    """해시 생성 함수 테스트"""
    
    def test_hash_consistent(self):
        """동일한 링크는 동일한 해시 생성"""
        link = "https://example.com/article"
        hash1 = generate_content_hash(link)
        hash2 = generate_content_hash(link)
        assert hash1 == hash2
    
    def test_hash_different_for_different_links(self):
        """다른 링크는 다른 해시 생성"""
        hash1 = generate_content_hash("https://example.com/article1")
        hash2 = generate_content_hash("https://example.com/article2")
        assert hash1 != hash2
    
    def test_hash_length(self):
        """MD5 해시는 32자 길이"""
        link = "https://example.com"
        hash_val = generate_content_hash(link)
        assert len(hash_val) == 32


class TestCleanDate:
    """날짜 정규화 함수 테스트"""
    
    def test_clean_date_iso_format(self):
        """ISO 형식 날짜 정규화"""
        date_str = "2026-02-01T12:30:00"
        result = clean_date(date_str)
        assert "T" in result
        assert "+" in result or result.endswith("Z")  # 타임존 정보 포함
    
    def test_clean_date_none_returns_iso_now(self):
        """None 입력 시 현재 시각을 ISO 형식으로 반환"""
        result = clean_date(None)
        assert "T" in result
        assert "+" in result or result.endswith("Z")
    
    def test_clean_date_rfc2822(self):
        """RFC 2822 형식 날짜 정규화"""
        date_str = "Mon, 01 Feb 2026 12:30:00 GMT"
        result = clean_date(date_str)
        assert "T" in result
        assert "+" in result or result.endswith("Z")
    
    def test_clean_date_invalid_returns_iso_now(self):
        """잘못된 날짜는 현재 시각 반환"""
        result = clean_date("invalid_date_string")
        assert "T" in result


class TestIsValidArticle:
    """기사 유효성 검사 함수 테스트"""
    
    def test_valid_article(self):
        """필수 필드가 모두 있는 기사는 유효"""
        article = {
            "title": "Breaking News",
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = []
        assert is_valid_article(article, ban_words) is True
    
    def test_missing_title(self):
        """제목이 없는 기사는 무효"""
        article = {
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = []
        assert is_valid_article(article, ban_words) is False
    
    def test_missing_link(self):
        """링크가 없는 기사는 무효"""
        article = {
            "title": "Breaking News",
            "description": "A news article"
        }
        ban_words = []
        assert is_valid_article(article, ban_words) is False
    
    def test_ban_word_match(self):
        """금지어가 포함된 기사는 무효"""
        article = {
            "title": "Breaking News about SPAM",
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = ["SPAM", "ADVERTISEMENT"]
        assert is_valid_article(article, ban_words) is False
    
    def test_ban_word_case_insensitive(self):
        """금지어 검사는 대소문자 구분 안 함"""
        article = {
            "title": "Breaking News about spam",
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = ["SPAM"]
        assert is_valid_article(article, ban_words) is False
    
    def test_ban_word_partial_match(self):
        """금지어 부분 매칭"""
        article = {
            "title": "Breaking News with advertisement content",
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = ["advert"]
        assert is_valid_article(article, ban_words) is False
    
    def test_no_ban_word_match(self):
        """금지어가 포함되지 않은 기사는 유효"""
        article = {
            "title": "Breaking News about technology",
            "link": "https://example.com/article",
            "description": "A news article"
        }
        ban_words = ["SPAM", "ADVERTISEMENT"]
        assert is_valid_article(article, ban_words) is True
    
    def test_empty_ban_words(self):
        """금지어 리스트가 비어있으면 필수 필드만 검사"""
        article = {
            "title": "Breaking News",
            "link": "https://example.com/article"
        }
        ban_words = []
        assert is_valid_article(article, ban_words) is True
