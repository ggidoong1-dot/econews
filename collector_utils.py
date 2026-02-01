import hashlib
from datetime import datetime, timezone
from dateutil import parser
from typing import List, Dict, Optional
import config

logger = config.setup_logger(__name__)


def generate_content_hash(link: str) -> str:
    """링크 기반 컨텐츠 해시 생성"""
    return hashlib.md5(link.encode('utf-8')).hexdigest()


def clean_date(date_str: Optional[str]) -> str:
    """날짜 문자열을 ISO 형식으로 정규화"""
    try:
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        
        dt = parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception as e:
        logger.debug(f"날짜 파싱 실패: {date_str}, 에러: {e}")
        return datetime.now(timezone.utc).isoformat()


def is_valid_article(article: Dict, ban_words: List[str]) -> bool:
    """
    기사의 유효성을 검사합니다.
    """
    title = article.get('title', '').lower()
    
    # 필수 필드 확인
    if not article.get('link') or not article.get('title'):
        logger.debug("필수 필드 누락")
        return False
    
    # 금지어 체크
    for ban_word in ban_words:
        if ban_word.lower() in title:
            logger.debug(f"금지어 발견: {ban_word}")
            return False
    
    return True
