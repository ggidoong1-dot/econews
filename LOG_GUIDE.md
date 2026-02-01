# 📋 로그 시스템 가이드

## 개요
이 프로젝트는 **파일 기반 로깅**을 사용하여 모든 작업을 추적합니다.  
데이터 저장 중 오류가 발생하면 상세 정보가 자동으로 기록됩니다.

---

## 📂 로그 파일 위치

```
/workspaces/global-well-dying-archive/logs/
├── __main__.log              # main.py 실행 로그
├── database.log              # 데이터베이스 작업 로그
├── collector.log             # 뉴스 수집 로그
├── analyzer.log              # AI 분석 로그
├── reporter.log              # 리포트 생성 로그
└── app.log                   # Streamlit 앱 로그
```

---

## 🔍 로그 확인 방법

### 1. 최신 데이터 저장 오류 확인
```bash
# database.log에서 에러 부분만 보기
tail -100 logs/database.log | grep -i "error\|실패\|❌"

# 또는 전체 보기
tail -50 logs/database.log
```

### 2. 특정 시간대 오류 찾기
```bash
# 예: 오늘 오류 찾기
grep "2026-02" logs/database.log | grep -i "error\|실패"
```

### 3. 저장 실패한 기사 상세 정보
```bash
# 기사별 저장 실패 정보 조회
grep "기사 저장 실패" logs/database.log
```

예시 출력:
```
2026-02-01 15:45:30,123 - database - ERROR - [1/5] 기사 저장 실패 - 출처: Google News, 제목: Euthanasia Law Changes..., 링크: https://..., 에러: Unique violation
```

---

## 📊 로그 수준 설정

### 기본값: INFO (일반 정보 + 에러)
```bash
python main.py  # LOG_LEVEL=INFO (기본값)
```

### DEBUG 모드 (더 자세한 정보)
```bash
LOG_LEVEL=DEBUG python main.py
```

### ERROR 모드 (에러만)
```bash
LOG_LEVEL=ERROR python main.py
```

---

## 🚨 주요 에러 메시지 설명

| 에러 | 의미 | 해결 방법 |
|------|------|----------|
| **Unique violation** | 중복된 데이터 | 중복 체크 로직 확인 |
| **NOT NULL constraint** | 필수 필드 누락 | 기사 데이터 검증 강화 필요 |
| **Foreign key violation** | 참조 데이터 없음 | 관련 테이블 확인 |
| **Connection timeout** | DB 연결 실패 | Supabase 상태 확인 |
| **Invalid JSON** | 데이터 형식 오류 | 기사 필드 형식 확인 |

---

## 💡 로그 분석 팁

### 1. 배치 저장 vs 개별 저장 추적
```bash
# 배치 저장 시도
grep "배치 저장" logs/database.log

# 개별 저장으로 전환됨
grep "개별 저장 모드" logs/database.log
```

### 2. 청크별 진행률 모니터링
```bash
# 예: [1/10], [2/10], ... 형태로 진행 상황 확인
grep "\[.*/.*/\]" logs/database.log | tail -20
```

### 3. 중복 데이터 통계
```bash
# 중복 기사 개수 확인
grep "✅.*중복" logs/database.log | awk -F',' '{print $3}' | awk '{sum+=$2} END {print "총 중복:", sum}'
```

### 4. ID 갭 확인 (유실된 기사)
```bash
# 저장 실패 패턴 조사
grep "기사 저장 실패" logs/database.log | wc -l  # 실패 개수
```

---

## 🔄 로그 로테이션 (선택사항)

로그 파일이 너무 커지면:

```bash
# 방법 1: 오래된 로그 삭제
find logs/ -name "*.log" -mtime +30 -delete  # 30일 이상 된 로그

# 방법 2: 로그 압축
gzip logs/database.log
tar czf logs/database.log.tar.gz logs/*.log
```

---

## 📝 실시간 로그 모니터링

```bash
# database.log 실시간 확인 (터미널에서 계속 보기)
tail -f logs/database.log

# 에러만 실시간 확인
tail -f logs/database.log | grep -i "error\|실패"

# 특정 출처의 에러만 확인
tail -f logs/database.log | grep "Naver\|Google"
```

---

## 🎯 문제 해결 워크플로우

1. **문제 발생 → 로그 확인**
   ```bash
   tail -50 logs/database.log | grep -i error
   ```

2. **에러 타입 파악**
   - 데이터 검증 오류?
   - 데이터베이스 연결 문제?
   - 개별 기사 저장 실패?

3. **상세 정보 수집**
   ```bash
   grep "2026-02-01" logs/database.log | grep "기사 저장 실패"
   ```

4. **원인 분석 및 수정**
   - 수집 로직 수정
   - 데이터 검증 강화
   - DB 설정 확인

---

## 📞 도움말

로그에서 다음 정보를 찾을 수 있습니다:

✅ **저장 성공**
- 저장된 기사 개수
- 중복 개수
- 처리 시간

❌ **저장 실패**
- 실패한 기사의 출처
- 실패한 기사의 제목
- 실패한 기사의 링크
- 정확한 에러 메시지
- 스택 트레이스

---

마지막 업데이트: 2026-02-01
