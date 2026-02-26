import altair as alt

# Section 1 visuals
MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTH_TICK_VALUES = [1, 3, 5, 7, 9, 11]
MONTH_LABEL_EXPR = (
    "datum.value == 1 ? 'Jan' : "
    "datum.value == 2 ? 'Feb' : "
    "datum.value == 3 ? 'Mar' : "
    "datum.value == 4 ? 'Apr' : "
    "datum.value == 5 ? 'May' : "
    "datum.value == 6 ? 'Jun' : "
    "datum.value == 7 ? 'Jul' : "
    "datum.value == 8 ? 'Aug' : "
    "datum.value == 9 ? 'Sep' : "
    "datum.value == 10 ? 'Oct' : "
    "datum.value == 11 ? 'Nov' : 'Dec'"
)


def group_time(df, year="ALL", month="ALL"):
    if month != "ALL":
        d = df.dropna(subset=["order_date"]).copy()
        d["day"] = d["order_date"].dt.day
        g_time = (
            d.groupby("day", dropna=True)
            .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"))
            .reset_index()
            .sort_values("day")
        )
    elif year != "ALL":
        g_time = (
            df.dropna(subset=["month_num", "month_name"])
            .groupby(["month_num", "month_name"], dropna=True)
            .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"))
            .reset_index()
            .sort_values("month_num")
        )
    else:
        g_time = (
            df.groupby("year", dropna=True)
            .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"))
            .reset_index()
            .sort_values("year")
        )
        if "year" in g_time.columns:
            g_time["year"] = g_time["year"].astype(int)
    g_time["margin"] = g_time["total_profit"] / g_time["total_sales"]
    return g_time

def group_category(df):
    g_cat = (
    df.groupby("category")
      .agg(sales=("sales","sum"),
           profit=("profit","sum"))
      .reset_index()
    )
    return g_cat

def sales_trend(df, year="ALL", month="ALL", width=260, height=120):
    g_time = group_time(df, year=year, month=month)
    if month != "ALL":
        x_encoding = alt.X("day:Q", title="Day", axis=alt.Axis(tickMinStep=1, format="d", grid=False))
        x_tooltip = alt.Tooltip("day:Q", title="Day")
    elif year != "ALL":
        x_encoding = alt.X(
            "month_num:Q",
            title="Month",
            axis=alt.Axis(values=MONTH_TICK_VALUES, labelExpr=MONTH_LABEL_EXPR, grid=False),
        )
        x_tooltip = alt.Tooltip("month_name:N", title="Month")
    else:
        x_encoding = alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0, grid=False))
        x_tooltip = alt.Tooltip("year:O", title="Year")
    return (
        alt.Chart(g_time)
        .mark_line(point=True)
        .encode(
            x=x_encoding,
            y=alt.Y("total_sales:Q", title="Total Sales", axis=alt.Axis(grid=False), scale=alt.Scale(zero=False)),
            tooltip=[
                x_tooltip,
                alt.Tooltip("total_sales:Q", title="Total Sales"),
            ],
        )
        .properties(width=width, height=height, title="Total Sales")
    )

def profit_trend(df, year="ALL", month="ALL", width=260, height=120):
    g_time = group_time(df, year=year, month=month)
    if month != "ALL":
        x_encoding = alt.X("day:Q", title="Day", axis=alt.Axis(tickMinStep=1, format="d", grid=False))
        x_tooltip = alt.Tooltip("day:Q", title="Day")
    elif year != "ALL":
        x_encoding = alt.X(
            "month_num:Q",
            title="Month",
            axis=alt.Axis(values=MONTH_TICK_VALUES, labelExpr=MONTH_LABEL_EXPR, grid=False),
        )
        x_tooltip = alt.Tooltip("month_name:N", title="Month")
    else:
        x_encoding = alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0, grid=False))
        x_tooltip = alt.Tooltip("year:O", title="Year")
    return (
        alt.Chart(g_time).mark_line(point=True)
        .encode(
            x=x_encoding,
            y=alt.Y("total_profit:Q", axis=alt.Axis(grid=False), scale=alt.Scale(zero=False)),
            tooltip=[x_tooltip, alt.Tooltip("total_profit:Q", title="Total Profit")]
        )
        .properties(width=width, height=height, title="Total Profit")
    )

def margin_trend(df, year="ALL", month="ALL", width=260, height=120):
    g_time = group_time(df, year=year, month=month)
    if month != "ALL":
        x_encoding = alt.X("day:Q", title="Day", axis=alt.Axis(tickMinStep=1, format="d", grid=False))
        x_tooltip = alt.Tooltip("day:Q", title="Day")
    elif year != "ALL":
        x_encoding = alt.X(
            "month_num:Q",
            title="Month",
            axis=alt.Axis(values=MONTH_TICK_VALUES, labelExpr=MONTH_LABEL_EXPR, grid=False),
        )
        x_tooltip = alt.Tooltip("month_name:N", title="Month")
    else:
        x_encoding = alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0, grid=False))
        x_tooltip = alt.Tooltip("year:O", title="Year")
    return (
        alt.Chart(g_time)
        .mark_line(point=True)
        .encode(
            x=x_encoding,
            y=alt.Y("margin:Q", axis=alt.Axis(format="%", grid=False), scale=alt.Scale(zero=False)),
            tooltip=[x_tooltip, alt.Tooltip("margin:Q", format=".2%", title="Avg Profit Margin")]
        )
        .properties(width=width, height=height, title="Avg Profit Margin"
        )
    )

def catagory_sales(df, width=260, height=120):
    g_cat = group_category(df)
    return (
        alt.Chart(g_cat)
        .mark_bar()
        .encode(
            y=alt.Y("category:N", sort="-x", axis=alt.Axis(grid=False)),
            x=alt.X("sales:Q", axis=alt.Axis(grid=False)),
            color="category:N",
            tooltip=["sales","profit"]
        )
        .properties(width=width, height=height, title="Category Sales")
    )

def discount_margin(df, width=420, height=130):
    return (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("discount:Q", bin=alt.Bin(maxbins=10), title="Discount Bin", axis=alt.Axis(format=".0%", grid=False)),
            y=alt.Y("margin:Q", aggregate="mean", title="Mean Margin", axis=alt.Axis(format=".0%", grid=False)),
            tooltip=[alt.Tooltip("mean(margin):Q", title="Mean Margin", format=".2%")],
        )
        .properties(width=width, height=height, title="Discount vs Margin (Binned Mean)")
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
            x=alt.X("total_profit:Q", title="Total Profit", axis=alt.Axis(grid=False)),
            y=alt.Y(
                "product_name:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=140, grid=False),
            ),
            color=alt.Color(
                "category:N",
                title="Category",
                legend=alt.Legend(orient="right", labelLimit=120, titleLimit=120),
            ),
            tooltip=[
                "product_name:N",
                alt.Tooltip("total_profit:Q", format=",.0f"),
                alt.Tooltip("avg_margin:Q", format=".2%")
            ],
            opacity=alt.condition(sel, alt.value(1), alt.value(0.35)),
        )
        .add_params(sel)
        .properties(width=width, height=height, title="Top 10 by Profit")
    )
    max_count = int(co_top["co_count"].max()) if not co_top.empty else 1

    co_chart = (
        alt.Chart(co_top)
        .transform_filter(sel)
        .transform_window(
            row_number="row_number()",
            sort=[alt.SortField("co_count", order="descending")]
        )
        .transform_filter(alt.datum.row_number <= 5)
        .transform_calculate(
            product_short="length(datum.product_name_co) > 24 ? substring(datum.product_name_co, 0, 24) + '...' : datum.product_name_co",
            product_ranked="datum.row_number + '. ' + datum.product_short",
        )
        .mark_bar()
        .encode(
            x=alt.X(
                "co_count:Q",
                title="Co-purchases",
                axis=alt.Axis(values=list(range(0, max_count + 1)), grid=False)
            ),
            y=alt.Y(
                "product_ranked:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=140, grid=False),
            ),
            color=alt.Color(
                "category_co:N",
                title=None,
                legend=None,
            ),
            tooltip=["product_name_co:N", alt.Tooltip("co_count:Q", title="Co-purchases")],
        )
        .properties(width=width, height=height, title="Top 5 Co-purchases")
    )

    return hero_chart, co_chart
