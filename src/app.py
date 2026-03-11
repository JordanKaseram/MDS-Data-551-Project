
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

from dash import Dash, html, dcc, Input, Output
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
        empty = alt.Chart(pd.DataFrame({"x":[0], "y":[0]})).mark_line().properties(width=84, height=42)
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
        .properties(width=84, height=42)
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


def _subcat_plotly(
    g: pd.DataFrame,
    selected_category: str | None = None,
    selected_pairs: list[tuple[str, str]] | None = None,
):
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
        custom_data=["category", "sub_category"],
    )

    selected_pair_set = set(selected_pairs or [])

    # Selection mode: only selected bubbles are emphasized.
    if selected_pair_set:
        for trace in fig.data:
            trace_subcats = g.loc[g["category"] == trace.name, "sub_category"].tolist()
            sel_idx = [i for i, subcat in enumerate(trace_subcats) if (trace.name, subcat) in selected_pair_set]
            trace.update(
                selectedpoints=sel_idx if sel_idx else [],
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=0.15)),
            )
    # Hover/click fallback mode: emphasize active category.
    elif selected_category:
        for trace in fig.data:
            is_active = trace.name == selected_category
            trace.update(
                marker=dict(
                    opacity=1.0 if is_active else 0.22,
                    line=dict(color="#ffffff", width=1.2 if is_active else 0.0),
                )
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
    if selected_pair_set:
        title += f" — {len(selected_pair_set)} selected bubble(s)"
    elif selected_category:
        title += f" — filtered to {selected_category}"

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        height=460,
        legend_title_text="Category",
        clickmode="event+select",
        dragmode="select",
        uirevision="subcat-selection",
        title=title,
    )
    fig.update_xaxes(title="Purchase Frequency (% of Orders)", tickfont=dict(size=14))
    fig.update_yaxes(title="Profit Margin (%)", tickfont=dict(size=14))
    return fig


def _extract_category(event_data: dict | None) -> str | None:
    """Read selected category from Plotly hover/click payload."""
    if not event_data or not isinstance(event_data, dict):
        return None
    points = event_data.get("points")
    if not points:
        return None

    p0 = points[0]
    custom = p0.get("customdata")
    if isinstance(custom, (list, tuple)) and custom:
        return str(custom[0]) if custom[0] is not None else None
    if isinstance(custom, str) and custom:
        return custom
    return None


def _extract_selected_pairs(event_data: dict | None) -> list[tuple[str, str]]:
    """Read selected category/subcategory pairs from Plotly selectedData payload."""
    if not event_data or not isinstance(event_data, dict):
        return []
    points = event_data.get("points")
    if not points:
        return []

    pairs: list[tuple[str, str]] = []
    for point in points:
        custom = point.get("customdata")
        if isinstance(custom, (list, tuple)) and len(custom) >= 2:
            cat, subcat = custom[0], custom[1]
            if cat is not None and subcat is not None:
                pairs.append((str(cat), str(subcat)))

    # De-duplicate while preserving order.
    return list(dict.fromkeys(pairs))


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
                                    inline=True,
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
                                    value=SEGMENTS,
                                    className="pill-group",
                                    inline=True,
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

                # Main row: bubble chart
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Subcategory Opportunity", className="card-header"),
                                html.Div(
                                    dcc.Graph(
                                        id="subcat-graph",
                                        config={"displayModeBar": False},
                                        clear_on_unhover=True,
                                        style={"height": "520px"},
                                    ),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                    ],
                    className="row row-tall row-single",
                ),

                # Bottom row: products + pricing
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Breakdown: Top 5 Products", className="card-header"),
                                html.Div(
                                    html.Iframe(id="top-products-frame", className="iframe", style={"height": "400px"}),
                                    className="card-body",
                                ),
                            ],
                            className="card",
                        ),
                        html.Div(
                            [
                                html.Div("Pricing Strategy (Discount Guardrails)", className="card-header"),
                                html.Div(
                                    html.Iframe(id="pricing-frame", className="iframe", style={"height": "400px"}),
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
    Input("year-range", "value"),
    Input("season", "value"),
    Input("segment", "value"),
    Input("subcat-graph", "selectedData"),
    Input("subcat-graph", "clickData"),
    Input("subcat-graph", "hoverData"),
)
def update_dashboard(year_range, season, segments, selectedData, clickData, hoverData):
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

    # Interactive bubble chart (Plotly)
    g_sub = _subcat_agg(d)
    valid_pairs = {
        (str(cat), str(subcat))
        for cat, subcat in g_sub[["category", "sub_category"]].dropna().itertuples(index=False, name=None)
    }
    selected_pairs = [p for p in _extract_selected_pairs(selectedData) if p in valid_pairs]

    # Bubble chart interaction priority:
    # 1) selected bubbles, 2) hovered category, 3) clicked category.
    selected_category = None
    if not selected_pairs:
        selected_category = _extract_category(hoverData) or _extract_category(clickData)

    subcat_fig = _subcat_plotly(
        g_sub,
        selected_category=selected_category,
        selected_pairs=selected_pairs,
    )

    # Focus dataset for dependent charts
    d_focus = d
    if selected_pairs:
        pair_df = pd.DataFrame(selected_pairs, columns=["category", "sub_category"])
        d_focus = d_focus.merge(pair_df, on=["category", "sub_category"], how="inner")
    elif selected_category and "category" in d_focus.columns:
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
        panel_height=350,
    )
    pricing = ch.discount_guardrail(d_focus, top_n=12, width=620, height=380)

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
    )


if __name__ == "__main__":
    app.run(debug=True)
