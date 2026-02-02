"""
Streamlit 대시보드 (v3.4) - 품질 모니터링 추가
Well-Dying Archive 관리 및 모니터링
"""
import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timezone, timedelta
import config
import database as db

# =============================================================================
# 페이지 설정 & CSS
# =============================================================================
st.set_page_config(
    page_title="Global Well-Dying Archive",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 다크 네이비 테마
st.markdown("""
<style>
    .main { background-color: #1e2936; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 95%; } /* 화면 넓게 사용 */
    
    h1 { color: #e8edf2; font-weight: 600; font-size: 2.2rem !important; margin-bottom: 0.5rem; }
    h2, h3, h4 { color: #d4dce5; font-weight: 500; }
    p, label, .stMarkdown { color: #a8b4c0; }
    
    /* 메트릭 스타일 */
    [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 600; color: #e8edf2; }
    [data-testid="stMetricLabel"] { color: #7a8a99; font-size: 0.75rem; text-transform: uppercase; }
    
    /* 사이드바 */
    [data-testid="stSidebar"] { background-color: #16202c; border-right: 1px solid #2a3847; }
    
    /* 테이블 스타일 */
    .stDataFrame { background-color: #16202c; border: 1px solid #2a3847; border-radius: 8px; }
    
    hr { margin: 2rem 0; border: none; height: 1px; background-color: #2a3847; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 유틸리티 함수
# =============================================================================
def get_flag_emoji(country):
    """국가명을 국기 이모지로 변환"""
    if not country or country == 'Unknown': return "🌍"
    country = str(country).upper().strip()
    mapping = {
        'KOREA': '🇰🇷', 'KR': '🇰🇷', 'SOUTH KOREA': '🇰🇷',
        'USA': '🇺🇸', 'US': '🇺🇸', 'UNITED STATES': '🇺🇸',
        'UK': '🇬🇧', 'UNITED KINGDOM': '🇬🇧', 'GB': '🇬🇧',
        'GLOBAL': '🌍', 'WORLD': '🌍', 'INTERNATIONAL': '🌍',
        'JAPAN': '🇯🇵', 'JP': '🇯🇵', 'CANADA': '🇨🇦', 'CA': '🇨🇦',
        'AUSTRALIA': '🇦🇺', 'AU': '🇦🇺', 'FRANCE': '🇫🇷', 'FR': '🇫🇷',
        'GERMANY': '🇩🇪', 'DE': '🇩🇪', 'NETHERLANDS': '🇳🇱', 'NL': '🇳🇱',
        'SWITZERLAND': '🇨🇭', 'CH': '🇨🇭', 'SPAIN': '🇪🇸', 'ES': '🇪🇸',
        'ITALY': '🇮🇹', 'IT': '🇮🇹',
    }
    return mapping.get(country, '🌍')

def trigger_github_action(workflow_id: str = "morning_briefing.yml"):
    """GitHub Actions 워크플로우 트리거"""
    token = os.getenv("GITHUB_PAT")
    owner = os.getenv("GITHUB_OWNER", "ggidoong1-dot")
    repo = os.getenv("GITHUB_REPO", "econews")
    
    if not token: return False, "❌ GITHUB_PAT 환경변수가 설정되지 않았습니다."
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {token}"}
    data = {"ref": "main"}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return (True, "🚀 워크플로우 시작됨!") if response.status_code == 204 else (False, f"❌ 실패 ({response.status_code})")
    except Exception as e:
        return False, f"❌ 에러: {str(e)}"

def run_morning_briefing_local():
    """로컬에서 모닝 브리핑 실행 (Streamlit Cloud용)"""
    try:
        from morning_briefing import generate_morning_briefing
        briefing = generate_morning_briefing()
        return True, briefing
    except Exception as e:
        return False, f"❌ 에러: {str(e)}"

# =============================================================================
# 데이터 로딩 함수
# =============================================================================
@st.cache_data(ttl=300)
def load_news_data(days=7):
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = db.supabase.table("news").select("*").gte("created_at", cutoff).order("created_at", desc=True).limit(1000).execute()
        if not response.data: return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        df['created_at'] = pd.to_datetime(df['created_at'], format='mixed')
        
        # 데이터 전처리
        df['title_ko'] = df['title_ko'].fillna(df['title'])
        df['country'] = df['country'].fillna('Global')
        df['source'] = df['source'].fillna('Unknown')
        df['quality_score'] = df['quality_score'].fillna(0)
        df['flag'] = df['country'].apply(get_flag_emoji)
        
        # [핵심] 요약 데이터 통합 (summary_ai 우선)
        if 'summary_ai' not in df.columns: df['summary_ai'] = None
        if 'summary' not in df.columns: df['summary'] = None
        
        # 요약이 없으면 '대기 중' 표시
        df['final_summary'] = df['summary_ai'].fillna(df['summary']).fillna('⏳ 분석 대기 중...')
        
        return df
    except Exception as e:
        st.error(f"❌ 데이터 로딩 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_reports():
    try:
        response = db.supabase.table("daily_reports").select("*").order("report_date", desc=True).limit(30).execute()
        return response.data if response.data else []
    except: return []

# =============================================================================
# 메인 레이아웃
# =============================================================================
st.title("💰 오늘을 위한 경제픽")
st.caption("AI-Powered News Monitoring & Intelligence System (v3.3)")
st.markdown("---")

tab_feed, tab_ai, tab_reports, tab_quality, tab_admin = st.tabs(["📋 News Feed", "🤖 AI Insights", "📊 Daily Reports", "📈 Quality Monitor", "⚙️ Management"])
df = pd.DataFrame()

# =============================================================================
# TAB 1: News Feed (표 형식 전용)
# =============================================================================
with tab_feed:
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        st.markdown("")
        search_query = st.text_input("Search", placeholder="Search...", label_visibility="collapsed")
        date_range = st.selectbox("Date Range", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])
        days_map = {"Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90, "All Time": 365}
        
        df = load_news_data(days=days_map[date_range])
        
        if not df.empty:
            countries = ['All'] + sorted(df['country'].unique().tolist())
            selected_country = st.selectbox("Country", countries)
            sources = ['All'] + sorted(df['source'].unique().tolist())
            selected_source = st.selectbox("Source", sources)
            process_filter = st.selectbox("Status", ["All", "Analyzed", "Not Analyzed"])

    if df.empty:
        st.info("📭 선택한 기간에 데이터가 없습니다.")
    else:
        # 상단 통계
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📰 전체 기사", f"{len(df):,}건")
        c2.metric("🤖 분석 완료", f"{df['is_processed'].sum():,}건")
        avg_qual = df[df['quality_score'] > 0]['quality_score'].mean()
        c3.metric("⭐ 평균 품질", f"{avg_qual:.0f}점" if not pd.isna(avg_qual) else "N/A")
        
        # [오류 수정된 부분]
        c4.metric("📡 출처 수", f"{df['source'].nunique()}개")
        
        st.markdown("---")
        
        # 필터링
        filtered_df = df.copy()
        if search_query:
            mask = (filtered_df['title'].str.contains(search_query, case=False, na=False) |
                    filtered_df['title_ko'].str.contains(search_query, case=False, na=False))
            filtered_df = filtered_df[mask]
        if selected_country != 'All': filtered_df = filtered_df[filtered_df['country'] == selected_country]
        if selected_source != 'All': filtered_df = filtered_df[filtered_df['source'] == selected_source]
        if process_filter == "Analyzed": filtered_df = filtered_df[filtered_df['is_processed'] == True]
        elif process_filter == "Not Analyzed": filtered_df = filtered_df[filtered_df['is_processed'] == False]
        
        st.caption(f"총 {len(filtered_df)}개의 기사를 표시합니다.")

        if filtered_df.empty:
            st.info("조건에 맞는 기사가 없습니다.")
        else:
            # =========================================================
            # [최종] 엑셀 스타일 표 (Table View)
            # =========================================================
            # 표시할 컬럼 정리
            display_df = filtered_df[[
                'created_at', 'flag', 'title_ko', 'final_summary', 
                'source', 'sentiment', 'quality_score', 'link'
            ]].copy()
            
            # 한글 컬럼명 매핑
            display_df.columns = ['날짜', '국가', '제목 (한국어)', 'AI 3줄 요약', '출처', '감정', '품질', '링크']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=800, # 표 높이 넉넉하게
                column_config={
                    "날짜": st.column_config.DatetimeColumn(
                        "작성일", 
                        format="MM-DD HH:mm", 
                        width="small"
                    ),
                    "국가": st.column_config.TextColumn("국가", width="small"),
                    "제목 (한국어)": st.column_config.TextColumn(
                        "기사 제목", 
                        width="medium",
                        help="원문 제목은 마우스를 올리면 보입니다."
                    ),
                    # [핵심] 요약 컬럼을 넓게 설정
                    "AI 3줄 요약": st.column_config.TextColumn(
                        "AI 요약 내용", 
                        width="large", # 가장 넓게 배정
                        help="💡 마우스를 올리거나 더블 클릭하면 전체 요약을 볼 수 있습니다."
                    ),
                    "출처": st.column_config.TextColumn("출처", width="small"),
                    "감정": st.column_config.TextColumn("감정", width="small"),
                    "품질": st.column_config.ProgressColumn(
                        "품질", 
                        format="%d", 
                        min_value=0, 
                        max_value=100,
                        width="small"
                    ),
                    "링크": st.column_config.LinkColumn(
                        "원문", 
                        display_text="🔗 이동", 
                        width="small"
                    )
                }
            )

# =============================================================================
# TAB 2~4 (기능 유지)
# =============================================================================
with tab_ai:
    st.markdown("### 🧠 AI Analysis Dashboard")
    if df.empty: st.info("📭 No data.")
    else:
        ai_df = df[df['is_processed'] == True]
        if ai_df.empty: st.info("🤖 No analyzed data.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Analyzed", len(ai_df))
            c2.metric("Positive", len(ai_df[ai_df['sentiment']=='Positive']))
            c3.metric("Negative", len(ai_df[ai_df['sentiment']=='Negative']))
            c4.metric("Neutral", len(ai_df[ai_df['sentiment']=='Neutral']))
            st.dataframe(ai_df[['title_ko', 'category', 'sentiment', 'quality_score']], use_container_width=True)

with tab_reports:
    st.markdown("### 📊 Daily Briefing Archive")
    reports = load_reports()
    if not reports: st.info("📭 No reports.")
    else:
        for r in reports:
            with st.expander(f"📢 {r.get('report_date')}"):
                st.markdown(r['content'])

# =============================================================================
# TAB 4: Quality Monitor (신규)
# =============================================================================
with tab_quality:
    st.markdown("### 📈 수집 품질 모니터링")
    st.caption("뉴스 수집 및 분석 시스템의 건강 상태를 모니터링합니다.")
    
    # 품질 메트릭 로드
    try:
        metrics = db.get_collection_quality_metrics(days=1)
        
        # 주요 지표
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "📥 24시간 수집량", 
            f"{metrics.get('total_collected', 0):,}건",
            help="최근 24시간 동안 수집된 총 기사 수"
        )
        col2.metric(
            "✅ 분석 완료", 
            f"{metrics.get('total_processed', 0):,}건",
            delta=f"{metrics.get('success_rate', 0):.1f}%"
        )
        col3.metric(
            "⭐ 고품질 기사", 
            f"{metrics.get('high_quality_count', 0):,}건",
            delta=f"{metrics.get('quality_rate', 0):.1f}%"
        )
        
        # 시스템 상태
        source_health = metrics.get('source_health', {})
        healthy_count = sum(1 for s in source_health.values() if s.get('status') == 'healthy')
        total_sources = len(source_health)
        system_status = "🟢 정상" if healthy_count >= total_sources * 0.7 else "🟡 주의" if healthy_count >= total_sources * 0.3 else "🔴 경고"
        col4.metric("🔧 시스템 상태", system_status)
        
        st.markdown("---")
        
        # 소스별 상태
        st.markdown("#### 📡 뉴스 소스 상태")
        if source_health:
            source_data = []
            for source, info in source_health.items():
                status = info.get('status', 'unknown')
                status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}.get(status, "⚪")
                source_data.append({
                    "소스": source,
                    "상태": f"{status_emoji} {status.upper()}",
                    "수집량": info.get('count', 0)
                })
            
            source_df = pd.DataFrame(source_data)
            st.dataframe(source_df, use_container_width=True, hide_index=True)
        else:
            st.info("소스 상태 정보가 없습니다.")
        
        # 마지막 업데이트 시간
        st.caption(f"🕒 마지막 업데이트: {metrics.get('timestamp', 'N/A')}")
        
    except Exception as e:
        st.error(f"품질 메트릭 로드 실패: {e}")
        st.info("💡 database.py의 get_collection_quality_metrics() 함수가 필요합니다.")

with tab_admin:
    st.markdown("### ⚙️ System Management")
    
    # 모닝 브리핑 섹션
    st.markdown("#### 📊 모닝 브리핑")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌅 모닝 브리핑 실행 (로컬)", type="primary", use_container_width=True):
            with st.spinner("브리핑 생성 중... (약 30초 소요)"):
                success, result = run_morning_briefing_local()
                if success:
                    st.success("✅ 브리핑 생성 완료!")
                    st.text_area("브리핑 내용", result, height=400)
                else:
                    st.error(result)
    
    with col2:
        if st.button("☁️ GitHub Actions 트리거", use_container_width=True):
            s, m = trigger_github_action("morning_briefing.yml")
            if s: st.success(m)
            else: st.error(m)
    
    st.markdown("---")
    
    # 뉴스 수집 섹션
    with st.expander("📡 뉴스 수집 (Collector)"):
        if st.button("⚡ Run Collector", type="secondary"):
            from collector import run_collector
            with st.spinner("수집 중..."):
                try:
                    result = run_collector()
                    st.success(f"✅ 수집 완료: {result.get('inserted', 0)}개 저장")
                except Exception as e:
                    st.error(f"❌ 수집 실패: {e}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Keywords")
        st.dataframe(pd.DataFrame(db.get_keywords(), columns=["Keyword"]), use_container_width=True)
    with c2:
        st.markdown("#### Ban Words")
        st.dataframe(pd.DataFrame(db.get_ban_words(), columns=["Ban Word"]), use_container_width=True)