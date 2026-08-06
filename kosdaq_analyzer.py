import pandas as pd
import requests

def get_kosdaq_top_stocks(sort_by='PER', ascending=True, top_n=30):
    """
    Naver Finance에서 KOSDAQ 데이터를 스크래핑하고 지정된 컬럼으로 정렬하여 반환합니다.

    Args:
        sort_by (str): 정렬 기준이 될 컬럼명 (예: 'PER', 'ROE', '시가총액').
        ascending (bool): 오름차순 정렬 여부.
        top_n (int): 상위 몇 개를 반환할지 결정.

    Returns:
        pandas.DataFrame: 정렬된 KOSDAQ 종목 데이터.
    """
    # KOSDAQ 상승률 페이지 URL (sosok=1)
    url = "https://finance.naver.com/sise/sise_rise.naver?sosok=1"

    # 웹사이트가 스크립트 접근을 차단하는 것을 피하기 위해 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # requests를 사용하여 페이지 HTML 가져오기
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외 발생

        # Naver Finance는 'euc-kr' 인코딩을 사용합니다.
        html_content = response.content
        
        # pandas.read_html을 사용하여 HTML 테이블을 DataFrame 리스트로 읽어오기
        tables = pd.read_html(html_content, encoding='euc-kr')
        
        # 일반적으로 주요 데이터 테이블은 페이지에서 가장 큰 테이블 중 하나입니다.
        # 구조를 확인하고 가장 적합한 테이블을 선택합니다. (보통 type_2 클래스)
        df = None
        # read_html은 종종 여러 테이블을 반환합니다. 그 중 '종목명' 컬럼이 있는 테이블을 찾습니다.
        for table in tables:
            if '종목명' in table.columns:
                df = table
                break
        
        if df is None:
            print("데이터 테이블을 찾을 수 없습니다.")
            return pd.DataFrame()

        # 데이터 정제
        # 1. 불필요한 'Unnamed: *' 컬럼 제거
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 2. 모든 행이 NaN인 경우 해당 행 제거
        df = df.dropna(how='all')

        # 3. '종목명'이 NaN인 행(구분선 등) 제거
        df = df[df['종목명'].notna()]

        # 4. 숫자형으로 변환해야 할 컬럼 리스트
        numeric_cols = ['현재가', '전일비', '등락률', '거래량', '시가총액', 'PER', 'ROE']
        
        for col in numeric_cols:
            if col in df.columns:
                # 쉼표(,)를 제거하고 숫자형으로 변환, 변환할 수 없는 값은 NaT/NaN으로 처리
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # '등락률'은 이미 숫자형으로 변환되었으므로 추가 처리가 필요 없습니다.

        # 데이터 정렬
        if sort_by not in df.columns:
            print(f"'{sort_by}' 컬럼이 존재하지 않아 정렬할 수 없습니다. 사용 가능한 컬럼: {df.columns.tolist()}")
            return df

        # 정렬 기준 컬럼에 NaN 값이 없는 데이터만 필터링하여 정렬
        sorted_df = df.dropna(subset=[sort_by]).sort_values(by=sort_by, ascending=ascending)
        
        return sorted_df.head(top_n)

    except requests.exceptions.RequestException as e:
        print(f"HTTP 요청 오류: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"데이터 처리 중 오류 발생: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # PER 기준으로 오름차순 정렬하여 상위 15개 종목 보기
    print("--- KOSDAQ 주식 (PER 낮은 순) ---")
    sorted_by_per = get_kosdaq_top_stocks(sort_by='PER', ascending=True, top_n=15)
    print(sorted_by_per)

    print("\n" + "="*50 + "\n")

    # ROE 기준으로 내림차순 정렬하여 상위 15개 종목 보기
    # (참고: 현재 URL에서는 '시가총액' 정보를 제공하지 않습니다.)
    print("--- KOSDAQ 주식 (ROE 높은 순) ---")
    sorted_by_roe = get_kosdaq_top_stocks(sort_by='ROE', ascending=False, top_n=15)
    print(sorted_by_roe)
