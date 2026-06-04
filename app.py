import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 웹 페이지 레이아웃 설정
st.set_config = st.set_page_config(page_title="미국 전종목 프리마켓 검색기", layout="wide")

# ----------------- [로그인 시스템] -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 시스템 로그인")
    st.caption("프로그램을 사용하려면 관리자 계정으로 로그인해 주세요.")
    
    with st.form(key="login_form"):
        input_id = st.text_input("아이디(ID)", placeholder="아이디를 입력하세요")
        input_pw = st.text_input("비밀번호(PW)", type="password", placeholder="비밀번호를 입력하세요")
        submit_button = st.form_submit_button(label="로그인")
        
        if submit_button:
            if input_id == "관리자" and input_pw == "11111":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 일치하지 않습니다.")
    st.stop()

# ----------------- [메인 프로그램] -----------------
col1, col2 = st.columns([9, 1])
with col1:
    st.title("🇺🇸 미국 주식 전 종목 프리마켓 포함 검색기")
with col2:
    if st.button("로그아웃 🔓"):
        st.session_state.logged_in = False
        st.rerun()

st.caption("프리마켓(장전 외) 및 본장 데이터를 실시간으로 반영하여 조건에 맞는 급등주를 발굴합니다.")

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
    min_turnover = st.sidebar.number_input("최소 거래대금 조건 (백만 달러, $M)", min_value=0, value=50, step=10)
elif search_mode == "③ 당일 고상승률":
    min_change = st.sidebar.slider("당일 최소 상승률 조건 (%)", min_value=-10, max_value=30, value=8, step=1)

# 미국 시장 주요 활성 종목 풀 구성 (S&P 500 + 대표 테마 중소형주 약 540개)
@st.cache_data(ttl=60) # 실시간 데이터 반영을 위해 캐시 주기를 1분(60초)으로 대폭 축소
def get_all_us_tickers():
    try:
        ticker_df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        sp500 = {row['Symbol'].replace('.', '-'): row['Security'] for _, row in ticker_df.iterrows()}
        
        hot_growth = {
            'PLTR': '팔란티어', 'SOUN': '사운드하운드 AI', 'BBAI': '빅베어 AI', 'AI': 'C3.ai', 'SMCI': '슈퍼마이크로',
            'MARA': '마라톤 디지털', 'RIOT': '라이엇 플랫폼즈', 'COIN': '코인베이스', 'HOOD': '로빈후드', 'CLSK': '클린스파크',
            'MSTR': '마이크로스트레티지', 'GME': '게임스탑', 'AMC': 'AMC 엔터', 'DJT': '트럼프 미디어', 'SOFI': '소파이',
            'UPST': '업스타트', 'AFRM': '어펌 홀딩스', 'RIVN': '리비안', 'LCID': '루시드 그룹', 'NIO': '니오', 'IONQ': '아이온큐',
            'OKLO': '오클로', 'RDDT': '레딧', 'DKNG': '드래프트킹즈', 'PLUG': '플러그 파워', 'ASTS': 'AST 스페이스모바일',
            'VKTX': '바이킹 테라퓨틱스', 'WULF': '테라울프', 'CIFR': '사이퍼 마이닝', 'XPEV': '샤오펑', 'LI': '리오토'
        }
        return {**sp500, **hot_growth}
    except:
        return {'AAPL': '애플', 'MSFT': '마이크로소프트', 'NVDA': '엔비디아', 'TSLA': '테슬라', 'PLTR': '팔란티어'}

# 3. 데이터 수집 및 조건 필터링 가동
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner(f"♻️ 프리마켓 포함 실시간 마켓 스캔 중..."):
        try:
            ticker_map = get_all_us_tickers()
            tickers = list(ticker_map.keys())
            
            end_date = datetime.today() + timedelta(days=1) # 안전하게 내일까지 지정
            start_date = end_date - timedelta(days=15)
            
            # [핵심 노하우] prepost=True 옵션을 넣어 프리마켓/애프터마켓 가격을 통째로 가져옵니다!
            group_data = yf.download(
                tickers, 
                start=start_date.strftime("%Y-%m-%d"), 
                end=end_date.strftime("%Y-%m-%d"), 
                group_by='ticker',
                prepost=True
            )
            
            results = []
            
            for ticker in tickers:
                if ticker in group_data.columns.levels[0]:
                    df_stock = group_data[ticker].dropna()
                    
                    if len(df_stock) >= 6:
                        # 가장 최근 줄 데이터 (프리마켓 진행 중일 때는 프리마켓의 실시간 변동 가격이 들어옴)
                        latest_close = float(df_stock['Close'].iloc[-1])
                        prev_close = float(df_stock['Close'].iloc[-2])
                        latest_vol = float(df_stock['Volume'].iloc[-1])
                        latest_date = df_stock.index[-1].strftime("%Y-%m-%d %H:%M")
                        
                        if latest_close < 1.0: # 1달러 미만 제외
                            continue
                            
                        # 실시간 지표 연산
                        day_change_pct = round(((latest_close - prev_close) / prev_close) * 100, 2)
                        turnover_m = round((latest_close * latest_vol) / 1_000_000, 2)
                        five_day_avg_vol = df_stock['Volume'].iloc[-6:-1].mean()
                        vol_ratio_calc = round((latest_vol / five_day_avg_vol) * 100, 2) if five_day_avg_vol > 0 else 0
                        
                        # 조건 단독 검사
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
                                '현재가 ($)': latest_close,
                                '실시간 상승률': day_change_pct,
                                '당일 거래대금': turnover_m,
                                '5일 평균 거래량': int(five_day_avg_vol),
                                '실시간 거래량': int(latest_vol),
                                '거래량 증가율(%)': vol_ratio_calc
                            })
            
            # 결과 출력
            if results:
                result_df = pd.DataFrame(results)
                
                if search_mode == "① 거래량 급증":
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False)
                elif search_mode == "② 대량 거래대금":
                    result_df = result_df.sort_values(by='당일 거래대금', ascending=False)
                elif search_mode == "③ 당일 고상승률":
                    result_df = result_df.sort_values(by='실시간 상승률', ascending=False)
                    
                result_df = result_df.reset_index(drop=True)
                
                st.success(f"🎯 실시간 데이터 기준, [{search_mode}] 조건을 만족하는 종목 {len(result_df)}개를 찾았습니다!")
                
                display_df = result_df.copy()
                display_df['현재가 ($)'] = display_df['현재가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['실시간 상승률'] = display_df['실시간 상승률'].apply(lambda x: f"{x:+.2f}%")
                display_df['당일 거래대금'] = display_df['당일 거래대금'].apply(lambda x: f"${x:,.2f}M")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['실시간 거래량'] = display_df['실시간 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"조회 시점 기준, 설정하신 {min_change}% 조건 이상으로 움직이는 종목이 검색 풀 내에 없습니다.")
                
        except Exception as e:
            st.error(f"데이터 처리 오류: {e}")
else:
    st.info("왼쪽 사이드바에서 원하는 조건을 세팅하고 버튼을 누르면 프리마켓 포함 실시간 스캔이 시작됩니다.")
