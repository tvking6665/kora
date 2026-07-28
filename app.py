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
# 2. 데이터 전처리 및 데이터베이스 관리 함수
# -----------------------------------------------------------------------------
def parse_excel_file(uploaded_file):
    """
    엑셀 상단 헤더에 공백, 병합, 빈 셀이 섞여 있어도 
    '설비코드' 단어를 유연하게 찾아 데이터를 정제하는 보완 함수
    """
    try:
        df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)
        
        header_idx = None
        for idx, row in df_raw.iterrows():
            row_str = "".join([str(val).replace(" ", "") for val in row.values if pd.notna(val)])
            if "설비코드" in row_str:
                header_idx = idx
                break
        
        if header_idx is None:
            st.error("엑셀 파일 내에서 '설비코드' 항목을 찾지 못했습니다. 첫 번째 시트에 '설비코드' 열이 있는지 확인해주세요.")
            return None

        df = pd.read_excel(uploaded_file, header=header_idx)
        df.columns = [str(c).replace(" ", "").strip() for c in df.columns]

        target_code_col = None
        for col in df.columns:
            if "설비코드" in col:
                target_code_col = col
                break
                
        if not target_code_col:
            st.error("'설비코드' 열의 이름을 인식하지 못했습니다.")
            return None

        df = df.rename(columns={target_code_col: "설비코드"})

        df = df.dropna(subset=["설비코드"]).copy()
        df = df[df["설비코드"].astype(str).str.strip() != ""]

        code_str = df["설비코드"].astype(str)
        df = df[~code_str.str.contains("transfer|대형|소계|합계|계", case=False, na=False)]
        
        for col in df.columns:
            if "품번" in col or "품명" in col:
                df = df[~df[col].astype(str).str.contains("계|소계|합계", na=False)]

        numeric_cols = [
            "생산가능수", "가동생산량", "비가동생산량", "불량실적",
            "목표달성률(%)", "양품률(%)", "시간가동률(%)", "성능가동률(%)", "설비종합(%)",
            "이론CT", "실제CT"
        ]
        for col in numeric_cols:
            for df_col in df.columns:
                if col in df_col:
                    df[df_col] = pd.to_numeric(df[df_col].astype(str).str.replace(",", ""), errors='coerce').fillna(0)

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
        st.sidebar.warning("업로드할 엑셀 파일을 먼저 선택해주세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 사용 안내")
st.sidebar.caption("""
1. 엑셀 수식이나 '계' 행을 수정할 필요 없이 원본 그대로 올려주세요.
2. 업로드 시 '연도'와 '주차'만 잘 선택해주시면 됩니다.
""")


# -----------------------------------------------------------------------------
# 4. 메인 대시보드 화면
# -----------------------------------------------------------------------------
st.title("🏭 설비 종합 생산 실적 & 주간 추이 분석")

master_df = load_master_data()

if master_df.empty:
    st.info("👋 아직 누적된 데이터가 없습니다. 왼쪽 사이드바에서 엑셀 파일을 선택 후 [데이터 누적 저장하기] 버튼을 눌러주세요.")
else:
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
        
    eq_col = [c for c in df_year.columns if "설비명" in c]
    eq_col_name = eq_col[0] if eq_col else "설비명"
    available_equipments = df_year[eq_col_name].unique().tolist() if eq_col_name in df_year.columns else []
    
    with col_f3:
        sel_equipments = st.multiselect(
            "🔧 설비명 선택", 
            options=available_equipments, 
            default=available_equipments
        )

    filtered_df = df_year[
        (df_year["주차"].isin(sel_weeks)) & 
        (df_year[eq_col_name].isin(sel_equipments) if eq_col_name in df_year.columns else True)
    ]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
    else:
        # 주요 수량 검색
        p_col = [c for c in filtered_df.columns if "생산가능수" in c]
        a_col = [c for c in filtered_df.columns if "가동생산량" in c]
        d_col = [c for c in filtered_df.columns if "불량실적" in c]
        oee_col = [c for c in filtered_df.columns if "설비종합" in c]

        total_possible = filtered_df[p_col[0]].sum() if p_col else 0
        total_actual = filtered_df[a_col[0]].sum() if a_col else 0
        total_defect = filtered_df[d_col[0]].sum() if d_col else 0
        
        avg_yield = ((total_actual - total_defect) / total_actual * 100) if total_actual > 0 else 0
        avg_oee = filtered_df[oee_col[0]].mean() if oee_col else 0

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
                if a_col and eq_col_name in filtered_df.columns:
                    df_grouped_prod = filtered_df.groupby(["주차", eq_col_name])[a_col[0]].sum().reset_index()
                    df_grouped_prod["주차_num"] = df_grouped_prod["주차"].apply(lambda x: int(x.replace("주차", "")))
                    df_grouped_prod = df_grouped_prod.sort_values("주차_num")

                    fig_prod = px.bar(
                        df_grouped_prod, 
                        x="주차", 
                        y=a_col[0], 
                        color=eq_col_name,
                        barmode="group",
                        text_auto=',.0f',
                        title="주차별 설비 생산량 비교"
                    )
                    fig_prod.update_layout(xaxis_title="주차", yaxis_title="생산량 (개)", legend_title="설비명")
                    st.plotly_chart(fig_prod, use_container_width=True)

            with col_chart2:
                st.subheader("🎯 설비종합효율(OEE %) 추이")
                if oee_col and eq_col_name in filtered_df.columns:
                    df_grouped_oee = filtered_df.groupby(["주차", eq_col_name])[oee_col[0]].mean().reset_index()
                    df_grouped_oee["주차_num"] = df_grouped_oee["주차"].apply(lambda x: int(x.replace("주차", "")))
                    df_grouped_oee = df_grouped_oee.sort_values("주차_num")

                    fig_oee = px.line(
                        df_grouped_oee,
                        x="주차",
                        y=oee_col[0],
                        color=eq_col_name,
                        markers=True,
                        title="주차별 설비종합효율(OEE %) 변화"
                    )
                    fig_oee.update_layout(xaxis_title="주차", yaxis_title="설비종합효율 (%)", yaxis_range=[0, 100])
                    st.plotly_chart(fig_oee, use_container_width=True)

        with tab2:
            st.subheader("📑 주차별 / 설비별 상세 실적 집계표")
            st.dataframe(filtered_df, use_container_width=True, height=450)

            csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")
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
