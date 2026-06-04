import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="미장 급등 테마주 검색기", layout="wide")

# ----------------- [로그인 시스템 구현] -----------------
# 로그인 상태를 저장할 세션 상태(session_state) 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 로그인 전 화면 구성
if not st.session_state.logged_in:
    st.title("🔒 시스템 로그인")
    st.caption("프로그램을 사용하려면 관리자 계정으로 로그인해 주세요.")
    
    # 로그인 폼 생성
    with st.form(key="login_form"):
        input_id = st.text_input("아이디(ID)", placeholder="아이디를 입력하세요")
        input_pw = st.text_input("비밀번호(PW)", type="password", placeholder="비밀번호를 입력하세요")
        submit_button = st.form_submit_button(label="로그인")
        
        if submit_button:
            # 지정된 ID와 PW 검증 (요청사항: 관리자 / 11111)
            if input_id == "관리자" and input_pw == "11111":
                st.session_state.logged_in = True
                st.rerun() # 로그인 성공 시 화면 즉시 새로고침
            else:
                st.error("❌ 아이디 또는 비밀번호가 일치하지 않습니다.")
                
    st.stop() # 로그인이 안 되었으면 아래 메인 프로그램 코드는 실행하지 않고 중단

# ----------------- [로그인 성공 후 메인 프로그램] -----------------

# 상단에 로그아웃 버튼 배치
col1, col2 = st.columns([9, 1])
with col1:
    st.title("🇺🇸 미국 주식 급등·테마 중소형주 검색기")
with col2:
    if st.button("로그아웃 🔓"):
        st.session_state.logged_in = False
        st.rerun()

st.caption("변동성이 크고 거래량이 자주 폭발하는 미국 시장의 핫한 성장주 및 테마주를 검색합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 모드 선택")

search_mode = st.sidebar.radio(
    "적용할 검색 조건을 선택하세요",
    ["① 거래량 급증", "② 대량 거래대금", "③ 당일 고상승률"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 세부 수치 설정")

if search_mode == "① 거래량 급증":
    volume_ratio = st.sidebar.slider("평균(5일) 대비 거래량 증가율 (%)", min_value=50, max_value=1000, value=300, step=50)
elif search_mode == "② 대량 거래대금":
    min_turnover = st.sidebar.number_input("최소 거래대금 조건 (백만 달러, $M)", min_value=0, value=5, step=1)
elif search_mode == "③ 당일 고상승률":
    min_change = st.sidebar.slider("당일 최소 상승률 조건 (%)", min_value=-10, max_value=30, value=5, step=1)

# [핵심 변경] 미국 중소형 테마주 80종목의 이름을 직관적인 '한글명'으로 전면 변환
@st.cache_data
def get_speculative_tickers_kr():
    stock_dict_kr = {
        # AI / 반도체 / 데이터 성장주
        'PLTR': '팔란티어 테크놀로지스', 'SOUN': '사운드하운드 AI', 'BBAI': '빅베어 AI',
        'AI': 'C3.ai', 'SMCI': '슈퍼마이크로컴퓨터', 'ARM': '암 홀딩스',
        'ASTS': 'AST 스페이스모바일', 'VKTX': '바이킹 테라퓨틱스',
        
        # 가상자산 / 블록체인 테마주
        'MARA': '마라톤 디지털', 'RIOT': '라이엇 플랫폼즈', 'COIN': '코인베이스 글로벌',
        'HOOD': '로빈후드 마켓츠', 'CLSK': '클린스파크', 'WULF': '테라울프',
        'MSTR': '마이크로스트레티지', 'CIFR': '사이퍼 마이닝', 'CAN': '카나안',
        
        # 밈주식 / 유동성 대장주 / 정치 테마
        'GME': '게임스탑', 'AMC': 'AMC 엔터테인먼트', 'DJT': '트럼프 미디어(트루소셜)',
        'SPCE': '버진 갤럭틱',
        
        # 핀테크 / 중소형 금융
        'SOFI': '소파이 테크놀로지스', 'UPST': '업스타트 홀딩스', 'AFRM': '어펌 홀딩스',
        'NU': '누 홀딩스',
        
        # 전기차 / 에너지 / 우주 테마주
        'RIVN': '리비안 오토모티브', 'LCID': '루시드 그룹', 'NIO': '니오 (나스닥 ADR)',
        'XPEV': '샤오펑', 'LI': '리오토', 'FCEL': '퓨얼셀 에너지',
        'PLUG': '플러그 파워', 'BLNK': '블링크 차징', 'CHPT': '차지포인트 홀딩스',
        'RGTI': '리게티 컴퓨팅', 'IONQ': '아이온큐', 'OKLO': '오클로(샘알트만 원전)',
        
        # 바이오 / 헬스케어 중소형주
        'CRSP': '크리스퍼 테라퓨틱스', 'BEAM': '빔 테라퓨틱스', 'NTLA': '인텔리아 테라퓨틱스',
        'IBRX': '이뮤니티바이오', 'GERN': '게론', 'ACHV': '어치브 라이프사이언스',
        
        # 이커머스 / 플랫폼 / 미디어 성장주
        'TEM': '템퍼스 AI', 'RDDT': '레딧', 'DKNG': '드래프트킹즈', 
        'PINS': '핀터레스트', 'SNAP': '스냅(스냅챗)', 'ROKU': '로쿠', 
        'ETSY': '엣시', 'SHOP': '쇼피파이', 'JMIA': '주미아 테크놀로지스', 
        'SE': '씨 리미티드', 'MELI': '메르카도리브레'
    }
    return stock_dict_kr

# 3. 데이터 수집 및 조건 필터링 가동
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner(f"🔥 한글화된 미국 테마주 데이터 분석 중..."):
        try:
            ticker_map = get_speculative_tickers_kr()
            tickers = list(ticker_map.keys())
            
            end_date = datetime.today()
            start_date = end_date - timedelta(days=15)
            
            # 데이터 다운로드
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
                        
                        # 1달러 미만 동전주 필터링
                        if latest_close < 1.0:
                            continue
                            
                        # 수치 계산
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
                                '종목명': ticker_map.get(ticker, ticker), # 변환된 한글 종목명 주입
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
                
                st.success(f"🎯 미국 마감일({latest_date}) 기준, [{search_mode}] 조건을 충족하는 핫한 종목 {len(result_df)}개를 발굴했습니다!")
                
                # 가독성 포맷팅 정리
                display_df = result_df.copy()
                display_df['종가 ($)'] = display_df['종가 ($)'].apply(lambda x: f"${x:,.2f}")
                display_df['당일 상승률'] = display_df['당일 상승률'].apply(lambda x: f"{x:+.2f}%")
                display_df['당일 거래대금'] = display_df['당일 거래대금'].apply(lambda x: f"${x:,.2f}M")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['최근일 거래량'] = display_df['최근일 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"선택하신 [{search_mode}] 조건에 만족하는 테마주가 현재 마켓에 없습니다. 세부 수치를 조절해 보세요!")
                
        except Exception as e:
            st.error(f"데이터를 처리하는 중 에러가 발생했습니다: {e}")
else:
    st.info("왼쪽 사이드바에서 원하는 검색 조건을 선택하고 [검색기 돌리기] 버튼을 눌러주세요.")
