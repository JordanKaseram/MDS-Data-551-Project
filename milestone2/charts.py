import altair as alt

# Section 1 visuals
def group_year(df):
    g_year = (
    df.groupby("year")
      .agg(total_sales=("sales","sum"),
           total_profit=("profit","sum"))
      .reset_index()
    )
    g_year["margin"] = g_year["total_profit"] / g_year["total_sales"]
    return g_year

def group_category(df):
    g_cat = (
    df.groupby("category")
      .agg(sales=("sales","sum"),
           profit=("profit","sum"))
      .reset_index()
    )
    return g_cat

def sales_trend(df, width=260, height=120):
    g_year = group_year(df)
    return (
        alt.Chart(g_year)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total_sales:Q", title="Total Sales", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("total_sales:Q", title="Total Sales"),
            ],
        )
        .properties(width=width, height=height, title="Total Sales")
    )

def profit_trend(df, width=260, height=120):
    g_year = group_year(df)
    return (
        alt.Chart(g_year).mark_line(point=True)
        .encode(
            x=alt.X("year:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total_profit:Q", scale=alt.Scale(zero=False)),
            tooltip=["year","total_profit"]
        )
        .properties(
        width=260, height=120, title="Total Profit"
        )
    )

def margin_trend(df, width=260, height=120):
    g_year = group_year(df)
    return (
        alt.Chart(g_year)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("margin:Q", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("margin:Q", format=".2%")]
        )
        .properties(width=260, height=120, title="Avg Profit Margin"
        )
    )

def catagory_sales(df, idth=260, height=120):
    g_cat = group_category(df)
    return (
        alt.Chart(g_cat)
        .mark_bar()
        .encode(
            y=alt.Y("category:N", sort="-x"),
            x="sales:Q",
            color="category:N",
            tooltip=["sales","profit"]
        )
        .properties(width=260, height=150, title="Category Sales")
    )

def discount_margin(df, width=260, height=120):
    return(
        alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("discount:Q", bin=alt.Bin(maxbins=10), axis=alt.Axis(format=".0%")),
        y=alt.Y("margin:Q", aggregate="mean", axis=alt.Axis(format=".0%")),
        tooltip=[alt.Tooltip("mean(margin):Q", format=".2%")]
        ).properties(title="Discount vs Margin (binned mean)", width=520, height=150)
    )


# Section 2 visuals
def hero_profitability(df, width=260, height=120):
    alt.data_transformers.disable_max_rows()

    hero = (
        df.groupby(["product_name", "category"], as_index=False)
        .agg(
            total_profit=("profit", "sum"),
            avg_margin=("margin", "mean")
        )
        .sort_values("total_profit", ascending=False)
        .head(10)
    )

    top_products = hero["product_name"].tolist()

    left = df[["order_id", "product_name"]].drop_duplicates()
    right = df[["order_id", "product_name"]].drop_duplicates()

    pairs = left.merge(right, on="order_id", suffixes=("", "_co"))
    pairs = pairs[pairs["product_name"] != pairs["product_name_co"]]

    co_counts = (
        pairs.groupby(["product_name", "product_name_co"], as_index=False)
            .size()
            .rename(columns={"size": "co_count"})
    )

    # Keep only pairs where the "left" product is one of the top 10 hero products
    co_top = co_counts[co_counts["product_name"].isin(top_products)]

    product_cat = df[["product_name", "category"]].drop_duplicates()
    co_top = co_top.merge(
        product_cat.rename(columns={"product_name": "product_name_co", "category": "category_co"}),
        on="product_name_co",
        how="left"
    )

    sel = alt.selection_point(fields=["product_name"], empty=False)  # click a bar

    hero_chart = (
        alt.Chart(hero)
        .mark_bar()
        .encode(
            x=alt.X("total_profit:Q", title="Total Profit"),
            y=alt.Y("product_name:N", sort="-x", title="Hero Product"),
            color=alt.Color("category:N", title="Category"),
            tooltip=[
                "product_name:N",
                alt.Tooltip("total_profit:Q", format=",.0f"),
                alt.Tooltip("avg_margin:Q", format=".2%")
            ],
            opacity=alt.condition(sel, alt.value(1), alt.value(0.35)),
        )
        .add_params(sel)
        .properties(width=width, height=height, title="Top 10 Products by Profitability")
    )
    max_count = int(co_top["co_count"].max())

    co_chart = (
        alt.Chart(co_top)
        .transform_filter(sel)
        .transform_window(
            row_number="row_number()",
            sort=[alt.SortField("co_count", order="descending")]
        )
        .transform_filter(alt.datum.row_number <= 5)
        .mark_bar()
        .encode(
            x=alt.X(
                "co_count:Q",
                title="Times Bought Together",
                axis=alt.Axis(values=list(range(0, max_count + 1)))
            ),
            y=alt.Y("product_name_co:N", sort="-x", title="Frequently Bought With"),
            color=alt.Color("category_co:N", title="Co-product category"),
            tooltip=["product_name_co:N", alt.Tooltip("co_count:Q", title="Co-purchases")],
        )
        .properties(width=width, height=height, title="Frequently Bought With (Top 5)")
    )

    return (hero_chart | co_chart)

