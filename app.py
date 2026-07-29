def parse_excel_file(uploaded_file):
    try:
        # header없이 전체 읽어오기
        raw_df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

        # '설비명'과 '품번'이 있는 진짜 헤더 행을 강력 탐지
        header_row_idx = None
        for idx, row in raw_df.iterrows():
            row_str = "".join(str(v).replace(" ", "").strip() for v in row.values if pd.notna(v))
            if "설비명" in row_str or ("품번" in row_str and "가동생산량" in row_str):
                header_row_idx = idx
                break

        if header_row_idx is None:
            header_row_idx = 0 # 탐지 실패시 기본 0행

        # 헤더 설정 및 슬라이싱
        df = raw_df.iloc[header_row_idx + 1:].copy()
        raw_cols = [str(c).replace("\n", "").replace(" ", "").strip() for c in raw_df.iloc[header_row_idx].values]
        
        # 중복 컬럼 고유 이름 지정
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

        # 빈 행/열 및 Unnamed 열 제거
        df = df.dropna(how="all").dropna(how="all", axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

        # '계', '소계', '합계' 등 불필요 합계 행 제거
        for col in df.columns[:3]:
            mask = df[col].astype(str).str.contains("계|소계|합계|transfer|대형\(transfer\)", case=False, na=False)
            df = df[~mask]

        # 수식 오류 무시 처리
        for col in df.columns:
            s = df[col].astype(str)
            mask_err = s.str.startswith("#", na=False)
            if mask_err.any():
                df.loc[mask_err, col] = None

        return df

    except Exception as e:
        st.error(f"엑셀 파일 처리 중 오류가 발생했습니다: {e}")
        return None
