"""
KOSPI 영업이익 순위 Top 200 데이터를 wisereport에서 가져와 Excel로 저장
"""

import pandas as pd
import sys
from datetime import datetime


def fetch_top200():
    # sec_cd=STK: KOSPI만
    url = (
        "https://comp.wisereport.co.kr/ranking/mktExcel.aspx"
        "?sec_cd=STK&sch=1&fin_typ=0&cn=&menuType=MAIN"
        "&ordertyp=desc&ordercol=4&sec_nm=KOSPI"
    )

    dfs = pd.read_html(url, encoding="utf-8")
    df = dfs[2]
    df.columns = df.iloc[0]
    df = df.iloc[2:].reset_index(drop=True)

    df["종목명"] = df["기업명"].str.replace(r"\[\d+\]", "", regex=True)
    df["영업이익"] = pd.to_numeric(df["영업이익"], errors="coerce")
    df["매출액"] = pd.to_numeric(df["매출액"], errors="coerce")
    df["자산총계"] = pd.to_numeric(df["자산총계"], errors="coerce")
    df["당기순이익"] = pd.to_numeric(df["당기순이익"], errors="coerce")

    # 영업이익 내림차순 정렬 후 Top 200
    df_sorted = (
        df.sort_values("영업이익", ascending=False)
        .head(200)
        .reset_index(drop=True)
    )
    df_sorted.index = df_sorted.index + 1
    df_sorted.index.name = "순위"

    result = df_sorted[["종목명", "매출액", "영업이익", "당기순이익", "자산총계", "주재무제표"]]
    return result


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "top200_operating_profit_kospi.xlsx"

    print(f"KOSPI 영업이익 Top 200 데이터 수집 중...")
    df = fetch_top200()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="영업이익 Top200")

        # 메타 정보 시트
        meta = pd.DataFrame({
            "항목": ["데이터 기준", "시장", "정렬 기준", "단위", "생성 시각"],
            "값": ["최근결산기준", "KOSPI", "영업이익 내림차순", "억원", now],
        })
        meta.to_excel(writer, sheet_name="정보", index=False)

    print(f"저장 완료: {output}")
    print(f"Top 5:")
    print(df.head())


if __name__ == "__main__":
    main()
