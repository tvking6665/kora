import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="미장 선택형 조건 검색기", layout="wide")
st.title("🇺🇸 미국 주식 맞춤형 단일 조건 검색기")
st.caption("원하는 검색 조건을 하나만 선택하여 해당하는 미국 우량 종목을 빠르게 찾아냅니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 모드 선택")

search_mode = st.sidebar.radio(
    "적용할 검색 조건을 선택하세요",
    ["① 거래량 급증", "② 대량 거래대금", "③ 당일 고상승률"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 세부 수치 설정")

if search_mode == "① 거래량 급증":
    volume_ratio = st.sidebar.slider("평균(5일) 대비 거래량 증가율 (%)", min_value=50, max_value=1000, value=400, step=50)
elif search_mode == "② 대량 거래대금":
    min_turnover = st.sidebar.number_input("최소 거래대금 조건 (백만 달러, $M)", min_value=0, value=100, step=10)
elif search_mode == "③ 당일 고상승률":
    min_change = st.sidebar.slider("당일 최소 상승률 조건 (%)", min_value=-10, max_value=30, value=3, step=1)

# 미국 주요 우량 종목 리스트 내장
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
        'HDB': 'HDFC Bank (ADR)', 'BABA': 'Alibaba Group (ADR)', 'DIS': 'Walt Disney Co.', 
        'CSCO': 'Cisco Systems Inc.', 'INTC': 'Intel Corporation', 'VZ': 'Verizon Communications', 
        'CMCSA': 'Comcast Corp.', 'NKE': 'NIKE Inc.', 'PFE': 'Pfizer Inc.', 'T': 'AT&T Inc.', 
        'QCOM': 'Qualcomm Inc.', 'TXN': 'Texas Instruments Inc.', 'MCD': 'McDonald Corp.', 
        'CAT': 'Caterpillar Inc.', 'GE': 'General Electric Co.', 'HON': 'Honeywell International Inc.', 
        'AXP': 'American Express Co.', 'IBM': 'IBM Corporation', 'LOW': 'Lowe Companies Inc.', 
        'SBUX': 'Starbucks Corp.', 'BA': 'Boeing Company', 'DE': 'Deere & Company', 
        'LMT': 'Lockheed Martin Corp.', 'UPS': 'United Parcel Service', 'GEV': 'GE Vernova Inc.', 
        'MU': 'Micron Technology', 'PANW': 'Palo Alto Networks', 'SNPS': 'Synopsys Inc.', 
        'CDNS': 'Cadence Design Systems', 'PLTR': 'Palantir Technologies', 'SMCI': 'Super Micro Computer', 
        'UBER': 'Uber Technologies', 'BX': 'Blackstone Inc.', 'SQ': 'Block Inc.', 'PYPL': 'PayPal Holdings',
        'COIN': 'Coinbase Global', 'HOOD': 'Robinhood Markets', 'MARA': 'Marathon Digital',
        'RIOT': 'Riot Platforms', 'SOFI': 'SoFi Technologies', 'U': 'Unity Software',
        'RIVN': 'Rivian Automotive', 'LCID': 'Lucid Group'
    }
    return stock_dict

# 3. 데이터 수집 및 버튼 클릭 시 동작
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner(f"[{search_mode}] 조건 설정에 맞춰 종목 분석 중..."):
        try:
            ticker_map = get_us_tickers()
            tickers = list(ticker_map.keys())
            
            end_date = datetime.today()
            start_date = end_date - timedelta(days=15)
            
            group_data = yf.download(tickers, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), group_by='ticker')
            
            results = []
            
            for ticker in tickers:
                if ticker in group_data.columns.levels[0]:
                    df_stock = group_data[ticker].dropna()
                    
                    if len(df_stock) >= 6:
                        latest_close = float(df_stock['Close'].iloc[-1])
                        prev_close = float(df_stock['Close'].iloc[-2])
                        latest_vol = float(df_stock['Volume'].iloc[-1])
                        latest_date = df_stock.index[-1].strftime("%Y-%m-%d")
                        
                        # 지표 계산
                        day_change_pct = round(((latest_close - prev_close) / prev_close) * 100, 2)
                        turnover_m = round((latest_close * latest_vol) / 1_000_000, 2)
                        five_day_avg_vol = df_stock['Volume'].iloc[-6:-1].mean()
                        vol_ratio_calc = round((latest_vol / five_day_avg_vol) * 100, 2) if five_day_avg_vol > 0 else 0
                        
                        # 조건 검사
                        is_match = False
                        if search_mode == "① 거래량 급증" and vol_ratio_calc >= volume_ratio:
                            is_match = True
                        elif search_mode == "② 대량 거래대금" and turnover_m >= min_turnover:
                            is_match = True
                        elif search_mode == "③ 당일 고상승률" and day_change_pct >= min_change:
                            is_match = True
                            
                        if is_match:
                            results.append({
                                '종목명': ticker_map.get(ticker, ticker),
                                '티커(Ticker)': ticker,
                                '종가 ($)': latest_close,
                                '당일 상승률': day_change_pct,
                                '당일 거래대금': turnover_m,
                                '5일 평균 거래량': int(five_day_avg_vol),
                                '최근일 거래량': int(latest_vol),
                                '거래량 증가율(%)': vol_ratio_calc
                            })
            
            # 결과 시각화
            if results:
                result_df = pd.DataFrame(results)
                
                # 정렬 처리
                if search_mode == "① 거래량 급증":
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False)
                elif search_mode == "② 대량 거래대금":
                    result_df = result_df.sort_values(by='당일 거래대금', ascending=False)
                elif search_mode == "③ 당일 고상승률":
                    result_df = result_df.sort_values(by='당일 상승률', ascending=False)
                    
                result_df = result_df.reset_index(drop=True)
                
                st.success(f"🔥 미국 마감일({latest_date}) 기준, [{search_mode}] 조건을 만족하는 종목 {len(result_df)}개를 찾았습니다!")
                
                # [오타 수정 완료] 가독성을 위한 포맷팅 정리 ($export 버그 제거)
                display_df = result_df.copy()
                display_df['종가 ($)'] = display_df['종가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['당일 상승률'] = display_df['당일 상승률'].apply(lambda x: f"{x:+.2f}%")
                display_df['당일 거래대금'] = display_df['당일 거래대금'].apply(lambda x: f"${x:,.2f}M")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['최근일 거래량'] = display_df['최근일 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"선택하신 [{search_mode}] 조건을 만족하는 종목이 현재 마켓에 없습니다. 수치를 조금 조절해 보세요!")
                
        except Exception as e:
            st.error(f"데이터를 처리하는 중 에러가 발생했습니다: {e}")
else:
    st.info("왼쪽 사이드바에서 원하시는 '검색 모드'를 선택한 후 [검색기 돌리기] 버튼을 눌러주세요.")
