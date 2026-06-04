import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="미장 5일 평균 거래량 급증 검색기", layout="wide")
st.title("🇺🇸 미국 주식 일주일 평균 거래량 급증 검색기")
st.caption("대표 우량 종목 중 최근 5영업일 평균 거래량 대비 직전 거래일 거래량이 급증한 종목을 검색합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 조건 설정")
volume_ratio = st.sidebar.slider("평균 대비 거래량 증가율 조건 (%)", min_value=100, max_value=1000, value=300, step=50)

# [403 에러 해결책] 위키피디아 크롤링 대신 대표 티커 목록과 기업명을 직접 내장 (차단 가능성 0%)
@st.cache_data
def get_us_tickers():
    stock_dict = {
        'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corporation', 'GOOGL': 'Alphabet Inc. (Class A)',
        'AMZN': 'Amazon.com Inc.', 'NVDA': 'NVIDIA Corporation', 'META': 'Meta Platforms Inc.',
        'TSLA': 'Tesla Inc.', 'BRK-B': 'Berkshire Hathaway Inc.', 'LLY': 'Eli Lilly and Company',
        'AVGO': 'Broadcom Inc.', 'V': 'Visa Inc.', 'JPM': 'JPMorgan Chase & Co.',
        'UNH': 'UnitedHealth Group Inc.', 'MA': 'Mastercard Inc.', 'XOM': 'Exxon Mobil Corporation',
        'JNJ': 'Johnson & Johnson', 'HD': 'Home Depot Inc.', 'PG': 'Procter & Gamble Co.',
        'COST': 'Costco Wholesale Corp.', 'AMD': 'Advanced Micro Devices Inc.', 'NFLX': 'Netflix Inc.',
        'CRM': 'Salesforce Inc.', 'ADBE': 'Adobe Inc.', 'CVX': 'Chevron Corporation',
        'WMT': 'Walmart Inc.', 'MRK': 'Merck & Co. Inc.', 'BAC': 'Bank of America Corp.',
        'PEP': 'PepsiCo Inc.', 'KO': 'Coca-Cola Company', 'TSM': 'Taiwan Semiconductor (ADR)',
        'ASML': 'ASML Holding (ADR)', 'NVO': 'Novo Nordisk (ADR)', 'TM': 'Toyota Motor (ADR)',
        'AZN': 'AstraZeneca (ADR)', 'SAP': 'SAP SE (ADR)', 'NVS': 'Novartis AG (ADR)',
        'HDB': 'HDFC Bank (ADR)', 'BABA': 'Alibaba Group (ADR)', 'FMC': 'FMC Corporation',
        'DIS': 'Walt Disney Co.', 'CSCO': 'Cisco Systems Inc.', 'INTC': 'Intel Corporation',
        'VZ': 'Verizon Communications', 'CMCSA': 'Comcast Corp.', 'NKE': 'NIKE Inc.',
        'PFE': 'Pfizer Inc.', 'T': 'AT&T Inc.', 'QCOM': 'Qualcomm Inc.',
        'TXN': 'Texas Instruments Inc.', 'MCD': 'McDonald Corp.', 'CAT': 'Caterpillar Inc.',
        'GE': 'General Electric Co.', 'HON': 'Honeywell International Inc.', 'AXP': 'American Express Co.',
        'IBM': 'IBM Corporation', 'LOW': 'Lowe Companies Inc.', 'SBUX': 'Starbucks Corp.',
        'BA': 'Boeing Company', 'DE': 'Deere & Company', 'LMT': 'Lockheed Martin Corp.',
        'UPS': 'United Parcel Service', 'GEV': 'GE Vernova Inc.', 'MU': 'Micron Technology',
        'PANW': 'Palo Alto Networks', 'SNPS': 'Synopsys Inc.', 'CDNS': 'Cadence Design Systems',
        'PLTR': 'Palantir Technologies', 'SMCI': 'Super Micro Computer', 'UBER': 'Uber Technologies',
        'BX': 'Blackstone Inc.', 'SQ': 'Block Inc.', 'PYPL': 'PayPal Holdings',
        'COIN': 'Coinbase Global', 'HOOD': 'Robinhood Markets', 'MARA': 'Marathon Digital',
        'RIOT': 'Riot Platforms', 'SOFI': 'SoFi Technologies', 'U': 'Unity Software',
        'DISH': 'Dish Network', 'RIVN': 'Rivian Automotive', 'LCID': 'Lucid Group'
    }
    return stock_dict

# 3. 데이터 수집 버튼
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner("미국 주요 우량 종목의 최근 일주일 거래량 분석 중... 잠시만 기다려주세요."):
        try:
            ticker_map = get_us_tickers()
            tickers = list(ticker_map.keys())
            
            # yfinance를 이용해 데이터 일괄 다운로드 (야후 파이낸스는 403 차단이 없음)
            end_date = datetime.today()
            start_date = end_date - timedelta(days=15)
            
            group_data = yf.download(tickers, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), group_by='ticker')
            
            results = []
            
            # 다운로드된 데이터 분석
            for ticker in tickers:
                if ticker in group_data.columns.levels[0]:
                    df_stock = group_data[ticker].dropna()
                    
                    # 최소 6일 이상의 데이터가 있어야 5일 평균과 최근일 비교 가능
                    if len(df_stock) >= 6:
                        # 가장 최근 거래일 데이터
                        latest_day_vol = df_stock['Volume'].iloc[-1]
                        latest_day_close = df_stock['Close'].iloc[-1]
                        latest_date = df_stock.index[-1].strftime("%Y-%m-%d")
                        
                        # 직전 5영업일의 거래량 평균 계산
                        five_day_avg_vol = df_stock['Volume'].iloc[-6:-1].mean()
                        
                        if five_day_avg_vol > 0:
                            ratio = round((latest_day_vol / five_day_avg_vol) * 100, 2)
                            
                            # 조건 충족 시 결과 담기
                            if ratio >= volume_ratio:
                                results.append({
                                    '종목명': ticker_map.get(ticker, ticker),
                                    '티커(Ticker)': ticker,
                                    '종가 ($)': round(float(latest_day_close), 2),
                                    '5일 평균 거래량': int(five_day_avg_vol),
                                    '최근일 거래량': int(latest_day_vol),
                                    '평균대비 증가율(%)': ratio
                                })
            
            # 결과 시각화
            if results:
                result_df = pd.DataFrame(results)
                result_df = result_df.sort_values(by='평균대비 증가율(%)', ascending=False).reset_index(drop=True)
                
                st.success(f"🔥 미국 마감일({latest_date}) 기준, 5일 평균 대비 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                
                # 천 단위 콤마 포맷팅
                display_df = result_df.copy()
                display_df['종가 ($)'] = display_df['종가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['최근일 거래량'] = display_df['최근일 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"조회는 정상 완료되었으나, 설정하신 조건({volume_ratio}%) 이상으로 거래량이 급증한 종목이 현재 마켓에 없습니다.")
                
        except Exception as e:
            st.error(f"데이터를 처리하는 중 에러가 발생했습니다: {e}")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
