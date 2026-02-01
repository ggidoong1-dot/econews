# ⚠️ 잊어버리기 쉬운 것들 체크리스트

설정 중 **반드시 확인**해야 하는 것들을 정리했습니다.

---

## 🔴 CRITICAL (이것만은 꼭!)

### 1. Streamlit Secrets 형식
```toml
# ✅ 올바른 형식
SUPABASE_URL = "https://xxxxx.supabase.co"

# ❌ 잘못된 형식
SUPABASE_URL = https://xxxxx.supabase.co  (따옴표 없음)
SUPABASE_URL="https://xxxxx.supabase.co"  (띄어쓰기 없음)
```

**중요**: 
- `키 = "값"` 형식 (띄어쓰기 포함!)
- 따옴표 필수!

### 2. GitHub Secrets vs Streamlit Secrets

| 위치 | 형식 | 용도 |
|------|------|------|
| **GitHub Secrets** | 따옴표 **없이** 값만 | GitHub Actions |
| **Streamlit Secrets** | 따옴표 **포함** `"값"` | 대시보드 |

**예시**:
```
GitHub Secret:
Name: SUPABASE_URL
Value: https://xxxxx.supabase.co  (따옴표 없음!)

Streamlit Secret:
SUPABASE_URL = "https://xxxxx.supabase.co"  (따옴표 있음!)
```

### 3. Python 버전 불일치

**반드시 확인**:
- `runtime.txt`: `python-3.11`
- Streamlit Advanced settings: **3.11** 선택

❌ 3.9, 3.10, 3.13은 안 됨!

### 4. GitHub 유저명 변경

**app.py 파일**에서 수정:
```python
# 87-90 줄 근처
owner = os.getenv("GITHUB_OWNER", "your-username")  # ← 여기 수정!
repo = os.getenv("GITHUB_REPO", "global-well-dying-archive")
```

**또는 Streamlit Secrets에**:
```toml
GITHUB_OWNER = "실제-깃허브-유저명"
GITHUB_REPO = "global-well-dying-archive"
```

---

## 🟡 IMPORTANT (자주 잊어버림)

### 5. Supabase 테이블 생성

**증상**: "relation 'news' does not exist"

**해결**:
- Supabase → SQL Editor
- README의 SQL 코드 **전체** 실행
- 6개 테이블 모두 생성되었는지 확인

### 6. .github 폴더 구조

```
.github/
└── workflows/
    └── daily_pipeline.yml  ← 정확한 위치!
```

❌ 잘못된 위치:
- `github/workflows/`
- `.github/daily_pipeline.yml`
- `workflows/daily_pipeline.yml`

### 7. requirements.txt에 beautifulsoup4

**반드시 포함**:
```txt
beautifulsoup4==4.12.3
```

Naver 스크래핑에 필수!

### 8. Git 푸시 잊지 않기

**파일 수정 후 반드시**:
```bash
git add .
git commit -m "Update files"
git push origin main
```

안 하면 GitHub/Streamlit에 반영 안 됨!

---

## 🟢 RECOMMENDED (하면 좋음)

### 9. Telegram Chat ID 확인

**흔한 실수**:
- 봇 토큰은 맞는데 Chat ID가 틀림
- 따옴표 포함해서 입력 (`"123456789"` ❌)

**확인 방법**:
```
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```
접속 후 `"id": 123456789` 찾기 (숫자만!)

### 10. NewsAPI 할당량

무료: **하루 100회**

6시간마다 실행 시:
- 하루 4회 × 각 10-15회 요청 = **40-60회**
- 충분함! ✅

### 11. Streamlit 재배포

**파일 수정 후**:
1. Git 푸시
2. Streamlit 자동 재배포 (1-2분)

**또는 수동**:
- Streamlit 앱 페이지 → 우측 상단 ⋮ → **Reboot app**

### 12. 캐시 클리어

**대시보드에서 데이터가 안 보이면**:
- 우측 상단 ⋮ → **Clear cache**
- 또는 페이지 새로고침 (F5)

---

## 📋 설정 완료 체크리스트

설정이 끝나면 아래 항목들을 확인하세요:

### GitHub
- [ ] 저장소 생성됨
- [ ] 모든 파일 푸시됨 (15개)
- [ ] `.github/workflows/daily_pipeline.yml` 위치 확인
- [ ] Secrets 6개 등록 (최소 3개)

### Supabase
- [ ] 프로젝트 생성됨
- [ ] 테이블 6개 생성됨 (news, settings, daily_reports, keywords, ban_words, monitored_sites)
- [ ] URL과 Key 복사함

### Streamlit
- [ ] 앱 배포 완료
- [ ] Secrets 올바른 형식으로 입력 (따옴표!)
- [ ] Python 3.11 선택
- [ ] 대시보드 접속 가능

### API 키
- [ ] Supabase URL & Key
- [ ] Gemini API Key
- [ ] NewsAPI Key (선택)
- [ ] Telegram Token & Chat ID (선택)

### 동작 확인
- [ ] GitHub Actions 수동 실행 성공
- [ ] Supabase에 기사 저장됨
- [ ] 대시보드에서 기사 확인됨
- [ ] 키워드 추가/삭제 작동
- [ ] Telegram 알림 수신 (설정했다면)

---

## 🚨 긴급 문제 해결

### "ModuleNotFoundError: No module named 'X'"

**원인**: requirements.txt 누락
**해결**: 
```bash
# 로컬에서 확인
pip install -r requirements.txt

# 누락된 패키지 추가
echo "패키지명==버전" >> requirements.txt
git push
```

### "Failed to load resource: net::ERR_BLOCKED_BY_CLIENT"

**원인**: 광고 차단기
**해결**: Streamlit 사이트를 허용 목록에 추가

### "This app has encountered an error"

**원인**: Secrets 형식 오류
**해결**:
1. Streamlit 앱 → Settings → Secrets
2. 형식 확인: `KEY = "value"`
3. 따옴표 확인!

### GitHub Actions가 자동 실행 안 됨

**원인**: Cron 설정 오류
**해결**:
1. `.github/workflows/daily_pipeline.yml` 확인
2. `schedule:` 아래 들여쓰기 확인
3. UTC 시간 계산 확인

---

## 💾 백업해두면 좋은 것

### 1. API 키들 (안전한 곳에)
```
Supabase URL: https://xxxxx.supabase.co
Supabase Key: eyJhbGci...
Gemini API Key: AIzaSy...
NewsAPI Key: 1234567...
Telegram Bot Token: 1234567890:ABC...
Telegram Chat ID: 123456789
```

### 2. Supabase Database Password
- 프로젝트 생성 시 입력한 비밀번호
- Direct Connection 필요 시 사용

### 3. GitHub Personal Access Token (선택)
- 대시보드에서 원격 실행용
- Settings → Developer settings → Personal access tokens

---

## 📞 도움이 필요할 때

### 1. GitHub Issues
- 프로젝트 저장소에 이슈 등록

### 2. Streamlit Community
- https://discuss.streamlit.io

### 3. Supabase Discord
- https://discord.supabase.com

---

**이 체크리스트를 프린트해두고 설정할 때마다 확인하세요!** ✅
