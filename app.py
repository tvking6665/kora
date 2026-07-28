import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.express as px

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
# 2. 데이터 전처리 및 유연한 컬럼 탐지 함수
# -----------------------------------------------------------------------------
def parse_excel_file(uploaded_file):
    try:
        # header없이 전체 읽어오기
        raw_df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # '설비명' 또는 '설비' 또는 '품번'이 들어간 행을 진짜 헤더 행으로 찾기
        header_row_idx = 0
        for idx, row in raw_df.iterrows():
            row_str = " ".join(str(val) for val in row.values if pd.notna(val))
            if any(k in row_str for k in ["설비명", "설비", "품번", "가동생산량"]):
                header_row_idx = idx
                break

        # 헤더 설정 및 데이터 슬라이싱
        df = raw_df.iloc[header_row_idx + 1:].copy()
        raw_cols = raw_df.iloc[header_row_idx].astype(str).values
        
        # 컬럼명 공백/줄바꿈 정리
        cleaned_cols = [str(c).replace("\n", "").replace(" ", "").strip() for c in raw_cols]
        
        # [중요] 중복된 컬럼명이 있을 경우 이름 뒤에 _1, _2 붙여 고유하게 만들기
        seen = {}
        unique_cols = []
        for c in cleaned_cols:
            if c in seen:
                seen[c] += 1
                unique_cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                unique_cols.append(c)
        
        df.columns = unique_cols

        # 완전히 빈 행/열 및 Unnamed 열 제거
        df = df.dropna(how="all").dropna(how="all", axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

        # 수식 오류 문자열(#N/A, #VALUE! 등)을 None(NaN)으로 치환
        for col in df.columns:
            s = df[col].astype(str)
            mask = s.str.startswith("#", na=False)
            if mask.any():
                df.loc[mask, col] = None

        # '계', '소계', '합계', 'transfer' 등 필터링 (첫번째 컬럼 또는 문자열 컬럼 기준)
        for col in df.columns:
            mask = df[col].astype(str).str.contains("계|소계|합계|transfer|대형\(transfer\)", case=False, na=False)
            df = df[~mask]

        # 수치형 컬럼 정제 및 안전한 변환 (쉼표 제거 후 numeric)
        for col in df.columns:
            if any(k in col for k in ["수", "량", "실적", "률", "비율", "효율", "CT", "C/T"]):
                s = df[col].astype(str).str.replace(",", "").str.strip()
                df[col] = pd.to_numeric(s, errors='coerce')

        return df

    except Exception as e:
        st.error(f"엑셀 파일 처리 중 오류가 발생했습니다: {e}")
        return None

def load_master_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

def find_col(df, keywords):
    """주어진 키워드가 포함된 컬럼명을 유연하게 검색하는 함수"""
    for col in df.columns:
        if any(k in col for k in keywords):
            return col
    return None

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
            cleaned_df.insert(0, "주차", selected_week)
            cleaned_df.insert(0, "연도", selected_year)
            cleaned_df["업로드일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            master_df = load_master_data()

            if not master_df.empty:
                already_exists = master_df[
                    (master_df["연도"] == selected_year) & (master_df["주차"] == selected_week)
                ]
                if not already_exists.empty:
                    master_df = master_df[
                        ~((master_df["연도"] == selected_year) & (master_df["주차"] == selected_week))
                    ]
                    st.sidebar.info(f"💡 기존 {selected_year}년 {selected_week} 데이터를 신규 파일로 업데이트했습니다.")

            updated_master = pd.concat([master_df, cleaned_df], ignore_index=True)
            updated_master.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
            st.sidebar.success(f"✅ {selected_year}년 {selected_week} 데이터 ({len(cleaned_df)}건) 누적 저장 완료!")
            st.rerun()
        else:
            st.sidebar.error("엑셀 파일 파싱 실패: 적절한 데이터 표를 찾지 못했습니다.")
    else:
        st.sidebar.warning("업로드할 엑셀 파일을 먼저 선택해주세요.")

st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# 4. 메인 대시보드 화면
# -----------------------------------------------------------------------------
st.title("🏭 설비 종합 생산 실적 & 주간 추이 분석")

master_df = load_master_data()

if master_df.empty:
    st.info("👋 아직 누적된 데이터가 없습니다. 왼쪽 사이드바에서 엑셀 파일을 선택 후 [데이터 누적 저장하기] 버튼을 눌러주세요.")
else:
    # 엑셀 실 컬럼명 기반 유연 탐지
    col_eq = find_col(master_df, ["설비명", "설비"])
    col_item = find_col(master_df, ["품번", "품명"])
    col_possible = find_col(master_df, ["생산가능수", "생산가능"])
    col_actual = find_col(master_df, ["가동생산량", "가동생산", "생산량"])
    col_defect = find_col(master_df, ["불량실적", "불량수량", "불량"])
    col_yield = find_col(master_df, ["양품률", "양품율"])
    col_time_rate = find_col(master_df, ["시간가동률", "시간가동율"])
    col_perf_rate = find_col(master_df, ["성능가동률", "성능가동율"])
    col_oee = find_col(master_df, ["설비종합", "OEE"])
    col_ct = find_col(master_df, ["실제CT", "실제C/T", "CT"])
    col_load_time = find_col(master_df, ["부하시간"])
    col_work_time = find_col(master_df, ["가동시간"])
    col_stop_loss = find_col(master_df, ["정지LOSS", "정지손실", "비가동"])

    # 필터 영역
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

    filtered_df = df_year[df_year["주차"].isin(sel_weeks)]

    if col_eq and col_eq in filtered_df.columns:
        available_equipments = filtered_df[col_eq].dropna().unique().tolist()
        with col_f3:
            sel_equipments = st.multiselect(
                f"🔧 설비 선택", 
                options=available_equipments, 
                default=available_equipments
            )
        filtered_df = filtered_df[filtered_df[col_eq].isin(sel_equipments)]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
    else:
        # 상단 핵심 KPI 요약
        v_possible = pd.to_numeric(filtered_df[col_possible], errors='coerce').sum() if col_possible else 0
        v_actual = pd.to_numeric(filtered_df[col_actual], errors='coerce').sum() if col_actual else 0
        v_defect = pd.to_numeric(filtered_df[col_defect], errors='coerce').sum() if col_defect else 0
        v_yield = ((v_actual - v_defect) / v_actual * 100) if v_actual > 0 else 0
        v_oee = pd.to_numeric(filtered_df[col_oee], errors='coerce').mean() if col_oee else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("총 생산가능수", f"{v_possible:,.0f} 개")
        k2.metric("총 가동생산량", f"{v_actual:,.0f} 개")
        k3.metric("총 불량수량", f"{v_defect:,.0f} 개")
        k4.metric("평균 양품률", f"{v_yield:.2f} %")
        k5.metric("평균 설비종합효율(OEE)", f"{v_oee:.2f} %")

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["📌 설비별 상세 현황 보고서", "📊 주차별 / 설비별 트렌드 분석", "🗄️ 누적 DB 관리"])

        # ---------------------------------------------------------------------
        # TAB 1: 지정 항목 중심 보고서
        # ---------------------------------------------------------------------
        with tab1:
            st.subheader("📋 설비 기준 상세 실적 및 시간/LOSS 현황")
            
            req_cols = [
                ("설비명", col_eq),
                ("품번", col_item),
                ("가동생산량", col_actual),
                ("불량실적", col_defect),
                ("양품률(%)", col_yield),
                ("시간가동률(%)", col_time_rate),
                ("성능가동률(%)", col_perf_rate),
                ("설비종합(%)", col_oee),
                ("실제 C/T", col_ct),
                ("부하시간", col_load_time),
                ("가동시간", col_work_time),
                ("정지LOSS", col_stop_loss)
            ]
            
            select_cols = [c[1] for c in req_cols if c[1] and c[1] in filtered_df.columns]
            rename_dict = {c[1]: c[0] for c in req_cols if c[1] and c[1] in filtered_df.columns}
            
            view_df = filtered_df[select_cols].rename(columns=rename_dict)
            
            st.dataframe(view_df, use_container_width=True, height=500)

            # 다운로드
            csv_data = view_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 현재 화면 데이터 엑셀(CSV) 다운로드",
                data=csv_data,
                file_name=f"설비상세실적_{sel_year}_{'_'.join(sel_weeks)}.csv",
                mime="text/csv"
            )

        # ---------------------------------------------------------------------
        # TAB 2: 주차별 추이 차트
        # ---------------------------------------------------------------------
        with tab2:
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("📈 주차별 / 설비별 가동생산량 추이")
                if col_actual and col_eq:
                    df_grouped_prod = filtered_df.groupby(["주차", col_eq])[col_actual].apply(lambda x: pd.to_numeric(x, errors='coerce').sum()).reset_index()
                    df_grouped_prod["주차_num"] = df_grouped_prod["주차"].apply(lambda x: int(x.replace("주차", "")))
                    df_grouped_prod = df_grouped_prod.sort_values("주차_num")

                    fig_prod = px.bar(
                        df_grouped_prod, 
                        x="주차", 
                        y=col_actual, 
                        color=col_eq,
                        barmode="group",
                        text_auto=',.0f',
                        title="주차별 설비 생산량 비교"
                    )
                    fig_prod.update_layout(xaxis_title="주차", yaxis_title="생산량 (개)")
                    st.plotly_chart(fig_prod, use_container_width=True)

            with col_chart2:
                st.subheader("🎯 설비종합효율(OEE %) 추이")
                if col_oee and col_eq:
                    df_grouped_oee = filtered_df.groupby(["주차", col_eq])[col_oee].apply(lambda x: pd.to_numeric(x, errors='coerce').mean()).reset_index()
                    df_grouped_oee["주차_num"] = df_grouped_oee["주차"].apply(lambda x: int(x.replace("주차", "")))
                    df_grouped_oee = df_grouped_oee.sort_values("주차_num")

                    fig_oee = px.line(
                        df_grouped_oee,
                        x="주차",
                        y=col_oee,
                        color=col_eq,
                        markers=True,
                        title="주차별 설비종합효율(OEE %) 변화"
                    )
                    fig_oee.update_layout(xaxis_title="주차", yaxis_title="설비종합효율 (%)", yaxis_range=[0, 100])
                    st.plotly_chart(fig_oee, use_container_width=True)

        # ---------------------------------------------------------------------
        # TAB 3: DB 관리
        # ---------------------------------------------------------------------
        with tab3:
            st.subheader("🗄️ 전체 누적 데이터베이스 관리")
            db_summary = master_df.groupby(["연도", "주차"]).agg(
                행수=(master_df.columns[2], "count"),
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
