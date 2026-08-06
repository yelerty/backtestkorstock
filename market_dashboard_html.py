import pandas as pd
import requests

def get_all_kosdaq_data():
    """
    Naver Finance에서 KOSDAQ 상승률 페이지의 모든 종목 데이터를 스크래핑하고 정제하여 반환합니다.
    """
    url = "https://finance.naver.com/sise/sise_rise.naver?sosok=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tables = pd.read_html(response.content, encoding='euc-kr')
        
        df = None
        for table in tables:
            if '종목명' in table.columns:
                df = table
                break
        
        if df is None:
            return pd.DataFrame()

        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(how='all')
        df = df[df['종목명'].notna()]

        numeric_cols = ['현재가', '전일비', '등락률', '거래량', 'PER', 'ROE']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 불필요한 컬럼 제거
        df = df.drop(columns=['N', '전일비', '매수호가', '매도호가', '매수총잔량', '매도총잔량'])
        # 컬럼 순서 재정의
        df = df[['종목명', '현재가', '등락률', '거래량', 'PER', 'ROE']]

        return df.reset_index(drop=True)

    except Exception as e:
        print(f"데이터 처리 중 오류 발생: {e}")
        return pd.DataFrame()

def generate_sortable_html(df, filename="kosdaq_dashboard.html"):
    """
    DataFrame을 받아 정렬 가능한 HTML 파일로 생성합니다.
    """
    # DataFrame을 HTML 테이블로 변환
    table_html = df.to_html(table_id="stock_table", classes="sortable-table", index=False)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KOSDAQ 실시간 정렬 대시보드</title>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; }}
            h1 {{ text-align: center; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 0.9em;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            }}
            th, td {{
                padding: 12px 15px;
                border: 1px solid #dddddd;
                text-align: right;
            }}
            td:first-child, th:first-child {{
                text-align: left;
            }}
            thead tr {{
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }}
            th {{
                cursor: pointer;
                position: relative;
            }}
            th::after {{
                content: '';
                position: absolute;
                right: 10px;
                top: 50%;
                margin-top: -8px;
                border: 5px solid transparent;
            }}
            th.sort-asc::after {{
                border-bottom-color: #ffffff;
            }}
            th.sort-desc::after {{
                border-top-color: #ffffff;
            }}
            tbody tr:nth-of-type(even) {{
                background-color: #f3f3f3;
            }}
            tbody tr:hover {{
                background-color: #f1f1f1;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>KOSDAQ 상승률 순위 (클릭하여 정렬)</h1>
        {table_html}
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;

                const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
                    v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
                )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));

                document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {{
                    const table = th.closest('table');
                    const tbody = table.querySelector('tbody');
                    
                    // 정렬 상태 초기화
                    table.querySelectorAll('th').forEach(header => {{
                        if (header !== th) {{
                            header.classList.remove('sort-asc', 'sort-desc');
                        }}
                    }});

                    // 정렬 방향 결정
                    let asc = true;
                    if (th.classList.contains('sort-asc')) {{
                        asc = false;
                        th.classList.remove('sort-asc');
                        th.classList.add('sort-desc');
                    }} else {{
                        th.classList.remove('sort-desc');
                        th.classList.add('sort-asc');
                    }}
                    
                    Array.from(tbody.querySelectorAll('tr'))
                        .sort(comparer(Array.from(th.parentNode.children).indexOf(th), asc))
                        .forEach(tr => tbody.appendChild(tr));
                }})));
            }});
        </script>
    </body>
    </html>
    """

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"'{filename}' 파일이 성공적으로 생성되었습니다. 파일을 열어 확인해보세요.")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    kosdaq_df = get_all_kosdaq_data()
    if not kosdaq_df.empty:
        generate_sortable_html(kosdaq_df)

