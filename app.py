import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 및 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="설비 실적 주간 취합 & 대시보드",
    page_icon="🏭",
    layout="wide"
)

DB_FILE = "master_production_data.csv"

# -----------------------------------------------------------------------------
# 2. 데이터 전처리 및 데이터베이스 관리 함수 (오류 보완)
# -----------------------------------------------------------------------------
def parse_excel_file(uploaded_file):
    """
    빈 셀(NaN)이나 다양한 타입의 셀이 포함되어 있어도 오류 없이
    '설비코드' 헤더를 탐지하고 원천 데이터만 안전하게 정제하는 함수
    """
    try:
        # 헤더 없이 원본 전체 읽기
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # '설비코드' 문구가 포함된 행 찾기
        header_idx = None
        for idx, row in df_raw.iterrows():
            # 각 셀을 문자열로 안전하게 변환
            row_values = [str(val) for val in row.values if pd.notna(val)]
            if any("설비코드" in val for val in row_values):
                header_idx = idx
                break
        
        if header_idx is None:
            st.error("엑셀 파일 내에서 '설비코드' 열을 찾을 수 없습니다. 시트 구성이나 열 이름을 확인해주세요.")
            return None

        # 헤더 위치 기준으로 다시 읽기
        df = pd.read_excel(uploaded_file, header=header_idx)
        df.columns = [str(c).strip() for c in df.columns]

        if "설비코드" not in df.columns:
            st.error("'설비코드' 컬럼을 인식하지 못했습니다.")
            return None

        # 1. 설비코드가 빈 값(NaN)인 행 제거
        df = df.dropna(subset=["설비코드"]).copy()

        # 2. 안전하게 문자열로 변환 후 '계', '소계', '합계', 'transfer' 등 집계 행 자동 제거
        code_str = df["설비코드"].astype(str)
        df = df[~code_str.str.contains("transfer|대형|소계|합계|계", case=False, na=False)]
        
        if "품번" in df.columns:
            df = df[~df["품번"].astype(str).str.contains("계|소계|합계", na=False)]
        if "품명" in df.columns:
            df = df[~df["품명"].astype(str).str.contains("계|소계|합계", na=False)]

        # 수량 및 비율 관련 주요 컬럼 수치형 변환
        numeric_cols = [
            "생산가능수", "가동생산량", "비가동생산량", "불량실적",
            "목표달성률(%)", "양품률(%)", "시간가동률(%)", "성능가동률(%)", "설비종합(%)",
            "이론CT", "실제CT"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except Exception as e:
        st.error(f"엑셀 파일 처리 중 오류가 발생했습니다: {e}")
        return None


def load_master_data():
    """누적 데이터베이스 파일 읽기"""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()


# -----------------------------------------------------------------------------
# 3. 사이드바 (데이터 업로드 및 누적 등록)
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 주간 데이터 업로드")
st.sidebar.caption("매주 출력되는 엑셀 파일을 올려주시면 자동으로 DB에 누적됩니다.")

current_year = datetime.now().year
current_week = int(datetime.now().isocalendar()[1])

selected_year = st.sidebar.number_input("연도 선택", min_value=2024, max_value=2030, value=current_year)
selected_week = st.sidebar.selectbox(
    "주차 선택", 
    [f"{i}주차" for i in range(1, 54)], 
    index=max(0, current_week - 1)
)

uploaded_file = st.sidebar.file_uploader(
    "주간 실적 엑셀 (.xlsx, .xls)", 
    type=["xlsx", "xls"]
)

if st.sidebar.button("📥 데이터 누적 저장하기", type="primary", use_container_width=True):
    if uploaded_file is not None:
        cleaned_df = parse_excel_file(uploaded_file)
        
        if cleaned_df is not None and not cleaned_df.empty:
            # 메타데이터 추가
            cleaned_df.insert(0, "주차", selected_week)
            cleaned_df.insert(0, "연도", selected_year)
            cleaned_df["업로드일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 기존 DB 불러오기
            master_df = load_master_data()

            # 동일 연도/주차 데이터가 존재할 경우 덮어쓰기
            if not master_df.empty:
                already_exists = master_df[
                    (master_df["연도"] == selected_year) & (master_df["주차"] == selected_week)
                ]
                if not already_exists.empty:
                    master_df = master_df[
                        ~((master_df["연도"] == selected_year) & (master_df["주차"] == selected_week))
                    ]
                    st.sidebar.info(f"💡 기존 {selected_year}년 {selected_week} 데이터를 신규 파일로 업데이트했습니다.")

            # 병합 및 저장
            updated_master = pd.concat([master_df, cleaned_df], ignore_index=True)
            updated_master.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.sidebar.success(f"✅ {selected_year}년 {selected_week} 데이터 ({len(cleaned_df)}건) 누적 저장 완료!")
            st.rerun()
    else:
        st.sidebar.warning("업로드할 엑셀 파일을 먼저 선택해주세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 사용 안내")
st.sidebar.caption("""
1. 엑셀 셀 병합이나 '계' 행을 직접 지우지 않고 원본 그대로 올려도 동작합니다.
2. 업로드 시 '연도'와 '주차'를 확인 후 [데이터 누적 저장하기]를 누르세요.
""")


# -----------------------------------------------------------------------------
# 4. 메인 대시보드 화면
# -----------------------------------------------------------------------------
st.title("🏭 설비 종합 생산 실적 & 주간 추이 분석")

master_df = load_master_data()

if master_df.empty:
    st.info("👋 아직 누적된 데이터가 없습니다. 왼쪽 사이드바에서 엑셀 파일을 선택 후 [데이터 누적 저장하기] 버튼을 눌러주세요.")
else:
    # --- 글로벌 필터 (연도, 주차, 설비) ---
    col_f1, col_f2, col_f3 = st.columns([1, 2, 2])
    
    years = sorted(master_df["연도"].unique().tolist(), reverse=True)
    with col_f1:
        sel_year = st.selectbox("📆 연도", years)
        
    df_year = master_df[master_df["연도"] == sel_year]
    
    available_weeks = df_year["주차"].unique().tolist()
    available_weeks.sort(key=lambda x: int(x.replace("주차", "")))
    
    with col_f2:
        sel_weeks = st.multiselect(
            "🗓️ 조회 주차 선택 (복수 선택 시 누적 합산/비교)", 
            options=available_weeks, 
            default=available_weeks
        )
        
    available_equipments = df_year["설비명"].unique().tolist()
    with col_f3:
        sel_equipments = st.multiselect(
            "🔧 설비명 선택", 
            options=available_equipments, 
            default=available_equipments
        )

    # 필터 적용 데이터셋
    filtered_df = df_year[
        (df_year["주차"].isin(sel_weeks)) & 
        (df_year["설비명"].isin(sel_equipments))
    ]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
    else:
        # KPI 요약
        total_possible = filtered_df["생산가능수"].sum()
        total_actual = filtered_df["가동생산량"].sum()
        total_defect = filtered_df["불량실적"].sum()
        
        avg_yield = ((total_actual - total_defect) / total_actual * 100) if total_actual > 0 else 0
        avg_oee = filtered_df["설비종합(%)"].mean() if "설비종합(%)" in filtered_df.columns else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("총 생산가능수", f"{total_possible:,.0f} 개")
        k2.metric("총 가동생산량", f"{total_actual:,.0f} 개")
        k3.metric("총 불량수량", f"{total_defect:,.0f} 개")
        k4.metric("평균 양품률", f"{avg_yield:.2f} %")
        k5.metric("평균 설비종합효율(OEE)", f"{avg_oee:.2f} %")

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["📊 주차별 / 설비별 트렌드 분석", "📋 상세 보고서 및 집계", "🗄️ 누적 DB 관리"])

        with tab1:
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("📈 주차별 / 설비별 가동생산량 추이")
                df_grouped_prod = filtered_df.groupby(["주차", "설비명"])["가동생산량"].sum().reset_index()
                df_grouped_prod["주차_num"] = df_grouped_prod["주차"].apply(lambda x: int(x.replace("주차", "")))
                df_grouped_prod = df_grouped_prod.sort_values("주차_num")

                fig_prod = px.bar(
                    df_grouped_prod, 
                    x="주차", 
                    y="가동생산량", 
                    color="설비명",
                    barmode="group",
                    text_auto=',.0f',
                    title="주차별 설비 생산량 비교"
                )
                fig_prod.update_layout(xaxis_title="주차", yaxis_title="생산량 (개)", legend_title="설비명")
                st.plotly_chart(fig_prod, use_container_width=True)

            with col_chart2:
                st.subheader("🎯 설비종합효율(OEE %) & 가동률 추이")
                df_grouped_oee = filtered_df.groupby(["주차", "설비명"])[["시간가동률(%)", "성능가동률(%)", "설비종합(%)"]].mean().reset_index()
                df_grouped_oee["주차_num"] = df_grouped_oee["주차"].apply(lambda x: int(x.replace("주차", "")))
                df_grouped_oee = df_grouped_oee.sort_values("주차_num")

                fig_oee = px.line(
                    df_grouped_oee,
                    x="주차",
                    y="설비종합(%)",
                    color="설비명",
                    markers=True,
                    title="주차별 설비종합효율(OEE %) 변화"
                )
                fig_oee.update_layout(xaxis_title="주차", yaxis_title="설비종합효율 (%)", yaxis_range=[0, 100])
                st.plotly_chart(fig_oee, use_container_width=True)

            st.markdown("---")
            
            st.subheader("⚙️ 주요 가동 및 비가동수량 구성 비중")
            c1, c2 = st.columns(2)
            with c1:
                prod_summary = pd.DataFrame({
                    "구분": ["가동생산량", "비가동생산량", "불량실적"],
                    "수량": [total_actual, filtered_df["비가동생산량"].sum(), total_defect]
                })
                fig_pie = px.pie(prod_summary, names="구분", values="수량", hole=0.4, title="전체 생산수량 구성비")
                st.plotly_chart(fig_pie, use_container_width=True)

            with c2:
                df_defect_eq = filtered_df.groupby("설비명")["불량실적"].sum().reset_index()
                fig_defect = px.bar(df_defect_eq, x="설비명", y="불량실적", color="설비명", title="설비별 누적 불량 발생 수량")
                st.plotly_chart(fig_defect, use_container_width=True)

        with tab2:
            st.subheader("📑 주차별 / 설비별 상세 실적 집계표")
            display_cols = [
                "연도", "주차", "설비코드", "설비명", "품번", "품명",
                "생산가능수", "가동생산량", "비가동생산량", "불량실적",
                "목표달성률(%)", "양품률(%)", "시간가동률(%)", "성능가동률(%)", "설비종합(%)"
            ]
            actual_display_cols = [c for c in display_cols if c in filtered_df.columns]

            st.dataframe(
                filtered_df[actual_display_cols].style.format({
                    "생산가능수": "{:,.0f}",
                    "가동생산량": "{:,.0f}",
                    "비가동생산량": "{:,.0f}",
                    "불량실적": "{:,.0f}",
                    "목표달성률(%)": "{:.2f}%",
                    "양품률(%)": "{:.2f}%",
                    "시간가동률(%)": "{:.2f}%",
                    "성능가동률(%)": "{:.2f}%",
                    "설비종합(%)": "{:.2f}%"
                }),
                use_container_width=True,
                height=450
            )

            csv_data = filtered_df[actual_display_cols].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 현재 필터 데이터 엑셀(CSV) 다운로드",
                data=csv_data,
                file_name=f"설비실적보고서_{sel_year}_{'_'.join(sel_weeks)}.csv",
                mime="text/csv"
            )

        with tab3:
            st.subheader("🗄️ 전체 누적 데이터베이스 관리")
            db_summary = master_df.groupby(["연도", "주차"]).agg(
                행수=("설비코드", "count"),
                총가동생산량=("가동생산량", "sum"),
                업로드일시=("업로드일시", "max")
            ).reset_index()

            st.dataframe(db_summary, use_container_width=True)

            st.markdown("#### 🗑️ 특정 주차 데이터 삭제")
            col_del1, col_del2, col_del3 = st.columns([2, 2, 2])
            with col_del1:
                del_year = st.selectbox("삭제할 연도", master_df["연도"].unique(), key="del_y")
            with col_del2:
                available_del_weeks = master_df[master_df["연도"] == del_year]["주차"].unique()
                del_week = st.selectbox("삭제할 주차", available_del_weeks, key="del_w")
            with col_del3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"🔥 {del_year}년 {del_week} 삭제하기", type="primary"):
                    new_master = master_df[
                        ~((master_df["연도"] == del_year) & (master_df["주차"] == del_week))
                    ]
                    new_master.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                    st.success(f"{del_year}년 {del_week} 데이터가 성공적으로 삭제되었습니다.")
                    st.rerun()
