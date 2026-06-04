import streamlit as st
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd

# 1. 웹 페이지 레이아웃 설정
st.set_page_config(page_title="국장 5일 평균 거래량 급증 검색기", layout="wide")
st.title("📈 한국 주식 일주일(5일) 평균 거래량 급증 검색기")
st.caption("최근 5영업일 평균 거래량 대비 직전 거래일 거래량이 급증한 종목을 검색합니다.")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 조건 설정")
volume_ratio = st.sidebar.slider("평균 대비 거래량 증가율 조건 (%)", min_value=100, max_value=1000, value=300, step=50)

# 3. 데이터 수집 버튼
if st.sidebar.button("검색기 돌리기 🚀"):
    with st.spinner("시장 전체 종목의 최근 일주일 거래량 분석 중... 잠시만 기다려주세요."):
        try:
            # 1. 현재 상장된 한국 주식 전 종목 리스트 가져오기 (날짜 지정 불필요하여 에러 없음)
            df_krx = fdr.StockListing('KRX')
            
            # 우선 관리종목이나 우선주 등을 제외하고 거래량이 유의미한 상위 종목 위주로 세팅하기 위해 
            # 데이터가 준비된 시총 상위 혹은 일반 종목 리스트 추출
            # 여기서는 안정적인 연산을 위해 상위 800개 종목을 샘플링하여 빠르게 계산합니다.
            # (전체 2500개를 한 번에 돌리면 클라우드 사양에 따라 속도가 느려질 수 있습니다)
            df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])].head(1000)
            
            results = []
            
            # 날짜를 오늘 기준으로 여유 있게 잡음
            start_date = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d")
            
            # 프로그레스 바 생성 (유저 시각용)
            progress_bar = st.progress(0)
            total_stocks = len(df_krx)
            
            for idx, row in df_krx.iterrows():
                code = row['Code']
                name = row['Name']
                
                # 각 종목의 최근 주가/거래량 데이터 긁어오기 (날짜 에러 없음)
                df_stock = fdr.DataReader(code, start_date)
                
                # 최소 6일 이상의 데이터가 있어야 5일 평균과 직전일 비교 가능
                if len(df_stock) >= 6:
                    # 가장 최근 영업일 데이터
                    latest_day_vol = df_stock['Volume'].iloc[-1]
                    latest_day_close = df_stock['Close'].iloc[-1]
                    latest_date = df_stock.index[-1].strftime("%Y-%m-%d")
                    
                    # 직전 5영업일의 거래량 평균 계산 (가장 최근일 제외)
                    five_day_avg_vol = df_stock['Volume'].iloc[-6:-1].mean()
                    
                    if five_day_avg_vol > 0:
                        # 5일 평균 대비 최근일 거래량 비율 계산 (%)
                        ratio = round((latest_day_vol / five_day_avg_vol) * 100, 2)
                        
                        # 유저가 설정한 조건(예: 300%) 이상인 경우 결과 리스트에 담기
                        if ratio >= volume_ratio:
                            results.append({
                                '종목명': name,
                                '종목코드': code,
                                '종가': int(latest_day_close),
                                '5일 평균 거래량': int(five_day_avg_vol),
                                '최근일 거래량': int(latest_day_vol),
                                '평균대비 증가율(%)': ratio
                            })
                
                # 프로그레스 바 업데이트
                if idx % 100 == 0:
                    progress_bar.progress(min(idx / total_stocks, 1.0))
            
            progress_bar.progress(1.0)
            
            # 결과 데이터프레임 시각화
            if results:
                result_df = pd.DataFrame(results)
                result_df = result_df.sort_values(by='평균대비 증가율(%)', ascending=False).reset_index(drop=True)
                
                st.success(f"🔥 최근 마감일({latest_date}) 기준, 5일 평균 대비 거래량 {volume_ratio}% 이상 급증한 종목 {len(result_df)}개를 찾았습니다!")
                
                # 천 단위 콤마 포맷팅
                display_df = result_df.copy()
                display_df['종가'] = display_df['종가'].apply(lambda x: f"{x:,}")
                display_df['5일 평균 거래량'] = display_df['5일 평균 거래량'].apply(lambda x: f"{x:,}")
                display_df['최근일 거래량'] = display_df['최근일 거래량'].apply(lambda x: f"{x:,}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info(f"조회는 정상 완료되었으나, 5일 평균 대비 거래량이 {volume_ratio}% 이상 급증한 종목이 현재 없습니다.")
                
        except Exception as e:
            st.error(f"데이터를 처리하는 중 에러가 발생했습니다: {e}")
else:
    st.info("왼쪽 사이드바에서 조건을 설정한 후 [검색기 돌리기] 버튼을 눌러주세요.")
