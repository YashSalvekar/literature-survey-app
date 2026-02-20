import streamlit as st
import pandas as pd


def step2_filter_ui(df: pd.DataFrame):
    st.subheader("Filter & Select Papers")

    # ---------------- Filters ----------------
    #col1, col2, col3 = st.columns(3)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_citations = st.number_input("Min citations", min_value=0, value=0)
    with col2:
        reviews_only = st.checkbox("Reviews only")
    with col3:
        open_access_only = st.checkbox("Open access only")
    with col4:
        top_n = st.number_input("Top N (0 = all)", min_value=0, value=0)

    '''if "Publication Year" in df.columns:
        year_min, year_max = int(df["Publication Year"].min()), int(df["Publication Year"].max())
        year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))
    else:
        year_range = None'''
    year_selection = None

    if "Publication Year" in df.columns:
    
        # Clean year values
        years = (
            pd.to_numeric(df["Publication Year"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )
    
        if len(years) > 0:
            years = sorted(years, reverse=True)  # Most recent first
    
            year_selection = st.multiselect(
                "Select Publication Year(s)",
                options=years,
                default=years  # default = all selected
            )


    filtered_df = df.copy()

    if "Citations Count" in df.columns:
        filtered_df = filtered_df[filtered_df["Citations Count"] >= min_citations]

    if reviews_only and "Review" in df.columns:
        filtered_df = filtered_df[filtered_df["Review"] == "YES"]

    if open_access_only and "Open Access" in df.columns:
        filtered_df = filtered_df[filtered_df["Open Access"] == True]

    '''if year_range and "Publication Year" in df.columns:
        filtered_df = filtered_df[
            (filtered_df["Publication Year"] >= year_range[0]) &
            (filtered_df["Publication Year"] <= year_range[1])
        ]'''
    if year_selection and "Publication Year" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Publication Year"].isin(year_selection)
        ]


    if top_n and top_n > 0 and "Citations Count" in df.columns:
        filtered_df = filtered_df.sort_values("Citations Count", ascending=False).head(top_n)

    filtered_df = filtered_df.reset_index(drop=True)

    st.markdown("### Select papers to proceed")

    # ---------------- Row selection ----------------
    selection = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun",
    )

    selected_rows = selection.get("selection", {}).get("rows", [])

    if selected_rows:
        selected_df = filtered_df.iloc[selected_rows].reset_index(drop=True)
        st.success(f"{len(selected_df)} rows selected")
        return selected_df

    st.info("No rows selected yet — showing filtered results.")
    return filtered_df
