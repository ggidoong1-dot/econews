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
    logger.info("ℹ️ GOOGLE_API_KEY 미설정 - Gemini 사용 불가")

# Groq API - API 키가 있을 때만 초기화
GROQ_AVAILABLE = False
if config.GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=config.GROQ_API_KEY)
        GROQ_AVAILABLE = True
        logger.info("✅ Groq API 초기화 완료")
    except Exception as e:
        logger.warning(f"Groq API 초기화 실패: {e}")
else:
    logger.info("ℹ️ GROQ_API_KEY 미설정 - Groq 사용 불가")


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


def analyze_korea_impact_batch(articles: List[Dict], mode: str = "auto") -> List[Dict]:
    """
    뉴스 배치를 한 번에 분석합니다 (Gemini 또는 Groq 사용).
    
    Args:
        articles: 뉴스 기사 리스트
        mode: 분석 모드 ("auto", "gemini", "groq")
        
    Returns:
        List[Dict]: 분석 결과가 포함된 기사 리스트
    """
    if not articles:
        return []

    # 사용할 API 결정 logic
    use_groq = False
    
    if mode == "groq":
        if GROQ_AVAILABLE:
            use_groq = True
        else:
            logger.warning("Groq 모드 선택되었으나 사용 불가. Gemini로 폴백.")
            if not GEMINI_AVAILABLE:
                logger.warning("Gemini도 사용 불가. 규칙 기반 분석.")
                return _fallback_batch(articles)
                
    elif mode == "gemini":
        if not GEMINI_AVAILABLE:
            if GROQ_AVAILABLE:
                logger.warning("Gemini 사용 불가. Groq로 폴백.")
                use_groq = True
            else:
                return _fallback_batch(articles)
                
    else: # auto
        # 기본적으로 Groq 선호 (더 빠르고 안정적일 경우)
        if GROQ_AVAILABLE:
            use_groq = True
        elif GEMINI_AVAILABLE:
            use_groq = False
        else:
            return _fallback_batch(articles)

    # 1. 프롬프트 구성
    prompt_intro = """당신은 한국 주식시장 전문 애널리스트입니다.
아래 제공된 글로벌 뉴스들이 한국 주식시장에 미치는 영향을 분석해주세요.

[분석 요청]
각 뉴스에 대해 아래 JSON 형식의 객체를 생성하고, 이를 리스트로 묶어서 반환해주세요.
응답은 오직 JSON 리스트만 포함해야 합니다.

개별 뉴스 분석 포맷 (JSON):
{
    "id": "뉴스ID",
    "korea_relevance": "high/medium/low/none",
    "impact_direction": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "affected_sectors": ["섹터명1", "섹터명2"],
    "reasoning": "한국 시장에 미치는 영향 설명 (한글, 100자 이내)",
    "title_ko": "한글 제목 번역"
}

[주의사항]
- affected_sectors는 다음 중에서만 선택: 반도체, 2차전지, 자동차, 바이오, IT/인터넷, 금융, 조선, 화학/정유, 철강, 방산, 원자력, 엔터
- korea_relevance가 "none"이면 reasoning은 간단히 적고 나머지 필드는 기본값.
- 순서를 반드시 지켜주세요.

[뉴스 목록]
"""
    
    news_items = []
    for idx, article in enumerate(articles):
        # 임시 ID 부여 (순서 추적용)
        article_id = f"news_{idx}"
        title = article.get('title', '')
        description = article.get('description', '')[:300]
        source = article.get('source', '')
        
        news_items.append(f"""
ID: {article_id}
제목: {title}
내용: {description}
출처: {source}
---""")
        
    full_prompt = prompt_intro + "\n".join(news_items)

    try:
        text = ""
        
        if use_groq:
            # Groq 호출
            # 새벽 시간대(심층 분석) vs 평시(빠른 분석) 구분 가능하나 현재는 deep 모델 권장
            model_name = config.GROQ_MODEL_DEEP
            
            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a financial analyst specializing in the Korean stock market. Output strictly in JSON."},
                    {"role": "user", "content": full_prompt}
                ],
                model=model_name,
                temperature=0.1,
                response_format={"type": "json_object"} # JSON 모드
            )
            text = completion.choices[0].message.content
            
        else:
            # Gemini 호출
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            response = model.generate_content(full_prompt)
            text = response.text

        # JSON 파싱 공통 로직
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        text = text.strip()
        
        # Groq의 경우 response_format을 써도 가끔 래핑된 JSON이 올 수 있음
        try:
            results_list = json.loads(text)
            # 만약 {"articles": [...]} 형태라면 추출
            if isinstance(results_list, dict):
                for key in results_list:
                    if isinstance(results_list[key], list):
                        results_list = results_list[key]
                        break
        except json.JSONDecodeError:
            # 재시도 또는 오류 처리
            raise ValueError(f"JSON 파싱 실패. 응답 내용: {text[:100]}...")
            
        
        # 결과 매핑
        analyzed_articles = []
        
        # ID로 매핑하기 위해 딕셔너리로 변환
        results_map = {}
        if isinstance(results_list, list):
            for res in results_list:
                if "id" in res:
                    results_map[res["id"]] = res
                    
        for idx, article in enumerate(articles):
            article_id = f"news_{idx}"
            result = results_map.get(article_id)
            
            if result:
                clean_result = {
                    "korea_relevance": result.get("korea_relevance", "none"),
                    "impact_direction": result.get("impact_direction", "neutral"),
                    "confidence": float(result.get("confidence", 0.5)),
                    "affected_sectors": result.get("affected_sectors", []),
                    "reasoning": result.get("reasoning", ""),
                    "title_ko": result.get("title_ko", ""),
                    "analysis_method": "groq" if use_groq else "gemini"
                }
                
                if clean_result["korea_relevance"] not in ["high", "medium", "low", "none"]:
                    clean_result["korea_relevance"] = "none"
                    
                article["korea_impact"] = clean_result
            else:
                logger.warning(f"배치 분석 누락: {article.get('title')}")
                article["korea_impact"] = analyze_korea_impact_fallback(article)
                
            analyzed_articles.append(article)
            
        return analyzed_articles

    except Exception as e:
        logger.error(f"{'Groq' if use_groq else 'Gemini'} 배치 분석 실패: {e}")
        return _fallback_batch(articles)


def _fallback_batch(articles: List[Dict]) -> List[Dict]:
    """전체 규칙 기반 분석으로 처리하는 내부 함수"""
    fallback_results = []
    for article in articles:
        article["korea_impact"] = analyze_korea_impact_fallback(article)
        fallback_results.append(article)
    return fallback_results


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



def analyze_news_batch(articles: List[Dict], use_ai: bool = True, rate_limit_delay: float = 20.0) -> List[Dict]:
    """
    여러 뉴스 기사를 배치로 분석합니다.
    
    Args:
        articles: 분석할 기사 목록
        use_ai: AI 분석 사용 여부 (False면 규칙 기반만 사용)
        rate_limit_delay: 배치 간 대기 시간 (초) - 무료 할당량 보호를 위해 충분히 설정
        
    Returns:
        List[Dict]: 분석 결과가 추가된 기사 목록
    """
    import time
    
    logger.info(f"📊 한국 시장 영향 분석 시작: {len(articles)}개 기사")
    
    analyzed_final = []
    korea_related_count = 0
    
    # 배치 설정 (Gemini Context Window 고려하여 5~10개 적절)
    BATCH_SIZE = 10 
    
    # AI 미사용 시 전체 규칙 기반 처리
    if not use_ai or not GEMINI_AVAILABLE:
        logger.info("ℹ️ AI 미사용 또는 Gemini 모듈 부재 - 전체 규칙 기반 분석")
        for article in articles:
            impact = analyze_korea_impact_fallback(article)
            article["korea_impact"] = impact
            analyzed_final.append(article)
            if impact.get("korea_relevance") in ["high", "medium"]:
                korea_related_count += 1
        return analyzed_final

    # 배치 처리 루프
    total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1
        
        logger.info(f"   🔄 Batch {current_batch_num}/{total_batches} 분석 중 ({len(batch)}건)...")
        
        try:
            # 배치 분석 실행
            analyzed_batch = analyze_korea_impact_batch(batch, mode=config.AI_ANALYZER_MODE)
            
            # 후처리 (추천 종목 등) 및 결과 집계
            for article in analyzed_batch:
                impact = article.get("korea_impact", {})
                
                if impact.get("korea_relevance") in ["high", "medium"]:
                    korea_related_count += 1
                    
                    # 추천 종목 추가
                    if impact.get("affected_sectors"):
                        article["recommended_stocks"] = get_recommended_stocks(
                            impact["affected_sectors"],
                            impact.get("impact_direction", "neutral")
                        )
                
                analyzed_final.append(article)
            
            # Rate Limiting (마지막 배치 제외)
            if i + BATCH_SIZE < len(articles):
                logger.debug(f"   ⏳ Rate limit 대기 ({rate_limit_delay}초)...")
                time.sleep(rate_limit_delay)
                
        except Exception as e:
            logger.error(f"   ❌ Batch {current_batch_num} 처리 중 치명적 오류: {e}")
            # 오류 발생 시 해당 배치만 폴백 처리하여 진행
            for article in batch:
                article["korea_impact"] = analyze_korea_impact_fallback(article)
                analyzed_final.append(article)

    logger.info(f"   ✅ 분석 완료: {len(analyzed_final)}개 중 {korea_related_count}개 한국 관련")
    return analyzed_final


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
