# src/charts.py
import numpy as np
import pandas as pd
import altair as alt

alt.data_transformers.disable_max_rows()

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

def _apply_dark_theme(chart: alt.Chart | alt.LayerChart | alt.ConcatChart):
    return (
        chart.configure(background="#151823")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#d7dbe7",
            titleColor="#d7dbe7",
            gridColor="#2a2f3a",
            tickColor="#2a2f3a",
        )
        .configure_legend(
            labelColor="#d7dbe7",
            titleColor="#d7dbe7",
        )
        .configure_title(color="#d7dbe7", anchor="start")
    )

# -----------------------------
# 1) KPI strip (top bar)
# -----------------------------
def _kpi_tile(label, value, width=160, height=60):
    data = pd.DataFrame({"label": [label], "value": [value]})

    value_layer = (
        alt.Chart(data)
        .mark_text(align="left", baseline="top", fontSize=20, fontWeight="bold", color="#e6e6e6")
        .encode(text="value:N")
        .properties(width=width, height=height)
    )

    label_layer = (
        alt.Chart(data)
        .mark_text(align="left", baseline="top", dy=28, fontSize=12, color="#b8bdc9")
        .encode(text="label:N")
        .properties(width=width, height=height)
    )

    return value_layer + label_layer


def kpi_strip(d):
    total_sales = d["sales"].sum()
    total_profit = d["profit"].sum()
    avg_margin = (total_profit / total_sales * 100) if total_sales != 0 else np.nan
    avg_discount = d["discount"].mean() * 100 if "discount" in d.columns else np.nan

    # frequency = avg line items per order
    freq = d.groupby("order_id").size().mean() if "order_id" in d.columns else np.nan

    # avg products per txn = avg unique product_name per order
    if "product_name" in d.columns and "order_id" in d.columns:
        avg_prod_txn = d.groupby("order_id")["product_name"].nunique().mean()
    else:
        avg_prod_txn = np.nan

    n_customers = d["customer_name"].nunique() if "customer_name" in d.columns else d["order_id"].nunique()

    row = alt.hconcat(
        _kpi_tile("Total Customers", f"{int(n_customers):,}"),
        _kpi_tile("Revenue", f"${total_sales:,.0f}"),
        _kpi_tile("Profit", f"${total_profit:,.0f}"),
        _kpi_tile("Margin %", f"{avg_margin:.1f}%"),
        _kpi_tile("Discount %", f"{avg_discount:.1f}%"),
        _kpi_tile("Avg Frequency", f"{freq:.2f}"),
        _kpi_tile("Avg Products/Txn", f"{avg_prod_txn:.2f}"),
        spacing=18
    ).properties(
        title="Campaign Optimize Profit Strategy"
    )

    return _apply_dark_theme(row)

# -----------------------------
# 2) Subcategory discovery bubble
# x = frequency (% orders), y = margin %, size = sales, color = category
# -----------------------------
def subcat_bubble(df_f: pd.DataFrame) -> alt.LayerChart:
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
            x=alt.X("freq_pct:Q", title="Purchase frequency (% of orders)"),
            y=alt.Y("margin_pct:Q", title="Margin %"),
            size=alt.Size("sales:Q", scale=alt.Scale(range=[40, 1200]), title="Sales"),
            color=alt.Color("category:N", title="Category"),
            tooltip=[
                "category:N",
                "sub_category:N",
                alt.Tooltip("freq_pct:Q", format=".2f", title="Freq %"),
                alt.Tooltip("margin_pct:Q", format=".2f", title="Margin %"),
                alt.Tooltip("sales:Q", format=",.0f", title="Sales"),
            ],
        )
        .properties(width=640, height=340, title="Subcategory Discovery (Freq vs Margin)")
    )

    labels = (
        alt.Chart(g)
        .mark_text(align="left", dx=7, dy=-7, fontSize=10, color="#d7dbe7")
        .encode(x="freq_pct:Q", y="margin_pct:Q", text="sub_category:N")
    )

    vline = alt.Chart(pd.DataFrame({"x": [x_med]})).mark_rule(strokeDash=[6, 6], opacity=0.5).encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [y_med]})).mark_rule(strokeDash=[6, 6], opacity=0.5).encode(y="y:Q")

    return _apply_dark_theme(points + labels + vline + hline)

# -----------------------------
# 3) Product panel (Top 5 products sorted by margin%)
# label col + 3 bars: margin%, sales, #customers
# -----------------------------
def top_products_panel(df_f: pd.DataFrame, top_n: int = 5) -> alt.ConcatChart:
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

    y_lbl = alt.Y(
        "label:N",
        sort=alt.SortField(field="margin_pct", order="descending"),
        title=None,
        axis=alt.Axis(labelLimit=380),
    )
    y_none = alt.Y("label:N", sort=alt.SortField(field="margin_pct", order="descending"), title=None, axis=None)

    label_col = (
        alt.Chart(top)
        .mark_text(align="left", baseline="middle", color="#d7dbe7")
        .encode(y=y_lbl, text="label:N")
        .properties(width=360, height=220, title="Top products (sorted by margin%)")
    )

    m_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(y=y_none, x=alt.X("margin_pct:Q", title="Margin %"))
        .properties(width=170, height=220, title="Margin %")
    )

    s_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(y=y_none, x=alt.X("sales:Q", title="Sales"))
        .properties(width=170, height=220, title="Sales")
    )

    c_bar = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(y=y_none, x=alt.X("customers:Q", title="# Customers"))
        .properties(width=170, height=220, title="# Customers")
    )

    panel = alt.hconcat(label_col, m_bar, s_bar, c_bar, spacing=12).resolve_scale(y="shared")
    return _apply_dark_theme(panel)

# -----------------------------
# 4) Discount guardrail heatmap (strategy bins)
# -----------------------------
def discount_guardrail(df_f: pd.DataFrame, top_n: int = 15) -> alt.Chart:
    d = df_f.copy()
    d["discount"] = pd.to_numeric(d["discount"], errors="coerce")

    bins = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 1.00]
    labels = ["0–5%", "5–10%", "10–15%", "15–20%", "20–25%", "25–35%", ">35%"]
    d["disc_bin"] = pd.cut(d["discount"], bins=bins, labels=labels, include_lowest=True)

    disc = (
        d.groupby(["sub_category", "disc_bin"], as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
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

    # sort rows by worst margin in >35%
    sens = disc_top[disc_top["disc_bin"] == ">35%"][["sub_category", "margin_pct"]]
    row_order = sens.sort_values("margin_pct")["sub_category"].tolist() if len(sens) else list(top_subcats)

    CLAMP = 40
    disc_top["margin_clamped"] = disc_top["margin_pct"].clip(-CLAMP, CLAMP)

    heat = (
        alt.Chart(disc_top)
        .mark_rect()
        .encode(
            x=alt.X("disc_bin:N", sort=labels, title="% discount (strategy bucket)"),
            y=alt.Y("sub_category:N", sort=row_order, title=None),
            color=alt.Color(
                "margin_clamped:Q",
                title="Margin %",
                scale=alt.Scale(scheme="redblue", domain=[-CLAMP, CLAMP], domainMid=0),
            ),
            tooltip=[
                "sub_category:N",
                "disc_bin:N",
                alt.Tooltip("orders:Q", format=",.0f", title="# Orders"),
                alt.Tooltip("sales:Q", format=",.0f", title="Sales"),
                alt.Tooltip("margin_pct:Q", format=".2f", title="Margin % (raw)"),
            ],
        )
        .properties(width=820, height=360, title="Discount Guardrail Framework")
    )

    return _apply_dark_theme(heat)

# -----------------------------
# 5) Bundle table chart (Altair table-style with lift highlighted)
# Input is already prepared mba_table_df with columns:
# sub_cat1, sub_cat2, support, confidence, lift
# -----------------------------
def bundle_table_chart(mba_table_df: pd.DataFrame, top_n: int = 10) -> alt.ConcatChart:
    d = mba_table_df.head(top_n).copy()
    d["row"] = range(1, len(d) + 1)
    y = alt.Y("row:O", axis=None)

    c1 = alt.Chart(d).mark_text(align="left", baseline="middle", color="#d7dbe7").encode(y=y, text="sub_cat1:N")\
        .properties(width=140, title="Sub cat 1")
    c2 = alt.Chart(d).mark_text(align="left", baseline="middle", color="#d7dbe7").encode(y=y, text="sub_cat2:N")\
        .properties(width=140, title="Sub cat 2")
    c3 = alt.Chart(d).mark_text(align="right", baseline="middle", color="#d7dbe7").encode(y=y, text=alt.Text("support:Q", format=".2f"))\
        .properties(width=90, title="Support %")
    c4 = alt.Chart(d).mark_text(align="right", baseline="middle", color="#d7dbe7").encode(y=y, text=alt.Text("confidence:Q", format=".2f"))\
        .properties(width=95, title="Conf %")

    lift_bg = alt.Chart(d).mark_rect().encode(
        y=y, x=alt.value(0), x2=alt.value(1),
        color=alt.Color("lift:Q", scale=alt.Scale(scheme="blues"), legend=None)
    ).properties(width=80)

    lift_text = alt.Chart(d).mark_text(align="right", baseline="middle", color="#111").encode(
        y=y, text=alt.Text("lift:Q", format=".2f")
    ).properties(width=80, title="Lift")

    table = alt.hconcat(c1, c2, c3, c4, lift_bg + lift_text, spacing=12)\
        .resolve_scale(y="shared")\
        .properties(title="Top Bundle Pairs (Lift highlighted)")

    return _apply_dark_theme(table)