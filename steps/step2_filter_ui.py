import streamlit as st
import pandas as pd


def step2_filter_ui(df):
    st.subheader("Step 2 — Filter & Select Papers")

    st.info("You can filter rows here or upload a filtered Excel file.")

    uploaded_file = st.file_uploader("Upload filtered Excel (optional)", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("Uploaded file loaded and will be used for next steps.")

    st.write("### Filter Data")

    with st.expander("Column Filters"):
        for col in df.columns:
            if df[col].dtype == "object":
                selected_vals = st.multiselect(f"{col}", df[col].unique())
                if selected_vals:
                    df = df[df[col].isin(selected_vals)]

    st.write("### Select Rows to Proceed")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="step2_editor",
    )

    selected_rows = edited_df.copy()

    if st.button("Confirm Selection"):
        st.session_state["step2_df"] = selected_rows
        st.success(f"{len(selected_rows)} papers selected for PDF download.")

    return selected_rows
