# 주식 분석 대시보드 🚀

외국인/기관 순매수 정보와 펀더멘탈 분석을 제공하는 자동화된 주식 대시보드입니다.

## 📊 라이브 대시보드

**GitHub Pages에서 확인하기:** [대시보드 보러가기](https://yelerty.github.io/gethighlight/)

매일 오전 8시 45분에 자동으로 업데이트됩니다.

## 🔧 주요 기능

### 1. 시장 현황
- 코스피, 코스닥 지수
- 나스닥 100 선물, S&P 500 선물
- VIX 공포지수

### 2. 오늘의 순매수 상위 종목
- 외국인/기관 순매수 상위 20개 종목

### 3. 어제 순매수 종목의 오늘 등락률
- 평균 수익률 분석

### 4. N일 연속 순매수 종목 펀더멘탈 분석
- PER, PBR, ROE 지표 기반 필터링
- 점수 시스템으로 종목 평가

## 📁 프로젝트 구조

```
├── unified_dashboard.py          # 콘솔용 통합 대시보드
├── unified_dashboard_html.py     # HTML 생성용 대시보드
├── find_stocks.py               # N일 연속 순매수 종목 분석
├── backtest.py                  # 어제 순매수 종목 등락률 분석
├── get_stock_names.py           # 순매수 상위 종목 리스트
├── market_dashboard.py          # 시장 지수 현황
└── docs/
    └── index.html               # GitHub Pages용 HTML (자동 생성)
```

## 🚀 사용 방법

### 콘솔에서 바로 확인

```bash
# 기본 실행 (코스피 외국인 2일 연속)
python unified_dashboard.py

# 코스닥 시장 분석
python unified_dashboard.py --market kosdaq

# 기관 투자자 분석
python unified_dashboard.py --investor institution

# 3일 연속 순매수 분석
python unified_dashboard.py --days 3
```

### HTML 파일 생성

```bash
# GitHub Pages용 HTML 생성
python unified_dashboard_html.py

# 다른 경로에 저장
python unified_dashboard_html.py --output output.html

# 옵션 조합
python unified_dashboard_html.py --market kosdaq --investor institution --days 3
```

## 🛠️ 설치

```bash
pip install requests beautifulsoup4 pandas FinanceDataReader yfinance
```

## 📅 자동 업데이트

GitHub Actions를 통해 매일 오전 8시 45분에 자동으로 실행됩니다.
- `.github/workflows/daily-update.yml` 참조

## ⚙️ GitHub Pages 설정 방법

1. GitHub 저장소 → **Settings** 이동
2. 왼쪽 메뉴에서 **Pages** 선택
3. **Source** 섹션에서:
   - Branch: `main` 선택
   - Folder: `/docs` 선택
   - **Save** 클릭
4. 몇 분 후 `https://[username].github.io/[repository-name]/`에서 확인 가능

## 📊 데이터 출처

- Naver Finance
- FinanceDataReader
- yfinance

## 🔒 주의사항

- 이 도구는 투자 참고용이며, 투자 결정의 책임은 본인에게 있습니다.
- 실시간 데이터가 아닌 거래일 종료 후 데이터를 기반으로 합니다.
- 네이버 금융 데이터 수집 정책을 준수합니다.

## 📝 라이선스

MIT License

---

**Made with ❤️ for Korean Stock Market Investors**
