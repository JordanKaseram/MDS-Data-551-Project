
from pathlib import Path
import sys


def _fix_altair_html(html: str) -> str:
    """Inject CSS to control margins/scrollbars inside iframe."""
    if not html:
        return html
    css = (
        "<style>"
        "html,body{width:100%;height:100%;margin:0;padding:0;overflow:hidden;background:#fff;}"
        "#vis,.vega-embed,.vega-embed>div{width:100%!important;height:100%!important;overflow:hidden!important;}"
        "svg,canvas{display:block;}"
        "</style>"
    )
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

from dash import Dash, html, dcc, Input, Output, State, ctx, no_update
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
import plotly.graph_objects as go

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
        return "โ€”"
    try:
        prev = float(prev)
        current = float(current)
    except Exception:
        return "โ€”"
    if prev == 0:
        return "โ€”"
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
        empty = alt.Chart(pd.DataFrame({"x":[0], "y":[0]})).mark_line().properties(width=80, height=38)
        return _fix_altair_html(empty.to_html(embed_options={"actions": False}))

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
        .properties(width=80, height=38)
    )
    dot = alt.Chart(ts.tail(1)).mark_point(size=36).encode(x="month:T", y=f"{y}:Q")

    return (
        _fix_altair_html(
            (base + dot)
            .configure_view(strokeOpacity=0)
            .configure_axis(grid=False)
            .to_html(embed_options={"actions": False})
        )
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
    active_pair: tuple[str, str] | None = None,
    locked_pair: tuple[str, str] | None = None,
    uirevision_key: str = "subcat-selection",
):
    """Plotly bubble chart that can drive Dash interactions."""
    if g is None or g.empty:
        fig = px.scatter(pd.DataFrame({"x": [], "y": []}), x="x", y="y")
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=48, r=24, t=28, b=48),
            autosize=True,
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
    active_pair_set = {active_pair} if active_pair else set()
    locked_pair_set = {locked_pair} if locked_pair else set()

    # Selection mode: only selected bubbles are emphasized.
    if selected_pair_set or active_pair_set:
        for trace in fig.data:
            trace_subcats = g.loc[g["category"] == trace.name, "sub_category"].tolist()
            emphasized_pairs = selected_pair_set or active_pair_set
            sel_idx = [i for i, subcat in enumerate(trace_subcats) if (trace.name, subcat) in emphasized_pairs]
            trace.update(
                selectedpoints=sel_idx if sel_idx else [],
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=0.16)),
            )
    elif locked_pair_set:
        for trace in fig.data:
            trace_subcats = g.loc[g["category"] == trace.name, "sub_category"].tolist()
            sel_idx = [i for i, subcat in enumerate(trace_subcats) if (trace.name, subcat) in locked_pair_set]
            trace.update(
                selectedpoints=sel_idx if sel_idx else [],
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=0.16)),
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
    else:
        # Explicitly clear any persisted client-side selection state.
        for trace in fig.data:
            trace.update(
                selectedpoints=[],
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=1.0)),
                marker=dict(opacity=1.0, line=dict(color="#ffffff", width=0.0)),
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
    pad_y = (y1 - y0) * 0.04 if y1 > y0 else 0.6

    fig.add_annotation(x=x0 + pad_x, y=y1 - pad_y,
                       text="Invest (High margin / Low frequency)",
                       showarrow=False, xanchor="left", yanchor="top",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x1 - pad_x, y=y1 - pad_y,
                       text="Grow (High margin / High frequency)",
                       showarrow=False, xanchor="right", yanchor="top",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x0 + pad_x, y=y0 + pad_y,
                       text="Fix/Exit (Low margin / Low frequency)",
                       showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=12, color="#334155"))
    fig.add_annotation(x=x1 - pad_x, y=y0 + pad_y,
                       text="Promote (Low margin / High frequency)",
                       showarrow=False, xanchor="right", yanchor="bottom",
                       font=dict(size=12, color="#334155"))

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=84, r=28, t=58, b=74),
        autosize=True,
        legend_title_text="Category",
        clickmode="event+select",
        dragmode="select",
        hovermode="closest",
        uirevision=uirevision_key,
        font=dict(size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            font=dict(size=12),
            title_font=dict(size=13),
        ),
    )
    fig.update_xaxes(
        title="Purchase Frequency (% of Orders)",
        tickfont=dict(size=12),
        title_font=dict(size=14),
        automargin=True,
        title_standoff=10,
    )
    fig.update_yaxes(
        title="Profit Margin (%)",
        tickfont=dict(size=12),
        title_font=dict(size=14),
        automargin=True,
        title_standoff=10,
    )

    focus_pairs = selected_pair_set or active_pair_set or locked_pair_set
    if focus_pairs:
        focus_df = g[g.apply(lambda r: (str(r["category"]), str(r["sub_category"])) in focus_pairs, axis=1)]
        if not focus_df.empty:
            x_lo, x_hi = float(focus_df["freq_pct"].min()), float(focus_df["freq_pct"].max())
            y_lo, y_hi = float(focus_df["margin_pct"].min()), float(focus_df["margin_pct"].max())
            pad_x = max((x_hi - x_lo) * 0.35, 0.9)
            pad_y = max((y_hi - y_lo) * 0.35, 2.8)
            fig.update_xaxes(range=[x_lo - pad_x, x_hi + pad_x], autorange=False)
            fig.update_yaxes(range=[y_lo - pad_y, y_hi + pad_y], autorange=False)

    return fig


def _discount_guardrail_plotly(d: pd.DataFrame, top_n: int = 12):
    """Responsive Plotly heatmap for discount guardrails."""
    bins = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 1.00]
    labels = ["0–5%", "5–10%", "10–15%", "15–20%", "20–25%", "25–35%", ">35%"]
    boundary_ticks = {
        "0–5%": "0",
        "5–10%": "5",
        "10–15%": "10",
        "15–20%": "15",
        "20–25%": "20",
        "25–35%": "25",
        ">35%": "35",
    }
    clamp = 40

    data = d.copy()
    data["discount"] = pd.to_numeric(data.get("discount"), errors="coerce")
    data = data.dropna(subset=["sub_category", "order_id", "sales", "profit", "discount"])

    if data.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            autosize=True,
            margin=dict(l=110, r=40, t=14, b=48),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text="No discount-bin data for current filters",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#334155"),
                )
            ],
        )
        return fig

    data["disc_bin"] = pd.cut(data["discount"], bins=bins, labels=labels, include_lowest=True)
    data = data.dropna(subset=["disc_bin"])

    disc = (
        data.groupby(["sub_category", "disc_bin"], observed=True)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    disc["margin_pct"] = np.where(disc["sales"] == 0, np.nan, disc["profit"] / disc["sales"] * 100.0)
    disc = disc.replace([np.inf, -np.inf], np.nan).dropna(subset=["margin_pct", "disc_bin"])
    disc = disc[(disc["orders"] >= 20) & (disc["sales"] >= 3000)].copy()

    top_subcats = (
        data.groupby("sub_category")["sales"].sum().sort_values(ascending=False).head(top_n).index.tolist()
    )
    disc_top = disc[disc["sub_category"].isin(top_subcats)].copy()

    if disc_top.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            autosize=True,
            margin=dict(l=110, r=40, t=14, b=48),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text="No discount-bin data for current filters",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#334155"),
                )
            ],
        )
        return fig

    sens = disc_top[disc_top["disc_bin"].astype(str) == ">35%"][["sub_category", "margin_pct"]]
    if len(sens):
        row_order = sens.sort_values("margin_pct")["sub_category"].tolist()
    else:
        row_order = list(top_subcats)
    for subcat in top_subcats:
        if subcat not in row_order:
            row_order.append(subcat)

    disc_top["disc_bin"] = disc_top["disc_bin"].astype(str)
    disc_top["margin_clamped"] = disc_top["margin_pct"].clip(-clamp, clamp)

    pivot = disc_top.pivot_table(
        index="sub_category",
        columns="disc_bin",
        values="margin_clamped",
        aggfunc="mean",
    )
    y_order = [y for y in row_order if y in pivot.index]
    x_order = [x for x in labels if x in pivot.columns]
    pivot = pivot.reindex(index=y_order, columns=x_order)

    margin_pivot = disc_top.pivot_table(
        index="sub_category",
        columns="disc_bin",
        values="margin_pct",
        aggfunc="mean",
    ).reindex(index=y_order, columns=x_order)
    orders_pivot = disc_top.pivot_table(
        index="sub_category",
        columns="disc_bin",
        values="orders",
        aggfunc="sum",
    ).reindex(index=y_order, columns=x_order)
    sales_pivot = disc_top.pivot_table(
        index="sub_category",
        columns="disc_bin",
        values="sales",
        aggfunc="sum",
    ).reindex(index=y_order, columns=x_order)

    custom = np.dstack(
        [
            np.where(np.isnan(orders_pivot.to_numpy(dtype=float)), np.nan, orders_pivot.to_numpy(dtype=float)),
            np.where(np.isnan(sales_pivot.to_numpy(dtype=float)), np.nan, sales_pivot.to_numpy(dtype=float)),
            np.where(np.isnan(margin_pivot.to_numpy(dtype=float)), np.nan, margin_pivot.to_numpy(dtype=float)),
        ]
    )

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.to_numpy(dtype=float),
            x=x_order,
            y=y_order,
            zmin=-clamp,
            zmax=clamp,
            zmid=0,
            colorscale="RdBu",
            xgap=1,
            ygap=1,
            hoverongaps=False,
            customdata=custom,
            hovertemplate=(
                "sub_category: %{y}<br>"
                "disc_bin: %{x}<br>"
                "Orders: %{customdata[0]:,.0f}<br>"
                "Total Sales: %{customdata[1]:,.0f}<br>"
                "Profit Margin (%): %{customdata[2]:.2f}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="Profit Margin (%)", side="top"),
                thickness=12,
                len=0.92,
                y=0.5,
                yanchor="middle",
                tickfont=dict(size=10),
            ),
        )
    )

    fig.update_layout(
        template="plotly_white",
        autosize=True,
        margin=dict(l=124, r=42, t=10, b=48),
        font=dict(size=12, color="#334155"),
    )
    fig.update_xaxes(
        title="Discount (%)",
        tickmode="array",
        tickvals=x_order,
        ticktext=[boundary_ticks.get(x, x) for x in x_order],
        tickangle=0,
        tickfont=dict(size=13),
        title_font=dict(size=15),
        automargin=True,
    )
    fig.update_yaxes(
        title="Subcategory",
        tickfont=dict(size=14),
        title_font=dict(size=15),
        automargin=True,
        autorange="reversed",
    )
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


def _extract_pair(event_data: dict | None) -> tuple[str, str] | None:
    """Read one category/subcategory pair from Plotly hover/click payload."""
    pairs = _extract_selected_pairs(event_data)
    return pairs[0] if pairs else None


def _focus_pairs_from_store(focus_state: dict | None) -> list[tuple[str, str]]:
    if not isinstance(focus_state, dict):
        return []
    pairs = focus_state.get("pairs", [])
    if not isinstance(pairs, list):
        return []

    out: list[tuple[str, str]] = []
    for item in pairs:
        if isinstance(item, dict):
            cat = item.get("category")
            subcat = item.get("sub_category")
            if cat is not None and subcat is not None:
                out.append((str(cat), str(subcat)))
    return out


def _focus_reset_seq_from_store(focus_state: dict | None) -> int:
    if not isinstance(focus_state, dict):
        return 0
    seq = focus_state.get("reset_seq", 0)
    try:
        return int(seq)
    except (TypeError, ValueError):
        return 0


def _focus_store_payload(pairs: list[tuple[str, str]], reset_seq: int = 0) -> dict:
    return {
        "pairs": [{"category": c, "sub_category": s} for c, s in pairs],
        "reset_seq": int(reset_seq),
    }


def _focus_label(selected_pairs, locked_pair, hovered_pair) -> str:
    if selected_pairs:
        return f"{len(selected_pairs)} bubble(s) selected"
    if locked_pair:
        return f"Locked on {locked_pair[1]}"
    return "Showing all subcategories"


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
        dcc.Store(id="focus-state", data={"pairs": [], "reset_seq": 0}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Profit Optimization Strategy for Retail Campaigns", className="title"),
                        html.Div(
                            "Executive view: identify subcategory opportunities, bundle tactics, and discount guardrails",
                            className="subtitle",
                        ),
                    ],
                    className="screen-region header-region",
                ),

                # Filters (not dropdowns)
                html.Div(
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
                    className="screen-region controls-region",
                ),

                # KPI row (cards injected from callback)
                html.Div(
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
                    className="screen-region kpi-region",
                ),

                # Main analysis area: left bubble chart + right stacked panels
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Subcategory Opportunity", className="card-header-title"),
                                        html.Div(
                                            [
                                                html.Div(id="focus-mode-text", className="focus-mode-text"),
                                                html.Button("Reset focus", id="reset-focus", n_clicks=0, className="reset-focus-btn"),
                                            ],
                                            className="focus-controls",
                                        ),
                                    ],
                                    className="card-header card-header-split",
                                ),
                                html.Div(
                                    dcc.Graph(
                                        id="subcat-graph",
                                        config={"displayModeBar": False},
                                        clear_on_unhover=True,
                                        responsive=True,
                                        style={"height": "100%", "width": "100%"},
                                    ),
                                    className="card-body",
                                ),
                            ],
                            className="card main-chart-card",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Breakdown: Top 10 Products", className="card-header"),
                                        html.Div(
                                            html.Iframe(id="top-products-frame", className="iframe", style={"height": "100%", "width": "100%"}),
                                            className="card-body",
                                        ),
                                    ],
                                    className="card",
                                ),
                                html.Div(
                                    [
                                        html.Div("Pricing Strategy (Discount Guardrails)", className="card-header"),
                                        html.Div(
                                            dcc.Graph(
                                                id="pricing-heatmap",
                                                config={"displayModeBar": False, "responsive": True},
                                                responsive=True,
                                                style={"height": "100%", "width": "100%"},
                                            ),
                                            className="card-body",
                                        ),
                                    ],
                                    className="card pricing-card",
                                ),
                            ],
                            className="side-stack",
                        ),
                    ],
                    className="screen-region analysis-region",
                ),
            ],
            className="container dashboard-grid",
        ),
    ],
    className="app-shell",
)


# -----------------------------
# Callback
# -----------------------------
@app.callback(
    Output("focus-state", "data"),
    Input("subcat-graph", "selectedData"),
    Input("subcat-graph", "clickData"),
    Input("reset-focus", "n_clicks"),
    Input("year-range", "value"),
    Input("season", "value"),
    Input("segment", "value"),
    State("focus-state", "data"),
    prevent_initial_call=True,
)
def update_focus_state(selectedData, clickData, reset_clicks, year_range, season, segments, focus_state):
    trigger = ctx.triggered_id
    triggered_props = set((ctx.triggered_prop_ids or {}).keys())
    reset_seq = _focus_reset_seq_from_store(focus_state)

    if trigger == "reset-focus":
        return _focus_store_payload([], reset_seq=reset_seq + 1)

    if trigger in {"year-range", "season", "segment"}:
        # Filter changes clear focus and any persisted view state.
        return _focus_store_payload([], reset_seq=reset_seq + 1)

    if trigger == "subcat-graph":
        selected_triggered = "subcat-graph.selectedData" in triggered_props
        click_triggered = "subcat-graph.clickData" in triggered_props

        # Click is authoritative when both clickData and selectedData fire together.
        # This prevents stale selectedData from overriding a fresh click interaction.
        if click_triggered:
            pair = _extract_pair(clickData)
            if pair:
                current = _focus_pairs_from_store(focus_state)
                if len(current) == 1 and current[0] == pair:
                    return no_update
                return _focus_store_payload([pair], reset_seq=reset_seq)
            return no_update

        # Handle box/lasso multi-select when selectedData is the only trigger.
        if selected_triggered:
            selected_pairs = _extract_selected_pairs(selectedData)
            if selected_pairs:
                current = _focus_pairs_from_store(focus_state)
                if current == selected_pairs:
                    return no_update
                return _focus_store_payload(selected_pairs, reset_seq=reset_seq)
            # Ignore transient empty selectedData events.
            return no_update

    return no_update


@app.callback(
    Output("subcat-graph", "selectedData"),
    Output("subcat-graph", "clickData"),
    Output("subcat-graph", "hoverData"),
    Output("subcat-graph", "relayoutData"),
    Input("reset-focus", "n_clicks"),
    Input("year-range", "value"),
    Input("season", "value"),
    Input("segment", "value"),
    prevent_initial_call=True,
)
def clear_graph_interaction_state(reset_clicks, year_range, season, segments):
    # Clear transient interaction payloads on explicit reset/filter changes.
    # This prevents stale click/selection payloads from being replayed.
    return None, None, None, None


@app.callback(
    Output("year-range-text", "children"),
    Output("kpi-customers", "children"),
    Output("kpi-revenue", "children"),
    Output("kpi-profit", "children"),
    Output("kpi-margin", "children"),
    Output("kpi-discount", "children"),
    Output("kpi-frequency", "children"),
    Output("kpi-avg-products", "children"),
    Output("focus-mode-text", "children"),
    Output("subcat-graph", "figure"),
    Output("top-products-frame", "srcDoc"),
    Output("pricing-heatmap", "figure"),
    Input("year-range", "value"),
    Input("season", "value"),
    Input("segment", "value"),
    Input("focus-state", "data"),
)
def update_dashboard(year_range, season, segments, focus_state):
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
    selected_pairs = [p for p in _focus_pairs_from_store(focus_state) if p in valid_pairs]
    reset_seq = _focus_reset_seq_from_store(focus_state)

    # Focus priority: durable selected pairs from store.
    selected_category = None
    locked_pair = selected_pairs[0] if len(selected_pairs) == 1 else None
    selected_key = "|".join([f"{c}::{s}" for c, s in selected_pairs]) if selected_pairs else "all"
    focus_key = f"{reset_seq}|{selected_key}"

    subcat_fig = _subcat_plotly(
        g_sub,
        selected_category=selected_category,
        selected_pairs=selected_pairs,
        active_pair=None,
        locked_pair=locked_pair,
        uirevision_key=focus_key,
    )

    # Focus dataset for dependent charts
    d_focus = d
    if selected_pairs:
        pair_df = pd.DataFrame(selected_pairs, columns=["category", "sub_category"])
        d_focus = d_focus.merge(pair_df, on=["category", "sub_category"], how="inner")
    elif locked_pair:
        d_tmp = d_focus[
            (d_focus["category"] == locked_pair[0]) & (d_focus["sub_category"] == locked_pair[1])
        ]
        if len(d_tmp):
            d_focus = d_tmp
    elif selected_category and "category" in d_focus.columns:
        d_tmp = d_focus[d_focus["category"] == selected_category]
        if len(d_tmp):
            d_focus = d_tmp

    # Dependent charts (Altair)
    top_products = ch.top_products_panel_present(
        d_focus,
        top_n=10,
        label_width=165,
        metric_width=90,
        sales_width=110,
        customers_width=85,
        panel_height=210,
    )
    pricing = _discount_guardrail_plotly(d_focus, top_n=12)

    year_text = f"{y0} - {y1}"
    focus_text = _focus_label(selected_pairs, locked_pair, None)

    return (
        year_text,
        k_customers,
        k_revenue,
        k_profit,
        k_margin,
        k_discount,
        k_frequency,
        k_avgp,
        focus_text,
        subcat_fig,
        _fix_altair_html(top_products.to_html(embed_options={"actions": False})),
        pricing,
    )


if __name__ == "__main__":
    app.run(debug=True)
