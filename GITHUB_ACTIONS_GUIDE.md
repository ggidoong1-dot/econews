# 🔄 GitHub Actions 설정 가이드

## 📋 개요

GitHub Actions를 사용하면 서버 없이 자동으로 뉴스를 수집할 수 있습니다.

- **무료**: Public 저장소는 무제한, Private는 월 2,000분
- **자동 실행**: 6시간마다 자동 실행
- **수동 실행**: 필요 시 즉시 실행 가능

## 🚀 설정 방법

### 1. 워크플로우 파일 배치

저장소에 다음 구조로 파일을 생성:

```
your-repo/
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml  # 이 파일 사용
├── config.py
├── database.py
├── collector.py
├── analyzer.py
├── reporter.py
├── main.py
├── requirements.txt
└── ...
```

### 2. GitHub Secrets 설정

GitHub 저장소 페이지에서:

1. **Settings** 탭 클릭
2. 좌측 메뉴에서 **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭
4. 아래 Secret들을 하나씩 추가:

#### 필수 Secrets (3개)

| Name | Value | 설명 |
|------|-------|------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | `eyJhbGci...` | Supabase anon key |
| `GOOGLE_API_KEY` | `AIzaSy...` | Gemini API 키 |

#### 선택 Secrets (3개)

| Name | Value | 설명 |
|------|-------|------|
| `NEWSAPI_KEY` | `1234567...` | NewsAPI 키 (선택) |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABC...` | Telegram 봇 토큰 (선택) |
| `TELEGRAM_CHAT_ID` | `123456789` | Telegram 채팅 ID (선택) |

### 3. 워크플로우 활성화

1. 저장소에 코드 푸시:
   ```bash
   git add .github/workflows/daily_pipeline.yml
   git commit -m "Add: GitHub Actions workflow"
   git push origin main
   ```

2. **Actions** 탭에서 워크플로우 확인

3. 처음 실행 (수동):
   - **Actions** 탭 클릭
   - 좌측에서 "Well-Dying Archive Pipeline" 선택
   - **Run workflow** 버튼 클릭
   - **Run workflow** 확인

## ⏰ 실행 스케줄

### 기본 스케줄 (6시간마다)

```yaml
schedule:
  - cron: '0 */6 * * *'
```

**실행 시각 (UTC)**:
- 00:00 (한국 09:00)
- 06:00 (한국 15:00)
- 12:00 (한국 21:00)
- 18:00 (한국 03:00)

### 스케줄 변경 방법

`daily_pipeline.yml` 파일 수정:

```yaml
# 예시 1: 하루 2번 (오전/오후)
schedule:
  - cron: '0 1,13 * * *'  # UTC 1시, 13시 (한국 10시, 22시)

# 예시 2: 하루 1번 (아침만)
schedule:
  - cron: '0 1 * * *'  # UTC 1시 (한국 10시)

# 예시 3: 매시간
schedule:
  - cron: '0 * * * *'
```

**Cron 문법**:
```
분 시 일 월 요일
*  *  *  *  *
│  │  │  │  │
│  │  │  │  └─ 요일 (0-6, 0=일요일)
│  │  │  └──── 월 (1-12)
│  │  └─────── 일 (1-31)
│  └────────── 시 (0-23)
└───────────── 분 (0-59)
```

## 🎯 워크플로우 단계 설명

### 1. 연결 테스트 (🔌)
- Supabase, Gemini API 연결 확인
- 실패 시 즉시 중단

### 2. 뉴스 수집 (📡)
- Google, Bing, NewsAPI, Naver, Reddit 등에서 수집
- 실패 시 워크플로우 중단

### 3. AI 분석 (🤖)
- Gemini로 기사 분석
- 실패해도 계속 진행 (다음 실행에서 재시도)

### 4. 일일 리포트 (📊)
- **조건부**: UTC 1시(한국 10시)에만 실행
- 또는 수동 실행 시 강제 생성
- Telegram으로 브리핑 전송

### 5. 통계 출력 (📈)
- 수집/분석 통계 출력
- 항상 실행

### 6. 에러 알림 (🚨)
- 워크플로우 실패 시 Telegram 알림
- Telegram 설정 시만 작동

## 🔧 고급 설정

### 수동 실행 옵션

**리포트 강제 생성**:
1. Actions 탭 → "Well-Dying Archive Pipeline" 선택
2. "Run workflow" 클릭
3. "리포트 강제 생성" 드롭다운에서 **yes** 선택
4. "Run workflow" 클릭

### 타임아웃 변경

```yaml
jobs:
  run-pipeline:
    timeout-minutes: 30  # 기본 30분 → 60분으로 변경
```

### 병렬 실행 방지

```yaml
concurrency:
  group: pipeline
  cancel-in-progress: false  # 이전 실행 완료까지 대기
```

### 특정 단계만 실행

워크플로우 파일에서 불필요한 step 주석 처리:

```yaml
# - name: 🤖 Analyze articles  # 주석 처리
#   env:
#     ...
#   run: |
#     python main.py analyze
```

## 📊 모니터링

### 실행 로그 확인

1. **Actions** 탭 클릭
2. 실행 기록에서 원하는 워크플로우 클릭
3. 각 단계 클릭하여 상세 로그 확인

### 실패 알림

Telegram 설정 시 자동으로 실패 알림 전송:
```
⚠️ GitHub Actions 워크플로우 실패

워크플로우: Well-Dying Archive Pipeline
시간: 2026-02-01 12:00:00 UTC

로그: [링크]
```

### 통계 확인

각 실행의 마지막 단계에서 통계 확인:
```
📊 시스템 통계
═══════════════════════════════════════

[최근 7일 통계]
  총 기사: 150개
  처리 완료: 120개
  미처리: 30개
  처리율: 80.0%
```

## ⚠️ 주의사항

### 1. API 레이트 리밋

**Gemini Free Tier**:
- 분당 15회
- 하루 1,500회
- → 배치 크기 20개 권장

**NewsAPI Free**:
- 하루 100회
- → 6시간마다 실행 시 충분

### 2. GitHub Actions 할당량

**Public 저장소**: 무제한
**Private 저장소**: 
- 무료: 월 2,000분
- 6시간마다 실행 시: 실행당 ~5분 → 월 600분 사용

### 3. 시간대 (Timezone)

- GitHub Actions는 **UTC 시간**만 사용
- 한국 시간(KST) = UTC + 9시간
- 예: UTC 1시 = 한국 10시

## 🐛 문제 해결

### "Secrets not found" 에러

**해결**:
1. Settings → Secrets and variables → Actions 확인
2. Secret 이름이 정확한지 확인 (대소문자 구분)
3. Secret 값에 공백이 없는지 확인

### 워크플로우가 실행되지 않음

**해결**:
1. `.github/workflows/` 경로 확인
2. YAML 문법 오류 확인 (들여쓰기 주의)
3. 저장소가 Public인지 확인 (Private는 권한 필요)

### Collector 실패

**해결**:
1. Supabase 연결 확인
2. `python test_rss.py`로 RSS 소스 확인
3. Naver 스크래핑 실패 시 `test_naver.py` 실행

### Analyzer API 에러

**해결**:
1. Gemini API 키 확인
2. 레이트 리밋 확인 (15 RPM)
3. 배치 크기 줄이기: `--batch-size 10`

## 📝 커스터마이징 예시

### 하루 1번만 실행 (한국 오전 10시)

```yaml
on:
  schedule:
    - cron: '0 1 * * *'  # UTC 1시 = 한국 10시
```

### 평일만 실행

```yaml
on:
  schedule:
    - cron: '0 1 * * 1-5'  # 월-금요일만
```

### 수집만 하고 분석/리포트 스킵

```yaml
# Analyzer, Reporter step 주석 처리
```

---

## ✅ 체크리스트

설정 완료 전 확인:

- [ ] `.github/workflows/daily_pipeline.yml` 파일 생성
- [ ] GitHub Secrets 등록 (최소 3개)
- [ ] 코드 푸시
- [ ] Actions 탭에서 수동 실행 테스트
- [ ] 첫 실행 성공 확인
- [ ] Telegram 알림 테스트 (선택)

---

**🎉 설정 완료! 이제 자동으로 뉴스가 수집됩니다.**
