import streamlit as st
import pandas as pd
# 함수 이름이 변경되었으므로 반드시 run_collector를 가져와야 합니다.
from scraper import run_collector, supabase

st.set_page_config(page_title="EcoNews Data Dam", page_icon="🌐", layout="wide")

st.title("🛡️ EcoNews: 24h 데이터 댐 (Supabase 연동)")
st.caption("Auto-Archiving System for Stock Prediction")

# ---------------------------------------------------------
# 1. 사이드바: 수집기 작동 (Trigger)
# ---------------------------------------------------------
with st.sidebar:
    st.header("🕵️‍♀️ 수집기 (Collector)")
    st.info("버튼을 누르면 뉴스를 수집해 DB에 저장합니다.")
    
    target_country = st.selectbox("타겟 국가", ["미국 (US)", "한국 (KR)"])
    
    if st.button("🚀 수집 및 DB 저장 시작"):
        # 국가별 설정 매핑
        config_map = {
            "미국 (US)": {"lang": "en", "code": "US", "query": "Economy"},
            "한국 (KR)": {"lang": "ko", "code": "KR", "query": "경제"}
        }
        cfg = config_map[target_country]
        
        with st.spinner(f"[{target_country}] 뉴스 수집 및 저장 중..."):
            # run_collector 함수 실행
            saved_count = run_collector(cfg["query"], cfg["lang"], cfg["code"])
            
        if saved_count > 0:
            st.success(f"✅ {saved_count}개의 새로운 기사가 DB에 저장되었습니다!")
            st.balloons()
        else:
            st.warning("새로운 기사가 없거나, 이미 저장된 기사들입니다.")

# ---------------------------------------------------------
# 2. 메인 화면: DB 데이터 조회 (Viewer)
# ---------------------------------------------------------
st.divider()
st.subheader("💾 Supabase 실시간 데이터 (최신순 50개)")

if not supabase:
    st.error("🚨 Supabase 연결 실패! Secrets 설정을 확인해주세요.")
else:
    # [중요] try 블록 시작
    try:
        # DB에서 데이터 가져오기
        response = supabase.table("news_articles")\
            .select("*")\
            .order("published_at", desc=True)\
            .limit(50)\
            .execute()
        
        data = response.data
        
        if data:
            # 보기 좋게 데이터프레임으로 변환
            df = pd.DataFrame(data)
            
            # 주요 컬럼만 선택해서 보여주기
            display_cols = ["title", "categories", "keywords", "country", "published
