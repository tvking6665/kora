import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

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
    st.title("🇺🇸 미국 주식 현재 시점 실시간 검색기")
with col2:
    if st.button("로그아웃 🔓"):
        st.session_state.logged_in = False
        st.rerun()

st.caption("과거 데이터가 아닌 현재 조회 버튼을 누른 시점의 실시간 프리마켓/정규장 가격을 추적합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 모드 선택")
search_mode = st.sidebar.radio(
    "적용할 검색 조건을 선택하세요",
    ["① 거래량 급증", "② 대량 거래대금", "③ 당일 고상승률"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 세부 수치 설정")

# [에러 해결] 어떤 모드를 고르든 기본값을 미리 할당해두어 변수 미정의(NameError)를 완벽히 차단합니다.
volume_ratio = 400
min_turnover = 10
min_change = 8

if search_mode == "① 거래량 급증":
    volume_ratio = st.sidebar.slider("평균(5일) 대비 거래량 증가율 (%)", min_value=50, max_value=1000, value=400, step=50)
elif search_mode == "② 대량 거래대금":
    min_turnover = st.sidebar.number_input("최소 거래대금 조건 (백만 달러, $M)", min_value=0, value=10, step=2)
elif search_mode == "③ 당일 고상승률":
    min_change = st.sidebar.slider("당일 최소 상승률 조건 (%)", min_value=-10, max_value=30, value=8, step=1)

# 미국 시장 주요 활성 종목 풀 구성 (속도를 위해 주력 테마 성장주 타겟팅)
@st.cache_data(ttl=3600)
def get_all_us_tickers():
    hot_growth = {
        'PLTR': '팔란티어 테크놀로지스', 'SOUN': '사운드하운드 AI', 'BBAI': '빅베어 AI', 'AI': 'C3.ai', 'SMCI': '슈퍼마이크로컴퓨터',
        'MARA': '마라톤 디지털', 'RIOT': '라이엇 플랫폼즈', 'COIN': '코인베이스', 'HOOD': '로빈후드 마켓츠', 'CLSK': '클린스파크',
        'MSTR': '마이크로스트레티지', 'GME': '게임스탑', 'AMC': 'AMC 엔터테인먼트', 'DJT': '트럼프 미디어', 'SOFI': '소파이 테크놀로지스',
        'UPST': '업스타트 홀딩스', 'AFRM': '어펌 홀딩스', 'RIVN': '리비안 오토모티브', 'LCID': '루시드 그룹', 'NIO': '니오', 'IONQ': '아이온큐',
        'OKLO': '오클로', 'RDDT': '레딧', 'DKNG': '드래프트킹즈', 'PLUG': '플러그 파워', 'ASTS': 'AST 스페이스모바일',
        'VKTX': '바이킹 테라퓨틱스', 'WULF': '테라울프', 'CIFR': '사이퍼 마이닝', 'XPEV': '샤오펑', 'LI': '리오토',
        'AAPL': '애플', 'MSFT': '마이크로소프트', 'NVDA': '엔비디아', 'TSLA': '테슬라', 'AMD': 'AMD', 'INTC': '인텔',
        'AMZN': '아마존', 'META': '메타 플랫폼스', 'GOOGL': '알파벳 A', 'NFLX': '넷플릭스'
    }
    return hot_growth

# 3. 데이터 수집 및 조건 필터링 가동
if st.sidebar.button("검색기 돌리기 🚀"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner(f"♻️ {now_time} 현재 시점 실시간 가격 정보 스캔 중..."):
        try:
            ticker_map = get_all_us_tickers()
            tickers_list = list(ticker_map.keys())
            
            tickers_obj = yf.Tickers(' '.join(tickers_list))
            results = []
            
            for ticker in tickers_list:
                try:
                    info = tickers_obj.tickers[ticker].info
                    
                    # 실시간 현재가 추출 (프리마켓 호가 연동)
                    current_price = info.get('preMarketPrice') or info.get('currentPrice') or info.get('regularMarketPrice')
                    prev_close = info.get('previousClose')
                    current_vol = info.get('regularMarketVolume') or info.get('volume', 0)
                    
                    if not current_price or not prev_close:
                        continue
                        
                    if current_price < 1.0: # 동전주 제외
                        continue

                    # 지표 계산
                    day_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)
                    turnover_m = round((current_price * current_vol) / 1_000_000, 2)
                    five_day_avg_vol = info.get('averageVolume') or info.get('averageVolume10days', 1)
                    vol_ratio_calc = round((current_vol / five_day_avg_vol) * 100, 2) if five_day_avg_vol > 0 else 0
                    
                    # 단일 선택 조건 매칭
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
                            '현재가 ($)': current_price,
                            '실시간 상승률': day_change_pct,
                            '실시간 거래대금': turnover_m,
                            '평균 거래량': int(five_day_avg_vol),
                            '실시간 거래량': int(current_vol),
                            '거래량 증가율(%)': vol_ratio_calc
                        })
                except:
                    continue
                    
            if results:
                result_df = pd.DataFrame(results)
                
                if search_mode == "① 거래량 급증":
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False)
                elif search_mode == "② 대량 거래대금":
                    result_df = result_df.sort_values(by='실시간 거래대금', ascending=False)
                elif search_mode == "③ 당일 고상승률":
                    result_df = result_df.sort_values(by='실시간 상승률', ascending=False)
                    
                result_df = result_df.reset_index(drop=True)
                
                st.success(f"🎯 조회 시점({now_time}) 기준, 실시간 [{search_mode}] 조건을 만족하는 종목 {len(result_df)}개를 찾았습니다!")
                
                display_df = result_df.copy()
                display_df['현재가 ($)'] = display_df['현재가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['실시간 상승률'] = display_df['실시간 상승률'].apply(lambda x: f"{x:+.2f}%")
                display_df['실시간 거래대금'] = display_df['실시간 거래대금'].apply(lambda x: f"${x:,.2f}M")
                display_df['평균 거래량'] = display_df['평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['실시간 거래량'] = display_df['실시간 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"현재 실시간 마켓에 선택하신 조건을 충족하는 종목이 없습니다. 수치를 조절하거나 시장 개장 상태를 확인해 주세요.")
                
        except Exception as e:
            st.error(f"실시간 데이터 수집 오류: {e}")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기]를 누르면 현재 초 단위의 실시간 데이터 검색이 실행됩니다.")
