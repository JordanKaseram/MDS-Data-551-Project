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
        html.H1("Retail Dashboard"),
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
                style={"display": "flex", "alignItems": "center", "gap": "32px"}
        ),


        # The KPI statistics 
        html.Div(
            [
            # KPI 1
                html.Div(
                    [
                        html.Div("Total Revenue", style={"color": "#6b7280", "fontSize": "14px"}),
                        html.Div(id="kpi-revenue", style={"fontSize": "36px", "fontWeight": "700"}),
                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eef0f4",
                        "borderRadius": "12px",
                        "background": "white",
                        "width": "260px",
                        },
                    ),

            # KPI 2
                html.Div(
                    [
                        html.Div("Total Profit", style={"color": "#6b7280", "fontSize": "14px"}),
                        html.Div(id="kpi-profit", style={"fontSize": "36px", "fontWeight": "700"}),
                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eef0f4",
                        "borderRadius": "12px",
                        "background": "white",
                        "width": "260px",
                        },
                    ),
            # KPI 3
                html.Div(
                    [
                        html.Div("Average Backet Spend", style={"color": "#6b7280", "fontSize": "14px"}),
                        html.Div(id="kpi-avg_order", style={"fontSize": "36px", "fontWeight": "700"}),
                    ],
                    style={
                        "padding": "12px",
                        "border": "1px solid #eef0f4",
                        "borderRadius": "12px",
                        "background": "white",
                        "width": "260px",
                        },
                ),
            ],
            style={
                "display": "flex",
                "gap": "16px",
                "marginTop": "16px",
            },
        ),
        
        
        # Section 1 for plots
        html.Div(
            [
                html.H2("Section 1: Trends & Breakdown", style={"margin": "0 0 12px 0"}),

                # Top row: 3 charts (total sales, total profit & avg margin)
                html.Div(
                    [
                        html.Iframe(
                            id="trend-charts-frame",
                            style={"border": "0", "width": "100%", "height": "320px"},
                        ),
                    ],
                    style={
                        "marginBottom": "16px",
                    },
                ),
                # Bottom row: 2 charts (cat sales and discount vs margin)
                html.Div(
                    [
                        html.Iframe(
                            id="trend-brkdwn-frame",
                            style={"border": "0", "width": "100%", "height": "320px"},
                        ),
                    ],
                ),
            ],
            style={
                "padding": "16px",
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "marginTop": "16px",
                "background": "white",
            },
        ),

       
        # Section 2 for plots
        html.Div(
            [
                html.H2("Section 2: Hero Profitability", style={"margin": "0 0 12px 0"}),

                # bar chart with the most profitable items
                html.Iframe(
                    id="hero-profit-frame",
                    style={
                        "border": "0",
                        "width": "100%",
                        "height": "320px",
                    },
                ),
            ],
            style={
                "padding": "16px",
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "marginTop": "16px",
                "background": "white",
            },
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
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "marginTop": "16px",
                "background": "white",
            },
        ),

    ],
)



# updates the charts with the year/month/country filter
@app.callback(
    Output("kpi-revenue", "children"),
    Output("kpi-profit", "children"),
    Output("kpi-avg_order", "children"),
    Output("hero-profit-frame", "srcDoc"),
    Output("trend-charts-frame", "srcDoc"),
    Output("trend-brkdwn-frame", "srcDoc"),
    Output("sales-trend-frame", "srcDoc"),
    Output("profit-trend-frame", "srcDoc"),

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


    # section 1 plots
    s_trend = ch.sales_trend(d)
    p_trend = ch.profit_trend(d)
    m_trend = ch.margin_trend(d)
    c_sales = ch.catagory_sales(d)
    d_margin = ch.discount_margin(d)
    trend_charts = s_trend | p_trend | m_trend
    trend_brkdwn = c_sales | d_margin

    # section 2 plots
    h_profit = ch.hero_profitability(d, width=320, height=220)

    return (
        f"${total_revenue:,.0f}",
        f"${total_profit:,.0f}",
        f"${avg_order:,.0f}",
        h_profit.to_html(),
        trend_charts.to_html(),
        trend_brkdwn.to_html(),
        s_trend.to_html(),
        p_trend.to_html(),
    )

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
