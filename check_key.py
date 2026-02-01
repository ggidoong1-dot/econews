# check_key.py
import os
from dotenv import load_dotenv

# 1. .env 파일 강제 로드
loaded = load_dotenv()

print("="*40)
print(f"📂 .env 파일 로드 성공 여부: {loaded}")
print("-" * 40)

# 2. 키 확인
key = os.getenv("NEWSAPI_KEY")

if key:
    print(f"✅ 키 발견 성공!")
    print(f"🔑 키 값 앞부분: {key[:4]}****")
else:
    print("❌ 키를 찾을 수 없습니다.")
    print("   👉 .env 파일에 'NEWSAPI_KEY=...' 라고 적혀있는지 확인하세요.")
    print("   👉 파일명이 '.env'가 맞는지 확인하세요. (.env.txt 안됨)")

print("="*40)