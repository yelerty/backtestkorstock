#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 주식 대시보드 - HTML 출력 버전
GitHub Pages용 HTML 파일을 생성합니다.
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
import os

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


class UnifiedStockDashboardHTML:
    """통합 주식 정보 대시보드 - HTML 생성"""

    BASE_URL = "https://finance.naver.com"

    def __init__(self, market='kospi', investor_type='foreign', consecutive_days=2):
        self.market = market
        self.investor_type = investor_type
        self.consecutive_days = consecutive_days
        self.investor_code = self._get_investor_code()
        self.market_code = self._get_market_code()
        self.html_parts = []

    def _get_investor_code(self):
        return {'foreign': '9000', 'institution': '1000'}.get(self.investor_type, '9000')

    def _get_market_code(self):
        return {'kospi': '01', 'kosdaq': '02'}.get(self.market, '01')

    def _fetch_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'euc-kr'
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logging.error(f"URL 가져오기 오류: {url} - {e}")
            return None

    def _add_html(self, html):
        """HTML 파트를 추가합니다."""
        self.html_parts.append(html)

    def get_market_indices(self):
        """국내외 시장 지수 정보를 가져와 HTML로 변환합니다."""
        html = '<div class="section"><h2>📊 시장 현황</h2><div class="indices-grid">'

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
                change_class = 'positive' if change > 0 else 'negative' if change < 0 else 'neutral'
                change_str = f"{change:+.2f}%"

                html += f'''
                <div class="index-card">
                    <div class="index-name">{name}</div>
                    <div class="index-symbol">{symbol}</div>
                    <div class="index-price">{price}</div>
                    <div class="index-change {change_class}">{change_str}</div>
                </div>
                '''
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
                change_class = 'positive' if change_percent > 0 else 'negative' if change_percent < 0 else 'neutral'
                change_str = f"{change_percent:+.2f}%"

                html += f'''
                <div class="index-card">
                    <div class="index-name">{name}</div>
                    <div class="index-symbol">{ticker}</div>
                    <div class="index-price">{price_str}</div>
                    <div class="index-change {change_class}">{change_str}</div>
                </div>
                '''
            except Exception as e:
                logging.error(f"{name} 조회 오류: {e}")

        html += '</div></div>'
        self._add_html(html)

    def get_today_top_stocks(self):
        """오늘의 순매수 상위 종목 리스트를 HTML로 변환합니다."""
        investor_kr = '외국인' if self.investor_type == 'foreign' else '기관'
        market_kr = 'KOSPI' if self.market == 'kospi' else 'KOSDAQ'

        html = f'<div class="section"><h2>📈 오늘의 {investor_kr} 순매수 상위 종목 ({market_kr})</h2>'
        html += '<div class="stock-list">'

        list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
        soup = self._fetch_url(list_url)

        if not soup:
            html += '<p>데이터를 가져올 수 없습니다.</p></div></div>'
            self._add_html(html)
            return

        boxes = soup.find_all('div', class_='box_type_ms')
        if len(boxes) < 1:
            html += '<p>데이터를 찾을 수 없습니다.</p></div></div>'
            self._add_html(html)
            return

        stock_table = boxes[0].find('table')
        if not stock_table:
            html += '<p>테이블을 찾을 수 없습니다.</p></div></div>'
            self._add_html(html)
            return

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

        html += '<ol class="top-stocks-list">'
        for stock in stocks[:20]:
            html += f'<li><span class="stock-name">{stock["name"]}</span> <span class="stock-code">({stock["code"]})</span></li>'
        html += '</ol></div></div>'

        self._add_html(html)

    def analyze_yesterday_performance(self):
        """어제 순매수 상위 종목들의 오늘 등락률을 분석하여 HTML로 변환합니다."""
        investor_kr = '외국인' if self.investor_type == 'foreign' else '기관'
        market_kr = 'KOSPI' if self.market == 'kospi' else 'KOSDAQ'

        html = f'<div class="section"><h2>📉 어제 {investor_kr} 순매수 종목의 오늘 등락률 ({market_kr})</h2>'

        list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
        soup = self._fetch_url(list_url)

        if not soup:
            html += '<p>데이터를 가져올 수 없습니다.</p></div>'
            self._add_html(html)
            return

        boxes = soup.find_all('div', class_='box_type_ms')
        if len(boxes) < 2:
            html += '<p>어제 데이터를 찾을 수 없습니다.</p></div>'
            self._add_html(html)
            return

        stock_table = boxes[1].find('table')
        if not stock_table:
            html += '<p>테이블을 찾을 수 없습니다.</p></div>'
            self._add_html(html)
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

        html += '<div class="performance-list">'

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
                change_class = 'positive' if change_percent > 0 else 'negative' if change_percent < 0 else 'neutral'
                change_str = f"{change_percent:+.2f}%"

                html += f'<div class="performance-item"><span class="stock-name">{stock["name"]}</span> <span class="change {change_class}">{change_str}</span></div>'

            except Exception as e:
                logging.error(f"{stock['name']} 분석 오류: {e}")

        html += '</div>'

        if results:
            average_change = sum(item['change'] for item in results) / len(results)
            average_change_percent = average_change * 100
            avg_class = 'positive' if average_change_percent > 0 else 'negative' if average_change_percent < 0 else 'neutral'
            avg_str = f"{average_change_percent:+.2f}%"

            html += f'<div class="summary-box"><strong>평균 등락률:</strong> <span class="change {avg_class}">{avg_str}</span>'
            if yesterday_trade_date and today_trade_date:
                html += f'<br><small>기준: {yesterday_trade_date} → {today_trade_date}</small>'
            html += '</div>'

        html += '</div>'
        self._add_html(html)

    def analyze_consecutive_stocks(self):
        """N일 연속 순매수 상위 종목의 펀더멘탈을 분석하여 HTML로 변환합니다."""
        investor_kr = '외국인' if self.investor_type == 'foreign' else '기관'
        market_kr = 'KOSPI' if self.market == 'kospi' else 'KOSDAQ'

        html = f'<div class="section"><h2>🎯 {self.consecutive_days}일 연속 {investor_kr} 순매수 종목 펀더멘탈 분석 ({market_kr})</h2>'

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
            html += f'<p>{self.consecutive_days}일 연속 순매수 종목이 없습니다.</p></div>'
            self._add_html(html)
            return

        latest_stocks_map = {code: name for name, code in all_day_stocks[0]}
        consecutive_stocks = [(latest_stocks_map[code], code) for code in consecutive_codes if code in latest_stocks_map]

        html += f'<p class="info-text">총 {len(consecutive_stocks)}개 종목 발견</p>'

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

                per, pbr, roe, foreign_ratio = self._get_stock_fundamentals(stock_code, soup)

                if pd.isna(current_price) or pd.isna(high_52_week) or high_52_week == 0:
                    continue

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

        sorted_results = sorted(analyzed_results, key=lambda x: x['종합 점수'], reverse=True)

        html += '<div class="stock-analysis-list">'
        for i, result in enumerate(sorted_results, 1):
            price_ratio = result['현재가'] / result['52주 신고가']
            change_class = 'positive' if result['등락률'] > 0 else 'negative' if result['등락률'] < 0 else 'neutral'
            change_str = f"{result['등락률']:+.2f}%"

            html += f'''
            <div class="stock-card">
                <div class="stock-header">
                    <span class="rank">#{i}</span>
                    <span class="stock-name">{result['종목명']}</span>
                    <span class="stock-code">({result['코드']})</span>
                    <span class="score">점수: {result['종합 점수']}/3</span>
                </div>
                <div class="stock-price">
                    <strong>{result['현재가']:,}원</strong>
                    <span class="change {change_class}">{change_str}</span>
                </div>
                <div class="stock-details">
                    <div>52주 신고가: {result['52주 신고가']:,}원 ({price_ratio:.1%})</div>
                    <div>PER: {result['PER'] if result['PER'] else 'N/A'} | PBR: {result['PBR'] if result['PBR'] else 'N/A'} | ROE: {str(result['ROE'])+'%' if result['ROE'] is not None else 'N/A'}</div>
                    <div>외국인보유율: {str(result['외국인보유율'])+'%' if result['외국인보유율'] is not None else 'N/A'}</div>
            '''

            if result['필터']:
                html += f'<div class="filters">✓ {result["필터"]}</div>'

            html += '</div></div>'

        html += '</div></div>'
        self._add_html(html)

    def _get_stock_fundamentals(self, stock_code, soup):
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

    def generate_html(self, output_file='index.html'):
        """모든 데이터를 수집하고 HTML 파일을 생성합니다."""
        print("데이터 수집 중...")

        self.get_market_indices()
        self.get_today_top_stocks()
        self.analyze_yesterday_performance()
        self.analyze_consecutive_stocks()

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        html_template = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 분석 대시보드</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .header .update-time {{
            color: #666;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.5em;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .indices-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .index-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s;
        }}
        .index-card:hover {{
            transform: translateY(-5px);
        }}
        .index-name {{
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 1.1em;
        }}
        .index-symbol {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 10px;
        }}
        .index-price {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .index-change {{
            font-size: 1.1em;
            font-weight: bold;
        }}
        .positive {{
            color: #e53935;
        }}
        .negative {{
            color: #1e88e5;
        }}
        .neutral {{
            color: #666;
        }}
        .stock-list {{
            padding: 10px 0;
        }}
        .top-stocks-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 10px;
            padding-left: 0;
            list-style-position: inside;
        }}
        .top-stocks-list li {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            transition: background 0.2s;
        }}
        .top-stocks-list li:hover {{
            background: #e9ecef;
        }}
        .stock-name {{
            font-weight: 600;
        }}
        .stock-code {{
            color: #666;
            font-size: 0.9em;
        }}
        .performance-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }}
        .performance-item {{
            padding: 12px;
            background: #f8f9fa;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.2em;
        }}
        .summary-box .change {{
            color: white;
            font-size: 1.5em;
            font-weight: bold;
        }}
        .stock-analysis-list {{
            display: grid;
            gap: 15px;
        }}
        .stock-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
            transition: all 0.3s;
        }}
        .stock-card:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }}
        .stock-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .rank {{
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .score {{
            background: #764ba2;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-left: auto;
        }}
        .stock-price {{
            font-size: 1.3em;
            margin-bottom: 10px;
        }}
        .stock-details {{
            color: #666;
            line-height: 1.8;
        }}
        .stock-details > div {{
            padding: 5px 0;
        }}
        .filters {{
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 5px;
            color: #667eea;
            font-weight: 500;
        }}
        .info-text {{
            background: #e3f2fd;
            padding: 10px 15px;
            border-radius: 5px;
            color: #1976d2;
            margin-bottom: 15px;
        }}
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .indices-grid,
            .top-stocks-list,
            .performance-list {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 주식 분석 대시보드</h1>
            <div class="update-time">마지막 업데이트: {now}</div>
        </div>

        {''.join(self.html_parts)}

        <div class="section" style="text-align: center; color: #666;">
            <p>이 대시보드는 매일 아침 8시 45분에 자동으로 업데이트됩니다.</p>
            <p style="margin-top: 10px;"><small>데이터 출처: Naver Finance, FinanceDataReader, yfinance</small></p>
        </div>
    </div>
</body>
</html>
'''

        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print(f"✓ HTML 파일이 생성되었습니다: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="통합 주식 분석 대시보드 - HTML 생성")
    parser.add_argument('--market', type=str, default='kospi',
                        choices=['kospi', 'kosdaq'],
                        help="분석할 시장 (kospi 또는 kosdaq, 기본값: kospi)")
    parser.add_argument('--investor', type=str, default='foreign',
                        choices=['foreign', 'institution'],
                        help="분석할 투자자 종류 (foreign 또는 institution, 기본값: foreign)")
    parser.add_argument('--days', type=int, default=2,
                        help="연속 순매수 일수 (기본값: 2)")
    parser.add_argument('--output', type=str, default='docs/index.html',
                        help="출력 HTML 파일 경로 (기본값: docs/index.html)")

    args = parser.parse_args()

    dashboard = UnifiedStockDashboardHTML(
        market=args.market,
        investor_type=args.investor,
        consecutive_days=args.days
    )

    dashboard.generate_html(output_file=args.output)


if __name__ == "__main__":
    main()
