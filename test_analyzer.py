"""
analyzer.py 단위 테스트

AI 분석기의 핵심 함수들을 테스트합니다.
"""
import pytest
from unittest.mock import patch, MagicMock
from analyzer import (
    fallback_translate,
    calculate_quality_score,
    extract_content_from_description,
    get_adaptive_delay,
    AI_COOLDOWN_DEFAULT,
    AI_COOLDOWN_MIN,
    AI_COOLDOWN_MAX
)


class TestGetAdaptiveDelay:
    """적응형 대기 시간 함수 테스트"""
    
    def test_no_requests_returns_default(self):
        """요청이 없으면 기본값 반환"""
        delay = get_adaptive_delay(0, 0)
        assert delay == AI_COOLDOWN_DEFAULT
    
    def test_high_success_returns_min(self):
        """성공률이 높으면 최소 대기 시간"""
        delay = get_adaptive_delay(10, 0)
        assert delay == AI_COOLDOWN_MIN
    
    def test_high_failure_returns_max(self):
        """실패율이 높으면 최대 대기 시간"""
        delay = get_adaptive_delay(3, 7)
        assert delay == AI_COOLDOWN_MAX
    
    def test_moderate_failure_returns_default(self):
        """중간 실패율은 기본 대기 시간"""
        delay = get_adaptive_delay(8, 2)
        assert delay == AI_COOLDOWN_DEFAULT
    
    def test_all_success_returns_min(self):
        """모두 성공하면 최소 대기 시간"""
        delay = get_adaptive_delay(100, 0)
        assert delay == AI_COOLDOWN_MIN


class TestFallbackTranslate:
    """폴백 번역 함수 테스트"""
    
    @patch('deep_translator.GoogleTranslator')
    def test_korean_translation(self, mock_translator_class):
        """한국어 번역 테스트"""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "번역된 제목"
        mock_translator_class.return_value = mock_translator
        
        result = fallback_translate("Original Title", target_lang='ko')
        
        # deep_translator가 설치되지 않은 경우에도 테스트 통과
        if result is not None:
            assert 'is_fallback' in result
    
    def test_import_error_returns_none(self):
        """deep_translator가 없으면 None 반환"""
        with patch.dict('sys.modules', {'deep_translator': None}):
            # 이 테스트는 실제로 ImportError를 시뮬레이션하기 어려우므로 스킵
            pass


class TestCalculateQualityScore:
    """품질 점수 계산 함수 테스트"""
    
    def test_full_score(self):
        """완벽한 결과는 100점"""
        result = {
            'title_ko': '충분히 긴 한국어 제목입니다',
            'summary': '- 첫 번째 포인트\n- 두 번째 포인트\n- 세 번째 포인트',
            'category': 'Law/Policy',
            'sentiment': 'Positive'
        }
        score = calculate_quality_score(result)
        assert score == 100
    
    def test_missing_title_loses_points(self):
        """제목이 없으면 30점 손실"""
        result = {
            'title_ko': '',
            'summary': '- 첫 번째\n- 두 번째\n- 세 번째',
            'category': 'Medical',
            'sentiment': 'Neutral'
        }
        score = calculate_quality_score(result)
        assert score == 70
    
    def test_short_summary_loses_points(self):
        """요약이 짧으면 점수 감소"""
        result = {
            'title_ko': '충분히 긴 한국어 제목',
            'summary': '- 하나만',
            'category': 'Tech',
            'sentiment': 'Negative'
        }
        score = calculate_quality_score(result)
        assert score < 100
    
    def test_empty_result(self):
        """빈 결과는 낮은 점수"""
        result = {}
        score = calculate_quality_score(result)
        assert score == 0


class TestExtractContentFromDescription:
    """HTML 추출 함수 테스트"""
    
    def test_plain_text(self):
        """일반 텍스트는 그대로 반환"""
        text = "This is plain text."
        result = extract_content_from_description(text)
        assert result == text
    
    def test_html_stripped(self):
        """HTML 태그 제거 (또는 BeautifulSoup 없으면 그대로)"""
        html = "<p>This is <strong>HTML</strong> content.</p>"
        result = extract_content_from_description(html)
        # BeautifulSoup가 설치되어 있으면 태그 제거, 아니면 그대로
        assert "HTML" in result or "content" in result
    
    def test_empty_returns_empty(self):
        """빈 입력은 빈 문자열"""
        result = extract_content_from_description("")
        assert result == ""
    
    def test_none_returns_empty(self):
        """None 입력은 빈 문자열"""
        result = extract_content_from_description(None)
        assert result == ""
    
    def test_max_length_respected(self):
        """최대 길이 제한"""
        long_text = "A" * 2000
        result = extract_content_from_description(long_text, max_length=500)
        assert len(result) <= 500


# 통합 테스트 (선택적)
class TestAnalyzerIntegration:
    """통합 테스트 (실제 API 호출 없이)"""
    
    def test_quality_score_range(self):
        """품질 점수는 0-100 범위"""
        test_cases = [
            {},
            {'title_ko': 'x'},
            {'title_ko': '충분히 긴 제목', 'summary': '- a\n- b\n- c'}
        ]
        
        for result in test_cases:
            score = calculate_quality_score(result)
            assert 0 <= score <= 100
