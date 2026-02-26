# Import packages
from dash import Dash, html, dcc, Input, Output
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


# Initialize the app
app = Dash(__name__)

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
                    "background": "rgba(226, 232, 240, 0.62)",
                    "border": "1px solid rgba(148, 163, 184, 0.34)",
                    "borderRadius": "14px",
                    "boxShadow": "0 8px 22px rgba(15, 23, 42, 0.06)",
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
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
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
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Div("Average Backet Spend", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="kpi-avg_order", style={"fontSize": "28px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
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
                        html.Iframe(
                            id="trend-charts-frame",
                            style={"border": "0", "width": "100%", "height": "620px", "overflow": "hidden"},
                        ),
                    ],
                    style={
                        "padding": "16px",
                        "border": "1px solid rgba(59, 130, 246, 0.18)",
                        "borderRadius": "14px",
                        "marginTop": "16px",
                        "background": "linear-gradient(180deg, rgba(239, 246, 255, 0.92) 0%, rgba(248, 250, 252, 0.96) 100%)",
                        "boxShadow": "0 10px 30px rgba(30, 64, 175, 0.08)",
                        "flex": "8",
                    },
                ),
                # Section 2 for plots
                html.Div(
                    [
                        html.H2("Section 2: Hero Profitability", style={"margin": "0 0 12px 0"}),
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
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Div("Attach Rate", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="hero-kpi-attach-rate", style={"fontSize": "24px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Div("Avg Co-products", style={"color": "#475569", "fontSize": "13px"}),
                                        html.Div(id="hero-kpi-avg-coproducts", style={"fontSize": "24px", "fontWeight": "700"}),
                                    ],
                                    style={
                                        "padding": "10px",
                                        "border": "1px solid rgba(148, 163, 184, 0.34)",
                                        "borderRadius": "10px",
                                        "background": "rgba(241, 245, 249, 0.92)",
                                        "boxShadow": "0 1px 4px rgba(15, 23, 42, 0.05)",
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
                        html.Iframe(
                            id="hero-profit-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "600px",
                            },
                        ),
                    ],
                    style={
                        "padding": "16px",
                        "border": "1px solid rgba(16, 185, 129, 0.18)",
                        "borderRadius": "14px",
                        "marginTop": "16px",
                        "background": "linear-gradient(180deg, rgba(236, 253, 245, 0.9) 0%, rgba(248, 250, 252, 0.96) 100%)",
                        "boxShadow": "0 10px 30px rgba(5, 150, 105, 0.08)",
                        "flex": "12",
                    },
                ),
            ],
            style={"display": "flex", "gap": "16px", "alignItems": "flex-start"},
        ),

        # Section 3: To be changed with the actual plots. Current plots are placeholders
        html.Div(
            [
                html.H2("Section 3: Detailed Trends", style={"margin": "0 0 12px 0"}),
                html.Div(
                    [
                        html.Iframe(
                            id="sales-trend-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "450px",
                            },
                        ),
                        html.Iframe(
                            id="profit-trend-frame",
                            style={
                                "border": "0",
                                "width": "100%",
                                "height": "450px",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "1fr 1fr",
                        "gap": "16px",
                    },
                ),
            ],
            style={
                "padding": "16px",
                "border": "1px solid rgba(99, 102, 241, 0.2)",
                "borderRadius": "14px",
                "marginTop": "16px",
                "background": "linear-gradient(180deg, rgba(238, 242, 255, 0.88) 0%, rgba(248, 250, 252, 0.96) 100%)",
                "boxShadow": "0 10px 30px rgba(79, 70, 229, 0.08)",
            },
        ),

    ],
    style={
        "minHeight": "100vh",
        "padding": "20px 24px 28px",
        "background": "radial-gradient(circle at 0% 0%, #f8fbff 0%, #eef3ff 42%, #f6f9fc 100%)",
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
    Output("hero-kpi-attach-rate", "children"),
    Output("hero-kpi-avg-coproducts", "children"),

    # Charts
    Output("hero-profit-frame", "srcDoc"),
    Output("trend-charts-frame", "srcDoc"),
    Output("sales-trend-frame", "srcDoc"),
    Output("profit-trend-frame", "srcDoc"),

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


    # section 1 plots
    s_trend = ch.sales_trend(d, year=year, month=month)
    p_trend = ch.profit_trend(d, year=year, month=month)
    d_margin = ch.discount_margin(d, width=420, height=120)
    section1_grid = (
        (ch.sales_trend(d, year=year, month=month, width=200, height=115) | ch.profit_trend(d, year=year, month=month, width=200, height=115))
        & (ch.margin_trend(d, year=year, month=month, width=200, height=115) | ch.catagory_sales(d, width=200, height=115))
        & d_margin
    )

    # section 2 plots
    h_profit, co_chart = ch.hero_profitability(d, width=560, height=170)
    hero_combo = alt.vconcat(h_profit, co_chart, spacing=8)


    return (
        format_compact_currency(total_revenue),
        format_compact_currency(total_profit),
        format_compact_currency(avg_order),
        format_compact_currency(hero_profit),
        f"{attach_rate:.1%}",
        f"{avg_coproducts:.2f}",
        hero_combo.to_html(),
        section1_grid.to_html(embed_options={"actions": False}),
        s_trend.to_html(),
        p_trend.to_html(),
    )

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
