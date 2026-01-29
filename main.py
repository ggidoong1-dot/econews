import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from scraper import run_global_batch, supabase, add_keyword, delete_keyword, get_all_keywords
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="Global Economic Intelligence Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 커스텀 CSS (고대비 전문 디자인)
# ==========================================
st.markdown("""
<style>
    /* 메인 배경 - 어두운 배경으로 대비 강화 */
    .main {
        background: #0a0e27;
        color: #e0e7ff;
    }
    
    /* 모든 텍스트 기본 색상 */
    .stMarkdown, .stText, p, span, div {
        color: #e0e7ff !important;
    }
    
    /* 헤더 스타일 */
    .header-container {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #06b6d4 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
        text-align: center;
        letter-spacing: -1px;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #dbeafe !important;
        text-align: center;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* 메트릭 카드 - 밝은 텍스트 */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1.8rem;
        border-radius: 12px;
        border-left: 5px solid #60a5fa;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        margin-bottom: 1rem;
        border: 1px solid rgba(96, 165, 250, 0.2);
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        color: #60a5fa !important;
        margin: 0;
        text-shadow: 0 0 20px rgba(96, 165, 250, 0.5);
    }
    
    .metric-label {
        font-size: 0.95rem;
        color: #cbd5e1 !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 0.8rem;
        font-weight: 600;
    }
    
    /* 섹션 타이틀 */
    h1, h2, h3, h4 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
    }
    
    /* 상태 배지 */
    .status-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
    }
    
    .status-active {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
    }
    
    .status-inactive {
        background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        color: white !important;
    }
    
    /* 데이터 테이블 */
    .dataframe {
        font-size: 0.95rem !important;
        color: #e0e7ff !important;
    }
    
    /* 버튼 커스텀 */
    .stButton>button {
        border-radius: 10px;
        font-weight: 700;
        transition: all 0.3s;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: 700;
        color: #94a3b8 !important;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white !important;
    }
    
    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: #e0e7ff !important;
    }
    
    /* 입력 필드 */
    .stTextInput input, .stSelectbox select {
        background-color: #1e293b !important;
        color: #e0e7ff !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
    }
    
    /* 슬라이더 */
    .stSlider {
        color: #e0e7ff !important;
    }
    
    /* Info, Warning, Success 박스 */
    .stAlert {
        background-color: rgba(30, 41, 59, 0.8) !important;
        color: #e0e7ff !important;
        border: 1px solid rgba(96, 165, 250, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 헤더
# ==========================================
st.markdown("""
<div class="header-container">
    <h1 class="main-title">📊 Global Economic Intelligence Hub</h1>
    <p class="subtitle">Real-time Economic News Monitoring & Analysis Platform</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 사이드바 - 통계 및 제어
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/stock-share.png", width=80)
    st.markdown("### 🎛️ Control Panel")
    
    # 수집 설정
    st.markdown("#### ⚙️ Collection Settings")
    interval_min = st.slider(
        "Auto-refresh Interval (min)",
        min_value=30,
        max_value=360,
        value=60,
        step=30,
        help="뉴스 수집 주기를 설정합니다"
    )
    
    # 상태 관리
    if "auto_running" not in st.session_state:
        st.session_state.auto_running = False
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start", use_container_width=True, type="primary"):
            st.session_state.auto_running = True
    with col2:
        if st.button("⏸️ Pause", use_container_width=True):
            st.session_state.auto_running = False
    
    # 상태 표시
    st.markdown("---")
    if st.session_state.auto_running:
        st.markdown("""
        <div class="status-badge status-active">
            🟢 ACTIVE - Collecting Data
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-badge status-inactive">
            ⚪ PAUSED
        </div>
        """, unsafe_allow_html=True)
    
    # 커버리지 정보
    st.markdown("---")
    st.markdown("#### 🌍 Global Coverage")
    coverage_data = {
        "Region": ["미국", "아시아", "유럽", "기타"],
        "Countries": [1, 6, 3, 2]
    }
    fig_coverage = px.pie(
        coverage_data,
        values="Countries",
        names="Region",
        hole=0.4,
        color_discrete_sequence=['#3b82f6', '#06b6d4', '#8b5cf6', '#10b981']
    )
    fig_coverage.update_layout(
        showlegend=True,
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e7ff', size=10),
        legend=dict(
            font=dict(color='#e0e7ff')
        )
    )
    fig_coverage.update_traces(
        textfont=dict(color='white', size=10),
        marker=dict(line=dict(color='#0a0e27', width=2))
    )
    st.plotly_chart(fig_coverage, use_container_width=True)
    
    # 수집 국가 목록
    st.markdown("#### 📍 Monitored Countries")
    countries = "🇺🇸 🇰🇷 🇨🇳 🇯🇵 🇩🇪 🇫🇷 🇬🇧 🇮🇳 🇹🇼 🇸🇬 🇭🇰 🇨🇦"
    st.info(countries)

# ==========================================
# 메인 탭
# ==========================================
tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "📰 Latest News", "⚙️ Settings"])

# =========================================================
# TAB 1: 대시보드
# =========================================================
with tab1:
    # KPI 메트릭
    if supabase:
        try:
            # 전체 기사 수
            total_response = supabase.table("news_articles").select("*", count="exact").execute()
            total_articles = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
            
            # 오늘 수집 기사
            today = datetime.now().date()
            today_response = supabase.table("news_articles")\
                .select("*")\
                .gte("published_at", today.isoformat())\
                .execute()
            today_articles = len(today_response.data)
            
            # 카테고리 수
            categories_response = supabase.table("news_articles").select("categories").execute()
            all_categories = set()
            for item in categories_response.data:
                if item.get('categories'):
                    all_categories.update(item['categories'])
            category_count = len(all_categories)
            
            # 활성 국가
            countries_response = supabase.table("news_articles").select("country").execute()
            active_countries = len(set([item['country'] for item in countries_response.data if item.get('country')]))
            
        except Exception as e:
            total_articles = 0
            today_articles = 0
            category_count = 0
            active_countries = 0
    else:
        total_articles = 0
        today_articles = 0
        category_count = 0
        active_countries = 0
    
    # KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_articles:,}</div>
            <div class="metric-label">Total Articles</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">+{today_articles}</div>
            <div class="metric-label">Today's Collection</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{category_count}</div>
            <div class="metric-label">Categories</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{active_countries}</div>
            <div class="metric-label">Active Countries</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 차트 섹션
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("### 📊 Articles by Country")
        if supabase:
            try:
                response = supabase.table("news_articles").select("country").execute()
                if response.data:
                    country_counts = pd.DataFrame(response.data)['country'].value_counts()
                    
                    # 전문적인 수평 바 차트
                    fig_country = go.Figure()
                    
                    fig_country.add_trace(go.Bar(
                        y=country_counts.index,
                        x=country_counts.values,
                        orientation='h',
                        marker=dict(
                            color=country_counts.values,
                            colorscale='Blues',
                            line=dict(color='#3b82f6', width=2),
                            colorbar=dict(
                                title="Articles",
                                titlefont=dict(color='#e0e7ff'),
                                tickfont=dict(color='#e0e7ff')
                            )
                        ),
                        text=country_counts.values,
                        textposition='outside',
                        textfont=dict(size=12, color='#e0e7ff', weight='bold'),
                        hovertemplate='<b>%{y}</b><br>Articles: %{x}<extra></extra>'
                    ))
                    
                    fig_country.update_layout(
                        height=350,
                        paper_bgcolor='rgba(15, 23, 42, 0.8)',
                        plot_bgcolor='rgba(30, 41, 59, 0.5)',
                        font=dict(color='#e0e7ff', size=12, family='Arial'),
                        xaxis=dict(
                            showgrid=True,
                            gridcolor='rgba(96, 165, 250, 0.15)',
                            title="Number of Articles",
                            titlefont=dict(color='#cbd5e1', size=13),
                            tickfont=dict(color='#e0e7ff')
                        ),
                        yaxis=dict(
                            showgrid=False,
                            tickfont=dict(color='#e0e7ff', size=11)
                        ),
                        margin=dict(l=10, r=40, t=30, b=40),
                        hoverlabel=dict(
                            bgcolor='#1e293b',
                            font_size=12,
                            font_color='#e0e7ff'
                        )
                    )
                    st.plotly_chart(fig_country, use_container_width=True)
            except:
                st.info("Loading data...")
    
    with chart_col2:
        st.markdown("### 🏷️ Top Categories")
        if supabase:
            try:
                response = supabase.table("news_articles").select("categories").execute()
                if response.data:
                    all_cats = []
                    for item in response.data:
                        if item.get('categories'):
                            all_cats.extend(item['categories'])
                    
                    cat_counts = pd.Series(all_cats).value_counts().head(8)
                    
                    # 전문적인 도넛 차트
                    fig_cat = go.Figure()
                    
                    fig_cat.add_trace(go.Pie(
                        labels=cat_counts.index,
                        values=cat_counts.values,
                        hole=0.5,
                        marker=dict(
                            colors=px.colors.sequential.Blues_r,
                            line=dict(color='#0a0e27', width=2)
                        ),
                        textinfo='label+percent',
                        textfont=dict(size=11, color='white', weight='bold'),
                        hovertemplate='<b>%{label}</b><br>Articles: %{value}<br>Share: %{percent}<extra></extra>'
                    ))
                    
                    fig_cat.add_annotation(
                        text=f"<b>{len(all_cats)}</b><br>Total",
                        x=0.5, y=0.5,
                        font=dict(size=18, color='#60a5fa', weight='bold'),
                        showarrow=False
                    )
                    
                    fig_cat.update_layout(
                        height=350,
                        paper_bgcolor='rgba(15, 23, 42, 0.8)',
                        font=dict(color='#e0e7ff', size=11),
                        margin=dict(l=20, r=20, t=30, b=20),
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="middle",
                            y=0.5,
                            xanchor="left",
                            x=1.05,
                            font=dict(color='#e0e7ff', size=10),
                            bgcolor='rgba(30, 41, 59, 0.5)'
                        ),
                        hoverlabel=dict(
                            bgcolor='#1e293b',
                            font_size=12,
                            font_color='#e0e7ff'
                        )
                    )
                    st.plotly_chart(fig_cat, use_container_width=True)
            except:
                st.info("Loading data...")
    
    # 타임라인 차트
    st.markdown("### 📅 Collection Timeline (Last 7 Days)")
    if supabase:
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            response = supabase.table("news_articles")\
                .select("published_at")\
                .gte("published_at", week_ago)\
                .execute()
            
            if response.data:
                df_timeline = pd.DataFrame(response.data)
                df_timeline['published_at'] = pd.to_datetime(df_timeline['published_at'])
                df_timeline['date'] = df_timeline['published_at'].dt.date
                daily_counts = df_timeline.groupby('date').size().reset_index(name='count')
                
                # 전문적인 Area + Line 차트
                fig_timeline = go.Figure()
                
                # Area 차트 (배경)
                fig_timeline.add_trace(go.Scatter(
                    x=daily_counts['date'],
                    y=daily_counts['count'],
                    fill='tozeroy',
                    fillcolor='rgba(59, 130, 246, 0.3)',
                    line=dict(color='#3b82f6', width=3),
                    mode='lines',
                    name='Articles',
                    hovertemplate='<b>%{x}</b><br>Articles: %{y}<extra></extra>'
                ))
                
                # 포인트 마커
                fig_timeline.add_trace(go.Scatter(
                    x=daily_counts['date'],
                    y=daily_counts['count'],
                    mode='markers',
                    marker=dict(
                        size=10,
                        color='#60a5fa',
                        line=dict(color='white', width=2)
                    ),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                fig_timeline.update_layout(
                    height=300,
                    paper_bgcolor='rgba(15, 23, 42, 0.8)',
                    plot_bgcolor='rgba(30, 41, 59, 0.5)',
                    font=dict(color='#e0e7ff', size=12),
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(96, 165, 250, 0.1)',
                        title="",
                        tickfont=dict(color='#cbd5e1')
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(96, 165, 250, 0.15)',
                        title="Articles Collected",
                        titlefont=dict(color='#cbd5e1', size=13),
                        tickfont=dict(color='#e0e7ff')
                    ),
                    margin=dict(l=60, r=40, t=30, b=40),
                    hovermode='x unified',
                    hoverlabel=dict(
                        bgcolor='#1e293b',
                        font_size=12,
                        font_color='#e0e7ff'
                    )
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
        except:
            st.info("Loading timeline data...")

# =========================================================
# TAB 2: 최신 뉴스
# =========================================================
with tab2:
    col_header, col_refresh = st.columns([3, 1])
    
    with col_header:
        st.markdown("### 📰 Latest Economic News")
    
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # 필터
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        filter_country = st.selectbox(
            "Country",
            ["All"] + ["미국", "한국", "중국", "일본", "독일", "프랑스", "영국", "인도", "대만", "싱가포르", "홍콩", "캐나다"],
            key="filter_country"
        )
    
    with filter_col2:
        if supabase:
            try:
                cat_response = supabase.table("news_articles").select("categories").execute()
                all_categories = set()
                for item in cat_response.data:
                    if item.get('categories'):
                        all_categories.update(item['categories'])
                filter_category = st.selectbox("Category", ["All"] + sorted(list(all_categories)))
            except:
                filter_category = "All"
        else:
            filter_category = "All"
    
    with filter_col3:
        limit = st.selectbox("Show", [50, 100, 200], index=0)
    
    # 뉴스 데이터 로드
    status_area = st.empty()
    
    if supabase:
        try:
            query = supabase.table("news_articles")\
                .select("*")\
                .order("published_at", desc=True)\
                .limit(limit)
            
            # 필터 적용
            if filter_country != "All":
                query = query.eq("country", filter_country)
            
            response = query.execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                # 카테고리 필터 (클라이언트 사이드)
                if filter_category != "All":
                    df = df[df['categories'].apply(lambda x: filter_category in x if x else False)]
                
                # 날짜 포맷
                df['published_at'] = pd.to_datetime(df['published_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                # 카테고리 표시 개선
                df['categories_display'] = df['categories'].apply(
                    lambda x: ', '.join(x[:3]) if x else 'General'
                )
                
                # 테이블 표시
                display_cols = ['country', 'title', 'categories_display', 'published_at', 'source']
                column_config = {
                    'country': st.column_config.TextColumn('🌍 Country', width='small'),
                    'title': st.column_config.TextColumn('📰 Title', width='large'),
                    'categories_display': st.column_config.TextColumn('🏷️ Categories', width='medium'),
                    'published_at': st.column_config.TextColumn('📅 Published', width='small'),
                    'source': st.column_config.TextColumn('📌 Source', width='small')
                }
                
                st.dataframe(
                    df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config,
                    height=600
                )
                
                st.caption(f"Showing {len(df)} articles")
                
            else:
                st.info("No articles found. Start collection to populate the database.")
                
        except Exception as e:
            st.error(f"Database Error: {str(e)}")
    else:
        st.warning("⚠️ Database connection not configured. Please check Supabase settings.")
    
    # 자동 수집 실행
    if st.session_state.auto_running:
        status_area.info("🌍 Scanning global news sources...")
        try:
            total_saved, logs = run_global_batch()
            if total_saved > 0:
                status_area.success(f"🎉 Collected {total_saved} new articles!\n\n" + "\n".join(logs))
            else:
                status_area.info("✅ Scan complete. No new articles.")
        except Exception as e:
            status_area.error(f"❌ Collection Error: {str(e)}")
        
        time.sleep(interval_min * 60)
        st.rerun()

# =========================================================
# TAB 3: 설정 (키워드 관리)
# =========================================================
with tab3:
    st.markdown("### ⚙️ Keyword Management")
    st.caption("Configure custom keywords for categorization and filtering")
    
    # 키워드 추가 폼
    with st.expander("➕ Add New Keyword", expanded=True):
        with st.form("add_keyword_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                new_cat = st.text_input(
                    "Category",
                    placeholder="e.g., Semiconductor",
                    help="분류할 카테고리 이름"
                )
            
            with col2:
                new_word = st.text_input(
                    "Keyword",
                    placeholder="e.g., TSMC, 삼성전자, 华为",
                    help="검색할 키워드 (다국어 지원)"
                )
            
            with col3:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("Add", type="primary", use_container_width=True)
            
            if submitted:
                if new_cat and new_word:
                    add_keyword(new_cat, new_word)
                    st.success(f"✅ Keyword '{new_word}' added to category '{new_cat}'")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ Please fill in all fields")
    
    st.markdown("---")
    
    # 등록된 키워드 표시
    keywords = get_all_keywords()
    
    if keywords:
        df_k = pd.DataFrame(keywords)
        st.markdown(f"### 📋 Registered Keywords ({len(keywords)} total)")
        
        # 카테고리별 그룹화
        for cat in sorted(df_k['category'].unique()):
            with st.expander(f"📂 {cat}", expanded=False):
                cat_data = df_k[df_k['category'] == cat]
                
                # 그리드 레이아웃
                cols = st.columns(4)
                for idx, (_, row) in enumerate(cat_data.iterrows()):
                    with cols[idx % 4]:
                        col_text, col_btn = st.columns([3, 1])
                        with col_text:
                            st.markdown(f"**{row['keyword']}**")
                        with col_btn:
                            if st.button("🗑️", key=f"del_{row['id']}", help="Delete keyword"):
                                delete_keyword(row['id'])
                                st.rerun()
    else:
        st.info("📭 No keywords registered yet. Add your first keyword above!")
    
    st.markdown("---")
    
    # 시스템 정보
    st.markdown("### 🔧 System Information")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown("""
        **Collection Status**
        - Auto-refresh: {}
        - Interval: {} minutes
        - Monitored Countries: 12
        - Economic Keywords: 100+
        """.format(
            "🟢 Active" if st.session_state.auto_running else "⚪ Paused",
            interval_min
        ))
    
    with info_col2:
        st.markdown("""
        **Database**
        - Provider: Supabase
        - Status: {}
        - Tables: news_articles, search_keywords
        """.format("🟢 Connected" if supabase else "🔴 Disconnected"))

# ==========================================
# Footer
# ==========================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; padding: 2rem;'>
    <p>Global Economic Intelligence Hub v2.0 | Powered by AI & Real-time Data</p>
    <p style='font-size: 0.875rem;'>🌍 Monitoring 12 countries • 📊 100+ economic indicators • 🔄 Real-time updates</p>
</div>
""", unsafe_allow_html=True)
