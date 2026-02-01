#!/usr/bin/env python3
"""
Naver 뉴스 스크래핑 디버그 도구
현재 HTML 구조를 분석하여 올바른 CSS selector를 찾습니다.
"""
import requests
from bs4 import BeautifulSoup
import urllib.parse

def test_naver_structure(keyword="웰다잉"):
    """Naver 뉴스 구조 분석"""
    print("=" * 70)
    print("🔍 Naver 뉴스 HTML 구조 분석")
    print("=" * 70)
    
    encoded = urllib.parse.quote(keyword)
    url = f"https://search.naver.com/search.naver?where=news&query={encoded}&sort=1"
    
    print(f"\n검색어: {keyword}")
    print(f"URL: {url}\n")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"✅ HTTP Status: {response.status_code}\n")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다양한 셀렉터 시도
        selectors_to_try = [
            ('a.news_tit', '기본 셀렉터'),
            ('.news_area .news_tit', '뉴스 영역 내 제목'),
            ('div.news_wrap a.news_tit', '뉴스 래퍼 내 제목'),
            ('a[href*="n.news.naver.com"]', 'URL 패턴 기반'),
            ('.news_contents a', '뉴스 컨텐츠 링크'),
            ('div.group_news a', '그룹 뉴스 링크'),
            ('a.api_txt_lines', 'API 텍스트 라인'),
        ]
        
        print("📋 셀렉터 테스트 결과:\n")
        
        working_selectors = []
        
        for selector, description in selectors_to_try:
            items = soup.select(selector)
            print(f"[{len(items):3d}개] {selector:40s} - {description}")
            
            if items:
                working_selectors.append((selector, items))
        
        # 가장 많이 찾은 셀렉터 상세 분석
        if working_selectors:
            print("\n" + "=" * 70)
            print("✅ 작동하는 셀렉터 발견!")
            print("=" * 70)
            
            # 개수가 많은 순으로 정렬
            working_selectors.sort(key=lambda x: len(x[1]), reverse=True)
            
            best_selector, items = working_selectors[0]
            
            print(f"\n🎯 추천 셀렉터: {best_selector}")
            print(f"   발견된 항목: {len(items)}개\n")
            
            print("📰 첫 5개 기사 미리보기:\n")
            for i, item in enumerate(items[:5], 1):
                title = item.get_text(strip=True)
                link = item.get('href', '')
                
                print(f"{i}. {title[:60]}...")
                print(f"   링크: {link[:80]}...\n")
            
            # HTML 샘플 저장
            sample_file = '/home/claude/naver_sample.html'
            with open(sample_file, 'w', encoding='utf-8') as f:
                # 첫 번째 뉴스 항목의 HTML 구조 저장
                if items:
                    parent = items[0].find_parent()
                    if parent:
                        f.write(str(parent.prettify()))
            
            print(f"💾 HTML 샘플 저장: {sample_file}")
            
        else:
            print("\n" + "=" * 70)
            print("❌ 작동하는 셀렉터를 찾지 못했습니다.")
            print("=" * 70)
            
            # 전체 HTML 저장 (디버깅용)
            debug_file = '/home/claude/naver_full_debug.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"\n💾 전체 HTML 저장: {debug_file}")
            print("   파일을 열어서 HTML 구조를 직접 확인해주세요.")
            
            # 모든 <a> 태그 분석
            all_links = soup.find_all('a', href=True)
            naver_news_links = [a for a in all_links if 'news.naver.com' in a.get('href', '')]
            
            print(f"\n📊 전체 링크 통계:")
            print(f"   총 <a> 태그: {len(all_links)}개")
            print(f"   Naver 뉴스 링크: {len(naver_news_links)}개")
            
            if naver_news_links:
                print(f"\n🔗 Naver 뉴스 링크 샘플 (처음 3개):")
                for i, link in enumerate(naver_news_links[:3], 1):
                    print(f"\n{i}. 텍스트: {link.get_text(strip=True)[:50]}...")
                    print(f"   클래스: {link.get('class', [])}")
                    print(f"   URL: {link['href'][:80]}...")
        
        print("\n" + "=" * 70)
        print("테스트 완료")
        print("=" * 70)
        
    except requests.exceptions.Timeout:
        print("❌ 타임아웃 (10초)")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    keyword = sys.argv[1] if len(sys.argv) > 1 else "웰다잉"
    test_naver_structure(keyword)
