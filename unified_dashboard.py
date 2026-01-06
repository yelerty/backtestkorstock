#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 주식 대시보드
모든 시장 정보와 수급 분석 결과를 한 화면에 표시합니다.
"""

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import FinanceDataReader as fdr
import yfinance as yf
from datetime import datetime, timedelta
import argparse
import logging

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


class UnifiedStockDashboard:
    """통합 주식 정보 대시보드"""

    BASE_URL = "https://finance.naver.com"

    def __init__(self, market='kospi', investor_type='foreign', consecutive_days=2):
        self.market = market
        self.investor_type = investor_type
        self.consecutive_days = consecutive_days
        self.investor_code = self._get_investor_code()
        self.market_code = self._get_market_code()

    def _get_investor_code(self):
        """투자자 타입에 맞는 코드를 반환합니다."""
        return {'foreign': '9000', 'institution': '1000'}.get(self.investor_type, '9000')

    def _get_market_code(self):
        """시장 종류에 맞는 코드를 반환합니다."""
        return {'kospi': '01', 'kosdaq': '02'}.get(self.market, '01')

    def _fetch_url(self, url):
        """주어진 URL의 HTML을 가져옵니다."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'euc-kr'
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logging.error(f"URL 가져오기 오류: {url} - {e}")
            return None

    # ========== 1. 시장 현황 ==========
    def get_market_indices(self):
        """국내외 시장 지수 정보를 가져옵니다."""
        print("\n" + "="*80)
        print(f"📊 시장 현황 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        print("="*80)

        # 국내 지수
        krx_indices = {
            'KS11': '코스피 (KOSPI)',
            'KQ11': '코스닥 (KOSDAQ)',
        }

        for symbol, name in krx_indices.items():
            try:
                df = fdr.DataReader(symbol, (datetime.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d'))
                if df.empty:
                    continue

                latest = df.iloc[-1]
                price = f"{latest['Close']:,.2f}"
                change = latest['Change'] * 100
                change_str = f"{change:+.2f}%"

                if change > 0:
                    change_str = f"\033[92m{change_str}\033[0m"  # 녹색
                elif change < 0:
                    change_str = f"\033[91m{change_str}\033[0m"  # 빨간색

                print(f"▶ {name} ({symbol})")
                print(f"  - 현재가: {price} | 등락률: {change_str}")
            except Exception as e:
                logging.error(f"{name} 조회 오류: {e}")

        # 해외 선물 지수
        futures_indices = {
            'NQ=F': '나스닥 100 선물',
            'ES=F': 'S&P 500 선물',
            '^VIX': 'VIX 공포지수',
        }

        for ticker, name in futures_indices.items():
            try:
                data = yf.Ticker(ticker).history(period="2d")
                if data.empty or len(data) < 2:
                    continue

                latest = data.iloc[-1]
                previous = data.iloc[-2]
                price = latest['Close']
                change = price - previous['Close']
                change_percent = (change / previous['Close']) * 100

                price_str = f"{price:,.2f}"
                change_str = f"{change_percent:+.2f}%"

                if change_percent > 0:
                    change_str = f"\033[92m{change_str}\033[0m"
                elif change_percent < 0:
                    change_str = f"\033[91m{change_str}\033[0m"

                print(f"▶ {name} ({ticker})")
                print(f"  - 현재가: {price_str} | 등락률: {change_str}")
            except Exception as e:
                logging.error(f"{name} 조회 오류: {e}")

        print("="*80)

    # ========== 2. 오늘의 순매수 상위 종목 ==========
    def get_today_top_stocks(self):
        """오늘의 순매수 상위 종목 리스트를 표시합니다."""
        print(f"\n📈 오늘의 '{self.investor_type.upper()}' 순매수 상위 종목 ({self.market.upper()})")
        print("-"*80)

        list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
        soup = self._fetch_url(list_url)

        if not soup:
            print("데이터를 가져올 수 없습니다.")
            return []

        boxes = soup.find_all('div', class_='box_type_ms')
        if len(boxes) < 1:
            print("데이터를 찾을 수 없습니다.")
            return []

        stock_table = boxes[0].find('table')
        if not stock_table:
            print("테이블을 찾을 수 없습니다.")
            return []

        stocks = []
        for row in stock_table.find_all('tr'):
            if row.find('th'):
                continue
            stock_link = row.select_one('td:nth-of-type(1) p a')
            if not stock_link:
                continue

            stock_name = stock_link.text.strip()
            href = stock_link.get('href', '')
            match = re.search(r'code=(\d+)', href)
            if not match:
                continue
            stock_code = match.group(1)

            if stock_name and stock_code:
                stocks.append({'name': stock_name, 'code': stock_code})

        for i, stock in enumerate(stocks[:20], 1):  # 상위 20개만 표시
            print(f"[{i:02d}] {stock['name']} ({stock['code']})")

        print("-"*80)
        return stocks

    # ========== 3. 어제 순매수 종목의 오늘 등락률 ==========
    def analyze_yesterday_performance(self):
        """어제 순매수 상위 종목들의 오늘 등락률을 분석합니다."""
        print(f"\n📉 어제 '{self.investor_type.upper()}' 순매수 종목의 오늘 등락률 분석 ({self.market.upper()})")
        print("-"*80)

        list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
        soup = self._fetch_url(list_url)

        if not soup:
            print("데이터를 가져올 수 없습니다.")
            return

        boxes = soup.find_all('div', class_='box_type_ms')
        if len(boxes) < 2:
            print("어제 데이터를 찾을 수 없습니다.")
            return

        stock_table = boxes[1].find('table')  # 어제 데이터는 두 번째 박스
        if not stock_table:
            return

        yesterday_stocks = []
        for row in stock_table.find_all('tr'):
            if row.find('th'):
                continue
            stock_link = row.select_one('td:nth-of-type(1) p a')
            if not stock_link:
                continue

            stock_name = stock_link.text.strip()
            href = stock_link.get('href', '')
            match = re.search(r'code=(\d+)', href)
            if not match:
                continue
            stock_code = match.group(1)

            if stock_name and stock_code:
                yesterday_stocks.append({'name': stock_name, 'code': stock_code})

        today = datetime.now()
        start_day = today - timedelta(days=5)

        results = []
        yesterday_trade_date = None
        today_trade_date = None

        for i, stock in enumerate(yesterday_stocks):
            try:
                df = fdr.DataReader(stock['code'], start=start_day, end=today)
                if len(df) < 2:
                    continue

                if i == 0:
                    today_trade_date = df.index[-1].strftime('%Y-%m-%d')
                    yesterday_trade_date = df.index[-2].strftime('%Y-%m-%d')

                latest_change = df['Change'].iloc[-1]
                results.append({
                    'name': stock['name'],
                    'change': latest_change
                })

                change_percent = latest_change * 100
                change_str = f"{change_percent:+.2f}%"

                if change_percent > 0:
                    change_str = f"\033[92m{change_str}\033[0m"
                elif change_percent < 0:
                    change_str = f"\033[91m{change_str}\033[0m"

                print(f"  {stock['name']}: {change_str}")

            except Exception as e:
                logging.error(f"{stock['name']} 분석 오류: {e}")

        if results:
            average_change = sum(item['change'] for item in results) / len(results)
            average_change_percent = average_change * 100

            avg_str = f"{average_change_percent:+.2f}%"
            if average_change_percent > 0:
                avg_str = f"\033[92m{avg_str}\033[0m"
            elif average_change_percent < 0:
                avg_str = f"\033[91m{avg_str}\033[0m"

            print(f"\n💡 평균 등락률: {avg_str}")
            if yesterday_trade_date and today_trade_date:
                print(f"   (기준: {yesterday_trade_date} → {today_trade_date})")

        print("-"*80)

    # ========== 4. N일 연속 순매수 종목 펀더멘탈 분석 ==========
    def analyze_consecutive_stocks(self):
        """N일 연속 순매수 상위 종목의 펀더멘탈을 분석합니다."""
        print(f"\n🎯 {self.consecutive_days}일 연속 '{self.investor_type.upper()}' 순매수 종목 펀더멘탈 분석 ({self.market.upper()})")
        print("-"*80)

        # N일간의 순매수 종목 가져오기
        consecutive_codes = set()
        all_day_stocks = []

        for i in range(self.consecutive_days):
            list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
            soup = self._fetch_url(list_url)

            if not soup:
                continue

            boxes = soup.find_all('div', class_='box_type_ms')
            if len(boxes) <= i:
                break

            stock_table = boxes[i].find('table')
            if not stock_table:
                continue

            stocks = []
            for row in stock_table.find_all('tr'):
                if row.find('th'):
                    continue
                stock_link = row.select_one('td:nth-of-type(1) p a')
                if not stock_link:
                    continue

                stock_name = stock_link.text.strip()
                href = stock_link.get('href', '')
                match = re.search(r'code=(\d+)', href)
                if not match:
                    continue
                stock_code = match.group(1)

                if stock_name and stock_code:
                    stocks.append((stock_name, stock_code))

            all_day_stocks.append(stocks)
            codes = {code for name, code in stocks}

            if i == 0:
                consecutive_codes = codes
            else:
                consecutive_codes.intersection_update(codes)

        if not consecutive_codes:
            print(f"{self.consecutive_days}일 연속 순매수 종목이 없습니다.")
            print("-"*80)
            return

        latest_stocks_map = {code: name for name, code in all_day_stocks[0]}
        consecutive_stocks = [(latest_stocks_map[code], code) for code in consecutive_codes if code in latest_stocks_map]

        print(f"총 {len(consecutive_stocks)}개 종목 발견")
        print()

        # 각 종목의 펀더멘탈 분석
        analyzed_results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        for i, (stock_name, stock_code) in enumerate(consecutive_stocks, 1):
            try:
                detail_url = f"{self.BASE_URL}/item/main.naver?code={stock_code}"
                soup = self._fetch_url(detail_url)
                if not soup:
                    continue

                df = fdr.DataReader(stock_code, start=start_date, end=end_date)
                if df.empty:
                    continue

                current_price = df['Close'].iloc[-1]
                change_rate = df['Change'].iloc[-1] * 100
                high_52_week = df['High'].max()

                # 펀더멘탈 데이터 추출
                per, pbr, roe, foreign_ratio = self._get_stock_fundamentals(stock_code, soup)

                if pd.isna(current_price) or pd.isna(high_52_week) or high_52_week == 0:
                    continue

                # 필터 점수 계산
                score = 0
                passed_filters = []
                if pbr is not None and 0 < pbr < 1.0:
                    score += 1
                    passed_filters.append(f"PBR: {pbr:.2f}")
                if per is not None and 0 < per < 15:
                    score += 1
                    passed_filters.append(f"PER: {per:.2f}")
                if roe is not None and roe > 15:
                    score += 1
                    passed_filters.append(f"ROE: {roe:.2f}%")

                analyzed_results.append({
                    "종목명": stock_name,
                    "코드": stock_code,
                    "종합 점수": score,
                    "현재가": int(current_price),
                    "등락률": change_rate,
                    "52주 신고가": int(high_52_week),
                    "PER": per,
                    "PBR": pbr,
                    "ROE": roe,
                    "외국인보유율": foreign_ratio,
                    "필터": ', '.join(passed_filters)
                })

            except Exception as e:
                logging.error(f"{stock_name} ({stock_code}) 분석 오류: {e}")

        # 종합 점수 순으로 정렬하여 출력
        sorted_results = sorted(analyzed_results, key=lambda x: x['종합 점수'], reverse=True)

        for i, result in enumerate(sorted_results, 1):
            price_ratio = result['현재가'] / result['52주 신고가']
            change_rate_str = f"{result['등락률']:+.2f}%"

            if result['등락률'] > 0:
                change_rate_str = f"\033[92m{change_rate_str}\033[0m"
            elif result['등락률'] < 0:
                change_rate_str = f"\033[91m{change_rate_str}\033[0m"

            print(f"[{i:02d}] {result['종목명']} ({result['코드']}) - 점수: {result['종합 점수']}/3")
            print(f"    현재가: {result['현재가']:,}원 ({change_rate_str}) | 52주 신고가: {result['52주 신고가']:,}원 ({price_ratio:.1%})")
            print(f"    PER: {result['PER'] or 'N/A'} | PBR: {result['PBR'] or 'N/A'} | ROE: {str(result['ROE'])+'%' if result['ROE'] is not None else 'N/A'}")
            if result['필터']:
                print(f"    ✓ 필터: {result['필터']}")
            print()

        print("-"*80)

    def _get_stock_fundamentals(self, stock_code, soup):
        """종목의 펀더멘탈 및 추가 지표를 추출합니다."""
        try:
            per_tag = soup.select_one('#_per')
            pbr_tag = soup.select_one('#_pbr')
            per = float(per_tag.text) if per_tag and per_tag.text not in ['N/A', ''] else None
            pbr = float(pbr_tag.text) if pbr_tag and pbr_tag.text not in ['N/A', ''] else None

            foreign_ratio = None
            foreign_ratio_th = soup.find('th', string=lambda text: text and '외국인소진율' in text)
            if foreign_ratio_th:
                foreign_ratio_td = foreign_ratio_th.find_next_sibling('td')
                if foreign_ratio_td and '%' in foreign_ratio_td.text:
                    foreign_ratio = float(foreign_ratio_td.text.strip().replace('%', ''))

            roe = None
            finance_summary_table = soup.find('div', class_='cop_analysis')
            if finance_summary_table:
                finance_summary_table = finance_summary_table.find('table')
                if finance_summary_table:
                    for row in finance_summary_table.find_all('tr'):
                        th_text = row.find('th').get_text(strip=True) if row.find('th') else ''
                        if 'ROE(지배주주)' in th_text and row.find_all('td'):
                            roe_text = row.find_all('td')[-1].text.strip()
                            if roe_text:
                                roe = float(roe_text)

            return per, pbr, roe, foreign_ratio
        except (ValueError, AttributeError) as e:
            logging.error(f"펀더멘탈 추출 오류: {e}")
            return None, None, None, None

    # ========== 메인 대시보드 ==========
    def display_full_dashboard(self):
        """모든 정보를 표시하는 통합 대시보드"""
        print("\n")
        print("╔" + "═"*78 + "╗")
        print("║" + " "*20 + "🚀 통합 주식 분석 대시보드 🚀" + " "*26 + "║")
        print("╚" + "═"*78 + "╝")

        # 1. 시장 현황
        self.get_market_indices()

        # 2. 오늘의 순매수 상위 종목
        self.get_today_top_stocks()

        # 3. 어제 순매수 종목의 오늘 등락률
        self.analyze_yesterday_performance()

        # 4. N일 연속 순매수 종목 펀더멘탈 분석
        self.analyze_consecutive_stocks()

        print("\n" + "="*80)
        print(f"대시보드 업데이트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="통합 주식 분석 대시보드")
    parser.add_argument('--market', type=str, default='kospi',
                        choices=['kospi', 'kosdaq'],
                        help="분석할 시장 (kospi 또는 kosdaq, 기본값: kospi)")
    parser.add_argument('--investor', type=str, default='foreign',
                        choices=['foreign', 'institution'],
                        help="분석할 투자자 종류 (foreign 또는 institution, 기본값: foreign)")
    parser.add_argument('--days', type=int, default=2,
                        help="연속 순매수 일수 (기본값: 2)")

    args = parser.parse_args()

    dashboard = UnifiedStockDashboard(
        market=args.market,
        investor_type=args.investor,
        consecutive_days=args.days
    )

    dashboard.display_full_dashboard()


if __name__ == "__main__":
    main()
