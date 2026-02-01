"""
데이터베이스 모듈 (Supabase)
모든 DB 작업을 중앙에서 관리합니다.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from supabase import create_client, Client
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import config

# 로거 설정
logger = config.setup_logger(__name__)

# 실패 기사 기록 파일
FAILED_ARTICLES_LOG = os.path.join(config.LOG_DIR, "failed_articles.jsonl")

# ==============================================
# Supabase 클라이언트 초기화
# ==============================================
supabase: Optional[Client] = None

try:
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        raise ValueError("Supabase 설정 누락: SUPABASE_URL 또는 SUPABASE_KEY가 없습니다.")

    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    logger.info("✅ Supabase 연결 성공")
except ValueError as e:
    logger.error(f"❌ Supabase 설정 오류: {e}")
    supabase = None
except Exception as e:
    logger.error(f"❌ Supabase 연결 실패: {e}")
    supabase = None

# ==============================================
# 유틸리티 함수
# ==============================================
def ensure_connection():
    """DB 연결 확인"""
    if not supabase:
        raise RuntimeError("Supabase 클라이언트가 초기화되지 않았습니다.")
    return supabase


def validate_article(article: Dict) -> Tuple[bool, str]:
    """
    기사 데이터 검증 및 정규화
    
    Args:
        article: 검증할 기사 데이터
        
    Returns:
        Tuple[bool, str]: (성공 여부, 에러 메시지)
    """
    # 1. 필수 필드 정의
    required_fields = ['title', 'link', 'source']
    
    # 2. 필수 필드 체크
    missing = [f for f in required_fields if f not in article or not article[f]]
    if missing:
        return False, f"필수 필드 누락: {', '.join(missing)}"
        
    # 3. 날짜 필드 호환성 및 정규화 (핵심 수정 사항)
    # Streamlit 등에서 에러가 나지 않도록 저장 전에 ISO 포맷으로 통일합니다.
    try:
        if 'pub_date' in article and 'published_at' not in article:
            article['published_at'] = article.pop('pub_date')
            
        if 'published_at' in article:
            date_val = article['published_at']
            # 문자열이면 파싱 후 다시 포맷팅
            if isinstance(date_val, str):
                dt = date_parser.parse(date_val)
            elif isinstance(date_val, datetime):
                dt = date_val
            else:
                dt = datetime.now(timezone.utc)
            
            # 타임존이 없으면 UTC로 간주
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # 표준 ISO 8601 문자열로 변환하여 저장
            article['published_at'] = dt.isoformat()
        else:
            # 날짜가 없으면 현재 시간
            article['published_at'] = datetime.now(timezone.utc).isoformat()
            
    except Exception as e:
        # 날짜 파싱 실패 시 현재 시간으로 대체 (데이터 유실 방지)
        logger.warning(f"날짜 형식 변환 실패 ({article.get('published_at')}): {e}, 현재 시간으로 대체")
        article['published_at'] = datetime.now(timezone.utc).isoformat()
        
    return True, "Valid"


def log_failed_article(article: Dict, error_reason: str, error_type: str = "SAVE_FAILED"):
    """
    실패한 기사를 상세 정보와 함께 기록
    """
    try:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        
        failed_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "error_reason": error_reason,
            "article": {
                "source": article.get('source', 'N/A'),
                "title": article.get('title', 'N/A'),
                "link": article.get('link', 'N/A'),
                "published_at": article.get('published_at', 'N/A')
            }
        }
        
        with open(FAILED_ARTICLES_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(failed_record, ensure_ascii=False) + '\n')
            
    except Exception as e:
        logger.warning(f"실패 기사 기록 실패: {e}")


# ==============================================
# 조회 함수들 (Getters)
# ==============================================

def get_keywords() -> List[str]:
    """DB에서 활성화된 키워드 목록을 가져옵니다."""
    try:
        db = ensure_connection()
        response = db.table("keywords").select("word").eq("enabled", True).execute()
        keywords = [item['word'] for item in response.data]
        return keywords
    except RuntimeError:
        logger.warning("DB 미연결 - config의 기본 키워드 사용")
        return config.KEYWORDS_EN + config.KEYWORDS_KO
    except Exception as e:
        logger.error(f"❌ 키워드 로딩 실패: {e}")
        return config.KEYWORDS_EN + config.KEYWORDS_KO


def get_countries() -> List[Dict]:
    """DB에서 활성화된 국가 정보를 가져옵니다."""
    try:
        db = ensure_connection()
        response = db.table("countries").select("*").eq("enabled", True).execute()
        return response.data
    except RuntimeError:
        logger.warning("DB 미연결 - 기본 국가 리스트 사용")
        return [{"code": "Global", "name": "Global", "enabled": True}]
    except Exception as e:
        logger.error(f"❌ 국가 정보 로딩 실패: {e}")
        return []


def get_ban_words() -> List[str]:
    """DB에서 활성화된 금지어 목록을 가져옵니다."""
    try:
        db = ensure_connection()
        response = db.table("ban_words").select("word").eq("enabled", True).execute()
        ban_words = [item['word'] for item in response.data]
        return ban_words
    except Exception as e:
        logger.error(f"❌ 금지어 로딩 실패: {e}")
        return []


def get_monitored_sites() -> List[Dict]:
    """활성화된 커스텀 RSS 사이트 목록을 가져옵니다."""
    try:
        db = ensure_connection()
        response = db.table("monitored_sites").select("*").eq("enabled", True).execute()
        return response.data
    except Exception as e:
        logger.error(f"❌ RSS 사이트 로딩 실패: {e}")
        return []


def get_recent_links(days: int = 2) -> Set[str]:
    """중복 방지용: 최근 N일 간의 기사 링크만 가져옵니다."""
    try:
        db = ensure_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        response = db.table("news")\
            .select("link")\
            .gte("created_at", cutoff)\
            .execute()
            
        links = {item['link'] for item in response.data}
        return links
        
    except Exception as e:
        logger.error(f"❌ 최근 링크 로딩 실패: {e}")
        return set()


def get_unprocessed_articles(limit: int = 10, days: int = 3) -> List[Dict]:
    """AI 분석이 필요한 기사들을 가져옵니다."""
    try:
        db = ensure_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        response = db.table("news")\
            .select("*")\
            .gte("created_at", cutoff)\
            .is_("summary_ai", "null")\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"❌ 미처리 기사 조회 실패: {e}")
        return []


def get_recent_articles(hours: int = 24) -> List[Dict]:
    """리포트 생성용: 최근 N시간 내 기사를 가져옵니다."""
    try:
        db = ensure_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        response = db.table("news")\
            .select("*")\
            .gte("created_at", cutoff)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"❌ 최근 기사 조회 실패: {e}")
        return []

# ==============================================
# 설정 및 운영 로직 (Settings)
# ==============================================

def get_settings() -> Dict:
    """수집 설정 가져오기"""
    default_settings = {
        "interval_minutes": config.DEFAULT_COLLECTION_INTERVAL,
        "last_run": "2000-01-01T00:00:00+00:00"
    }
    
    try:
        db = ensure_connection()
        response = db.table("settings").select("*").limit(1).single().execute()
        return response.data
    except Exception:
        return default_settings


def update_last_run() -> bool:
    """마지막 실행 시간 업데이트"""
    try:
        db = ensure_connection()
        now = datetime.now(timezone.utc).isoformat()
        settings = get_settings()
        target_id = settings.get('id', 1)
        
        db.table("settings").update({
            "last_run": now,
            "updated_at": now
        }).eq("id", target_id).execute()
        return True
    except Exception as e:
        logger.error(f"❌ 마지막 실행 시간 업데이트 실패: {e}")
        return False


def should_run_collector() -> bool:
    """수집 주기 체크"""
    try:
        settings = get_settings()
        last_run_str = settings.get('last_run')
        
        try:
            last_run = date_parser.parse(last_run_str)
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
        except:
            last_run = datetime(2000, 1, 1, tzinfo=timezone.utc)
            
        interval_minutes = int(settings.get('interval_minutes', config.DEFAULT_COLLECTION_INTERVAL))
        elapsed_minutes = (datetime.now(timezone.utc) - last_run).total_seconds() / 60
        
        if elapsed_minutes >= interval_minutes:
            logger.info(f"✅ 수집 주기 도래 (경과: {elapsed_minutes:.1f}분)")
            return True
        else:
            logger.info(f"⏳ 수집 주기 미도래 (남은시간: {interval_minutes - elapsed_minutes:.0f}분)")
            return False
            
    except Exception:
        return True

# ==============================================
# 저장 함수 (분할 저장)
# ==============================================

def save_news_batch(news_list: List[Dict]) -> int:
    """
    뉴스 리스트를 청크 단위로 나누어 저장합니다.
    """
    if not news_list:
        return 0
    
    try:
        db = ensure_connection()
    except RuntimeError:
        return 0
    
    saved_count = 0
    duplicate_count = 0
    validation_failed_count = 0
    save_failed_count = 0
    chunk_size = config.COLLECTOR_BATCH_SIZE
    total_chunks = (len(news_list) + chunk_size - 1) // chunk_size
    
    logger.info(f"💾 총 {len(news_list)}개 기사를 {total_chunks}개 청크로 분할 저장 시작")
    
    for i in range(0, len(news_list), chunk_size):
        chunk = news_list[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        
        try:
            # 1. 데이터 검증 및 정규화
            validation_failed = []
            articles_to_check = []
            
            for idx, article in enumerate(chunk):
                is_valid, error_msg = validate_article(article)
                if not is_valid:
                    validation_failed.append((idx, article, error_msg))
                    log_failed_article(article, error_msg, "VALIDATION_FAILED")
                else:
                    articles_to_check.append(article)
            
            validation_failed_count += len(validation_failed)
            
            if not articles_to_check:
                continue
            
            # 2. 중복 확인
            chunk_links = [article['link'] for article in articles_to_check]
            try:
                existing = db.table("news").select("link").in_("link", chunk_links).execute()
                existing_links = {item['link'] for item in existing.data}
            except:
                existing_links = set()
            
            # 3. 신규 기사 필터링
            new_news = [article for article in articles_to_check if article['link'] not in existing_links]
            current_dupes = len(articles_to_check) - len(new_news)
            duplicate_count += current_dupes
            
            # 4. DB 저장
            if new_news:
                try:
                    # 필요한 컬럼만 추출
                    allowed_columns = {
                        'title', 'link', 'description', 'published_at', 'source', 'country',
                        'author', 'content_hash', 'is_processed', 'collected_at',
                        'summary_ai', 'title_ko', 'category', 'sentiment', 'quality_score'
                    }
                    cleaned_batch = []
                    for art in new_news:
                        cleaned = {k: v for k, v in art.items() if k in allowed_columns}
                        cleaned_batch.append(cleaned)

                    result = db.table("news").insert(cleaned_batch).execute()
                    saved_count += len(result.data)
                    logger.info(f"   [{chunk_num}/{total_chunks}] ✅ {len(result.data)}개 저장 완료")
                    
                except Exception as insert_error:
                    logger.warning(f"   [{chunk_num}/{total_chunks}] ⚠️ 배치 저장 실패 -> 개별 저장 시도")
                    
                    # 개별 저장 모드 (Fallback)
                    chunk_saved = 0
                    for article in new_news:
                        try:
                            cleaned = {k: v for k, v in article.items() if k in allowed_columns}
                            db.table("news").insert([cleaned]).execute()
                            chunk_saved += 1
                        except Exception as e:
                            log_failed_article(article, str(e), "INSERT_FAILED")
                    
                    saved_count += chunk_saved
                    save_failed_count += (len(new_news) - chunk_saved)
            
        except Exception as e:
            logger.error(f"   [{chunk_num}/{total_chunks}] ❌ 청크 에러: {e}")
            save_failed_count += len(chunk)
            continue
            
    return saved_count


def update_article_analysis(article_id: int, analysis_result: Dict) -> bool:
    """
    기사의 AI 분석 결과를 업데이트합니다.
    """
    try:
        db = ensure_connection()
        
        # analyzer.py는 'summary'를 주지만, DB 컬럼은 'summary_ai'일 가능성이 높음
        update_data = {
            "title_ko": analysis_result.get("title_ko"),
            "summary_ai": analysis_result.get("summary"),  # 매핑 처리
            "category": analysis_result.get("category"),
            "sentiment": analysis_result.get("sentiment"),
            "is_processed": True,
            "quality_score": analysis_result.get("quality_score", 0)
        }
        
        db.table("news").update(update_data).eq("id", article_id).execute()
        return True
        
    except Exception as e:
        logger.error(f"❌ 분석 업데이트 실패 (ID: {article_id}): {e}")
        return False


def save_daily_report(report_date: str, content: str, keywords: List[str]) -> bool:
    """일일 리포트 저장"""
    try:
        db = ensure_connection()
        db.table("daily_reports").insert({
            "report_date": report_date,
            "content": content,
            "keywords": keywords
        }).execute()
        return True
    except Exception as e:
        logger.error(f"❌ 리포트 저장 실패: {e}")
        return False

# ==============================================
# 통계 조회
# ==============================================

def get_statistics(days: int = 7) -> Dict:
    """통계 조회"""
    try:
        db = ensure_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        total = db.table("news").select("id", count="exact").gte("created_at", cutoff).execute()
        processed = db.table("news").select("id", count="exact")\
            .gte("created_at", cutoff).eq("is_processed", True).execute()
        
        # 소스별 통계는 데이터가 많으면 느릴 수 있으므로 예외처리
        try:
            sources_resp = db.table("news").select("source")\
                .gte("created_at", cutoff).execute()
            # Python 측에서 카운팅 (Supabase GroupBy가 복잡하므로)
            source_counts = defaultdict(int)
            for item in sources_resp.data:
                source_counts[item.get('source', 'Unknown')] += 1
            sources_data = [{"source": k, "count": v} for k, v in source_counts.items()]
        except:
            sources_data = []
        
        return {
            "total_articles": total.count,
            "processed_articles": processed.count,
            "unprocessed_articles": total.count - processed.count,
            "processing_rate": round((processed.count / total.count * 100) if total.count > 0 else 0, 1),
            "sources": sources_data
        }
    except Exception as e:
        logger.error(f"통계 에러: {e}")
        return {"total_articles": 0, "processed_articles": 0, "processing_rate": 0, "sources": []}

if __name__ == "__main__":
    # 간단 테스트
    if ensure_connection():
        print("✅ DB 연결 정상")
        print(f"   키워드: {len(get_keywords())}개")
        print(f"   국가: {len(get_countries())}개")