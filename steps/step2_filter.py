import pandas as pd


def filter_dataframe(
    df,
    min_citations=None,
    reviews_only=False,
    open_access_only=False,
    year_range=None,
    top_n=None
):
    filtered = df.copy()

    if min_citations is not None:
        filtered = filtered[filtered["Citations Count"] >= min_citations]

    if reviews_only:
        filtered = filtered[filtered["Review"] == "YES"]

    if open_access_only:
        filtered = filtered[filtered["Open Access"] == True]

    if year_range:
        filtered = filtered[
            (filtered["Publication Year"] >= year_range[0]) &
            (filtered["Publication Year"] <= year_range[1])
        ]

    if top_n:
        filtered = filtered.sort_values("Citations Count", ascending=False).head(top_n)

    return filtered.reset_index(drop=True)
