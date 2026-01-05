import requests
from bs4 import BeautifulSoup
import re

def get_foreign_buy_stock_list():
    """
    Naver Finance에서 '외국인 순매수' 상위 종목명의 리스트를 가져와 출력합니다.
    """
    # '외국인 순매수' 데이터가 실제로 담겨있는 iframe의 URL
    list_url = "https://finance.naver.com/sise/sise_deal_rank_iframe.naver?sosok=01&investor_gubun=9000&type=buy"
    
    print(f"Fetching stock list from: {list_url}")

    try:
        response = requests.get(list_url)
        response.raise_for_status()
        # Naver Finance는 EUC-KR 인코딩을 사용합니다.
        response.encoding = 'euc-kr'
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stock list: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # '외국인 순매수' 테이블은 두 번째 'box_type_ms' div 안에 있습니다.
    boxes = soup.find_all('div', class_='box_type_ms')
    if len(boxes) < 2:
        print("오류: '외국인 순매수' 종목 리스트를 포함하는 div를 찾지 못했습니다.")
        return

    # 두 번째 div 박스에서 테이블을 찾습니다.
    stock_table = boxes[1].find('table')
    if not stock_table:
        print("오류: 종목 테이블을 찾지 못했습니다.")
        return
    
    stock_names = []
    # 테이블의 모든 행(tr)을 순회합니다.
    for row in stock_table.find_all('tr'):
        # 헤더 행(th 포함)은 건너뜁니다.
        if row.find('th'):
            continue

        # 각 행의 첫 번째 'td' 안에 있는 링크(a)를 찾습니다.
        stock_link = row.select_one('td:nth-of-type(1) p a')
        if stock_link:
            stock_name = stock_link.text.strip()
            if stock_name: # 빈 텍스트가 아닌 경우에만 추가
                stock_names.append(stock_name)

    if not stock_names:
        print("종목명을 찾지 못했습니다.")
        return
        
    print("\n--- '외국인 순매수' 상위 종목 리스트 ---")
    for i, name in enumerate(stock_names, 1):
        print(f"[{i:02d}] {name}")
    print("------------------------------------")


if __name__ == "__main__":
    get_foreign_buy_stock_list()
