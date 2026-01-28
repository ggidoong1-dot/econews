import streamlit as st
import pandas as pd
from scraper import run_collector, supabase

st.set_page_config(page_title="EcoNews Data Dam", page_icon="🌐", layout="wide")

st.title("🛡️ EcoNews: 24h 데이터 댐")
st.caption("Supabase 연동 자동 수집 시스템")

# ---------------------------------------------------------
# 1. 사이드바: 수집기 작동
# ---------------------------------------------------------
with st.sidebar:
    st.header("🕵️‍♀️ 수집기 (Collector)")
    target_country = st.selectbox("타겟 국가", ["미국 (US)", "한국 (KR)"])
    
    if st.button("🚀 수집 및 DB 저장 시작"):
        config_map = {
            "미국 (US)": {"lang": "en", "code": "US", "query": "Economy"},
            "한국 (KR)": {"lang": "ko", "code": "KR", "query": "경제"}
        }
        cfg = config_map[target_country]
        
        with st.spinner(f"[{target_country}] 뉴스 수집 중..."):
            saved_count = run_collector(cfg["query"], cfg["lang"], cfg["code"])
            
        if saved_count > 0:
            st.success(f"✅ {saved_count}개 기사 저장 완료!")
            st.balloons()
        else:
            st.warning("새로운 기사가 없습니다.")

# ---------------------------------------------------------
# 2. 메인 화면: DB 데이터 조회
# ---------------------------------------------------------
st.divider()
st.subheader("💾 Supabase 저장 데이터")

if not supabase:
    st.error("🚨 Supabase 연결 실패! Secrets를 확인하세요.")
else:
    try:
        # 데이터 조회
        response = supabase.table("news_articles")\
            .select("*")\
            .order("published_at", desc=True)\
            .limit(50)\
            .execute()
        
        data = response.data
        
        if data:
            df = pd.DataFrame(data)
            
            # [수정] 여기가 잘리지 않도록 줄바꿈 처리했습니다
            display_cols = [
                "title", 
                "categories", 
                "keywords", 
                "country", 
                "published_at"
            ]
            
            # 실제 존재하는 컬럼만 필터링
            valid_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[valid_cols],
                use_container_width=True,
                hide_index=True
            )
            
            with st.expander("🔍 기사 상세 내용"):
                for item in data[:5]:
                    st.markdown(f"**[{item['country']}] {item['title']}**")
                    st.caption(f"링크: {item['link']} | 날짜: {item['published_at']}")
                    st.write(f"키워드: {item['keywords']}")
                    st.divider()
        else:
            st.info("📭 DB가 비어있습니다. 수집 버튼을 눌러보세요.")
            
    except Exception as e:
        st.error(f"데이터 조회 중 오류: {e}")
