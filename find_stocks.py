import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import argparse
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockAnalyzer:
    """
    Naver Finance에서 수급 정보를 가져와 여러 지표를 기반으로 주식을 분석하는 클래스.
    """
    BASE_URL = "https://finance.naver.com"

    def __init__(self, investor_type='foreign', consecutive_days=2, market='kospi'):
        self.investor_type = investor_type
        self.consecutive_days = consecutive_days
        self.market = market
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
            response = requests.get(url)
            response.raise_for_status()
            response.encoding = 'euc-kr'
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logging.error(f"URL을 가져오는 중 오류 발생: {url} - {e}")
            return None

    def get_top_buy_stocks(self, day_index=1):
        """
        특정 날짜의 상위 순매수 종목 리스트를 가져옵니다.
        """
        list_url = f"{self.BASE_URL}/sise/sise_deal_rank_iframe.naver?sosok={self.market_code}&investor_gubun={self.investor_code}&type=buy"
        soup = self._fetch_url(list_url)
        if not soup: return []

        boxes = soup.find_all('div', class_='box_type_ms')
        if len(boxes) <= day_index: return []
        stock_table = boxes[day_index].find('table')
        if not stock_table: return []
        
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
                stocks.append((stock_name, stock_code))
        return stocks

    def get_stock_fundamentals(self, stock_code, soup):
        """종목의 펀더멘탈 및 추가 지표를 추출합니다."""
        try:
            per_tag = soup.select_one('#_per')
            pbr_tag = soup.select_one('#_pbr')
            per = float(per_tag.text) if per_tag and per_tag.text not in ['N/A', ''] else None
            pbr = float(pbr_tag.text) if pbr_tag and pbr_tag.text not in ['N/A', ''] else None

            dividend_yield, roe, debt_ratio, foreign_ratio = None, None, None, None
            
            div_yield_th = soup.find('th', string=lambda text: text and '배당수익률' in text)
            if div_yield_th:
                div_yield_td = div_yield_th.find_next_sibling('td')
                if div_yield_td and '%' in div_yield_td.text:
                    dividend_yield = float(div_yield_td.text.replace('%', '').strip())

            foreign_ratio_th = soup.find('th', string=lambda text: text and '외국인소진율' in text)
            if foreign_ratio_th:
                foreign_ratio_td = foreign_ratio_th.find_next_sibling('td')
                if foreign_ratio_td and '%' in foreign_ratio_td.text:
                    foreign_ratio = float(foreign_ratio_td.text.replace('%', '').strip())

            finance_summary_table = soup.find('div', class_='cop_analysis').find('table')
            if finance_summary_table:
                for row in finance_summary_table.find_all('tr'):
                    th_text = row.find('th').get_text(strip=True) if row.find('th') else ''
                    if 'ROE(지배주주)' in th_text and row.find_all('td'):
                        roe_text = row.find_all('td')[-1].text.strip()
                        if roe_text: roe = float(roe_text)
                    elif '부채비율' in th_text and row.find_all('td'):
                        debt_text = row.find_all('td')[-1].text.strip()
                        if debt_text: debt_ratio = float(debt_text)

            return per, pbr, dividend_yield, roe, debt_ratio, foreign_ratio
        except (ValueError, AttributeError):
            return None, None, None, None, None, None

    def analyze(self, output_file=None):
        """분석을 수행하고 결과를 출력하거나 파일로 저장합니다."""
        logging.info(f"{self.consecutive_days}일 연속 '{self.investor_type}'({self.market.upper()}) 순매수 상위 종목 분석 시작...")
        
        consecutive_codes = set()
        all_day_stocks = []
        for i in range(self.consecutive_days):
            stocks = self.get_top_buy_stocks(day_index=i)
            all_day_stocks.append(stocks)
            codes = {code for name, code in stocks}
            if not codes:
                logging.warning(f"{self.consecutive_days - i}일 전 데이터가 부족하여 분석을 중단합니다.")
                return
            if i == 0:
                consecutive_codes = codes
            else:
                consecutive_codes.intersection_update(codes)
        
        latest_stocks_map = {code: name for name, code in all_day_stocks[0]}
        consecutive_stocks = [(latest_stocks_map[code], code) for code in consecutive_codes if code in latest_stocks_map]

        if not consecutive_stocks:
            logging.info("분석할 종목이 없습니다.")
            return

        analyzed_results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        for i, (stock_name, stock_code) in enumerate(consecutive_stocks, 1):
            logging.info(f"({i}/{len(consecutive_stocks)}) {stock_name} ({stock_code}) 분석 중...")
            try:
                detail_url = f"{self.BASE_URL}/item/main.naver?code={stock_code}"
                soup = self._fetch_url(detail_url)
                if not soup: continue

                df = fdr.DataReader(stock_code, start=start_date, end=end_date)
                if df.empty: continue

                current_price = df['Close'].iloc[-1]
                change_rate = df['Change'].iloc[-1] * 100
                high_52_week = df['High'].max()
                
                per, pbr, dividend_yield, roe, debt_ratio, foreign_ratio = self.get_stock_fundamentals(stock_code, soup)

                if pd.isna(current_price) or pd.isna(high_52_week) or high_52_week == 0: continue

                score = 0
                passed_filters = []
                if pbr is not None and 0 < pbr < 1.0: score += 1; passed_filters.append(f"PBR: {pbr:.2f}")
                if per is not None and 0 < per < 15: score += 1; passed_filters.append(f"PER: {per:.2f}")
                if roe is not None and roe > 15: score += 1; passed_filters.append(f"ROE: {roe:.2f}%")
                if debt_ratio is not None and debt_ratio < 100: score += 1; passed_filters.append(f"부채비율: {debt_ratio:.2f}%")
                if dividend_yield is not None and dividend_yield > 2.0: score += 1; passed_filters.append(f"배당: {dividend_yield:.2f}%")

                analyzed_results.append({
                    "종목명": stock_name, "코드": stock_code, "종합 점수": score,
                    "현재가": int(current_price), "등락률": change_rate, "52주 신고가": int(high_52_week),
                    "PER": per, "PBR": pbr, "ROE": roe, "부채비율": debt_ratio, 
                    "배당수익률": dividend_yield, "외국인보유율": foreign_ratio,
                    "필터": ', '.join(passed_filters)
                })
            except Exception as e:
                logging.error(f"{stock_name} ({stock_code}) 분석 중 오류 발생: {e}")
                continue
        
        sorted_results = sorted(analyzed_results, key=lambda x: x['종합 점수'], reverse=True)
        
        if output_file:
            self.save_to_csv(sorted_results, output_file)
        else:
            self.print_results(sorted_results)

    def save_to_csv(self, results, filename):
        """분석 결과를 CSV 파일로 저장합니다."""
        if not results:
            logging.info("저장할 결과가 없습니다.")
            return
        df = pd.DataFrame(results)
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logging.info(f"분석 결과를 '{filename}' 파일로 저장했습니다.")
        except Exception as e:
            logging.error(f"파일 저장 중 오류 발생: {e}")

    def print_results(self, results):
        """분석 결과를 콘솔에 출력합니다."""
        if not results: return
        
        print("\n" + "="*80)
        print(f"분석 결과: {self.consecutive_days}일 연속 '{self.investor_type}'({self.market.upper()}) 순매수 상위 종목")
        print("="*80)

        for i, result in enumerate(results, 1):
            price_ratio = result['현재가'] / result['52주 신고가']
            change_rate_str = f"{result['등락률']:.2f}%"
            
            print(f"[{i:02d}] {result['종목명']} ({result['코드']}) - 종합 점수: {result['종합 점수']}/5")
            print(f"  - 현재가: {result['현재가']:,}원 (등락률: {change_rate_str}) | 52주 신고가: {result['52주 신고가']:,}원 (비율: {price_ratio:.2%})")
            print(f"  - PER: {result['PER'] or 'N/A'} | PBR: {result['PBR'] or 'N/A'} | ROE: {str(result['ROE'])+'%' if result['ROE'] is not None else 'N/A'}")
            print(f"  - 부채비율: {str(result['부채비율'])+'%' if result['부채비율'] is not None else 'N/A'} | 배당수익률: {str(result['배당수익률'])+'%' if result['배당수익률'] is not None else 'N/A'}")
            print(f"  - 외국인보유율: {str(result['외국인보유율'])+'%' if result['외국인보유율'] is not None else 'N/A'}")
            if result['필터']:
                print(f"  >>> 필터 만족: [ {result['필터']} ]")
            print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Naver Finance에서 수급 정보를 분석합니다.")
    parser.add_argument('--investor', type=str, default='foreign', choices=['foreign', 'institution'], help="분석할 투자자 종류 (foreign 또는 institution)")
    parser.add_argument('--days', type=int, default=2, help="연속 순매수 일수")
    parser.add_argument('--market', type=str, default='kospi', choices=['kospi', 'kosdaq'], help="분석할 시장 (kospi 또는 kosdaq)")
    parser.add_argument('--output', type=str, help="분석 결과를 저장할 CSV 파일명")
    
    args = parser.parse_args()

    analyzer = StockAnalyzer(investor_type=args.investor, consecutive_days=args.days, market=args.market)
    analyzer.analyze(output_file=args.output)

if __name__ == "__main__":
    main()
