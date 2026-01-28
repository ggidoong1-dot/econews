import streamlit as st
from scraper import fetch_global_news

# 페이지 설정
st.set_page_config(page_title="EcoNews Pro", page_icon="🌐", layout="wide")

st.title("🛡️ EcoNews: 글로벌 경제 정밀 모니터링")
st.markdown("---")

# 1. 사이드바: 제어 센터
with st.sidebar:
    st.header("⚙️ 수집 및 필터링 설정")
    
    # 국가 선택에 따른 코드 매핑
    country_choice = st.selectbox("수집 대상 국가", ["미국", "일본", "중국"])
    country_map = {
        "미국": {"lang": "en", "gl": "US"},
        "일본": {"lang": "ja", "gl": "JP"},
        "중국": {"lang": "zh-CN", "gl": "CN"}
    }
    
    # 검색 키워드 입력
    user_query = st.text_input("검색어를 입력하세요 (예: Nvidia, Interest Rate)", "Economy")
    
    start_btn = st.button("🚀 정밀 모니터링 시작")

# 2. 메인 화면: 뉴스 전시
if start_btn:
    with st.spinner(f"[{country_choice}] 뉴스 분석 및 필터링 중..."):
        config = country_map[country_choice]
        results = fetch_global_news(user_query, config['lang'], config['gl'])
        
        if results:
            st.success(f"총 {len(results)}개의 핵심 기사를 발견했습니다.")
            
            for item in results:
                with st.container():
                    # 카드 스타일 레이아웃
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.subheader(item['title'])
                        st.caption(f"📅 {item['date']} | 🏢 {item['source']}")
                    with col2:
                        st.link_button("기사 원문 보기", item['link'])
                    
                    st.write(f"🔍 원문: {item['original']}")
                    st.divider()
        else:
            st.warning("설정하신 핵심 키워드에 부합하는 뉴스가 현재 없습니다.")
else:
    st.info("사이드바에서 설정을 확인하고 [모니터링 시작] 버튼을 눌러주세요.")