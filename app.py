import streamlit as st
from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="국장 거래량 급증 검색기", layout="wide")
st.title("📈 한국 주식 거래량 급증 검색기")
st.caption("현재 날짜 기준으로 최근 영업일 대비 거래량이 급증한 종목을 검색합니다.")

# 2. 사이드바 설정 (조건 조절용)
st.sidebar.header("🔍 검색 조건 설정")
volume_ratio = st.sidebar.slider("거래량 증가율 조건 (%)", min_value=100, max_value=1000, value=300, step=50)

# 3. 데이터 수집 버튼
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner("현재 날짜 기준 전 종목 데이터 조회 중... 잠시만 기다려주세요."):
        try:
            # 현재 시점 기준 날짜 계산 (안전하게 최근 10일치 범위를 잡음)
            today = datetime.today()
            start_date = (today - timedelta(days=10)).strftime("%Y%m%d")
            end_date = today.strftime("%Y%m%d")
            
            # [핵심 변경] 크롤링 에러가 잦은 함수 대신, 가장 안정적인 KRX 등락률 함수 사용!
            # 이 함수는 시장 전체의 기간 내 시세 변동 및 거래량 데이터를 한 번에 가져옵니다.
            df = stock.get_market_price_change_by_ticker(start_date, end_date, market="ALL")
            
            if df.empty:
                st.warning("⚠️ 데이터를 가져오지 못했습니다. 주말이거나 거래소 서버가 응답하지 않는 시간대일 수 있습니다.")
            else:
                # KRX 등락률 데이터에는 '거래량'이 아닌 '거래량' 합산 데이터 등이 들어있으므로 
                # 전일 거래량 데이터를 가져오기 위해 날짜를 한 단계 좁혀 당일 데이터와 비교하는 방식으로 우회하거나,
                # 네이버 차단을 피하기 위해 최근 2개 영업일의 전 종목 시세를 직접 지정해서 가져옵니다.
                
                # 가장 안전하게 최근 열린 2일의 날짜를 샘플로 추출
                sample = stock.get_market_ohlcv_by_date(start_date, end_date, "005930")
                trading_days = sample.index.strftime("%Y%m%d").tolist()
                
                if len(trading_days) < 2:
                    st.warning("⚠️ 최근 2일간의 영업일 날짜를 확보하지 못했습니다. 장 시작 전이거나 휴일일 수 있습니다.")
                else:
                    prev_day = trading_days[-2]   # 전 영업일 (예: 어제)
                    target_day = trading_days[-1] # 최근 영업일 (예: 오늘)
                    
                    # 각 날짜의 전종목 거래량 직접 가져오기
                    df_prev = stock.get_market_ohlcv_by_ticker(prev_day, market="ALL")
                    df_target = stock.get_market_ohlcv_by_ticker(target_day, market="ALL")
                    
                    # 데이터가 정상적으로 한글 컬럼을 가지고 왔는지 확인하고, 없으면 영어 컬럼 이름으로 재시도
                    # (Streamlit Cloud 환경에 따라 pykrx가 가끔 영문 컬럼 ['Volume', 'Close']을 뱉는 경우가 있습니다)
                    if not df_prev.empty and not df_target.empty:
                        
                        # 영문 컬럼일 경우 한글로 매핑 변환
                        if 'Volume' in df_prev.columns:
                            df_prev = df_prev.rename(columns={'Volume': '거래량'})
                        if 'Volume' in df_target.columns:
                            df_target = df_target.rename(columns={'Volume': '거래량', 'Close': '종가', 'Name': '종목명'})
                            
                        # '종목명' 컬럼이 인덱스에 있거나 없는 경우 방어구문
                        if '종목명' not in df_target.columns and 'Name' not in df_target.columns:
                            # 종목코드를 종목명으로 매핑하기 위한 리스트 생성
                            tickers = df_target.index.tolist()
                            names = [stock.get_market_ticker_name(t) for t in tickers]
                            df_target['종목명'] = names
                        
                        # 필요한 데이터 추출 및 병합
                        df_prev_vol = df_prev[['거래량']].rename(columns={'거래량': '전일거래량'})
                        df_target_vol = df_target[['종목명', '종가', '거래량']].rename(columns={'거래량': '금일거래량'})
                        
                        merged_df = pd.merge(df_target_vol, df_prev_vol, left_index=True, right_index=True)
                        merged_df = merged_df[merged_df['전일거래량'] > 0]
                        
                        # 거래량 증가율 계산
                        merged_df['거래량 증가율(%)'] = round((merged_df['금일거래량'] / merged_df['전일거래량']) * 100, 2)
                        result_df = merged_df[merged_df['거래량 증가율(%)'] >= volume_ratio]
                        
                        result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False).reset_index()
                        result_df = result_df.rename(columns={'index': '종목코드'})
                        
                        st.success(f"🔥 {target_day} 기준, 전일({prev_day}) 대비 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                        st.dataframe(
                            result_df[['종목명', '종목코드', '종가', '전일거래량', '금일거래량', '거래량 증가율(%)']],
                            use_container_width=True
                        )
                    else:
                        st.error("거래소로부터 데이터를 가져왔으나 내용이 비어있습니다. 현재 시간대가 장 시작 전이거나 서버 점검 중일 수 있습니다.")
                        
        except Exception as e:
            st.error(f"오류가 발생했습니다. 현재 장외 시간이거나 서버 차단 가능성이 있습니다. (오류 내용: {e})")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
