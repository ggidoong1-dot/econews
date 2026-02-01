"""
한국 시장 영향 분석기
글로벌 뉴스가 한국 주식시장에 미치는 영향을 AI로 분석합니다.
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import config

logger = config.setup_logger(__name__)

# Gemini API - API 키가 있을 때만 초기화
GEMINI_AVAILABLE = False
if config.GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GOOGLE_API_KEY)
        GEMINI_AVAILABLE = True
        logger.info("✅ Gemini API 초기화 완료")
    except Exception as e:
        logger.warning(f"Gemini API 초기화 실패: {e}")
else:
    logger.info("ℹ️ GOOGLE_API_KEY 미설정 - 규칙 기반 분석 사용")


# ==============================================
# 섹터-종목 매핑 데이터
# ==============================================
SECTOR_STOCKS = {
    "반도체": [
        {"code": "005930", "name": "삼성전자", "weight": "high"},
        {"code": "000660", "name": "SK하이닉스", "weight": "high"},
        {"code": "005935", "name": "삼성전자우", "weight": "medium"},
    ],
    "2차전지": [
        {"code": "373220", "name": "LG에너지솔루션", "weight": "high"},
        {"code": "006400", "name": "삼성SDI", "weight": "high"},
        {"code": "247540", "name": "에코프로비엠", "weight": "medium"},
        {"code": "086520", "name": "에코프로", "weight": "medium"},
    ],
    "자동차": [
        {"code": "005380", "name": "현대차", "weight": "high"},
        {"code": "000270", "name": "기아", "weight": "high"},
        {"code": "012330", "name": "현대모비스", "weight": "medium"},
    ],
    "바이오": [
        {"code": "207940", "name": "삼성바이오로직스", "weight": "high"},
        {"code": "068270", "name": "셀트리온", "weight": "high"},
        {"code": "326030", "name": "SK바이오팜", "weight": "medium"},
    ],
    "IT/인터넷": [
        {"code": "035420", "name": "NAVER", "weight": "high"},
        {"code": "035720", "name": "카카오", "weight": "high"},
        {"code": "263750", "name": "펄어비스", "weight": "low"},
    ],
    "금융": [
        {"code": "105560", "name": "KB금융", "weight": "high"},
        {"code": "055550", "name": "신한지주", "weight": "high"},
        {"code": "316140", "name": "우리금융지주", "weight": "medium"},
    ],
    "조선": [
        {"code": "329180", "name": "HD현대중공업", "weight": "high"},
        {"code": "009540", "name": "HD한국조선해양", "weight": "high"},
        {"code": "010620", "name": "HD현대미포", "weight": "medium"},
    ],
    "화학/정유": [
        {"code": "051910", "name": "LG화학", "weight": "high"},
        {"code": "096770", "name": "SK이노베이션", "weight": "high"},
        {"code": "011170", "name": "롯데케미칼", "weight": "medium"},
    ],
    "철강": [
        {"code": "005490", "name": "POSCO홀딩스", "weight": "high"},
        {"code": "004020", "name": "현대제철", "weight": "medium"},
    ],
    "방산": [
        {"code": "012450", "name": "한화에어로스페이스", "weight": "high"},
        {"code": "079550", "name": "LIG넥스원", "weight": "high"},
        {"code": "047810", "name": "한국항공우주", "weight": "medium"},
    ],
    "원자력": [
        {"code": "034020", "name": "두산에너빌리티", "weight": "high"},
        {"code": "052690", "name": "한전기술", "weight": "high"},
    ],
    "엔터": [
        {"code": "352820", "name": "HYBE", "weight": "high"},
        {"code": "035900", "name": "JYP Ent.", "weight": "medium"},
        {"code": "041510", "name": "SM", "weight": "medium"},
    ],
}


# ==============================================
# AI 기반 한국 시장 영향 분석
# ==============================================

def analyze_korea_impact(article: Dict) -> Optional[Dict]:
    """
    Gemini를 사용하여 뉴스의 한국 시장 영향을 분석합니다.
    
    Args:
        article: 뉴스 기사 데이터 (title, description, source 등)
        
    Returns:
        Dict: 영향 분석 결과
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API 사용 불가. 규칙 기반 분석으로 폴백.")
        return analyze_korea_impact_fallback(article)
    
    title = article.get('title', '')
    description = article.get('description', '')[:500]  # 길이 제한
    source = article.get('source', '')
    
    prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다.
아래 글로벌 뉴스가 한국 주식시장에 미치는 영향을 분석해주세요.

[뉴스 정보]
제목: {title}
내용: {description}
출처: {source}

[분석 요청]
아래 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.

{{
    "korea_relevance": "high/medium/low/none",
    "impact_direction": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "affected_sectors": ["섹터명1", "섹터명2"],
    "reasoning": "한국 시장에 미치는 영향 설명 (한글, 100자 이내)",
    "title_ko": "한글 제목 번역"
}}

[주의사항]
- affected_sectors는 다음 중에서만 선택: 반도체, 2차전지, 자동차, 바이오, IT/인터넷, 금융, 조선, 화학/정유, 철강, 방산, 원자력, 엔터
- korea_relevance가 "none"이면 다른 필드는 공백이나 기본값으로 두세요
- 확실하지 않으면 confidence를 낮게 설정하세요
"""
    
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        response = model.generate_content(prompt)
        
        # JSON 파싱
        text = response.text.strip()
        # ```json 블록 제거
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        result = json.loads(text)
        
        # 필수 필드 검증
        required_fields = ["korea_relevance", "impact_direction", "affected_sectors"]
        for field in required_fields:
            if field not in result:
                result[field] = "none" if field == "korea_relevance" else []
        
        result["analysis_method"] = "gemini"
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        return analyze_korea_impact_fallback(article)
    except Exception as e:
        logger.error(f"Gemini 분석 실패: {e}")
        return analyze_korea_impact_fallback(article)


def analyze_korea_impact_fallback(article: Dict) -> Dict:
    """
    규칙 기반 한국 시장 영향 분석 (Gemini 실패 시 폴백).
    """
    from collectors.finance_rss import detect_affected_sectors, calculate_korea_relevance
    
    title = article.get('title', '')
    description = article.get('description', '')
    
    sectors = detect_affected_sectors(title, description)
    relevance = calculate_korea_relevance(title, description)
    
    # 감정 분석 (간단한 키워드 기반)
    text_lower = f"{title} {description}".lower()
    
    negative_words = ["drop", "fall", "decline", "crash", "risk", "concern", 
                      "warning", "cut", "ban", "restrict", "sanction", "loss"]
    positive_words = ["rise", "gain", "surge", "boost", "strong", "growth",
                      "profit", "deal", "invest", "expand", "record"]
    
    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)
    
    if neg_count > pos_count:
        direction = "negative"
    elif pos_count > neg_count:
        direction = "positive"
    else:
        direction = "neutral"
    
    return {
        "korea_relevance": relevance,
        "impact_direction": direction,
        "confidence": 0.5,  # 규칙 기반은 낮은 confidence
        "affected_sectors": sectors,
        "reasoning": "",
        "title_ko": "",
        "analysis_method": "rule_based"
    }


def get_recommended_stocks(sectors: List[str], direction: str) -> List[Dict]:
    """
    영향받는 섹터에서 종목을 추천합니다.
    
    Args:
        sectors: 영향받는 섹터 목록
        direction: 영향 방향 (positive/negative/neutral)
        
    Returns:
        List[Dict]: 추천 종목 목록
    """
    recommendations = []
    
    for sector in sectors:
        if sector not in SECTOR_STOCKS:
            continue
        
        stocks = SECTOR_STOCKS[sector]
        
        for stock in stocks:
            # 높은 가중치 종목만 추천
            if stock["weight"] in ["high", "medium"]:
                recommendations.append({
                    "code": stock["code"],
                    "name": stock["name"],
                    "sector": sector,
                    "direction": direction,
                    "weight": stock["weight"]
                })
    
    # 중복 제거 (종목 코드 기준)
    seen = set()
    unique_recs = []
    for rec in recommendations:
        if rec["code"] not in seen:
            seen.add(rec["code"])
            unique_recs.append(rec)
    
    # 가중치 순 정렬
    weight_order = {"high": 0, "medium": 1, "low": 2}
    unique_recs.sort(key=lambda x: weight_order.get(x["weight"], 2))
    
    return unique_recs[:10]  # 최대 10개


def analyze_news_batch(articles: List[Dict], use_ai: bool = True, rate_limit_delay: float = 5.0) -> List[Dict]:
    """
    여러 뉴스 기사를 배치로 분석합니다.
    
    Args:
        articles: 분석할 기사 목록
        use_ai: AI 분석 사용 여부 (False면 규칙 기반만 사용)
        rate_limit_delay: API 호출 간 대기 시간 (초) - Gemini 무료 버전은 분당 15회 제한
        
    Returns:
        List[Dict]: 분석 결과가 추가된 기사 목록
    """
    import time
    
    logger.info(f"📊 한국 시장 영향 분석 시작: {len(articles)}개 기사")
    
    analyzed = []
    korea_related = 0
    api_calls = 0
    
    for i, article in enumerate(articles):
        try:
            # AI 사용 여부에 따라 분석 방법 선택
            if use_ai and GEMINI_AVAILABLE:
                impact = analyze_korea_impact(article)
                api_calls += 1
                
                # Rate Limiting: Gemini 무료 API는 분당 15회 제한
                # 안전하게 매 호출마다 5초 대기 (분당 최대 12회)
                logger.debug(f"   ⏳ Rate limit 대기 ({rate_limit_delay}초)...")
                time.sleep(rate_limit_delay)
            else:
                impact = analyze_korea_impact_fallback(article)
            
            if impact:
                article["korea_impact"] = impact
                
                # 한국 관련 기사 카운트
                if impact.get("korea_relevance") in ["high", "medium"]:
                    korea_related += 1
                    
                    # 추천 종목 추가
                    if impact.get("affected_sectors"):
                        article["recommended_stocks"] = get_recommended_stocks(
                            impact["affected_sectors"],
                            impact.get("impact_direction", "neutral")
                        )
            
            analyzed.append(article)
            
            if (i + 1) % 10 == 0:
                logger.info(f"   진행: {i + 1}/{len(articles)} ({korea_related}개 한국 관련)")
                
        except Exception as e:
            logger.error(f"   ❌ 기사 분석 실패: {e}")
            analyzed.append(article)
    
    logger.info(f"   ✅ 분석 완료: {len(analyzed)}개 중 {korea_related}개 한국 관련")
    return analyzed


def filter_high_impact_news(articles: List[Dict]) -> List[Dict]:
    """
    한국 시장에 높은 영향을 미치는 뉴스만 필터링합니다.
    """
    high_impact = []
    
    for article in articles:
        impact = article.get("korea_impact", {})
        relevance = impact.get("korea_relevance", "none")
        
        if relevance in ["high", "medium"]:
            high_impact.append(article)
    
    # confidence 순 정렬
    high_impact.sort(
        key=lambda x: x.get("korea_impact", {}).get("confidence", 0),
        reverse=True
    )
    
    return high_impact


def format_impact_report(articles: List[Dict]) -> str:
    """
    한국 시장 영향 분석 결과를 보고서 형식으로 포맷팅합니다.
    """
    high_impact = filter_high_impact_news(articles)
    
    if not high_impact:
        return "📭 한국 시장에 영향을 미치는 주요 뉴스가 없습니다."
    
    lines = [
        "📰 **한국 시장 영향 뉴스**",
        f"총 {len(high_impact)}건의 관련 뉴스",
        ""
    ]
    
    for i, article in enumerate(high_impact[:10], 1):
        impact = article.get("korea_impact", {})
        direction = impact.get("impact_direction", "neutral")
        
        emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(direction, "⚪")
        
        title_ko = impact.get("title_ko") or article.get("title", "")[:50]
        sectors = ", ".join(impact.get("affected_sectors", [])[:3])
        reasoning = impact.get("reasoning", "")[:80]
        
        lines.append(f"{i}. {emoji} **{title_ko}**")
        if sectors:
            lines.append(f"   영향 섹터: {sectors}")
        if reasoning:
            lines.append(f"   → {reasoning}")
        
        # 추천 종목
        stocks = article.get("recommended_stocks", [])[:3]
        if stocks:
            stock_names = ", ".join([s["name"] for s in stocks])
            lines.append(f"   💡 관련 종목: {stock_names}")
        
        lines.append("")
    
    return "\n".join(lines)


# 테스트용
if __name__ == "__main__":
    # 샘플 기사로 테스트
    sample_articles = [
        {
            "title": "Samsung Electronics Q4 profit drops 30% amid chip downturn",
            "description": "Samsung Electronics reported a 30% decline in fourth-quarter operating profit due to weak memory chip demand.",
            "source": "WSJ"
        },
        {
            "title": "Tesla to expand battery production with new suppliers",
            "description": "Tesla announced plans to significantly expand its battery supply chain, potentially benefiting Asian suppliers.",
            "source": "BBC Business"
        },
        {
            "title": "Fed signals potential rate cut in upcoming meeting",
            "description": "The Federal Reserve indicated it may reduce interest rates, boosting global market sentiment.",
            "source": "NPR Business"
        }
    ]
    
    print("한국 시장 영향 분석 테스트...")
    analyzed = analyze_news_batch(sample_articles)
    print(format_impact_report(analyzed))
