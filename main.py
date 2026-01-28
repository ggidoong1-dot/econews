import streamlit as st
import pandas as pd
import time
from datetime import datetime
from scraper import run_global_batch, supabase, add_keyword, delete_keyword, get_all_keywords

st.set_page_config(page_title="Global EcoNews Dam", page_icon="🌍", layout="wide")

st.title("🌍 Global EcoNews: 전 세계 경제 데이터 댐")

tab1, tab2 = st.tabs(["📡 수집 모니터링", "⚙️ 키워드 관리"])

# =========================================================
# TAB 1: 수집 모니터링
# =========================================================
with tab1:
    col_ctrl, col_log = st.columns([1, 2])
    
    with col_ctrl:
        st.subheader("제어 센터")
        interval_min = st.slider("자동 수집 주기 (분)", 30, 360, 60, step=30)
        
        if "auto_running" not in st.session_state:
            st.session_state.auto_running = False

        if st.button(label="🚀 자동 수집 시작", type="primary", use_container_width=True):
            st.session_state.auto_running = True
        
        if st.button(label="⏹️ 중지", use_container_width=True):
            st.session_state.auto_running = False
            
        st.divider()
        if st.session_state.auto_running:
            st.success(f"가동 중... ({interval_min}분 주기)")
        else:
            st.warning("일시 정지됨")
            
        st.info("""
        **수집 대상 국가:**
        🇺🇸미국 🇰🇷한국 🇨🇳중국 🇯🇵일본 
        🇩🇪독일 🇫🇷프랑스 🇬🇧영국 🇮🇳인도 🇹🇼대만
        """)

    with col_log:
        st.subheader("실시간 현황")
        status_area = st.empty()
        
        if supabase:
            try:
                response = supabase.table("news_articles")\
                    .select("*")\
                    .order("published_at", desc=True)\
                    .limit(50)\
                    .execute()
                if response.data:
                    df = pd.DataFrame(response.data)
                    st.dataframe(
                        df[["country", "title", "categories", "published_at"]], 
                        use_container_width=True, 
                        hide_index=True
                    )
            except:
                st.error("DB 연결 오류")

    if st.session_state.auto_running:
        status_area.info("🌍 전 세계 뉴스 스캔 시작...")
        try:
            total_saved, logs = run_global_batch()
            if total_saved > 0:
                status_area.success(f"🎉 총 {total_saved}개 저장 완료!\n" + "\n".join(logs))
            else:
                status_area.info("새로운 기사 없음.")
        except Exception as e:
            status_area.error(f"에러: {e}")
        
        time.sleep(interval_min * 60)
        st.rerun()

# =========================================================
# TAB 2: 키워드 관리 (심플 버전)
# =========================================================
with tab2:
    st.header("키워드 설정")
    st.caption("언어 상관없이 키워드만 입력하세요. (예: Samsung, 삼성전자, 华为)")
    
    # [수정] 언어 선택란 삭제 -> 아주 심플해짐
    with st.form("add_keyword_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            new_cat = st.text_input("카테고리", placeholder="예: 반도체")
        with c2:
            new_word = st.text_input("검색 키워드", placeholder="예: TSMC")
        with c3:
            st.write("") 
            st.write("") 
            submitted = st.form_submit_button("추가", type="primary")
            
        if submitted:
            if new_cat and new_word:
                add_keyword(new_cat, new_word)
                st.success(f"✅ '{new_word}' 추가됨!")
                st.rerun()
            else:
                st.error("입력값을 확인하세요.")

    st.divider()

    keywords = get_all_keywords()
    if keywords:
        df_k = pd.DataFrame(keywords)
        st.subheader(f"등록된 키워드 ({len(keywords)}개)")
        
        for cat in df_k['category'].unique():
            with st.expander(f"📂 {cat}", expanded=True):
                cat_data = df_k[df_k['category'] == cat]
                for _, row in cat_data.iterrows():
                    col_txt, col_del = st.columns([4, 1])
                    with col_txt:
                        st.write(f"- {row['keyword']}")
                    with col_del:
                        if st.button("삭제", key=f"del_{row['id']}"):
                            delete_keyword(row['id'])
                            st.rerun()
    else:
        st.info("등록된 키워드가 없습니다.")
