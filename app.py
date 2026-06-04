import streamlit as st
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="국장 거래량 급증 검색기", layout="wide")
st.title("📈 한국 주식 거래량 급증 검색기")
st.caption("안정성이 검증된 마감 데이터를 활용해 전일 대비 거래량이 급증한 한국 주식을 검색합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 조건 설정")
volume_ratio = st.sidebar.slider("거래량 증가율 조건 (%)", min_value=100, max_value=1000, value=300, step=50)

# 3. 데이터 수집 버튼
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner("마감된 거래소 데이터 분석 중... 잠시만 기다려주세요."):
        try:
            # 안전하게 최근 15일 데이터를 지정해 영업일 날짜 확보
            today_str = datetime.today().strftime("%Y-%m-%d")
            start_str = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d")
            
            # KOSPI 지수 데이터를 통해 실제 시장이 열린 날짜 목록 추출
            kospi_index = fdr.DataReader('KS11', start_str, today_str)
            
            if kospi_index.empty or len(kospi_index) < 3:
                st.warning("⚠️ 최근 영업일 날짜 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
            else:
                # 전체 날짜 리스트 추출
                trading_days = kospi_index.index.strftime("%Y-%m-%d").tolist()
                
                # [핵심 방어 코드] 만약 오늘 날짜가 포함되어 있다면 아직 마감 데이터가 없을 수 있으므로 제외합니다.
                # 항상 안전하게 '완전히 데이터가 수집 완료된 직전 평일 2일'을 선택합니다.
                if trading_days[-1] == today_str:
                    prev_day = trading_days[-3]   # 2영업일 전 (기준점의 전날)
                    target_day = trading_days[-2] # 1영업일 전 (기준점)
                else:
                    prev_day = trading_days[-2]   # 데이터 상 직전 영업일의 전날
                    target_day = trading_days[-1] # 데이터 상 가장 최근 영업일
                
                # 확보한 안전한 날짜로 데이터 조회
                df_target = fdr.StockListing(f'KRX-STOCK-{target_day.replace("-", "")}')
                df_prev = fdr.StockListing(f'KRX-STOCK-{prev_day.replace("-", "")}')
                
                if df_target.empty or df_prev.empty:
                    st.warning(f"⚠️ {target_day} 기준 시장 데이터가 아직 업데이트되지 않았습니다. 잠시 후 다시 시도해 주세요.")
                else:
                    # 데이터 처리 편의를 위해 종목코드를 인덱스로 지정
                    df_target = df_target.set_index('Code')
                    df_prev = df_prev.set_index('Code')
                    
                    # 필요한 컬럼만 추출
                    df_target_sub = df_target[['Name', 'Close', 'Volume']].rename(columns={'Volume': '금일거래량', 'Close': '종가', 'Name': '종목명'})
                    df_prev_sub = df_prev[['Volume']].rename(columns={'Volume': '전일거래량'})
                    
                    # 데이터 병합
                    merged_df = pd.merge(df_target_sub, df_prev_sub, left_index=True, right_index=True)
                    
                    # 전일 거래량 0 및 거래정지 종목 제외
                    merged_df = merged_df[(merged_df['전일거래량'] > 0) & (merged_df['금일거래량'] > 0)]
                    
                    # 거래량 증가율 계산 (%)
                    merged_df['거래량 증가율(%)'] = round((merged_df['금일거래량'] / merged_df['전일거래량']) * 100, 2)
                    
                    # 조건 필터링
                    result_df = merged_df[merged_df['거래량 증가율(%)'] >= volume_ratio]
                    result_df = result_df.sort_values(by='거래량 증가율(%)', ascending=False).reset_index()
                    result_df = result_df.rename(columns={'Code': '종목코드'})
                    
                    # 결과 출력
                    if not result_df.empty:
                        st.success(f"🔥 기준일({target_day}) 대비 전일({prev_day}) 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                        
                        # 숫자 가독성을 위해 1,000 단위 콤마 포맷팅 적용
                        display_df = result_df.copy()
                        display_df['종가'] = display_df['종가'].apply(lambda x: f"{int(x):,}")
                        display_df['전일거래량'] = display_df['전일거래량'].apply(lambda x: f"{int(x):,}")
                        display_df['금일거래량'] = display_df['금일거래량'].apply(lambda x: f"{int(x):,}")
                        
                        st.dataframe(
                            display_df[['종목명', '종목코드', '종가', '전일거래량', '금일거래량', '거래량 증가율(%)']],
                            use_container_width=True
                        )
                    else:
                        st.info(f"조회는 정상 완료되었으나, {target_day} 기준 {volume_ratio}% 이상 거래량이 급증한 종목이 현재 마켓에 없습니다.")
                        
        except Exception as e:
            st.error(f"데이터 처리 중 일시적 에러가 발생했습니다. (사유: {e})")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
