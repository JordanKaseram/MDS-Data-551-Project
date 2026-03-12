import altair as alt
import numpy as np
import pandas as pd

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
            y=alt.Y("total_profit:Q", title="Total Profit", axis=alt.Axis(grid=False), scale=alt.Scale(zero=False)),
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
            y=alt.Y("margin:Q", title="Average Profit Margin (%)", axis=alt.Axis(format="%", grid=False), scale=alt.Scale(zero=False)),
            tooltip=[x_tooltip, alt.Tooltip("margin:Q", format=".2%", title="Average Profit Margin (%)")]
        )
        .properties(width=width, height=height, title="Average Profit Margin"
        )
    )

def catagory_sales(df, width=260, height=120):
    g_cat = group_category(df)
    return (
        alt.Chart(g_cat)
        .mark_bar()
        .encode(
            y=alt.Y("category:N", title="Category", sort="-x", axis=alt.Axis(grid=False)),
            x=alt.X("sales:Q", title="Total Sales", axis=alt.Axis(grid=False)),
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
            x=alt.X("discount:Q", bin=alt.Bin(maxbins=10), title="Discount (%)", axis=alt.Axis(format=".0%", grid=False)),
            y=alt.Y("margin:Q", aggregate="mean", title="Average Profit Margin (%)", axis=alt.Axis(format=".0%", grid=False)),
            tooltip=[alt.Tooltip("mean(margin):Q", title="Average Profit Margin (%)", format=".2%")],
        )
        .properties(width=width, height=height, title="Discount vs Average Profit Margin")
    )


def section1_interactive(df, year="ALL", month="ALL", width=200, height=115):
    d = df.copy()
    if month != "ALL":
        d = d.dropna(subset=["order_date"]).copy()
        d["time_key"] = d["order_date"].dt.day
        x_title = "Day"
        x_axis = alt.Axis(tickMinStep=1, format="d", grid=False)
        x_tooltip = alt.Tooltip("time_key:Q", title="Day")
    elif year != "ALL":
        d = d.dropna(subset=["month_num"]).copy()
        d["time_key"] = d["month_num"].astype(int)
        x_title = "Month"
        x_axis = alt.Axis(values=MONTH_TICK_VALUES, labelExpr=MONTH_LABEL_EXPR, grid=False)
        x_tooltip = alt.Tooltip("time_key:Q", title="Month")
    else:
        d = d.dropna(subset=["year"]).copy()
        d["time_key"] = d["year"].astype(int)
        x_title = "Year"
        x_axis = alt.Axis(tickMinStep=1, format="d", grid=False)
        x_tooltip = alt.Tooltip("time_key:Q", title="Year")

    sel = alt.selection_point(fields=["category"], empty=True)
    x_enc = alt.X("time_key:Q", title=x_title, axis=x_axis)

    sales_chart = (
        alt.Chart(d)
        .transform_filter(sel)
        .transform_aggregate(total_sales="sum(sales)", groupby=["time_key"])
        .mark_line(point=True)
        .encode(
            x=x_enc,
            y=alt.Y("total_sales:Q", title="Total Sales", axis=alt.Axis(format="~s", grid=False), scale=alt.Scale(zero=False)),
            tooltip=[x_tooltip, alt.Tooltip("total_sales:Q", title="Total Sales", format=",.0f")],
        )
        .properties(width=width, height=height, title="Total Sales")
    )

    profit_chart = (
        alt.Chart(d)
        .transform_filter(sel)
        .transform_aggregate(total_profit="sum(profit)", groupby=["time_key"])
        .mark_line(point=True)
        .encode(
            x=x_enc,
            y=alt.Y("total_profit:Q", title="Total Profit", axis=alt.Axis(format="~s", grid=False), scale=alt.Scale(zero=False)),
            tooltip=[x_tooltip, alt.Tooltip("total_profit:Q", title="Total Profit", format=",.0f")],
        )
        .properties(width=width, height=height, title="Total Profit")
    )

    margin_chart = (
        alt.Chart(d)
        .transform_filter(sel)
        .transform_aggregate(
            total_profit="sum(profit)",
            total_sales="sum(sales)",
            groupby=["time_key"],
        )
        .transform_calculate(margin="datum.total_sales == 0 ? null : datum.total_profit / datum.total_sales")
        .mark_line(point=True)
        .encode(
            x=x_enc,
            y=alt.Y(
                "margin:Q",
                title="Average Profit Margin (%)",
                axis=alt.Axis(format="%", grid=False),
                scale=alt.Scale(zero=False),
            ),
            tooltip=[x_tooltip, alt.Tooltip("margin:Q", title="Average Profit Margin (%)", format=".2%")],
        )
        .properties(width=width, height=height, title="Average Profit Margin")
    )

    category_chart = (
        alt.Chart(d)
        .transform_aggregate(sales="sum(sales)", profit="sum(profit)", groupby=["category"])
        .mark_bar()
        .encode(
            y=alt.Y("category:N", title="Category", sort="-x", axis=alt.Axis(grid=False)),
            x=alt.X("sales:Q", title="Total Sales", axis=alt.Axis(format="~s", grid=False)),
            color=alt.condition(sel, "category:N", alt.value("#cbd5e1")),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("sales:Q", title="Total Sales", format=",.0f"),
                alt.Tooltip("profit:Q", title="Total Profit", format=",.0f"),
            ],
        )
        .add_params(sel)
        .properties(
            width=width,
            height=height,
            title=alt.TitleParams(
                text="Category Sales",
                subtitle=["Click a category to filter the other 3 charts"],
                anchor="start",
            ),
        )
    )

    return _apply_chart_theme((sales_chart | profit_chart) & (margin_chart | category_chart))


# Section 2 visuals (Product Performance)
def hero_profitability(df, width=260, height=120):
    alt.data_transformers.disable_max_rows()

    hero = (
        df.groupby(["product_name", "category"], as_index=False)
        .agg(total_profit=("profit", "sum"), total_sales=("sales", "sum"), avg_margin=("margin", "mean"))
        .sort_values("total_profit", ascending=False)
        .head(10)
    )

    if hero.empty:
        return (
            alt.Chart(pd.DataFrame({"message": ["No product-performance data for current filters"]}))
            .mark_text(color="#64748b", fontSize=12)
            .encode(text="message:N")
            .properties(width=width, height=height, title="Top 10 Products by Profit")
        )

    return (
        alt.Chart(hero)
        .transform_calculate(
            product_short=(
                "length(datum.product_name) > 32 ? "
                "substring(datum.product_name, 0, 32) + '...' : datum.product_name"
            )
        )
        .mark_bar()
        .encode(
            x=alt.X("total_profit:Q", title="Total Profit", axis=alt.Axis(format="~s", grid=False)),
            y=alt.Y("product_short:N", sort="-x", title="Product Name", axis=alt.Axis(labelLimit=220, grid=False)),
            color=alt.Color(
                "category:N",
                title="Category",
                legend=alt.Legend(orient="right", labelLimit=120, titleLimit=120),
            ),
            tooltip=[
                alt.Tooltip("product_name:N", title="Product"),
                alt.Tooltip("total_profit:Q", title="Total Profit", format=",.0f"),
                alt.Tooltip("total_sales:Q", title="Total Sales", format=",.0f"),
                alt.Tooltip("avg_margin:Q", title="Average Profit Margin", format=".2%"),
            ],
        )
        .properties(width=width, height=height, title="Top 10 Products by Profit")
    )


# Section 3 visuals (Basket & Pricing Intelligence)
def co_purchase_chart(df, top_n=8, width=520, height=220):
    required = {"order_id", "product_name", "category"}
    if not required.issubset(df.columns):
        return (
            alt.Chart(pd.DataFrame({"message": ["Co-purchase data unavailable"]}))
            .mark_text(color="#64748b", fontSize=12)
            .encode(text="message:N")
            .properties(width=width, height=height, title="Top Co-Purchases")
        )

    orders = df[["order_id", "product_name", "category"]].dropna().drop_duplicates()
    left = orders.rename(columns={"product_name": "product_left"})
    right = orders.rename(columns={"product_name": "product_co", "category": "category_co"})

    pairs = left.merge(right, on="order_id")
    pairs = pairs[pairs["product_left"] != pairs["product_co"]]

    co_top = (
        pairs.groupby(["product_co", "category_co"], as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "co_orders"})
        .sort_values("co_orders", ascending=False)
        .head(top_n)
    )

    if co_top.empty:
        return (
            alt.Chart(pd.DataFrame({"message": ["No co-purchase data for current filters"]}))
            .mark_text(color="#64748b", fontSize=12)
            .encode(text="message:N")
            .properties(width=width, height=height, title="Top Co-Purchases")
        )

    return (
        alt.Chart(co_top)
        .transform_window(row_number="row_number()", sort=[alt.SortField("co_orders", order="descending")])
        .transform_calculate(
            product_short=(
                "length(datum.product_co) > 28 ? "
                "substring(datum.product_co, 0, 28) + '...' : datum.product_co"
            ),
            product_ranked="datum.row_number + '. ' + datum.product_short",
        )
        .mark_bar()
        .encode(
            x=alt.X("co_orders:Q", title="Co-Purchase Orders", axis=alt.Axis(tickMinStep=1, grid=False)),
            y=alt.Y(
                "product_ranked:N",
                sort="-x",
                title="Co-Product Rank",
                axis=alt.Axis(labelLimit=220, grid=False),
            ),
            color=alt.Color("category_co:N", title="Category"),
            tooltip=[
                alt.Tooltip("product_co:N", title="Product"),
                alt.Tooltip("co_orders:Q", title="Co-Purchase Orders"),
            ],
        )
        .properties(width=width, height=height, title="Top Co-Purchases")
    )



# -----------------------------
# Helpers
# -----------------------------
def _safe_div(a, b):
    return np.where(b != 0, a / b, np.nan)

def _kpi_value(label: str, value: str, width=155):
    data = pd.DataFrame({"label": [label], "value": [value]})

    v = (
        alt.Chart(data)
        .mark_text(align="left", fontSize=18, fontWeight="bold")
        .encode(text="value:N")
        .properties(width=width, height=26)
    )

    l = (
        alt.Chart(data)
        .mark_text(align="left", dy=18, fontSize=11, opacity=0.8)
        .encode(text="label:N")
        .properties(width=width, height=26)
    )
    return v + l

def _apply_chart_theme(chart):
    # Presentation-first theme: larger labels and stronger contrast.
    return (
        chart
        .configure_view(strokeOpacity=0)
        .configure_axis(
            grid=False,
            labelColor="#334155",
            titleColor="#334155",
            labelFontSize=15,
            titleFontSize=15,
        )
        .configure_title(
            anchor="start",
            color="#0f172a",
            fontSize=20,
            fontWeight="bold",
        )
        .configure_legend(
            labelColor="#334155",
            titleColor="#334155",
            labelFontSize=14,
            titleFontSize=15,
        )
    )


# 2) Subcategory discovery bubble
# x = frequency (% orders), y = margin %, size = sales, color = category
# -----------------------------
def subcat_bubble(
    df_f: pd.DataFrame,
    width: int = 640,
    height: int = 340,
    show_quadrants: bool = True,
    show_highlight: bool = True,
) -> alt.LayerChart:
    total_orders = df_f["order_id"].nunique()
    g = (
        df_f.groupby(["category", "sub_category"], as_index=False)
        .agg(orders=("order_id", "nunique"), sales=("sales", "sum"), profit=("profit", "sum"))
    )

    g["freq_pct"] = _safe_div(g["orders"], total_orders) * 100
    g["margin_pct"] = _safe_div(g["profit"], g["sales"]) * 100
    g = g.replace([np.inf, -np.inf], np.nan).dropna(subset=["margin_pct", "freq_pct"])

    x_med = float(g["freq_pct"].median())
    y_med = float(g["margin_pct"].median())

    points = (
        alt.Chart(g)
        .mark_circle(opacity=0.78, stroke="white", strokeWidth=0.6)
        .encode(
            x=alt.X("freq_pct:Q", title="Purchase Frequency (% of Orders)"),
            y=alt.Y("margin_pct:Q", title="Profit Margin (%)"),
            size=alt.Size("sales:Q", scale=alt.Scale(range=[40, 1200]), title="Sales"),
            color=alt.Color("category:N", title="Category"),
            tooltip=[
                "category:N",
                "sub_category:N",
                alt.Tooltip("freq_pct:Q", format=".2f", title="Purchase Frequency (%)"),
                alt.Tooltip("margin_pct:Q", format=".2f", title="Profit Margin (%)"),
                alt.Tooltip("sales:Q", format=",.0f", title="Sales"),
            ],
        )
        .properties(width=width, height=height, title="Subcategory Discovery (Frequency vs Profit Margin)")
    )

    labels = (
        alt.Chart(g)
        .mark_text(align="left", dx=7, dy=-7, fontSize=12, color="#0f172a")
        .encode(x="freq_pct:Q", y="margin_pct:Q", text="sub_category:N")
    )

    vline = alt.Chart(pd.DataFrame({"x": [x_med]})).mark_rule(strokeDash=[6, 6], opacity=0.5).encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [y_med]})).mark_rule(strokeDash=[6, 6], opacity=0.5).encode(y="y:Q")

    # ---- Strategy overlays: quadrant labels + highlight ----
    overlay = alt.LayerChart()

    if show_highlight and len(g) > 0:
        # Opportunity = high margin among below-median frequency
        try:
            candidates = g[g["freq_pct"] <= x_med].copy()
            opp = (
                candidates.sort_values("margin_pct", ascending=False).head(1)
                if not candidates.empty
                else g.sort_values("margin_pct", ascending=False).head(1)
            )

            highlight = alt.Chart(opp).mark_point(
                filled=False, size=600, strokeWidth=3, opacity=0.9
            ).encode(x="freq_pct:Q", y="margin_pct:Q")

            highlight_lbl = alt.Chart(opp).mark_text(
                align="left",
                dx=10,
                dy=-10,
                fontSize=12,
                fontWeight="bold",
                color="#0f172a",
            ).encode(x="freq_pct:Q", y="margin_pct:Q", text=alt.value("Opportunity"))

            overlay = overlay + highlight + highlight_lbl
        except Exception:
            pass

    if show_quadrants and len(g) > 0:
        try:
            quad_df = pd.DataFrame(
                {
                    "x": [x_med * 0.35, x_med * 0.35, x_med * 1.25, x_med * 1.25],
                    "y": [y_med * 1.25, y_med * 0.35, y_med * 1.25, y_med * 0.35],
                    "label": [
                        "Promote (High M / Low F)",
                        "Review (Low M / Low F)",
                        "Hero (High M / High F)",
                        "Fix (Low M / High F)",
                    ],
                }
            )
            quad = alt.Chart(quad_df).mark_text(
                fontSize=12,
                fontWeight="bold",
                opacity=0.55,
                color="#334155",
            ).encode(x="x:Q", y="y:Q", text="label:N")

            overlay = overlay + quad
        except Exception:
            pass

    return _apply_chart_theme(points + labels + vline + hline + overlay)

# -----------------------------
# 3) Product panel (Top 5 products sorted by margin%)
# label col + 3 bars: margin%, sales, #customers
# -----------------------------
def top_products_panel(
    df_f: pd.DataFrame,
    top_n: int = 5,
    label_width: int = 300,
    metric_width: int = 120,
    sales_width: int | None = None,
    customers_width: int | None = None,
    panel_height: int = 220,
    # Backward/alternate aliases (safe to ignore if unused)
    m_width: int | None = None,
    s_width: int | None = None,
    c_width: int | None = None,
) -> alt.ConcatChart:
    # --- width alias handling ---
    if m_width is not None:
        metric_width = m_width
    if s_width is not None:
        sales_width = s_width
    if c_width is not None:
        customers_width = c_width
    if sales_width is None:
        sales_width = metric_width
    if customers_width is None:
        customers_width = metric_width

    if "customer_name" in df_f.columns:
        cust_agg = ("customer_name", "nunique")
    else:
        cust_agg = ("order_id", "nunique")

    prod = (
        df_f.groupby(["sub_category", "product_name"], as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), customers=cust_agg)
    )
    prod["margin_pct"] = _safe_div(prod["profit"], prod["sales"]) * 100
    prod = prod.replace([np.inf, -np.inf], np.nan).dropna(subset=["margin_pct"])

    top = prod.sort_values("margin_pct", ascending=False).head(top_n).copy()
    top["label"] = top["sub_category"] + " • " + top["product_name"]
    top["label_short"] = np.where(
        top["label"].str.len() > 52,
        top["label"].str.slice(0, 52) + "...",
        top["label"],
    )

    y_shared = alt.Y(
        "label_short:N",
        sort=alt.SortField(field="margin_pct", order="descending"),
        title=None,
        axis=None,
    )

    label_col = (
        alt.Chart(top)
        .mark_text(align="right", baseline="middle", color="#334155", dx=-4)
        .encode(
            y=y_shared,
            x=alt.value(label_width),
            text="label_short:N",
            tooltip=[alt.Tooltip("label:N", title="Product")],
        )
        .properties(width=label_width, height=panel_height)
    )

    m_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=y_shared,
            x=alt.X("margin_pct:Q", title="Profit Margin (%)"),
            tooltip=[
                alt.Tooltip("label:N", title="Product"),
                alt.Tooltip("margin_pct:Q", title="Profit Margin (%)", format=".2f"),
                alt.Tooltip("sales:Q", title="Total Sales", format=",.0f"),
                alt.Tooltip("customers:Q", title="Customers"),
            ],
        )
        .properties(width=metric_width, height=panel_height, title=alt.TitleParams("Profit Margin (%)", anchor="middle"))
    )

    s_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=y_shared,
            x=alt.X("sales:Q", title="Total Sales"),
            tooltip=[
                alt.Tooltip("label:N", title="Product"),
                alt.Tooltip("sales:Q", title="Total Sales", format=",.0f"),
            ],
        )
        .properties(width=sales_width, height=panel_height, title=alt.TitleParams("Total Sales", anchor="middle"))
    )

    c_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=y_shared,
            x=alt.X("customers:Q", title="Customers"),
            tooltip=[
                alt.Tooltip("label:N", title="Product"),
                alt.Tooltip("customers:Q", title="Customers"),
            ],
        )
        .properties(width=customers_width, height=panel_height, title=alt.TitleParams("Customers", anchor="middle"))
    )

    panel = (
        alt.hconcat(label_col, m_bar, s_bar, c_bar, spacing=12)
        .resolve_scale(y="shared")
        .properties(title="Top Products (Sorted by Profit Margin)")
    )
    return _apply_chart_theme(panel)


def top_products_panel_present(
    df_f: pd.DataFrame,
    top_n: int = 10,
    label_width: int = 210,
    metric_width: int = 145,
    sales_width: int = 200,
    customers_width: int = 145,
    panel_height: int = 460,
) -> alt.ConcatChart:
    if "customer_name" in df_f.columns:
        cust_agg = ("customer_name", "nunique")
    else:
        cust_agg = ("order_id", "nunique")

    prod = (
        df_f.groupby(["sub_category", "product_name"], as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), customers=cust_agg)
    )
    prod["margin_pct"] = _safe_div(prod["profit"], prod["sales"]) * 100
    prod = prod.replace([np.inf, -np.inf], np.nan).dropna(subset=["margin_pct"])

    if prod.empty:
        empty = (
            alt.Chart(pd.DataFrame({"message": ["No product data for the current bubble focus"]}))
            .mark_text(align="center", baseline="middle", fontSize=18, color="#64748b")
            .encode(text="message:N")
            .properties(
                width=label_width + metric_width + sales_width + customers_width,
                height=min(panel_height, 140),
            )
        )
        return _apply_chart_theme(empty)

    top = prod.sort_values("margin_pct", ascending=False).head(top_n).copy()
    top["label"] = top["sub_category"] + " | " + top["product_name"]
    max_label_chars = 36
    top["label_short"] = top["label"].map(
        lambda s: s if len(s) <= max_label_chars else s[: max_label_chars - 3].rstrip() + "..."
    )
    top["margin_label"] = top["margin_pct"].map(lambda v: f"{v:.1f}%")
    top["sales_label"] = top["sales"].map(lambda v: f"${v:,.0f}")
    top["customers_label"] = top["customers"].map(lambda v: f"{int(v):,}")

    y_shared = alt.Y(
        "label_short:N",
        sort=alt.SortField(field="margin_pct", order="descending"),
        title=None,
        axis=None,
    )

    label_col = (
        alt.Chart(top)
        .mark_text(align="left", baseline="middle", color="#334155", dx=0, fontSize=11, fontWeight="bold")
        .encode(
            y=y_shared,
            x=alt.value(0),
            text="label_short:N",
            tooltip=[alt.Tooltip("label:N", title="Product")],
        )
        .properties(width=label_width, height=panel_height)
    )

    def _metric_bar(value_field, label_field, title_text, width, color):
        bars = (
            alt.Chart(top)
            .mark_bar(cornerRadiusEnd=5, color=color)
            .encode(
                y=y_shared,
                x=alt.X(
                    f"{value_field}:Q",
                    title=title_text,
                    axis=alt.Axis(grid=True, gridColor="#e2e8f0", labelFontSize=10, titleFontSize=10),
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Product"),
                    alt.Tooltip(
                        f"{value_field}:Q",
                        title=title_text,
                        format=",.2f" if value_field == "margin_pct" else ",.0f",
                    ),
                    alt.Tooltip("sales:Q", title="Total Sales", format=",.0f"),
                    alt.Tooltip("customers:Q", title="Customers"),
                ],
            )
            .properties(width=width, height=panel_height, title=alt.TitleParams(title_text, anchor="middle"))
        )
        labels = (
            alt.Chart(top)
            .mark_text(align="left", baseline="middle", dx=2, color="#1e293b", fontSize=9, fontWeight="bold")
            .encode(
                y=y_shared,
                x=alt.X(f"{value_field}:Q"),
                text=f"{label_field}:N",
            )
        )
        return bars + labels

    m_bar = _metric_bar("margin_pct", "margin_label", "Profit Margin (%)", metric_width, "#315f93")
    s_bar = _metric_bar("sales", "sales_label", "Total Sales", sales_width, "#1d8f80")
    c_bar = _metric_bar("customers", "customers_label", "Customers", customers_width, "#d97706")

    note = (
        alt.Chart(pd.DataFrame({"note": ["Top 10 products. Click or select bubbles above to filter this panel."]}))
        .mark_text(align="left", baseline="top", fontSize=10, color="#64748b")
        .encode(text="note:N")
        .properties(width=label_width + metric_width + sales_width + customers_width + 18, height=16)
    )

    panel = (
        alt.vconcat(
            note,
            alt.hconcat(label_col, m_bar, s_bar, c_bar, spacing=6).resolve_scale(y="shared"),
            spacing=6,
        )
    )
    return _apply_chart_theme(panel)

# -----------------------------
# 4) Discount guardrail heatmap (strategy bins)
# -----------------------------
def discount_guardrail(df_f: pd.DataFrame, top_n: int = 15, width: int = 820, height: int = 360) -> alt.Chart:
    d = df_f.copy()
    d["discount"] = pd.to_numeric(d["discount"], errors="coerce")
    d = d.dropna(subset=["sub_category", "order_id", "sales", "profit", "discount"])

    bins = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 1.00]
    labels = ["0–5%", "5–10%", "10–15%", "15–20%", "20–25%", "25–35%", ">35%"]
    d["disc_bin"] = pd.cut(d["discount"], bins=bins, labels=labels, include_lowest=True)
    d = d.dropna(subset=["disc_bin"])

    disc = (
        d.groupby(["sub_category", "disc_bin"], observed=True)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    disc["margin_pct"] = _safe_div(disc["profit"], disc["sales"]) * 100
    disc = disc.replace([np.inf, -np.inf], np.nan).dropna(subset=["margin_pct", "disc_bin"])

    # stability filter
    disc = disc[(disc["orders"] >= 20) & (disc["sales"] >= 3000)].copy()

    top_subcats = (
        d.groupby("sub_category")["sales"].sum().sort_values(ascending=False).head(top_n).index
    )
    disc_top = disc[disc["sub_category"].isin(top_subcats)].copy()
    disc_top["disc_bin"] = disc_top["disc_bin"].astype(str)
    if disc_top.empty:
        empty = (
            alt.Chart(pd.DataFrame({"message": ["No discount-bin data for current filters"]}))
            .mark_text(align="center", baseline="middle", fontSize=14, color="#334155")
            .encode(text="message:N")
            .properties(width=width, height=min(height, 140))
        )
        return _apply_chart_theme(empty)

    # sort rows by worst margin in >35%
    sens = disc_top[disc_top["disc_bin"] == ">35%"][["sub_category", "margin_pct"]]
    row_order = sens.sort_values("margin_pct")["sub_category"].tolist() if len(sens) else list(top_subcats)

    CLAMP = 40
    disc_top["margin_clamped"] = disc_top["margin_pct"].clip(-CLAMP, CLAMP)

    heat = (
        alt.Chart(disc_top)
        .mark_rect(stroke="#ffffff", strokeWidth=0.35)
        .encode(
            x=alt.X(
                "disc_bin:N",
                sort=labels,
                title="Discount Bucket (%)",
                axis=alt.Axis(
                    labelAngle=0,
                    labelAlign="center",
                    labelBaseline="top",
                    labelPadding=6,
                    labelOverlap=False,
                    labelFontSize=13,
                    labelFontWeight="bold",
                    titleFontSize=13,
                    titleFontWeight="bold",
                    labelLimit=100,
                ),
            ),
            y=alt.Y(
                "sub_category:N",
                sort=row_order,
                title="Subcategory",
                axis=alt.Axis(
                    labelFontSize=14,
                    labelFontWeight="bold",
                    titleFontSize=13,
                    titleFontWeight="bold",
                    labelLimit=180,
                    labelPadding=4,
                ),
            ),
            color=alt.Color(
                "margin_clamped:Q",
                title="Profit Margin (%)",
                scale=alt.Scale(scheme="redblue", domain=[-CLAMP, CLAMP], domainMid=0),
                legend=alt.Legend(orient="right", gradientLength=90, titleFontSize=10, labelFontSize=9),
            ),
            tooltip=[
                "sub_category:N",
                "disc_bin:N",
                alt.Tooltip("orders:Q", format=",.0f", title="Orders"),
                alt.Tooltip("sales:Q", format=",.0f", title="Total Sales"),
                alt.Tooltip("margin_pct:Q", format=".2f", title="Profit Margin (%)"),
            ],
        )
        .properties(
            width=width,
            height=height,
            padding={"left": 94, "right": 36, "top": 8, "bottom": 38},
        )
    )

    return _apply_chart_theme(heat)

# -----------------------------
# 5) Bundle table chart (Altair table-style with lift highlighted)
# Input is already prepared mba_table_df with columns:
# sub_cat1, sub_cat2, support, confidence, lift
# -----------------------------
def bundle_table_chart(mba_table_df: pd.DataFrame, top_n: int = 10) -> alt.ConcatChart:
    d = mba_table_df.head(top_n).copy()
    d["row"] = range(1, len(d) + 1)
    y = alt.Y("row:O", axis=None)

    c1 = alt.Chart(d).mark_text(align="left", baseline="middle", color="#0f172a").encode(y=y, text="sub_cat1:N")\
        .properties(width=140, title="Subcategory 1")
    c2 = alt.Chart(d).mark_text(align="left", baseline="middle", color="#0f172a").encode(y=y, text="sub_cat2:N")\
        .properties(width=140, title="Subcategory 2")
    c3 = alt.Chart(d).mark_text(align="right", baseline="middle", color="#0f172a").encode(y=y, text=alt.Text("support:Q", format=".2f"))\
        .properties(width=90, title="Support (%)")
    c4 = alt.Chart(d).mark_text(align="right", baseline="middle", color="#0f172a").encode(y=y, text=alt.Text("confidence:Q", format=".2f"))\
        .properties(width=95, title="Confidence (%)")

    lift_bg = alt.Chart(d).mark_rect().encode(
        y=y, x=alt.value(0), x2=alt.value(1),
        color=alt.Color("lift:Q", scale=alt.Scale(scheme="blues"), legend=None)
    ).properties(width=80)

    lift_text = alt.Chart(d).mark_text(align="right", baseline="middle", color="#111").encode(
        y=y, text=alt.Text("lift:Q", format=".2f")
    ).properties(width=80, title="Lift")

    table = alt.hconcat(c1, c2, c3, c4, lift_bg + lift_text, spacing=12)\
        .resolve_scale(y="shared")\
        .properties(title="Top Bundle Pairs (Lift Highlighted)")

    return _apply_chart_theme(table)
