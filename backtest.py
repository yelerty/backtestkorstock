import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import argparse

def get_top_buy_stocks(day_index=0, market='kospi'):
    """
    Naver Finance에서 특정 날짜의 '외국인 순매수' 상위 종목 리스트를 가져옵니다.
    """
    market_code = {'kospi': '01', 'kosdaq': '02'}.get(market, '01')
    list_url = f"https://finance.naver.com/sise/sise_deal_rank_iframe.naver?sosok={market_code}&investor_gubun=9000&type=buy"
    try:
        response = requests.get(list_url)
        response.raise_for_status()
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"종목 리스트를 가져오는 중 오류 발생: {e}")
        return []

    boxes = soup.find_all('div', class_='box_type_ms')
    if len(boxes) <= day_index:
        return []
    stock_table = boxes[day_index].find('table')
    if not stock_table:
        return []
    
    stocks = []
    for row in stock_table.find_all('tr'):
        if row.find('th'): continue
        stock_link = row.select_one('td:nth-of-type(1) p a')
        if not stock_link: continue
        
        stock_name = stock_link.text.strip()
        href = stock_link.get('href', '')
        match = re.search(r'code=(\d+)', href)
        if not match: continue
        stock_code = match.group(1)

        if stock_name and stock_code:
            stocks.append({'name': stock_name, 'code': stock_code})
    return stocks

def analyze_next_day_performance(market='kospi'):
    """
    어제 외국인 순매수 상위 종목들의 오늘 등락률을 분석합니다.
    """
    print(f"어제 '{market.upper()}' 시장의 '외국인 순매수' 상위 종목 리스트를 가져옵니다...")
    yesterday_stocks = get_top_buy_stocks(day_index=0, market=market)

    if not yesterday_stocks:
        print("어제 순매수 종목 리스트를 가져오지 못했습니다.")
        return

    today = datetime.now()
    start_day = today - timedelta(days=5) 
    
    results = []
    yesterday_trade_date = None
    today_trade_date = None

    print(f"\n총 {len(yesterday_stocks)}개 종목의 오늘 등락률을 확인합니다.")
    
    for i, stock in enumerate(yesterday_stocks):
        try:
            df = fdr.DataReader(stock['code'], start=start_day, end=today)
            if len(df) < 2:
                continue
            
            if i == 0:
                today_trade_date = df.index[-1].strftime('%Y-%m-%d')
                yesterday_trade_date = df.index[-2].strftime('%Y-%m-%d')
                print(f"(기준 거래일: 어제({yesterday_trade_date}) -> 오늘({today_trade_date}))")
                print("-" * 50)

            latest_change = df['Change'].iloc[-1]
            results.append({
                'name': stock['name'],
                'change': latest_change
            })
            
            change_percent = latest_change * 100
            print(f"- {stock['name']}: {change_percent:+.2f}%")

        except Exception as e:
            print(f"- {stock['name']}: 데이터 조회 중 오류 ({e})")

    if not results:
        print("\n등락률을 확인할 수 있는 종목이 없습니다.")
        return
        
    average_change = sum(item['change'] for item in results) / len(results)
    average_change_percent = average_change * 100
    
    print("-" * 50)
    print("\n[분석 요약]")
    print(f"'{yesterday_trade_date}'의 '{market.upper()}' 외국인 순매수 상위 {len(results)}개 종목을")
    print(f"'{today_trade_date}'까지 보유했다면, 평균 등락률은 【 {average_change_percent:+.2f}% 】 입니다.")
    print("="*50)

def main():
    parser = argparse.ArgumentParser(description="어제 외국인 순매수 상위 종목의 다음날 등락률을 분석합니다.")
    parser.add_argument('--market', type=str, default='kospi', choices=['kospi', 'kosdaq'], help="분석할 시장 (kospi 또는 kosdaq)")
    args = parser.parse_args()
    
    analyze_next_day_performance(market=args.market)

if __name__ == "__main__":
    main()
