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
            # 안전하게 최근 10일치 날짜 리스트 확보
            today = datetime.today().strftime("%Y%m%d")
            ten_days_ago = (datetime.today() - timedelta(days=10)).strftime("%Y%m%d")
            
            # 삼성전자 종목으로 실제 주식 시장이 열렸던 날짜 리스트 가져오기
            sample_df = stock.get_market_ohlcv_by_date(ten_days_ago, today, "005930")
            
            # [방어 코드 1] 날짜 데이터 자체가 없거나 부족한 경우 처리
            if sample_df.empty or len(sample_df) < 2:
                st.warning("⚠️ 현재 한국거래소(KRX)로부터 데이터를 가져올 수 없습니다. 장 시작 전(오전 9시 이전)이거나 주말/공휴일일 수 있습니다. 장이 열린 후에 다시 시도해 주세요.")
            else:
                trading_days = sample_df.index.strftime("%Y%m%d").tolist()
                prev_day = trading_days[-2]   # 전 영업일
                target_day = trading_days[-1] # 최근 영업일
                
                # 두 날짜의 전 종목 시세 데이터 가져오기
                df_prev = stock.get_market_ohlcv_by_ticker(prev_day, market="ALL")
                df_target = stock.get_market_ohlcv_by_ticker(target_day, market="ALL")
                
                # [방어 코드 2] 가져온 전 종목 데이터 세트가 비어있는지 완전히 검증
                if df_prev.empty or df_target.empty:
                    st.warning(f"⚠️ {target_day} 또는 {prev_day}의 전 종목 시세 데이터가 아직 생성되지 않았습니다. (보통 장 시작 직후나 휴일에 발생합니다)")
                # [방어 코드 3] pykrx가 에러를 뱉지 않도록 '거래량'과 '종목명' 컬럼이 확실히 존재하는지 검사
                elif '거래량' in df_prev.columns and '거래량' in df_target.columns and '종목명' in df_target.columns:
                    
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
                    if not result_df.empty:
                        st.success(f"🔥 {target_day} 기준, 전일({prev_day}) 대비 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                        st.dataframe(
                            result_df[['종목명', '종목코드', '종가', '전일거래량', '금일거래량', '거래량 증가율(%)']],
                            use_container_width=True
                        )
                    else:
                        st.info(f"정상적으로 조회되었으나, 전일 대비 거래량이 {volume_ratio}% 이상 급증한 종목이 현재 없습니다.")
                else:
                    st.warning("⚠️ 거래소 서버에서 빈 데이터를 반환했습니다. 잠시 후 다시 시도해 주세요.")
                    
        except Exception as e:
            # 최종 예외 처리 단계에서도 사용자에게 친절하게 안내
            st.error(f"데이터를 처리하는 중 일시적인 오류가 발생했습니다. (사유: {e})")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
