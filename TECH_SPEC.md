# TECH_SPEC

## 개요
이 문서는 `global-well-dying-archive` 프로젝트의 아키텍처와 기술 사양을 상세히 정리합니다. 다음 세션에서 이 파일만 읽어도 바로 작업을 이어갈 수 있도록 클래스/함수 인터페이스, 설정값, DB 계약, 로깅 규칙, 확장 포인트, 테스트 전략 등을 포함합니다.

---

## 목표
- 코드베이스의 모듈화와 가독성 향상
- 기술 부채 감소(중복 제거, SRP 적용)
- 확장성 있는 수집기(소스 추가 용이)
- CI/CD 친화적 구조 및 문서화

---

## 전체 아키텍처
- `collector.py`: 애플리케이션 진입점. 수집 파이프라인의 오케스트레이션 담당.
- `collector_utils.py`: 공통 유틸리티 함수(날짜 정규화, 해시, 유효성 검사 등).
- `collectors/` 패키지: 소스별 수집기 모듈 분리
  - `collectors/rss.py`: RSS 기반 수집 함수들(`fetch_google_news`, `fetch_reddit_rss`, `fetch_direct_rss` 등)
  - `collectors/scraper.py`: HTML 스크래핑 기반 수집기(`fetch_naver_news` 등)
- `config.py`: 환경설정과 상수(타임아웃, 키워드 리스트, 활성화된 소스 등).
- `database.py` (`db`): 영속성 레이어. 아래 계약(API)을 따릅니다.
- `log_analyzer.py` / `reporter.py`: 로그 분석 및 리포팅 도구

---

## 모듈별 책임(CSRP)
- Single Responsibility 원칙을 따릅니다: 각 수집 함수는 하나의 데이터 소스만 처리하고, 데이터 정제/검증/저장은 `collector.py`에서 담당합니다.
- 공통 로직(날짜 파싱, 해시 생성, 기사 유효성)은 `collector_utils.py`에 둡니다.

---

## 함수/인터페이스 계약
### Database (필수 함수)
`database.py`는 다음 함수를 구현해야 합니다:
- `get_recent_links(days: int) -> set` : 최근 N일간 수집된 링크의 집합을 반환합니다.
- `get_ban_words() -> List[str]` : 금지어 리스트 반환.
- `save_news_batch(articles: List[Dict]) -> int` : 배치 저장 후 저장된 레코드 수 반환.
- `update_last_run() -> None` : 마지막 실행 시각 업데이트.

계약을 지키면 `collector.py`는 DB 내부 구현을 몰라도 작동합니다.

### Collector 진입 파이프라인
- `run_collector()` 호출 시:
  1. DB에서 기존 링크/금지어 불러옴
  2. 활성화된 소스에서 기사 수집
  3. 중복/유효성 필터링(유틸 사용)
  4. `save_news_batch` 호출해서 DB 저장
  5. 통계 출력을 로깅하고 `update_last_run` 호출

---

## 설정값 (`config.py`) (필수 항목)
- `API_TIMEOUT` : 외부 요청 타임아웃
- `KEYWORDS_EN`, `KEYWORDS_KO` : 검색 키워드 리스트
- `COLLECTOR_LOOKBACK_DAYS` : 중복 체크용 기간
- `NEWS_SOURCES` : dict(예: {"google": {"enabled": True}, ...})
- `REDDIT_SOURCES`, `DIRECT_RSS_SOURCES`
- 로깅 설정 함수 `setup_logger(name)` 필요

---

## 로깅/에러 처리
- 모듈마다 `logger = config.setup_logger(__name__)` 사용
- WARN/ERROR 발생 시 사용자 친화적 메시지 + 디버그정보(logs/ 또는 임시 파일) 저장
- 외부 네트워크 호출은 예외를 포착해 개별 키워드/소스 실패로 전체 파이프라인이 중단되지 않게 함

---

## 테스트 전략
- 단위 테스트:
  - `collector_utils.clean_date`, `is_valid_article`, `generate_content_hash`에 대한 테스트
  - `collectors/rss.py`와 `collectors/scraper.py`의 주요 로직은 네트워크 호출을 모킹하여 테스트
- 통합 테스트:
  - DB 스텁(메모리 기반)을 사용해 `run_collector()` 전체 플로우 검증

---

## 확장 가이드
- 새로운 수집기 추가:
  1. `collectors/`에 모듈 생성
  2. `fetch_*` 형태의 함수로 구현
  3. `collector.py`에서 `NEWS_SOURCES` 설정에 따라 호출
- 인증이 필요한 API 추가 시, `config.py`에서 키/토큰 관리

---

## 코드 스타일 & 규칙
- 타입 힌트 사용 권장
- 함수는 50~80라인을 넘지 않도록 분해
- 중복 금지(DRY), 단일 책임(SRP), 테스트 가능한 코드
- 예외를 무시할 때는 반드시 로깅

---

## 다음 세션에서 바로 할 수 있는 작업
- DB 스텁을 만들어 `save_news_batch` 동작을 확인하는 테스트 추가
- CI 파이프라인에 `pytest` 실행 추가
- 추가 수집기(Bing, NewsAPI) 모듈 템플릿 생성

---

이 문서는 작업을 이어갈 때 필요한 모든 컨텍스트(설계, 계약, 변수)를 포함합니다. 추가로 상세한 변경이 필요하면 이 파일을 업데이트하세요.
