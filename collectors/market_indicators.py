"""
시장 지표 수집기
VIX, 환율, 미국 주요 지수 등 리스크 지표를 수집합니다.
FRED API 및 yfinance를 활용합니다.
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import config

logger = config.setup_logger(__name__)

# yfinance는 선택적 의존성
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance 미설치 - 일부 지표 수집 불가 (pip install yfinance)")


# ==============================================
# 시장 지표 심볼 정의
# ==============================================
MARKET_SYMBOLS = {
    # 변동성 지수
    "VIX": {"symbol": "^VIX", "name": "CBOE 변동성 지수", "type": "volatility"},
    "VIX9D": {"symbol": "^VIX9D", "name": "VIX 9일", "type": "volatility"},
    
    # 미국 주요 지수
    "SP500": {"symbol": "^GSPC", "name": "S&P 500", "type": "index"},
    "NASDAQ": {"symbol": "^IXIC", "name": "나스닥 종합", "type": "index"},
    "DOW": {"symbol": "^DJI", "name": "다우존스", "type": "index"},
    "RUSSELL2000": {"symbol": "^RUT", "name": "러셀 2000", "type": "index"},
    
    # 환율
    "USD_KRW": {"symbol": "KRW=X", "name": "달러/원 환율", "type": "currency"},
    "USD_JPY": {"symbol": "JPY=X", "name": "달러/엔 환율", "type": "currency"},
    "USD_CNY": {"symbol": "CNY=X", "name": "달러/위안 환율", "type": "currency"},
    "DXY": {"symbol": "DX-Y.NYB", "name": "달러 인덱스", "type": "currency"},
    
    # 채권 수익률
    "US10Y": {"symbol": "^TNX", "name": "미국채 10년물", "type": "bond"},
    "US2Y": {"symbol": "^IRX", "name": "미국채 2년물", "type": "bond"},
    
    # 원자재
    "CRUDE_OIL": {"symbol": "CL=F", "name": "WTI 원유", "type": "commodity"},
    "GOLD": {"symbol": "GC=F", "name": "금", "type": "commodity"},
    "COPPER": {"symbol": "HG=F", "name": "구리", "type": "commodity"},
    
    # 아시아 지수
    "NIKKEI": {"symbol": "^N225", "name": "니케이 225", "type": "index"},
    "HANG_SENG": {"symbol": "^HSI", "name": "항셍 지수", "type": "index"},
    "SHANGHAI": {"symbol": "000001.SS", "name": "상해 종합", "type": "index"},
}


def fetch_market_indicators(symbols: List[str] = None) -> Dict[str, Dict]:
    """
    시장 지표를 수집합니다.
    
    Args:
        symbols: 수집할 심볼 목록 (None이면 전체)
        
    Returns:
        Dict[str, Dict]: 심볼별 지표 데이터
    """
    if not YFINANCE_AVAILABLE:
        logger.error("yfinance 미설치. 시장 지표 수집 불가.")
        return {}
    
    logger.info("📊 [Market Indicators] 수집 시작")
    
    if symbols is None:
        symbols = list(MARKET_SYMBOLS.keys())
    
    results = {}
    
    for key in symbols:
        if key not in MARKET_SYMBOLS:
            logger.warning(f"   ⚠️ 알 수 없는 심볼: {key}")
            continue
        
        info = MARKET_SYMBOLS[key]
        symbol = info["symbol"]
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if hist.empty:
                logger.debug(f"   {key}: 데이터 없음")
                continue
            
            # 최신 데이터
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            
            price = float(latest['Close'])
            prev_price = float(prev['Close'])
            change = price - prev_price
            change_pct = (change / prev_price * 100) if prev_price != 0 else 0
            
            results[key] = {
                "name": info["name"],
                "type": info["type"],
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": str(hist.index[-1].date())
            }
            
            logger.debug(f"   {key}: {price:.2f} ({change_pct:+.2f}%)")
            
        except Exception as e:
            logger.error(f"   ❌ {key} 수집 실패: {e}")
            continue
    
    logger.info(f"   ✅ Market Indicators: {len(results)}개 수집")
    return results


def get_key_indicators() -> Dict[str, Dict]:
    """
    핵심 시장 지표만 수집합니다 (빠른 조회용).
    VIX, 주요 지수, 달러/원 환율, 미국채
    """
    key_symbols = ["VIX", "SP500", "NASDAQ", "USD_KRW", "US10Y", "CRUDE_OIL"]
    return fetch_market_indicators(key_symbols)


def get_risk_level(indicators: Dict[str, Dict]) -> Dict:
    """
    시장 지표를 기반으로 리스크 레벨을 계산합니다.
    
    Returns:
        Dict: 리스크 레벨 및 경고 사항
    """
    warnings = []
    risk_score = 0
    
    # VIX 체크 (공포지수)
    if "VIX" in indicators:
        vix = indicators["VIX"]["price"]
        if vix >= 30:
            risk_score += 3
            warnings.append(f"🚨 VIX {vix:.1f} - 극심한 공포 구간")
        elif vix >= 25:
            risk_score += 2
            warnings.append(f"⚠️ VIX {vix:.1f} - 높은 변동성")
        elif vix >= 20:
            risk_score += 1
            warnings.append(f"📊 VIX {vix:.1f} - 변동성 주의")
    
    # 달러/원 환율 체크
    if "USD_KRW" in indicators:
        usd_krw = indicators["USD_KRW"]["price"]
        change_pct = indicators["USD_KRW"]["change_pct"]
        
        if usd_krw >= 1400:
            risk_score += 2
            warnings.append(f"🚨 USD/KRW {usd_krw:.0f}원 - 원화 급락")
        elif usd_krw >= 1350:
            risk_score += 1
            warnings.append(f"⚠️ USD/KRW {usd_krw:.0f}원 - 원화 약세")
        
        if abs(change_pct) >= 1.0:
            warnings.append(f"📈 환율 급등락: {change_pct:+.2f}%")
    
    # 미국채 10년물 체크
    if "US10Y" in indicators:
        us10y = indicators["US10Y"]["price"]
        if us10y >= 5.0:
            risk_score += 2
            warnings.append(f"⚠️ 미국채 10년물 {us10y:.2f}% - 고금리 압박")
    
    # 미국 지수 하락 체크
    for idx in ["SP500", "NASDAQ"]:
        if idx in indicators:
            change_pct = indicators[idx]["change_pct"]
            if change_pct <= -2.0:
                risk_score += 2
                warnings.append(f"🔴 {indicators[idx]['name']} {change_pct:.2f}% 급락")
            elif change_pct <= -1.0:
                risk_score += 1
                warnings.append(f"📉 {indicators[idx]['name']} {change_pct:.2f}% 하락")
    
    # 리스크 레벨 결정
    if risk_score >= 5:
        level = "high"
        emoji = "🔴"
        description = "시장 리스크 높음 - 신중한 투자 필요"
    elif risk_score >= 3:
        level = "medium"
        emoji = "🟡"
        description = "시장 변동성 주의"
    else:
        level = "low"
        emoji = "🟢"
        description = "시장 안정"
    
    return {
        "level": level,
        "emoji": emoji,
        "description": description,
        "score": risk_score,
        "warnings": warnings
    }


def format_market_summary(indicators: Dict[str, Dict]) -> str:
    """
    시장 지표를 보기 좋은 텍스트로 포맷팅합니다.
    """
    lines = ["📊 **글로벌 시장 현황**", ""]
    
    # 변동성
    if "VIX" in indicators:
        vix = indicators["VIX"]
        lines.append(f"🌡️ VIX: {vix['price']:.1f} ({vix['change_pct']:+.1f}%)")
    
    # 미국 지수
    index_lines = []
    for key in ["SP500", "NASDAQ", "DOW"]:
        if key in indicators:
            idx = indicators[key]
            emoji = "📈" if idx["change_pct"] >= 0 else "📉"
            index_lines.append(f"{emoji} {idx['name']}: {idx['change_pct']:+.2f}%")
    if index_lines:
        lines.append("")
        lines.append("**미국 지수**")
        lines.extend(index_lines)
    
    # 환율
    if "USD_KRW" in indicators:
        krw = indicators["USD_KRW"]
        lines.append("")
        lines.append(f"💱 USD/KRW: {krw['price']:.0f}원 ({krw['change_pct']:+.2f}%)")
    
    # 채권
    if "US10Y" in indicators:
        us10y = indicators["US10Y"]
        lines.append(f"📜 미국채 10Y: {us10y['price']:.2f}%")
    
    # 원자재
    commodity_lines = []
    for key in ["CRUDE_OIL", "GOLD"]:
        if key in indicators:
            c = indicators[key]
            commodity_lines.append(f"{c['name']}: ${c['price']:.2f} ({c['change_pct']:+.1f}%)")
    if commodity_lines:
        lines.append("")
        lines.append("**원자재**")
        lines.extend(commodity_lines)
    
    return "\n".join(lines)


# 테스트용
if __name__ == "__main__":
    print("시장 지표 수집 테스트...")
    indicators = get_key_indicators()
    
    if indicators:
        print(format_market_summary(indicators))
        print()
        
        risk = get_risk_level(indicators)
        print(f"\n{risk['emoji']} 리스크 레벨: {risk['level'].upper()}")
        print(f"   {risk['description']}")
        if risk['warnings']:
            print("\n⚠️ 경고:")
            for w in risk['warnings']:
                print(f"   {w}")
    else:
        print("지표 수집 실패 (yfinance 설치 확인)")
