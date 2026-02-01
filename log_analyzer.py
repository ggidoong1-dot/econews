#!/usr/bin/env python3
"""
로그 분석 유틸리티
데이터 저장 오류를 쉽게 추적하고 분석합니다.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

LOG_DIR = "logs"
FAILED_ARTICLES_LOG = os.path.join(LOG_DIR, "failed_articles.jsonl")

def get_log_file(module_name):
    """로그 파일 경로 반환"""
    return os.path.join(LOG_DIR, f"{module_name}.log")

def read_log_file(file_path, lines=-1):
    """로그 파일 읽기"""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.readlines()
    
    return content[-lines:] if lines > 0 else content

def show_recent_errors(module="database", count=20):
    """최근 에러 표시"""
    log_file = get_log_file(module)
    print(f"\n📋 {module}.log - 최근 {count}개 에러\n" + "=" * 70)
    
    errors = []
    for line in read_log_file(log_file):
        if "ERROR" in line or "❌" in line or "실패" in line:
            errors.append(line.strip())
    
    if not errors:
        print("✅ 최근 에러 없음")
    else:
        for i, error in enumerate(errors[-count:], 1):
            print(f"{i:3d}. {error}")
    
    print("\n")

def show_save_statistics(module="database"):
    """저장 통계 표시"""
    log_file = get_log_file(module)
    print(f"\n📊 {module}.log - 저장 통계\n" + "=" * 70)
    
    saved = 0
    duplicates = 0
    failed = 0
    articles_saved = []
    errors = []
    
    for line in read_log_file(log_file):
        if "✅" in line and "저장" in line:
            # [1/5] ✅ 3개 저장, 2개 중복
            parts = line.split("✅")[1].strip() if "✅" in line else ""
            if "개 저장" in parts:
                count = int(parts.split("개 저장")[0].strip().split()[-1])
                saved += count
                articles_saved.append((line.split()[0], count))
            
            if "중복" in parts:
                dup = int(parts.split("개 중복")[0].strip().split()[-1])
                duplicates += dup
        
        if "기사 저장 실패" in line:
            failed += 1
            errors.append(line.split("기사 저장 실패")[1][:100])
        
        if "실패" in line and "개" in line:
            try:
                fail_count = int(line.split("실패")[1].split("개")[0].strip().split()[-1])
                failed += fail_count
            except:
                pass
    
    print(f"✅ 저장 성공: {saved}개")
    print(f"📌 중복 제외: {duplicates}개")
    print(f"❌ 저장 실패: {failed}개")
    
    if articles_saved:
        print(f"\n청크별 저장 통계:")
        for chunk_info, count in articles_saved[:5]:
            print(f"  {chunk_info}: {count}개")
        if len(articles_saved) > 5:
            print(f"  ... 외 {len(articles_saved) - 5}개 청크")
    
    print("\n")

def show_failed_articles(module="database", count=10):
    """저장 실패한 기사 표시"""
    log_file = get_log_file(module)
    print(f"\n🚨 {module}.log - 저장 실패한 기사 ({count}개)\n" + "=" * 70)
    
    failed_articles = []
    for line in read_log_file(log_file):
        if "기사 저장 실패" in line:
            failed_articles.append(line.strip())
    
    if not failed_articles:
        print("✅ 실패한 기사 없음")
    else:
        for i, article in enumerate(failed_articles[-count:], 1):
            # 출처와 에러만 추출
            if "출처:" in article:
                parts = article.split("출처:")[1].split("에러:")
                source = parts[0].split(",")[0].strip()
                error = parts[1].strip()[:60] if len(parts) > 1 else "Unknown"
                print(f"{i:3d}. [{source}] ❌ {error}")
            else:
                print(f"{i:3d}. {article[:100]}")
    
    print("\n")


def analyze_failed_articles_json(count=10):
    """failed_articles.jsonl 파일 분석"""
    print(f"\n📊 실패한 기사 상세 분석\n" + "=" * 70)
    
    if not os.path.exists(FAILED_ARTICLES_LOG):
        print("📝 아직 기록된 실패 기사가 없습니다.")
        print(f"   경로: {os.path.abspath(FAILED_ARTICLES_LOG)}\n")
        return
    
    error_types = defaultdict(int)
    error_reasons = defaultdict(int)
    sources = defaultdict(int)
    failed_records = []
    
    try:
        with open(FAILED_ARTICLES_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    failed_records.append(record)
                    error_types[record.get('error_type', 'UNKNOWN')] += 1
                    reason = record.get('error_reason', 'Unknown')
                    error_reasons[reason[:50]] += 1
                    source = record.get('article', {}).get('source', 'Unknown')
                    sources[source] += 1
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}\n")
        return
    
    if not failed_records:
        print("📝 기록된 실패 기사가 없습니다.\n")
        return
    
    # 에러 타입별 통계
    print(f"❌ 총 실패 기사: {len(failed_records)}개\n")
    print("📌 에러 타입별 통계:")
    for error_type, cnt in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (cnt / len(failed_records) * 100)
        print(f"  • {error_type}: {cnt}개 ({percentage:.1f}%)")
    
    print("\n📌 출처별 실패 통계:")
    for source, cnt in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {source}: {cnt}개")
    
    print("\n📌 최근 실패 원인 (상위 5개):")
    for reason, cnt in sorted(error_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {reason}: {cnt}개")
    
    # 최근 기사들 상세 정보
    print(f"\n📝 최근 실패한 기사 (상위 {count}개):\n")
    for i, record in enumerate(reversed(failed_records[-count:]), 1):
        article = record.get('article', {})
        print(f"{i:2d}. 시간: {record.get('timestamp', 'N/A')[:19]}")
        print(f"    타입: {record.get('error_type', 'N/A')}")
        print(f"    이유: {record.get('error_reason', 'N/A')[:80]}")
        print(f"    출처: {article.get('source', 'N/A')}")
        print(f"    제목: {article.get('title', 'N/A')[:60]}")
        print(f"    링크: {article.get('link', 'N/A')[:70]}")
        print()
    
    print()

def show_today_summary():
    """오늘의 요약"""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📅 {today} 요약\n" + "=" * 70)
    
    log_file = get_log_file("database")
    
    if not os.path.exists(log_file):
        print("❌ 로그 파일이 없습니다. 아직 한 번도 실행되지 않았습니다.")
        print(f"   로그 디렉토리: {os.path.abspath(LOG_DIR)}")
        return
    
    total_saved = 0
    total_failed = 0
    total_duplicates = 0
    
    for line in read_log_file(log_file):
        if today in line:
            if "✅" in line and "저장" in line:
                try:
                    parts = line.split("✅")[1]
                    count = int(parts.split("개 저장")[0].strip().split()[-1])
                    total_saved += count
                    dup = int(parts.split("중복")[0].strip().split()[-1])
                    total_duplicates += dup
                except:
                    pass
            
            if "❌" in line and "저장 실패" in line:
                total_failed += 1
    
    print(f"✅ 저장 성공: {total_saved}개")
    print(f"📌 중복: {total_duplicates}개")
    print(f"❌ 저장 실패: {total_failed}개")
    print(f"🎯 성공률: {(total_saved / (total_saved + total_failed) * 100):.1f}%" if (total_saved + total_failed) > 0 else "🎯 데이터 없음")
    
    print("\n")

def list_log_files():
    """로그 파일 목록 표시"""
    print(f"\n📂 로그 파일 (위치: {os.path.abspath(LOG_DIR)})\n" + "=" * 70)
    
    if not os.path.exists(LOG_DIR):
        print("❌ logs/ 디렉토리가 없습니다.")
        return
    
    files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith('.log')])
    
    if not files:
        print("❌ 로그 파일이 없습니다.")
        return
    
    for f in files:
        file_path = os.path.join(LOG_DIR, f)
        size = os.path.getsize(file_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
        print(f"  📄 {f:25s} | {size_str:>10s} | {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n")

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "errors":
            show_recent_errors(count=30)
        elif command == "stats":
            show_save_statistics()
        elif command == "failed":
            show_failed_articles(count=20)
        elif command == "analyze":
            analyze_failed_articles_json(count=15)
        elif command == "today":
            show_today_summary()
        elif command == "files":
            list_log_files()
        elif command == "full":
            list_log_files()
            show_today_summary()
            show_save_statistics()
            show_failed_articles(count=10)
            analyze_failed_articles_json(count=10)
        else:
            print(f"❌ 알 수 없는 명령어: {command}")
            print_help()
    else:
        print_help()

def print_help():
    """도움말"""
    print("""
📋 로그 분석 유틸리티

사용법: python log_analyzer.py [명령어]

명령어:
  errors     - 최근 에러 30개 표시
  stats      - 저장 통계 표시
  failed     - 저장 실패한 기사 20개 표시 (로그 기반)
  analyze    - 실패한 기사 상세 분석 (JSON 기반) ⭐ 추천
  today      - 오늘의 요약 표시
  files      - 로그 파일 목록 표시
  full       - 전체 분석 (위의 모든 항목)

주요 옵션:
  python log_analyzer.py errors    # 에러 보기
  python log_analyzer.py analyze   # 실패한 기사 상세 분석
  python log_analyzer.py full      # 전체 분석

출력 파일:
  ./logs/database.log              - 일반 로그
  ./logs/failed_articles.jsonl     - 실패한 기사 상세 정보 ← 여기서 원인 확인!

💡 팁: 'analyze' 명령어를 사용하면 실패 원인을 한 눈에 볼 수 있습니다.
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 에러: {e}")
        import traceback
        traceback.print_exc()
