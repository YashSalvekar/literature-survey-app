import streamlit as st
import pandas as pd
import io


def df_to_excel_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer


def step2_filter_ui(df_input):
    st.subheader("Step 2 — Filter & Select Papers")

    source = st.radio(
        "Data source",
        ["From Step 1 Results", "Upload Excel"],
        horizontal=True,
    )

    if source == "Upload Excel":
        uploaded_file = st.file_uploader("Upload filtered Excel", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.session_state["step2_df"] = df
            st.success(f"Uploaded {len(df)} rows")
            st.download_button(
                "⬇ Download Uploaded Excel",
                data=df_to_excel_bytes(df),
                file_name="uploaded_filtered_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            return df
        else:
            return None

    # ---------- From Step 1 ----------
    df = df_input.copy()

    with st.expander("🔎 Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            min_citations = st.number_input("Min citations", min_value=0, value=0)
        with col2:
            reviews_only = st.checkbox("Reviews only")
        with col3:
            open_access_only = st.checkbox("Open access only")
        with col4:
            top_n = st.number_input("Top N (0 = all)", min_value=0, value=0)

        if "Publication Year" in df.columns and not df["Publication Year"].isna().all():
            y_min = int(df["Publication Year"].min())
            y_max = int(df["Publication Year"].max())
            year_range = st.slider("Year range", y_min, y_max, (y_min, y_max))
        else:
            year_range = None

    filtered_df = df.copy()
    if "Citations Count" in df.columns:
        filtered_df = filtered_df[filtered_df["Citations Count"] >= min_citations]
    if reviews_only and "Review" in df.columns:
        filtered_df = filtered_df[filtered_df["Review"] == "YES"]
    if open_access_only and "Open Access" in df.columns:
        filtered_df = filtered_df[filtered_df["Open Access"] == True]
    if year_range and "Publication Year" in df.columns:
        filtered_df = filtered_df[
            (filtered_df["Publication Year"] >= year_range[0]) &
            (filtered_df["Publication Year"] <= year_range[1])
        ]
    if top_n and top_n > 0:
        filtered_df = filtered_df.head(top_n)

    st.markdown("### ✅ Select Rows to Keep")

    selection = st.dataframe(
        filtered_df,
        use_container_width=True,
        selection_mode="multiple",
        on_select="rerun",
    )

    if selection and "rows" in selection and selection["rows"]:
        selected_df = filtered_df.iloc[selection["rows"]]
    else:
        selected_df = filtered_df

    st.success(f"{len(selected_df)} rows selected")

    st.download_button(
        "⬇ Download Selected Excel",
        data=df_to_excel_bytes(selected_df),
        file_name="filtered_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.session_state["step2_df"] = selected_df
    return selected_df
