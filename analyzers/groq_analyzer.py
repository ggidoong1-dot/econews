"""
Groq AI 기반 뉴스 분석기
새벽 글로벌 뉴스를 초고속으로 분석하여 한국 주식시장 영향을 예측합니다.

핵심 특징:
- 2단계 분석 파이프라인 (1차 필터링 → 2차 심층분석)
- llama-3.1-8b-instant: 빠른 1차 필터링 (560 TPS)
- llama-3.3-70b-versatile: 심층 분석 (280 TPS)
"""
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import os

# Groq SDK
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = config.setup_logger(__name__)


# ==============================================
# Groq 모델 설정
# ==============================================
GROQ_MODELS = {
    "fast": "llama-3.1-8b-instant",      # 1차 필터링용 (빠르고 저렴)
    "deep": "llama-3.3-70b-versatile",   # 2차 심층분석용 (정확)
    "tool": "llama-3-groq-70b-tool-use", # 도구 사용 특화
}

# Rate Limit 설정 (Groq Free tier: 30 RPM)
RATE_LIMIT_DELAY = {
    "fast": 2.0,   # 8b 모델은 빠르므로 2초 대기
    "deep": 4.0,   # 70b 모델은 조금 더 여유있게
}


# ==============================================
# Groq 클라이언트 초기화
# ==============================================
class GroqAnalyzer:
    """Groq AI 분석기 클래스"""
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Groq API 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = None
        self.available = False
        
        if not GROQ_AVAILABLE:
            logger.warning("⚠️ groq 패키지가 설치되지 않음. pip install groq 실행 필요")
            return
            
        if not self.api_key:
            logger.warning("⚠️ GROQ_API_KEY가 설정되지 않음")
            return
        
        try:
            self.client = Groq(api_key=self.api_key)
            self.available = True
            logger.info("✅ Groq API 초기화 완료")
        except Exception as e:
            logger.error(f"❌ Groq API 초기화 실패: {e}")
    
    def _call_api(self, prompt: str, model_type: str = "fast", 
                  temperature: float = 0.3, max_tokens: int = 1024) -> Optional[str]:
        """
        Groq API 호출
        
        Args:
            prompt: 프롬프트
            model_type: "fast" 또는 "deep"
            temperature: 창의성 (0.0~1.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            str: 응답 텍스트 또는 None
        """
        if not self.available:
            return None
        
        model = GROQ_MODELS.get(model_type, GROQ_MODELS["fast"])
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식시장 전문 애널리스트입니다. 글로벌 뉴스를 분석하여 한국 시장에 미치는 영향을 정확히 예측합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq API 호출 실패 ({model}): {e}")
            return None
    
    def filter_korea_relevant(self, article: Dict) -> Dict:
        """
        1차 필터링: 한국 시장 관련성 빠르게 판단
        llama-3.1-8b-instant 사용 (초고속)
        
        Args:
            article: 뉴스 기사 데이터
            
        Returns:
            Dict: 관련성 판단 결과
        """
        title = article.get('title', '')
        description = article.get('description', '')[:300]
        
        prompt = f"""다음 뉴스가 한국 주식시장에 영향을 미치는지 빠르게 판단하세요.

제목: {title}
내용: {description}

JSON 형식으로만 응답:
{{
    "is_relevant": true/false,
    "relevance_level": "high/medium/low/none",
    "quick_reason": "한 문장 이유"
}}"""

        result = self._call_api(prompt, model_type="fast", max_tokens=256)
        
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        
        # 폴백: 규칙 기반 판단
        return self._rule_based_relevance(article)
    
    def analyze_deep(self, article: Dict) -> Dict:
        """
        2차 심층 분석: 상세한 영향 분석 및 예측
        llama-3.3-70b-versatile 사용 (정확)
        
        Args:
            article: 뉴스 기사 데이터
            
        Returns:
            Dict: 상세 분석 결과
        """
        title = article.get('title', '')
        description = article.get('description', '')[:500]
        source = article.get('source', '')
        
        prompt = f"""글로벌 뉴스의 한국 주식시장 영향을 상세히 분석하세요.

[뉴스 정보]
제목: {title}
내용: {description}
출처: {source}

[분석 요청]
JSON 형식으로만 응답:
{{
    "korea_relevance": "high/medium/low/none",
    "impact_direction": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "affected_sectors": ["섹터명1", "섹터명2"],
    "impact_timing": "시초가/장중/장마감/다음날",
    "investment_strategy": "매수/매도/관망",
    "reasoning": "한국 시장에 미치는 영향 설명 (한글, 150자 이내)",
    "title_ko": "한글 제목 번역",
    "key_factors": ["핵심 요인1", "핵심 요인2"]
}}

[섹터 선택지]
반도체, 2차전지, 자동차, 바이오, IT/인터넷, 금융, 조선, 화학/정유, 철강, 방산, 원자력, 엔터, 건설, 유통, 통신

[주의사항]
- korea_relevance가 "none"이면 다른 필드는 기본값으로
- confidence는 확신이 없으면 낮게 설정
- investment_strategy는 신중하게 제안"""

        result = self._call_api(prompt, model_type="deep", max_tokens=1024)
        
        if result:
            try:
                parsed = json.loads(result)
                parsed["analysis_method"] = "groq_deep"
                return parsed
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
        
        # 폴백: 규칙 기반 분석
        return self._rule_based_analysis(article)
    
    def _rule_based_relevance(self, article: Dict) -> Dict:
        """규칙 기반 관련성 판단 (폴백)"""
        title = article.get('title', '').lower()
        desc = article.get('description', '').lower()
        text = f"{title} {desc}"
        
        # 직접 관련 키워드
        direct_keywords = [
            "korea", "korean", "samsung", "sk hynix", "hyundai", "kia",
            "lg", "kospi", "kosdaq", "won", "krw", "seoul"
        ]
        
        # 간접 관련 키워드
        indirect_keywords = [
            "semiconductor", "chip", "battery", "ev", "fed", "interest rate",
            "china", "japan", "trade", "tariff", "oil", "nvidia", "tsmc",
            "nasdaq", "s&p", "dow jones", "treasury"
        ]
        
        direct_count = sum(1 for kw in direct_keywords if kw in text)
        indirect_count = sum(1 for kw in indirect_keywords if kw in text)
        
        if direct_count >= 2:
            return {"is_relevant": True, "relevance_level": "high", "quick_reason": "직접 언급"}
        elif direct_count >= 1:
            return {"is_relevant": True, "relevance_level": "medium", "quick_reason": "한국 관련 키워드 포함"}
        elif indirect_count >= 3:
            return {"is_relevant": True, "relevance_level": "medium", "quick_reason": "간접 영향 가능성"}
        elif indirect_count >= 1:
            return {"is_relevant": True, "relevance_level": "low", "quick_reason": "약한 연관성"}
        else:
            return {"is_relevant": False, "relevance_level": "none", "quick_reason": "관련성 없음"}
    
    def _rule_based_analysis(self, article: Dict) -> Dict:
        """규칙 기반 분석 (폴백)"""
        from collectors.finance_rss import detect_affected_sectors, calculate_korea_relevance
        
        title = article.get('title', '')
        description = article.get('description', '')
        
        sectors = detect_affected_sectors(title, description)
        relevance = calculate_korea_relevance(title, description)
        
        # 간단한 감정 분석
        text_lower = f"{title} {description}".lower()
        
        negative_words = ["drop", "fall", "decline", "crash", "risk", "concern", 
                          "warning", "cut", "ban", "restrict", "sanction", "loss"]
        positive_words = ["rise", "gain", "surge", "boost", "strong", "growth",
                          "profit", "deal", "invest", "expand", "record"]
        
        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)
        
        if neg_count > pos_count:
            direction = "negative"
            strategy = "관망"
        elif pos_count > neg_count:
            direction = "positive"
            strategy = "관망"
        else:
            direction = "neutral"
            strategy = "관망"
        
        return {
            "korea_relevance": relevance,
            "impact_direction": direction,
            "confidence": 0.5,
            "affected_sectors": sectors,
            "impact_timing": "장중",
            "investment_strategy": strategy,
            "reasoning": "",
            "title_ko": "",
            "key_factors": [],
            "analysis_method": "rule_based"
        }


# ==============================================
# 편의 함수 (모듈 레벨)
# ==============================================

# 싱글톤 인스턴스
_analyzer_instance: Optional[GroqAnalyzer] = None

def _get_analyzer() -> GroqAnalyzer:
    """싱글톤 분석기 인스턴스 반환"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GroqAnalyzer()
    return _analyzer_instance


def analyze_with_groq(article: Dict, deep: bool = True) -> Dict:
    """
    단일 기사 Groq 분석
    
    Args:
        article: 뉴스 기사
        deep: True면 심층분석, False면 1차 필터링만
        
    Returns:
        Dict: 분석 결과
    """
    analyzer = _get_analyzer()
    
    if deep:
        return analyzer.analyze_deep(article)
    else:
        return analyzer.filter_korea_relevant(article)


def filter_korea_relevant_news(articles: List[Dict], 
                                rate_limit_delay: float = 2.0) -> Tuple[List[Dict], List[Dict]]:
    """
    1차 필터링: 한국 관련 뉴스만 추출 (빠른 모델 사용)
    
    Args:
        articles: 전체 뉴스 목록
        rate_limit_delay: API 호출 간 대기 시간
        
    Returns:
        Tuple[relevant, not_relevant]: 관련 뉴스와 비관련 뉴스
    """
    logger.info(f"🔍 1차 필터링 시작: {len(articles)}개 기사")
    
    analyzer = _get_analyzer()
    relevant = []
    not_relevant = []
    
    for i, article in enumerate(articles):
        try:
            result = analyzer.filter_korea_relevant(article)
            article["filter_result"] = result
            
            if result.get("is_relevant", False):
                relevant.append(article)
            else:
                not_relevant.append(article)
            
            if (i + 1) % 10 == 0:
                logger.info(f"   진행: {i + 1}/{len(articles)} (관련: {len(relevant)}개)")
            
            time.sleep(rate_limit_delay)
            
        except Exception as e:
            logger.error(f"   ❌ 필터링 실패: {e}")
            not_relevant.append(article)
    
    logger.info(f"   ✅ 필터링 완료: {len(relevant)}개 관련, {len(not_relevant)}개 제외")
    return relevant, not_relevant


def analyze_news_batch_groq(articles: List[Dict], 
                            use_two_stage: bool = True,
                            rate_limit_delay: float = 3.0) -> List[Dict]:
    """
    배치 뉴스 분석 (2단계 파이프라인)
    
    Args:
        articles: 분석할 기사 목록
        use_two_stage: True면 2단계 분석, False면 바로 심층분석
        rate_limit_delay: API 호출 간 대기 시간
        
    Returns:
        List[Dict]: 분석 결과가 추가된 기사 목록
    """
    logger.info(f"📊 Groq 배치 분석 시작: {len(articles)}개 기사")
    
    analyzer = _get_analyzer()
    
    if not analyzer.available:
        logger.warning("⚠️ Groq API 사용 불가. 규칙 기반 분석으로 폴백")
        for article in articles:
            article["korea_impact"] = analyzer._rule_based_analysis(article)
        return articles
    
    # 2단계 분석
    if use_two_stage:
        # 1단계: 빠른 필터링
        relevant, _ = filter_korea_relevant_news(articles, rate_limit_delay=2.0)
        
        logger.info(f"🔬 2차 심층 분석: {len(relevant)}개 기사")
        
        # 2단계: 관련 뉴스만 심층 분석
        for i, article in enumerate(relevant):
            try:
                impact = analyzer.analyze_deep(article)
                article["korea_impact"] = impact
                
                if (i + 1) % 5 == 0:
                    logger.info(f"   심층분석 진행: {i + 1}/{len(relevant)}")
                
                time.sleep(rate_limit_delay)
                
            except Exception as e:
                logger.error(f"   ❌ 심층분석 실패: {e}")
                article["korea_impact"] = analyzer._rule_based_analysis(article)
        
        return relevant
    
    else:
        # 모든 기사 심층분석 (시간 오래 걸림)
        for i, article in enumerate(articles):
            try:
                impact = analyzer.analyze_deep(article)
                article["korea_impact"] = impact
                
                if (i + 1) % 5 == 0:
                    logger.info(f"   진행: {i + 1}/{len(articles)}")
                
                time.sleep(rate_limit_delay)
                
            except Exception as e:
                logger.error(f"   ❌ 분석 실패: {e}")
                article["korea_impact"] = analyzer._rule_based_analysis(article)
        
        return articles


# ==============================================
# 테스트
# ==============================================
if __name__ == "__main__":
    print("=" * 60)
    print("Groq 분석기 테스트")
    print("=" * 60)
    
    # 테스트 기사
    test_articles = [
        {
            "title": "Fed signals potential rate cut amid cooling inflation",
            "description": "The Federal Reserve indicated it may reduce interest rates in the coming months as inflation shows signs of cooling, boosting global market sentiment.",
            "source": "Reuters"
        },
        {
            "title": "Samsung Electronics Q1 profit expected to surge on memory chip demand",
            "description": "Samsung Electronics is expected to report a significant profit increase in Q1 driven by strong memory chip demand from AI data centers.",
            "source": "WSJ"
        },
        {
            "title": "Local bakery wins best croissant award",
            "description": "A small bakery in Paris has been awarded the best croissant in the city for the third consecutive year.",
            "source": "Local News"
        }
    ]
    
    print("\n1️⃣ 1차 필터링 테스트")
    print("-" * 40)
    
    analyzer = GroqAnalyzer()
    
    if analyzer.available:
        for article in test_articles:
            result = analyzer.filter_korea_relevant(article)
            print(f"\n제목: {article['title'][:50]}...")
            print(f"관련성: {result.get('relevance_level')} - {result.get('quick_reason')}")
        
        print("\n2️⃣ 2차 심층분석 테스트 (첫 번째 기사)")
        print("-" * 40)
        
        deep_result = analyzer.analyze_deep(test_articles[1])
        print(json.dumps(deep_result, ensure_ascii=False, indent=2))
    else:
        print("⚠️ Groq API 사용 불가. GROQ_API_KEY를 설정하세요.")
        print("   규칙 기반 분석 결과:")
        for article in test_articles:
            result = analyzer._rule_based_relevance(article)
            print(f"\n제목: {article['title'][:50]}...")
            print(f"관련성: {result.get('relevance_level')}")
