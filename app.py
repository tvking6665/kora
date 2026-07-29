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
# 2. 데이터 전처리 (엑셀 수정 없이 100% 자동 파싱)
# -----------------------------------------------------------------------------
def parse_excel_file(uploaded_file):
    try:
        # header=None으로 전체 로드하여 진짜 헤더 위치 자동 감지
        raw_df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # '설비명'이나 '품번'이 위치한 행을 완벽 탐지
        header_row_idx = None
        for idx, row in raw_df.iterrows():
            row_str = "".join(str(v).replace(" ", "").strip() for v in row.values if pd.notna(v))
            if "설비명" in row_str or ("품번" in row_str and "가동생산량" in row_str):
                header_row_idx = idx
                break

        if header_row_idx is None:
            header_row_idx = 0

        # 헤더 아래 데이터만 슬라이싱
        df = raw_df.iloc[header_row_idx + 1:].copy()
        raw_cols = [str(c).replace("\n", "").replace(" ", "").strip() for c in raw_df.iloc[header_row_idx].values]
        
        # 중복 컬럼 고유화
        seen = {}
        unique_cols = []
        for c in raw_cols:
            if c in seen:
                seen[c] += 1
                unique_cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                unique_cols.append(c)
        df.columns = unique_cols

        # 빈 행/열 및 Unnamed 제거
        df = df.dropna(how="all").dropna(how="all", axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

        # '계', '소계', '합계' 등 불필요 행 제거
        for col in df.columns[:3]:
            mask = df[col].astype(str).str.contains("계|소계|합계|transfer|대형\(transfer\)", case=False, na=False)
            df = df[~mask]

        # 수식 오류(#N/A 등) 무시 처리
        for col in df.columns:
            s = df[col].astype(str)
            mask_err = s.str.startswith("#", na=False)
            if mask_err.any():
                df.loc[mask_err, col] = None

        return df

    except Exception as e:
        st.error(f"엑셀 파일 처리 중 오류가 발생했습니다: {e}")
        return None

def load_master_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

def match_target_column(df_cols, target_keyword):
    """지정한 단어가 완벽히 일치하거나 가장 잘 맞아떨어지는 원본 열을 검색"""
    for col in df_cols:
        pure_name = col.split("_")[0]
        if pure_name == target_keyword:
            return col
    for col in df_cols:
        pure_name = col.split("_")[0]
        if target_keyword in pure_name:
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
    # 요청하신 빨간색 음영 타겟 항목 매핑
    col_eq = match_target_column(master_df.columns, "설비명")
    col_item_num = match_target_column(master_df.columns, "품번")
    col_item_name = match_target_column(master_df.columns, "품명")
    col_actual = match_target_column(master_df.columns, "가동생산량")
    col_defect = match_target_column(master_df.columns, "불량실적")
    col_yield = match_target_column(master_df.columns, "양품률(%)") or match_target_column(master_df.columns, "양품률")
    col_time_rate = match_target_column(master_df.columns, "시간가동률(%)") or match_target_column(master_df.columns, "시간가동률")
    col_perf_rate = match_target_column(master_df.columns, "성능가동률(%)") or match_target_column(master_df.columns, "성능가동률")
    col_oee = match_target_column(master_df.columns, "설비종합(%)") or match_target_column(master_df.columns, "설비종합")
    col_ct = match_target_column(master_df.columns, "실제CT")
    col_work_time = match_target_column(master_df.columns, "가동시간")
    col_load_time = match_target_column(master_df.columns, "부하시간")
    col_stop_loss = match_target_column(master_df.columns, "정지LOSS")
    col_possible = match_target_column(master_df.columns, "생산가능수")

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

        tab1, tab2, tab3 = st.tabs(["📌 지정 항목 중심 상세 현황 보고서", "📊 주차별 / 설비별 트렌드 분석", "🗄️ 누적 DB 관리"])

        # ---------------------------------------------------------------------
        # TAB 1: 지정 항목 보고서
        # ---------------------------------------------------------------------
        with tab1:
            st.subheader("📋 지정 항목 중심 상세 실적 표")
            
            target_mapping = [
                ("설비명", col_eq),
                ("품번", col_item_num),
                ("품명", col_item_name),
                ("가동생산량", col_actual),
                ("불량실적", col_defect),
                ("양품률(%)", col_yield),
                ("시간가동률(%)", col_time_rate),
                ("성능가동률(%)", col_perf_rate),
                ("설비종합(%)", col_oee),
                ("실제CT", col_ct),
                ("가동시간", col_work_time),
                ("부하시간", col_load_time),
                ("정지LOSS", col_stop_loss)
            ]
            
            selected_cols = []
            rename_map = {}
            for label, matched_col in target_mapping:
                if matched_col and matched_col in filtered_df.columns:
                    selected_cols.append(matched_col)
                    rename_map[matched_col] = label
            
            view_df = filtered_df[selected_cols].rename(columns=rename_map).copy()
            
            for col in view_df.columns:
                if view_df[col].dtype == 'object':
                    view_df[col] = view_df[col].astype(str).replace('nan', '').replace('None', '')

            st.dataframe(view_df, use_container_width=True, height=550)

            # CSV 다운로드
            csv_data = view_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 현재 화면 데이터 엑셀(CSV) 다운로드",
                data=csv_data,
                file_name=f"지정실적보고서_{sel_year}_{'_'.join(sel_weeks)}.csv",
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
                    temp_df = filtered_df.copy()
                    temp_df[col_actual] = pd.to_numeric(temp_df[col_actual], errors='coerce')
                    
                    df_grouped_prod = temp_df.groupby(["주차", col_eq], as_index=False)[col_actual].sum()
                    df_grouped_prod["주차_num"] = df_grouped_prod["주차"].apply(lambda x: int(str(x).replace("주차", "")))
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
                    temp_df = filtered_df.copy()
                    temp_df[col_oee] = pd.to_numeric(temp_df[col_oee], errors='coerce')
                    
                    df_grouped_oee = temp_df.groupby(["주차", col_eq], as_index=False)[col_oee].mean()
                    df_grouped_oee["주차_num"] = df_grouped_oee["주차"].apply(lambda x: int(str(x).replace("주차", "")))
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
