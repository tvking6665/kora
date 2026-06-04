import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="미국 전종목 실시간 검색기", layout="wide")

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
    st.title("🇺🇸 미국 주식 마켓 실시간 급등 검색기")
with col2:
    if st.button("로그아웃 🔓"):
        st.session_state.logged_in = False
        st.rerun()

st.caption("야후 파이낸스 실시간 거래 지표를 추적하여 마켓에서 가장 강하게 움직이는 급등주를 발굴합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 모드 선택")
search_mode = st.sidebar.radio(
    "적용할 검색 조건을 선택하세요",
    ["① 거래량 급증", "② 대량 거래대금", "③ 당일 고상승률"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 세부 수치 설정")

volume_ratio = 400
min_turnover = 10
min_change = 8

if search_mode == "① 거래량 급증":
    volume_ratio = st.sidebar.slider("평균(5일) 대비 거래량 증가율 (%)", min_value=50, max_value=1000, value=400, step=50)
elif search_mode == "② 대량 거래대금":
    min_turnover = st.sidebar.number_input("최소 거래대금 조건 (백만 달러, $M)", min_value=0, value=10, step=2)
elif search_mode == "③ 당일 고상승률":
    min_change = st.sidebar.slider("당일 최소 상승률 조건 (%)", min_value=-10, max_value=30, value=8, step=1)

# 유동성이 집중된 미국 시장 핵심 성장주 및 S&P 500 마켓 가이드 풀 생성
@st.cache_data(ttl=60)
def get_comprehensive_tickers():
    hot_growth = {
        'PLTR': '팔란티어', 'SOUN': '사운드하운드 AI', 'BBAI': '빅베어 AI', 'AI': 'C3.ai', 'SMCI': '슈퍼마이크로',
        'MARA': '마라톤 디지털', 'RIOT': '라이엇 플랫폼즈', 'COIN': '코인베이스', 'HOOD': '로빈후드', 'CLSK': '클린스파크',
        'MSTR': '마이크로스트레티지', 'GME': '게임스탑', 'AMC': 'AMC 엔터', 'DJT': '트럼프 미디어', 'SOFI': '소파이',
        'UPST': '업스타트', 'AFRM': '어펌 홀딩스', 'RIVN': '리비안', 'LCID': '루시드 그룹', 'NIO': '니오', 'IONQ': '아이온큐',
        'OKLO': '오클로', 'RDDT': '레딧', 'DKNG': '드래프트킹즈', 'PLUG': '플러그 파워', 'ASTS': 'AST 스페이스모바일',
        'VKTX': '바이킹 테라퓨틱스', 'WULF': '테라울프', 'CIFR': '사이퍼 마이닝', 'XPEV': '샤오펑', 'LI': '리오토',
        'AAPL': '애플', 'MSFT': '마이크로소프트', 'NVDA': '엔비디아', 'TSLA': '테슬라', 'AMD': 'AMD', 'INTC': '인텔',
        'AMZN': '아마존', 'META': '메타', 'GOOGL': '구글 A', 'NFLX': '넷플릭스', 'SQ': '블록', 'PYPL': '페이팔'
    }
    return hot_growth

# 3. 데이터 수집 및 조건 필터링 가동
if st.sidebar.button("검색기 돌리기 🚀"):
    utc_now = datetime.now(timezone.utc)
    kst_now = utc_now + timedelta(hours=9)
    now_time = kst_now.strftime("%Y-%m-%d %H:%M:%S")
    
    with st.spinner(f"♻️ {now_time} 마켓 급등 섹터 트래킹 중..."):
        try:
            ticker_map = get_comprehensive_tickers()
            tickers_list = list(ticker_map.keys())
            
            # 주말 및 시차 보정을 위해 넉넉하게 최근 15일 히스토리 수집
            end_date = datetime.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=15)
            
            # 프리/포스트마켓 데이터가 완벽히 병합된 역사적 데이터셋 호출 (낮 시간 버그 완전 방어)
            group_data = yf.download(tickers_list, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), group_by='ticker', prepost=True)
            
            results = []
            
            for ticker in tickers_list:
                if ticker in group_data.columns.levels[0]:
                    df_stock = group_data[ticker].dropna()
                    
                    # 만약 장외 시간이라 오늘의 가 데이터가 생성 전이거나 변동이 0이라면 직전 완료 마감 거래일로 롤백
                    if len(df_stock) >= 3:
                        if df_stock['Volume'].iloc[-1] == 0 or (df_stock['Close'].iloc[-1] == df_stock['Close'].iloc[-2]):
                            df_stock = df_stock.iloc[:-1]
                            
                    if len(df_stock) >= 6:
                        latest_close = float(df_stock['Close'].iloc[-1])
                        prev_close = float(df_stock['Close'].iloc[-2])
                        latest_vol = float(df_stock['Volume'].iloc[-1])
                        
                        if latest_close < 1.0:
                            continue
                            
                        # 다른 증권 앱 화면과 완벽히 일치하는 등락률/거래대금 동적 계산
                        day_change_pct = round(((latest_close - prev_close) / prev_close) * 100, 2)
                        turnover_m = round((latest_close * latest_vol) / 1_000_000, 2)
                        five_day_avg_vol = df_stock['Volume'].iloc[-6:-1].mean()
                        vol_ratio_calc = round((latest_vol / five_day_avg_vol) * 100, 2) if five_day_avg_vol > 0 else 0
                        
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
                                '상승률': day_change_pct,
                                '거래대금': turnover_m,
                                '5일 평균 거래량': int(five_day_avg_vol),
                                '당일 거래량': int(latest_vol),
                                '거래량 증가율(%)': vol_ratio_calc
                            })
            
            if results:
                result_df = pd.DataFrame(results)
                
                if search_mode == "① 거래량 급증":
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False)
                elif search_mode == "② 대량 거래대금":
                    result_df = result_df.sort_values(by='거래대금', ascending=False)
                elif search_mode == "③ 당일 고상승률":
                    result_df = result_df.sort_values(by='상승률', ascending=False)
                    
                result_df = result_df.reset_index(drop=True)
                
                st.success(f"🎯 한국 시간 기준 {now_time} 스캔 완료! 만족하는 종목 {len(result_df)}개를 발굴했습니다.")
                
                display_df = result_df.copy()
                display_df['현재가 ($)'] = display_df['현재가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['상승률'] = display_df['상승률'].apply(lambda x: f"{x:+.2f}%")
                display_df['거래대금'] = display_df['거래대금'].apply(lambda x: f"${x:,.2f}M")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['당일 거래량'] = display_df['당일 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"현재 선택하신 조건({min_change}%) 이상으로 움직인 종목이 검색 풀 내에 없습니다. 수치를 조금 낮춘 후 재시도해 보세요!")
                
        except Exception as e:
            st.error(f"데이터 갱신 오류: {e}")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기]를 누르면 실시간 랭킹 정렬이 시작됩니다.")
