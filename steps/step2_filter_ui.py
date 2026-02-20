import streamlit as st
import pandas as pd


def step2_filter_ui(df: pd.DataFrame):

    st.subheader("Filter & Select Papers")

    # ---------------- Safety: Empty DF ----------------
    if df is None or df.empty:
        st.warning("No data available to filter.")
        return pd.DataFrame()

    # ---------------- Filters ----------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_citations = st.number_input("Min citations", min_value=0, value=0)

    with col2:
        reviews_only = st.checkbox("Reviews only")

    with col3:
        open_access_only = st.checkbox("Open access only")

    with col4:
        top_n = st.number_input("Top N (0 = all)", min_value=0, value=0)

    # ---------------- Year Filter (Safe Version) ----------------
    year_range = None

    if "Publication Year" in df.columns:
        year_series = pd.to_numeric(df["Publication Year"], errors="coerce").dropna()

        if not year_series.empty:
            year_min = int(year_series.min())
            year_max = int(year_series.max())

            if year_min < year_max:
                year_range = st.slider(
                    "Year range",
                    min_value=year_min,
                    max_value=year_max,
                    value=(year_min, year_max),
                )
            else:
                # Only one unique year
                year_range = (year_min, year_max)
                st.info(f"All papers are from {year_min}.")
        else:
            st.warning("Publication Year column contains no valid numeric values.")

    # ---------------- Filtering Logic ----------------
    filtered_df = df.copy()

    if "Citations Count" in filtered_df.columns:
        filtered_df = filtered_df[
            pd.to_numeric(filtered_df["Citations Count"], errors="coerce").fillna(0)
            >= min_citations
        ]

    if reviews_only and "Review" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Review"] == "YES"]

    if open_access_only and "Open Access" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Open Access"] == True]

    if year_range and "Publication Year" in filtered_df.columns:
        filtered_df = filtered_df[
            (pd.to_numeric(filtered_df["Publication Year"], errors="coerce") >= year_range[0]) &
            (pd.to_numeric(filtered_df["Publication Year"], errors="coerce") <= year_range[1])
        ]

    if top_n and top_n > 0 and "Citations Count" in filtered_df.columns:
        filtered_df = (
            filtered_df.sort_values("Citations Count", ascending=False)
            .head(top_n)
        )

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
