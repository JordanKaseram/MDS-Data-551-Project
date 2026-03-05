
from pathlib import Path
import sys


def _fix_altair_html(html: str) -> str:
    """Inject CSS to remove margins/scrollbars inside iframe."""
    if not html:
        return html
    css = "<style>html,body{margin:0;padding:0;overflow:hidden;background:#fff;} </style>"
    if "<head>" in html:
        return html.replace("<head>", "<head>"+css, 1)
    if "<html" in html:
        # fallback: insert near top
        return css + html
    return "<!doctype html><html><head>"+css+"</head><body>"+html+"</body></html>"

# Ensure local imports always resolve to THIS src folder first
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from dash import Dash, html, dcc, Input, Output, dash_table
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px

import charts as ch
from data import df

alt.data_transformers.disable_max_rows()
alt.renderers.enable("html")

app = Dash(__name__)
server = app.server

# allow callbacks to reference components that may be swapped later
app.config.suppress_callback_exceptions = True


# -----------------------------
# Helpers
# -----------------------------
def _money(v: float) -> str:
    v = float(v) if v is not None else 0.0
    av = abs(v)
    if av >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if av >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def _pct(v: float, digits: int = 1) -> str:
    v = float(v) if v is not None else 0.0
    return f"{v:.{digits}f}%"


def _delta_text(current, prev) -> str:
    if current is None or prev is None:
        return "—"
    try:
        prev = float(prev)
        current = float(current)
    except Exception:
        return "—"
    if prev == 0:
        return "—"
    delta = (current - prev) / abs(prev) * 100.0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def _make_ts(d: pd.DataFrame) -> pd.DataFrame:
    # monthly time series within current filters
    if d.empty:
        return pd.DataFrame()

    x = d.copy()
    x["order_date"] = pd.to_datetime(x["order_date"], errors="coerce")
    x = x.dropna(subset=["order_date"])
    if x.empty:
        return pd.DataFrame()

    x["month"] = x["order_date"].dt.to_period("M").dt.to_timestamp()

    g = x.groupby("month", as_index=False).agg(
        sales=("sales", "sum"),
        profit=("profit", "sum"),
        customers=("customer_name", "nunique"),
        discount=("discount", "mean"),
        orders=("order_id", "nunique"),
        products=("product_name", "nunique"),
    )
    g["margin_pct"] = np.where(g["sales"] == 0, 0, g["profit"] / g["sales"] * 100.0)
    g["discount_pct"] = g["discount"] * 100.0
    g["avg_products"] = np.where(g["orders"] == 0, 0, g["products"] / g["orders"])
    g["frequency"] = np.where(g["customers"] == 0, 0, g["orders"] / g["customers"])
    return g.sort_values("month")


def _sparkline(ts: pd.DataFrame, y: str, title: str = "") -> str:
    if ts is None or ts.empty or y not in ts.columns:
        empty = alt.Chart(pd.DataFrame({"x":[0], "y":[0]})).mark_line().properties(width=150, height=48)
        return empty.to_html(embed_options={"actions": False})

    base = (
        alt.Chart(ts)
        .mark_line()
        .encode(
            x=alt.X("month:T", axis=None),
            y=alt.Y(f"{y}:Q", axis=None),
            tooltip=[
                alt.Tooltip("month:T", title="Month"),
                alt.Tooltip(f"{y}:Q", title=title or y),
            ],
        )
        .properties(width=150, height=48)
    )
    dot = alt.Chart(ts.tail(1)).mark_point(size=60).encode(x="month:T", y=f"{y}:Q")

    return (
        (base + dot)
        .configure_view(strokeOpacity=0)
        .configure_axis(grid=False)
        .to_html(embed_options={"actions": False})
    )


def _kpi_card(title: str, value: str, delta: str, spark_srcdoc: str) -> html.Div:
    return html.Div(
        [
            html.Div(title, className="kpi-title"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(value, className="kpi-value"),
                            html.Div(f"vs prev {delta}", className="kpi-delta"),
                        ],
                        className="kpi-left",
                    ),
                    html.Iframe(srcDoc=spark_srcdoc, className="kpi-spark"),
                ],
                className="kpi-inner",
            ),
        ],
        className="card kpi-card",
    )



def _compute_mba_table(d: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Compute top bundle pairs (sub_category) using association rules.

    Returns columns: sub_cat1, sub_cat2, support, confidence, lift
    """
    try:
        from mlxtend.frequent_patterns import apriori, association_rules
    except Exception:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    if d is None or d.empty:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    x = d[["order_id", "sub_category"]].dropna().drop_duplicates()
    if x.empty:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    # Speed guard: keep most common subcategories in current filter
    top_cats = x["sub_category"].value_counts().head(25).index
    x = x[x["sub_category"].isin(top_cats)]

    basket = pd.crosstab(x["order_id"], x["sub_category"]).astype(bool)

    # Adaptive support: aim for enough itemsets but avoid explosion
    min_support = max(0.002, min(0.02, 5 / max(len(basket), 1)))  # roughly 5 orders minimum
    itemsets = apriori(basket, min_support=min_support, use_colnames=True)
    if itemsets.empty:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    rules = association_rules(itemsets, metric="lift", min_threshold=1.0)
    if rules.empty:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    # Only 1-to-1 rules for clean bundles
    rules = rules[(rules["antecedents"].apply(len) == 1) & (rules["consequents"].apply(len) == 1)].copy()
    if rules.empty:
        return pd.DataFrame(columns=["sub_cat1","sub_cat2","support","confidence","lift"])

    rules["sub_cat1"] = rules["antecedents"].apply(lambda s: next(iter(s)))
    rules["sub_cat2"] = rules["consequents"].apply(lambda s: next(iter(s)))

    out = (
        rules[["sub_cat1","sub_cat2","support","confidence","lift"]]
        .sort_values(["lift","confidence","support"], ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    return out


def _subcat_agg(d: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to subcategory-level metrics used in the opportunity bubble chart."""
    if d is None or d.empty:
        return pd.DataFrame(columns=["category", "sub_category", "freq_pct", "margin_pct", "sales"])

    x = d.dropna(subset=["sub_category", "category", "order_id", "sales", "profit"]).copy()
    if x.empty:
        return pd.DataFrame(columns=["category", "sub_category", "freq_pct", "margin_pct", "sales"])

    orders_total = x["order_id"].nunique()
    g = (
        x.groupby(["category", "sub_category"], as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
    )
    g["margin_pct"] = np.where(g["sales"] == 0, 0, g["profit"] / g["sales"] * 100.0)
    g["freq_pct"] = np.where(orders_total == 0, 0, g["orders"] / orders_total * 100.0)
    return g


def _subcat_plotly(g: pd.DataFrame, selected_category: str | None = None):
    """Plotly bubble chart that can drive Dash interactions."""
    if g is None or g.empty:
        fig = px.scatter(pd.DataFrame({"x": [], "y": []}), x="x", y="y")
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=10, t=40, b=10),
            height=460,
            title="Subcategory Discovery (Frequency vs Profit Margin)",
        )
        return fig

    fig = px.scatter(
        g,
        x="freq_pct",
        y="margin_pct",
        color="category",
        size="sales",
        hover_name="sub_category",
        hover_data={"sales": ":,.0f", "freq_pct": ":.2f", "margin_pct": ":.2f", "category": True},
        custom_data=["category"],
    )

    # Median lines for quadrant guidance
    x_med = float(g["freq_pct"].median()) if len(g) else 0
    y_med = float(g["margin_pct"].median()) if len(g) else 0
    fig.add_vline(x=x_med, line_dash="dash", opacity=0.4)
    fig.add_hline(y=y_med, line_dash="dash", opacity=0.4)

    # Quadrant corner labels (business meaning)
    x0, x1 = float(g["freq_pct"].min()), float(g["freq_pct"].max())
    y0, y1 = float(g["margin_pct"].min()), float(g["margin_pct"].max())
    pad_x = (x1 - x0) * 0.02 if x1 > x0 else 0.2
    pad_y = (y1 - y0) * 0.06 if y1 > y0 else 0.6

    fig.add_annotation(x=x0 + pad_x, y=y1 - pad_y,
                       text="⭐ Invest (High margin / Low frequency)",
                       showarrow=False, xanchor="left", yanchor="top",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x1 - pad_x, y=y1 - pad_y,
                       text="🚀 Grow (High margin / High frequency)",
                       showarrow=False, xanchor="right", yanchor="top",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x0 + pad_x, y=y0 + pad_y,
                       text="⚠️ Fix/Exit (Low margin / Low frequency)",
                       showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x1 - pad_x, y=y0 + pad_y,
                       text="📣 Promote (Low margin / High frequency)",
                       showarrow=False, xanchor="right", yanchor="bottom",
                       font=dict(size=12, color="#334155"))


    title = "Subcategory Discovery (Frequency vs Profit Margin)"
    if selected_category:
        title += f" — filtered to {selected_category}"

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        height=460,
        legend_title_text="Category",
        title=title,
    )
    fig.update_xaxes(title="Purchase Frequency (% of Orders)")
    fig.update_yaxes(title="Profit Margin (%)")
    return fig


# -----------------------------
# UI controls data
# -----------------------------
YEARS = sorted(df["year"].dropna().unique().tolist())
YEAR_MIN, YEAR_MAX = int(min(YEARS)), int(max(YEARS))
YEAR_MARKS = {int(y): str(int(y)) for y in YEARS}

SEASONS = ["All", "Winter", "Spring", "Summer", "Fall"]
SEGMENTS = sorted(df["segment"].dropna().unique().tolist())


# -----------------------------
# Layout
# -----------------------------
app.layout = html.Div(
    [
        html.Div(
            [
                html.Div("Profit Optimization Strategy for Retail Campaigns", className="title"),
                html.Div(
                    "Executive view: identify subcategory opportunities, bundle tactics, and discount guardrails",
                    className="subtitle",
                ),

                # Filters (not dropdowns)
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Year range", className="filter-label"),
                                dcc.RangeSlider(
                                    id="year-range",
                                    min=YEAR_MIN,
                                    max=YEAR_MAX,
                                    value=[YEAR_MIN, YEAR_MAX],
                                    marks=YEAR_MARKS,
                                    step=1,
                                    allowCross=False,
                                ),
                                html.Div(id="year-range-text", className="filter-hint"),
                            ],
                            className="card filter-card",
                        ),
                        html.Div(
                            [
                                html.Div("Season", className="filter-label"),
                                dcc.RadioItems(
                                    id="season",
                                    options=[{"label": s, "value": s} for s in SEASONS],
                                    value="All",
                                    className="pill-group",
                                ),
                            ],
                            className="card filter-card",
                        ),
                        html.Div(
                            [
                                html.Div("Customer segment", className="filter-label"),
                                dcc.Checklist(
                                    id="segment",
                                    options=[{"label": s, "value": s} for s in SEGMENTS],
                                    value=[],
                                    className="pill-group",
                                ),
                                html.Div("Tip: select multiple segments to compare", className="filter-hint"),
                            ],
                            className="card filter-card",
                        ),
                    ],
                    className="filters-row",
                ),

                # KPI row (cards injected from callback)
                html.Div(
                    [
                        html.Div(id="kpi-customers"),
                        html.Div(id="kpi-revenue"),
                        html.Div(id="kpi-profit"),
                        html.Div(id="kpi-margin"),
                        html.Div(id="kpi-discount"),
                        html.Div(id="kpi-frequency"),
                        html.Div(id="kpi-avg-products"),
                    ],
                    className="kpi-row",
                ),

                # Main row: bubble + MBA (DataTable)
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Subcategory Opportunity", className="card-header"),
                                html.Div(
                                    dcc.Graph(
                                        id="subcat-graph",
                                        config={"displayModeBar": False},
                                        style={"height": "460px"},
                                    ),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                        html.Div(
                            [
                                html.Div("Top 5 Bundle Opportunities (Frequently Bought Together)", className="card-header"),
                                html.Div(
                                    dash_table.DataTable(
                                        id="mba-table",
                                        columns=[
                                            {"name": "Subcategory 1", "id": "sub_cat1"},
                                            {"name": "Subcategory 2", "id": "sub_cat2"},
                                            {"name": "Bundle Rate (%)", "id": "support_pct"},
                                            {"name": "Attach Rate (%)", "id": "confidence_pct"},
                                            {"name": "Lift (Strength)", "id": "lift"},
                                            {"name": "Recommendation", "id": "rec"},
                                        ],
                                        data=[],
                                        style_table={"height": "100%", "minHeight": "100%", "overflowY": "hidden", "overflowX": "auto"},
                                        style_header={
                                            "fontWeight": "800",
                                            "backgroundColor": "#f8fafc",
                                            "border": "1px solid rgba(15,23,42,0.08)",
                                        },
                                        style_cell={
                                            "fontSize": "13px",
                                            "padding": "10px",
                                            "color": "#0f172a",
                                            "border": "1px solid rgba(15,23,42,0.06)",
                                            "whiteSpace": "normal",
                                            "height": "auto",
                                            "maxWidth": 180,
                                        },
                                        style_data_conditional=[
                                            {"if": {"row_index": "odd"}, "backgroundColor": "#fbfdff"},
                                        ],
                                        sort_action="native",
                                    ),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                    ],
                    className="row row-tall",
                ),

                # Bottom row: products + pricing
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Breakdown: Top 5 Products", className="card-header"),
                                html.Div(
                                    html.Iframe(id="top-products-frame", className="iframe", style={"height": "320px"}),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                        html.Div(
                            [
                                html.Div("Pricing Strategy (Discount Guardrails)", className="card-header"),
                                html.Div(
                                    html.Iframe(id="pricing-frame", className="iframe", style={"height": "320px"}),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                    ],
                    className="row",
                ),
            ],
            className="container",
        )
    ]
)


# -----------------------------
# Callback
# -----------------------------
@app.callback(
    Output("year-range-text", "children"),
    Output("kpi-customers", "children"),
    Output("kpi-revenue", "children"),
    Output("kpi-profit", "children"),
    Output("kpi-margin", "children"),
    Output("kpi-discount", "children"),
    Output("kpi-frequency", "children"),
    Output("kpi-avg-products", "children"),
    Output("subcat-graph", "figure"),
    Output("top-products-frame", "srcDoc"),
    Output("pricing-frame", "srcDoc"),
    Output("mba-table", "data"),
    Input("year-range", "value"),
    Input("season", "value"),
    Input("segment", "value"),
    Input("subcat-graph", "clickData"),
    Input("subcat-graph", "hoverData"),
)
def update_dashboard(year_range, season, segments, clickData, hoverData):
    d = df.copy()

    # Year range filter
    y0, y1 = year_range if year_range else (YEAR_MIN, YEAR_MAX)
    d = d[(d["year"] >= y0) & (d["year"] <= y1)]

    # Season
    if season and season != "All":
        d = d[d["season"] == season]

    # Segments (multi-select). If none selected => All
    if segments:
        d = d[d["segment"].isin(segments)]

    # KPIs
    revenue = float(d["sales"].sum()) if len(d) else 0.0
    profit = float(d["profit"].sum()) if len(d) else 0.0
    margin = (profit / revenue * 100.0) if revenue else 0.0
    customers = int(d["customer_name"].nunique()) if len(d) else 0
    discount = float(d["discount"].mean() * 100.0) if len(d) else 0.0

    orders = int(d["order_id"].nunique()) if len(d) else 0
    avg_products = float(d.groupby("order_id")["product_name"].nunique().mean()) if orders else 0.0
    frequency = float(orders / customers) if customers else 0.0

    # Time series for sparklines + deltas
    ts = _make_ts(d)

    def _prev_cur(col):
        if ts is None or ts.empty or len(ts) < 2 or col not in ts.columns:
            return None, None
        return ts[col].iloc[-1], ts[col].iloc[-2]

    # Spark srcdocs
    sp_rev = _sparkline(ts, "sales", "Sales")
    sp_profit = _sparkline(ts, "profit", "Profit")
    sp_margin = _sparkline(ts, "margin_pct", "Margin %")
    sp_cust = _sparkline(ts, "customers", "Customers")
    sp_disc = _sparkline(ts, "discount_pct", "Discount %")
    sp_freq = _sparkline(ts, "frequency", "Frequency")
    sp_avgp = _sparkline(ts, "avg_products", "Avg products")

    # Deltas vs previous month
    d_rev = _delta_text(*_prev_cur("sales"))
    d_profit = _delta_text(*_prev_cur("profit"))
    d_margin = _delta_text(*_prev_cur("margin_pct"))
    d_cust = _delta_text(*_prev_cur("customers"))
    d_disc = _delta_text(*_prev_cur("discount_pct"))
    d_freq = _delta_text(*_prev_cur("frequency"))
    d_avgp = _delta_text(*_prev_cur("avg_products"))

    k_customers = _kpi_card("Total customers", f"{customers:,}", d_cust, sp_cust)
    k_revenue = _kpi_card("Revenue", _money(revenue), d_rev, sp_rev)
    k_profit = _kpi_card("Profit", _money(profit), d_profit, sp_profit)
    k_margin = _kpi_card("Margin %", _pct(margin, 1), d_margin, sp_margin)
    k_discount = _kpi_card("Discount %", _pct(discount, 1), d_disc, sp_disc)
    k_frequency = _kpi_card("Frequency", f"{frequency:.2f}", d_freq, sp_freq)
    k_avgp = _kpi_card("Avg products / txn", f"{avg_products:.2f}", d_avgp, sp_avgp)

    # Bubble chart selection (drives the two charts below)
    selected_category = None
    try:
        if clickData and clickData.get("points"):
            selected_category = (clickData["points"][0].get("customdata") or [None])[0]
        elif hoverData and hoverData.get("points"):
            selected_category = (hoverData["points"][0].get("customdata") or [None])[0]
    except Exception:
        selected_category = None

    # Interactive bubble chart (Plotly)
    g_sub = _subcat_agg(d)
    subcat_fig = _subcat_plotly(g_sub)

    # Focus dataset for dependent charts
    d_focus = d
    if selected_category and "category" in d_focus.columns:
        d_tmp = d_focus[d_focus["category"] == selected_category]
        if len(d_tmp):
            d_focus = d_tmp

    # Dependent charts (Altair)
    top_products = ch.top_products_panel(
        d_focus,
        top_n=5,
        label_width=260,
        metric_width=120,
        sales_width=250,
        customers_width=250,
        panel_height=260,
    )
    pricing = ch.discount_guardrail(d_focus, top_n=12, width=520, height=300)

    # MBA table
    mba_df = _compute_mba_table(d, top_n=5)
    mba_data = []
    if mba_df is not None and len(mba_df) > 0:
        t = mba_df.copy()
        for c in ["support", "confidence", "lift"]:
            if c in t.columns:
                t[c] = pd.to_numeric(t[c], errors="coerce")

        t["support_pct"] = (t["support"] * 100).round(2) if "support" in t.columns else None
        t["confidence_pct"] = (t["confidence"] * 100).round(2) if "confidence" in t.columns else None
        t["lift"] = t["lift"].round(2) if "lift" in t.columns else None

        def rec(row):
            try:
                if float(row.get("lift", 0)) >= 1.20:
                    return "Bundle at checkout"
                return "Cross-sell suggestion"
            except Exception:
                return "Cross-sell suggestion"

        t["rec"] = t.apply(rec, axis=1)
        mba_data = t[["sub_cat1", "sub_cat2", "support_pct", "confidence_pct", "lift", "rec"]].to_dict("records")

    year_text = f"{y0} – {y1}"

    return (
        year_text,
        k_customers,
        k_revenue,
        k_profit,
        k_margin,
        k_discount,
        k_frequency,
        k_avgp,
        subcat_fig,
        _fix_altair_html(top_products.to_html(embed_options={"actions": False})),
        _fix_altair_html(pricing.to_html(embed_options={"actions": False})),
        mba_data,
    )


if __name__ == "__main__":
    app.run(debug=True)