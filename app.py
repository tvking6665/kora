import streamlit as st
from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="국장 거래량 급증 검색기", layout="wide")
st.title("📈 한국 주식 거래량 급증 검색기")
st.caption("최근 영업일 기준 전일 대비 거래량이 급증한 종목을 실시간으로 검색합니다.")

# 2. 사이드바 설정 (조건 조절용)
st.sidebar.header("🔍 검색 조건 설정")
volume_ratio = st.sidebar.slider("거래량 증가율 조건 (%)", min_value=100, max_value=1000, value=300, step=50)

# 3. 데이터 수집 버튼
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner("한국 거래소 전체 종목 분석 중... 잠시만 기다려주세요."):
        try:
            # 안전하게 최근 10일치 데이터를 확보하여 실제 주식 시장이 열린 날(영업일)만 추출
            today = datetime.today().strftime("%Y%m%d")
            ten_days_ago = (datetime.today() - timedelta(days=10)).strftime("%Y%m%d")
            
            # 삼성전자 종목으로 실제 주식 시장이 열렸던 날짜 리스트 가져오기
            sample_df = stock.get_market_ohlcv_by_date(ten_days_ago, today, "005930")
            
            # 데이터가 비어있지 않은지 검증
            if sample_df.empty or len(sample_df) < 2:
                st.error("현재 조회 가능한 주식 시장 데이터가 없습니다. 장 시작 전(09:00 이전)이거나 시스템 점검 중일 수 있습니다.")
            else:
                # 실제 열렸던 날짜 중 가장 최근 2일 선택
                trading_days = sample_df.index.strftime("%Y%m%d").tolist()
                prev_day = trading_days[-2]   # 전 영업일
                target_day = trading_days[-1] # 최근 영업일
                
                # 두 날짜의 전 종목 시세 데이터 가져오기
                df_prev = stock.get_market_ohlcv_by_ticker(prev_day, market="ALL")
                df_target = stock.get_market_ohlcv_by_ticker(target_day, market="ALL")
                
                # 컬럼이 정상적으로 존재하는지 체크 (에러 방지 안전장치)
                if '거래량' in df_prev.columns and '거래량' in df_target.columns:
                    df_prev_vol = df_prev[['거래량']].rename(columns={'거래량': '전일거래량'})
                    df_target_vol = df_target[['종목명', '종가', '거래량']].rename(columns={'거래량': '금일거래량'})
                    
                    # 두 데이터 병합
                    merged_df = pd.merge(df_target_vol, df_prev_vol, left_index=True, right_index=True)
                    
                    # 전일 거래량이 0인 종목 제외 (나눗셈 에러 방지)
                    merged_df = merged_df[merged_df['전일거래량'] > 0]
                    
                    # 거래량 증가율 계산 (%)
                    merged_df['거래량 증가율(%)'] = round((merged_df['금일거래량'] / merged_df['전일거래량']) * 100, 2)
                    
                    # 사용자가 설정한 조건 (예: 300%) 이상인 종목만 필터링
                    result_df = merged_df[merged_df['거래량 증가율(%)'] >= volume_ratio]
                    
                    # 정렬 및 포맷팅
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False)
                    result_df.index.name = "종목코드"
                    result_df = result_df.reset_index()
                    
                    # 결과 출력
                    st.success(f"🔥 {target_day} 기준, 전일({prev_day}) 대비 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                    
                    # 데이터 테이블 보기 좋게 출력
                    st.dataframe(
                        result_df[['종목명', '종목코드', '종가', '전일거래량', '금일거래량', '거래량 증가율(%)']],
                        use_container_width=True
                    )
                else:
                    st.error("거래소 데이터 형식에 일시적인 문제가 있거나 컬럼을 읽어오지 못했습니다.")
                    
        except Exception as e:
            st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
