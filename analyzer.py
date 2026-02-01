"""
AI 분석기 (v3.0)
Gemini 2.5 Flash를 사용하여 뉴스 기사 분석
429 에러 시 무료 번역 라이브러리로 폴백
"""
import os
import time
import json
import random
from typing import Dict, Optional, List
import google.generativeai as genai
from google.api_core import exceptions

import config
import database as db

# 로거 설정
logger = config.setup_logger(__name__)

# ==============================================
# 폴백 번역 함수 (Gemini 429 시 사용)
# ==============================================
def fallback_translate(title: str) -> Optional[Dict]:
    """
    Gemini API가 429 에러 시 무료 번역 라이브러리 사용
    deep-translator (Google Translate 무료) 사용
    """
    try:
        from deep_translator import GoogleTranslator
        
        # 제목 번역
        translator = GoogleTranslator(source='auto', target='ko')
        title_ko = translator.translate(title)
        
        logger.info(f"   🔄 폴백 번역 사용: {title_ko[:50]}...")
        
        return {
            "title_ko": title_ko,
            "summary": "- AI 분석 대기 중 (Gemini 할당량 초과)\n- 번역만 완료됨\n- 나중에 재분석 필요",
            "category": "Uncategorized",
            "sentiment": "Neutral",
            "is_fallback": True  # 폴백 사용 표시
        }
    except ImportError:
        logger.error("❌ deep-translator가 설치되지 않았습니다. pip install deep-translator")
        return None
    except Exception as e:
        logger.error(f"❌ 폴백 번역 실패: {e}")
        return None

# ==============================================
# 전역 429 카운터 (서킷 브레이커)
# ==============================================
_consecutive_429_count = 0
_CIRCUIT_BREAKER_THRESHOLD = 2  # 연속 2개 기사 429 시 Gemini 스킵

def reset_429_counter():
    """429 카운터 리셋 (성공 시 호출)"""
    global _consecutive_429_count
    _consecutive_429_count = 0

def increment_429_counter():
    """429 카운터 증가"""
    global _consecutive_429_count
    _consecutive_429_count += 1
    return _consecutive_429_count

def should_skip_gemini() -> bool:
    """Gemini API를 건너뛰어야 하는지 확인"""
    if _consecutive_429_count >= _CIRCUIT_BREAKER_THRESHOLD:
        return True
    return False

# ==============================================
# AI 분석 함수
# ==============================================

def analyze_article(title: str, content: str, link: str = "") -> Optional[Dict]:
    """
    Gemini API를 사용하여 기사를 분석합니다.
    (google-generativeai 라이브러리 사용)
    연속 429 발생 시 자동으로 폴백 번역 사용
    """
    
    # 서킷 브레이커: 연속 429 발생 시 Gemini 건너뛰기
    if should_skip_gemini():
        logger.warning(f"⚡ 서킷 브레이커 발동 - Gemini 건너뛰고 폴백 사용 (연속 {_consecutive_429_count}회 429)")
        return fallback_translate(title)
    
    # 1. API 키 설정
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
        return fallback_translate(title)  # API 키 없어도 폴백 시도

    genai.configure(api_key=api_key)

    # 2. 모델 설정 (핵심: JSON 강제 및 토큰 증가)
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 8192,           # 👈 토큰을 넉넉하게 늘림 (짤림 방지)
            "response_mime_type": "application/json"  # 👈 무조건 JSON으로 반환 강제
        }
    )
    
    # 3. 프롬프트 구성
    prompt = f"""
Analyze this news article about 'Well-Dying/Euthanasia/Death with Dignity'.

Title: {title}
Content: {content}
{f"Link: {link}" if link else ""}

[Tasks]
1. Translate the title to Korean naturally and accurately.
2. Summarize the key points in 3 bullet points (write in Korean).
3. Categorize into ONE of: [Law/Policy, Medical, Social/Ethics, Tech/Industry, Research, Personal Story]
4. Sentiment Analysis: 
   - Positive (Pro-choice, supporting euthanasia/death with dignity)
   - Negative (Anti-choice, opposing euthanasia)
   - Neutral (balanced reporting, informational)

[Output Format]
You must output a JSON object with these exact keys:
{{
    "title_ko": "Korean translation",
    "summary": "- Point 1\\n- Point 2\\n- Point 3",
    "category": "Category Name",
    "sentiment": "Sentiment Value"
}}
"""
    
    retry_count = 0
    max_retries = 3
    use_fallback = False  # 폴백 사용 플래그
    
    while retry_count < max_retries:
        try:
            # 4. API 호출
            response = model.generate_content(prompt)
            
            # 5. 결과 파싱
            result_text = response.text
            data = json.loads(result_text)
            
            # 필수 필드 검증
            required = ['title_ko', 'summary', 'category', 'sentiment']
            if not all(k in data for k in required):
                logger.warning("⚠️ 필수 필드 누락, 재시도...")
                raise ValueError("Missing fields in JSON")
            
            # 성공! 429 카운터 리셋
            reset_429_counter()
            return data

        except exceptions.ResourceExhausted:
            # 429 Quota Exceeded (할당량 초과)
            retry_count += 1
            consecutive = increment_429_counter()  # 전역 카운터 증가
            
            if retry_count >= 2:
                # 2회 이상 429 에러 → 폴백 사용
                logger.warning(f"⚠️ 할당량 초과(429) 반복. 폴백 번역으로 전환... (전역 카운터: {consecutive})")
                use_fallback = True
                break
            else:
                wait_time = 15 + random.uniform(0, 5)  # 대기 시간 단축
                logger.warning(f"⚠️ 할당량 초과(429). {int(wait_time)}초 대기 후 재시도...")
                time.sleep(wait_time)
            
        except exceptions.ServiceUnavailable:
            # 503 Server Error
            time.sleep(5)
            retry_count += 1
            
        except Exception as e:
            logger.error(f"⚠️ 분석 중 오류 발생: {e}")
            retry_count += 1
            time.sleep(2)
    
    # 폴백 번역 시도
    if use_fallback or retry_count >= max_retries:
        logger.info("🔄 무료 번역 폴백 사용 중...")
        fallback_result = fallback_translate(title)
        if fallback_result:
            return fallback_result
            
    logger.error("❌ 최대 재시도 횟수 초과 및 폴백 실패")
    return None


def calculate_quality_score(result: Dict) -> int:
    """AI 응답 품질 점수 계산"""
    score = 0
    
    # 1. 제목 번역 품질 (30점)
    if result.get('title_ko') and len(result['title_ko']) > 5:
        score += 30
    
    # 2. 요약 품질 (40점)
    summary = result.get('summary', '')
    if summary:
        bullet_count = summary.count('-')
        if bullet_count >= 3:
            score += 40
        elif bullet_count >= 1:
            score += 20
    
    # 3. 카테고리/감정 (30점)
    if result.get('category'): score += 15
    if result.get('sentiment'): score += 15
    
    return min(score, 100)


def extract_content_from_description(description: str, max_length: int = 1000) -> str:
    """HTML 태그 제거 및 텍스트 추출"""
    if not description:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(description, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text[:max_length]
    except:
        return description[:max_length]

# ==============================================
# 메인 실행 로직
# ==============================================

def run_analyzer(batch_size: int = 10):
    logger.info("=" * 60)
    logger.info("🤖 AI 분석기 시작 (v3.0)")
    logger.info(f"   모델: {config.GEMINI_MODEL}")
    logger.info("=" * 60)
    
    # 1. 분석 대상 가져오기
    articles = db.get_unprocessed_articles(limit=batch_size)
    
    if not articles:
        logger.info("✅ 모든 기사가 분석되었습니다.")
        return
    
    logger.info(f"🔍 분석 대상: {len(articles)}개")
    
    success_count = 0
    fail_count = 0
    
    for idx, article in enumerate(articles, 1):
        logger.info(f"\n[{idx}/{len(articles)}] {article['title'][:60]}...")
        
        # 본문 구성
        content = extract_content_from_description(article.get('description', ''))
        if not content:
            content = article['title'] # 본문 없으면 제목으로 대체
            
        # AI 분석 호출
        result = analyze_article(article['title'], content, article.get('link', ''))
        
        if result:
            # 품질 점수 및 저장
            result['quality_score'] = calculate_quality_score(result)
            if db.update_article_analysis(article['id'], result):
                logger.info(f"   ✅ 분석 성공 (점수: {result['quality_score']})")
                logger.info(f"      제목: {result['title_ko']}")
                success_count += 1
            else:
                logger.error("   ❌ DB 저장 실패")
                fail_count += 1
        else:
            logger.warning("   ⚠️ 분석 실패 (API 오류 등)")
            fail_count += 1
            
        # API 쿨타임 (속도 조절)
        # [수정됨] 20초 대기로 변경 (안전성 최우선)
        logger.info("   ☕ 20초 휴식... (API 과부하 방지)")
        time.sleep(20)

    logger.info("\n" + "=" * 60)
    logger.info(f"📊 최종 결과: 성공 {success_count} / 실패 {fail_count}")