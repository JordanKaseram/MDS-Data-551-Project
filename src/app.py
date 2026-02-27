# Import packages
from dash import Dash, html, dcc, Input, Output
import pandas as pd
from data import df

import charts as ch
import altair as alt

alt.data_transformers.enable("default")

# Allow Altair to embed larger datasets (otherwise it may error when df has many rows)
alt.data_transformers.disable_max_rows()
alt.renderers.enable("html")

def apply_filters(df_in, year, month, country):
    d = df_in.copy()
    if year != "ALL":
        d = d[d["year"].eq(year).fillna(False)]
    if month != "ALL":
        d = d[d["month_num"].eq(month).fillna(False)]
    if country != "ALL":
        d = d[d["country"] == country]
    return d


def format_compact_currency(value):
    if value is None or value != value:
        return "$0"

    sign = "-" if value < 0 else ""
    n = abs(float(value))

    if n >= 1_000_000_000:
        scaled, suffix = n / 1_000_000_000, "B"
    elif n >= 1_000_000:
        scaled, suffix = n / 1_000_000, "M"
    elif n >= 1_000:
        scaled, suffix = n / 1_000, "K"
    else:
        return f"{sign}${n:,.0f}"

    if scaled >= 100:
        scaled_txt = f"{scaled:.0f}"
    else:
        scaled_txt = f"{scaled:.1f}".rstrip("0").rstrip(".")

    return f"{sign}${scaled_txt}{suffix}"


def build_bundle_table(df_in: pd.DataFrame) -> pd.DataFrame:
    required = {"order_id", "sub_category"}
    if not required.issubset(df_in.columns):
        return pd.DataFrame(columns=["sub_cat1", "sub_cat2", "support", "confidence", "lift"])

    orders = df_in[["order_id", "sub_category"]].dropna().drop_duplicates()
    total_orders = orders["order_id"].nunique()
    if total_orders == 0:
        return pd.DataFrame(columns=["sub_cat1", "sub_cat2", "support", "confidence", "lift"])

    subcat_orders = orders.groupby("sub_category")["order_id"].nunique()

    # Directed pair counts (A -> B)
    left = orders.rename(columns={"sub_category": "sub_cat1"})
    right = orders.rename(columns={"sub_category": "sub_cat2"})
    pairs = left.merge(right, on="order_id")
    pairs = pairs[pairs["sub_cat1"] != pairs["sub_cat2"]]

    pair_counts = (
        pairs.groupby(["sub_cat1", "sub_cat2"])["order_id"]
        .nunique()
        .reset_index(name="pair_orders")
    )
    if pair_counts.empty:
        return pd.DataFrame(columns=["sub_cat1", "sub_cat2", "support", "confidence", "lift"])

    pair_counts["orders_a"] = pair_counts["sub_cat1"].map(subcat_orders)
    pair_counts["orders_b"] = pair_counts["sub_cat2"].map(subcat_orders)

    support = pair_counts["pair_orders"] / total_orders
    prob_a = pair_counts["orders_a"] / total_orders
    prob_b = pair_counts["orders_b"] / total_orders

    pair_counts["support"] = support * 100
    pair_counts["confidence"] = (pair_counts["pair_orders"] / pair_counts["orders_a"]) * 100
    pair_counts["lift"] = support / (prob_a * prob_b)

    out = (
        pair_counts[["sub_cat1", "sub_cat2", "support", "confidence", "lift"]]
        .replace([float("inf"), float("-inf")], pd.NA)
        .dropna()
        .sort_values("lift", ascending=False)
    )
    return out


# Initialize the app
app = Dash(__name__)
server = app.server

year_options = (
    [{"label": "All Years", "value": "ALL"}] +
    [{"label": str(y), "value": y} for y in sorted(df["year"].dropna().unique())]
)
month_options = (
    [{"label": "All Months", "value": "ALL"}] +
    [
        {"label": month_name, "value": int(month_num)}
        for month_num, month_name in (
            df.loc[df["month_num"].notna(), ["month_num", "month_name"]]
            .drop_duplicates()
            .sort_values("month_num")
            .itertuples(index=False, name=None)
        )
    ]
)
country_options = [{"label": r, "value": r} for r in sorted(df["country"].dropna().unique())]

app.layout = html.Div(
    [
        html.H1(
            "Retail Dashboard",
            style={
                "margin": "0 0 14px 0",
                "color": "#0f172a",
                "fontSize": "38px",
                "letterSpacing": "-0.02em",
            },
        ),
        # Stores filter state so multiple callbacks can share it
        dcc.Store(id="filters-store", data={"year": "ALL", "month": "ALL", "country": "ALL"}),


        # Top filter bar for selecting year, month, and country
        html.Div(
            [
                html.Div([
                        html.Div("Year", style={"marginRight": "8px"}),
                        dcc.Dropdown(
                            id="year-dropdown",
                            options=year_options,
                            value="ALL",
                            clearable=False,
                            style={"width": "140px"},
                        )
                    ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px"}
                ),

                html.Div(
                    [
                        html.Div("Month", style={"marginRight": "8px"}),
                        dcc.Dropdown(
                            id="month-dropdown",
                            options=month_options,
                            value="ALL",
                            clearable=False,
                            style={"width": "160px"},
                        ),
                    ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                ),

                html.Div(
                    [
                        html.Div("Country", style={"marginRight": "8px"}),
                        dcc.Dropdown(
                            id="country-dropdown",
                            options=[{"label": "All Countries", "value": "ALL"}] + country_options,
                            value="ALL",
                            clearable=False,
                            style={"width": "180px"},
                        ),
                    ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                )
            ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "32px",
                    "padding": "12px 14px",
                    "border": "1px solid rgba(148, 163, 184, 0.34)",
                    "borderRadius": "14px",
                    "backdropFilter": "blur(6px)",
                }
        ),

        # Section 1 and Section 2 on the same row
        html.Div(
            [
                # Section 1 for plots
                html.Div(
                    [
                        html.H2("Section 1: Trends & Breakdown", style={"margin": "0 0 12px 0"}),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Total Revenue", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="kpi-revenue", style={"fontSize": "28px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Div("Total Profit", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="kpi-profit", style={"fontSize": "28px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                    },
                                ),
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                                "gap": "10px",
                                "marginBottom": "12px",
                            },
                        ),
                        html.Iframe(
                            id="trend-charts-frame",
                            style={"border": "0", "width": "100%", "height": "430px", "overflow": "hidden"},
                        ),
                    ],
                    style={
                        "padding": "16px",
                        "border": "1px solid rgba(59, 130, 246, 0.18)",
                        "borderRadius": "14px",
                        "marginTop": "16px",
                        "flex": "8",
                    },
                ),
                # Section 2 for product performance
                html.Div(
                    [
                        html.H2("Section 2: Product Performance", style={"margin": "0 0 12px 0"}),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Hero Profit", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="hero-kpi-profit", style={"fontSize": "24px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                    },
                                ),
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(1, minmax(0, 1fr))",
                                "gap": "10px",
                                "marginBottom": "12px",
                            },
                        ),
                        html.Div(
                            [
                                html.Iframe(
                                    id="hero-profit-frame",
                                    style={
                                        "border": "0",
                                        "width": "100%",
                                        "height": "265px",
                                        "overflow": "hidden",
                                    },
                                ),
                                html.Iframe(
                                    id="product-performance-frame",
                                    style={
                                        "border": "0",
                                        "width": "100%",
                                        "height": "265px",
                                        "overflow": "hidden",
                                    },
                                ),
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "1fr",
                                "gap": "10px",
                            },
                        ),
                    ],
                    style={
                        "padding": "16px",
                        "border": "1px solid rgba(148, 163, 184, 0.28)",
                        "borderRadius": "14px",
                        "marginTop": "16px",
                        "flex": "12",
                    },
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "flex-start"},
        ),

        # Section 3
        html.Div(
            [
                html.H2("Section 3: Basket & Pricing Intelligence", style={"margin": "0 0 12px 0"}),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Average Basket Spend", style={"color": "#475569", "fontSize": "13px"}),
                                html.Div(id="kpi-avg_order", style={"fontSize": "24px", "fontWeight": "700"}),
                            ],
                            style={
                                "padding": "10px",
                                "border": "1px solid rgba(148, 163, 184, 0.34)",
                                "borderRadius": "10px",
                            },
                        ),
                        html.Div(
                            [
                                html.Div("Attach Rate", style={"color": "#475569", "fontSize": "13px"}),
                                html.Div(id="section3-kpi-attach-rate", style={"fontSize": "24px", "fontWeight": "700"}),
                            ],
                            style={
                                "padding": "10px",
                                "border": "1px solid rgba(148, 163, 184, 0.34)",
                                "borderRadius": "10px",
                            },
                        ),
                        html.Div(
                            [
                                html.Div("Avg Co-products", style={"color": "#475569", "fontSize": "13px"}),
                                html.Div(id="section3-kpi-avg-coproducts", style={"fontSize": "24px", "fontWeight": "700"}),
                            ],
                            style={
                                "padding": "10px",
                                "border": "1px solid rgba(148, 163, 184, 0.34)",
                                "borderRadius": "10px",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                        "gap": "10px",
                        "marginBottom": "12px",
                    },
                ),
                html.Div(
                    [
                        html.Iframe(
                            id="section3-bubble-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "300px",
                                "overflow": "hidden",
                            },
                        ),
                        html.Iframe(
                            id="co-purchase-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "300px",
                                "overflow": "hidden",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "minmax(0, 3fr) minmax(0, 2fr)",
                        "gap": "16px",
                        "marginTop": "8px",
                    },
                ),
                html.Div(
                    [
                        html.Iframe(
                            id="bundle-table-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "300px",
                                "overflow": "hidden",
                            },
                        ),
                        html.Iframe(
                            id="discount-guardrail-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "300px",
                                "overflow": "hidden",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "minmax(0, 3fr) minmax(0, 2fr)",
                        "gap": "16px",
                        "marginTop": "8px",
                    },
                ),
            ],
            style={
                "padding": "16px",
                "border": "1px solid rgba(148, 163, 184, 0.28)",
                "borderRadius": "14px",
                "marginTop": "16px",
            },
        ),

    ],
    style={
        "minHeight": "100vh",
        "padding": "20px 24px 28px",
        "fontFamily": "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "color": "#0f172a",
    },
)



# updates the charts with the year/month/country filter
@app.callback(
    # KPIs 
    Output("kpi-revenue", "children"),
    Output("kpi-profit", "children"),
    Output("kpi-avg_order", "children"),
    Output("hero-kpi-profit", "children"),
    Output("section3-kpi-attach-rate", "children"),
    Output("section3-kpi-avg-coproducts", "children"),

    # Charts
    Output("hero-profit-frame", "srcDoc"),
    Output("product-performance-frame", "srcDoc"),
    Output("trend-charts-frame", "srcDoc"),
    Output("section3-bubble-frame", "srcDoc"),
    Output("co-purchase-frame", "srcDoc"),
    Output("bundle-table-frame", "srcDoc"),
    Output("discount-guardrail-frame", "srcDoc"),

    # top dashbar widget
    Input("year-dropdown", "value"),
    Input("month-dropdown", "value"),
    Input("country-dropdown", "value"),
)


def update_all_charts(year, month, country):
    d = apply_filters(df, year, month, country)
    
    # KPI
    total_revenue = d["sales"].sum()
    total_profit = d["profit"].sum()
    avg_order = d.groupby("order_id")["sales"].sum().mean()
    if d.empty:
        avg_order = 0

    # section 2 hero KPIs
    hero_summary = (
        d.groupby("product_name", as_index=False)
        .agg(total_profit=("profit", "sum"))
        .sort_values("total_profit", ascending=False)
        .head(10)
    )
    top_products = set(hero_summary["product_name"].tolist())
    hero_profit = hero_summary["total_profit"].sum()

    hero_orders = set(d[d["product_name"].isin(top_products)]["order_id"].dropna().unique())
    if hero_orders:
        hero_order_products = (
            d[d["order_id"].isin(hero_orders)]
            .groupby("order_id")["product_name"]
            .nunique()
        )
        attach_rate = (hero_order_products > 1).mean()
        avg_coproducts = (hero_order_products - 1).clip(lower=0).mean()
    else:
        attach_rate = 0
        avg_coproducts = 0


    # section 1 plots with category interaction
    section1_grid = ch.section1_interactive(d, year=year, month=month, width=200, height=115)

    # section 2 plots (product performance only)
    hero_chart = ch.hero_profitability(d, width=500, height=240)
    product_perf_chart = ch.top_products_panel(d, top_n=5, label_width=220, metric_width=95, panel_height=200)

    # section 3 plots (basket & pricing intelligence only)
    section3_bubble = ch.subcat_bubble(d, width=620, height=260)
    section3_co_purchase = ch.co_purchase_chart(d, top_n=8, width=420, height=260)
    mba_table_df = build_bundle_table(d)
    section3_bundle = ch.bundle_table_chart(mba_table_df, top_n=10)
    section3_guardrail = ch.discount_guardrail(d, top_n=12, width=460, height=260)


    return (
        format_compact_currency(total_revenue),
        format_compact_currency(total_profit),
        format_compact_currency(avg_order),
        format_compact_currency(hero_profit),
        f"{attach_rate:.1%}",
        f"{avg_coproducts:.2f}",
        hero_chart.to_html(embed_options={"actions": False}),
        product_perf_chart.to_html(embed_options={"actions": False}),
        section1_grid.to_html(embed_options={"actions": False}),
        section3_bubble.to_html(embed_options={"actions": False}),
        section3_co_purchase.to_html(embed_options={"actions": False}),
        section3_bundle.to_html(embed_options={"actions": False}),
        section3_guardrail.to_html(embed_options={"actions": False}),
    )

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
