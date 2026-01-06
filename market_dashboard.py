import FinanceDataReader as fdr
import yfinance as yf
from datetime import datetime
import pandas as pd

def get_krx_indices():
    """FinanceDataReader를 사용하여 코스피와 코스닥 지수를 가져옵니다."""
    indices = {
        'KS11': '코스피 (KOSPI)',
        'KQ11': '코스닥 (KOSDAQ)',
    }
    results = []
    
    for symbol, name in indices.items():
        try:
            df = fdr.DataReader(symbol, (datetime.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d'))
            if df.empty: continue
            
            latest = df.iloc[-1]
            results.append({
                'name': name,
                'symbol': symbol,
                'price': f"{latest['Close']:,.2f}",
                'change': f"{latest['Change']*100:+.2f}%"
            })
        except Exception:
            continue
    return results

def get_yfinance_futures():
    """yfinance를 사용하여 미국 선물 지수 데이터를 가져옵니다."""
    indices_to_find = {
        'NQ=F': '나스닥 100 선물',
        'ES=F': 'S&P 500 선물',
        '^VIX': 'VIX 공포지수',
    }
    results = []
    
    for ticker, name in indices_to_find.items():
        try:
            # yfinance는 최근 2일치 데이터를 위해 '2d' period를 사용할 수 있습니다.
            data = yf.Ticker(ticker).history(period="2d")
            if data.empty or len(data) < 2:
                continue
            
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            
            price = latest['Close']
            change = price - previous['Close']
            change_percent = (change / previous['Close']) * 100
            
            results.append({
                'name': name,
                'symbol': ticker,
                'price': f"{price:,.2f}",
                'change': f"{change_percent:+.2f}%"
            })
        except Exception as e:
            print(f"yfinance로 '{name}' 데이터를 가져오는 중 오류 발생: {e}")
    
    return results

def display_dashboard(all_indices):
    """가져온 모든 지수 정보를 보기 좋게 출력합니다."""
    print("\n" + "="*60)
    print(f"종합 시장 현황판 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("="*60)

    if not all_indices:
        print("표시할 데이터가 없습니다.")
        return

    for data in all_indices:
        change_str = data['change']
        # 등락률 부호에 따라 색상 지정
        if isinstance(change_str, str) and change_str.startswith('+'):
            change_str = f"\033[92m{change_str}\033[0m" # 녹색
        elif isinstance(change_str, str) and change_str.startswith('-'):
            change_str = f"\033[91m{change_str}\033[0m" # 빨간색

        print(f"▶ {data['name']} ({data['symbol']})")
        print(f"  - 현재가: {data['price']}")
        print(f"  - 등락률: {change_str}")
        print("-"*60)

if __name__ == "__main__":
    # 1. 국내 지수 가져오기
    krx_data = get_krx_indices()
    
    # 2. 해외 선물 지수 가져오기
    futures_data = get_yfinance_futures()
    
    # 3. 결과 합쳐서 출력하기
    display_dashboard(krx_data + futures_data)
