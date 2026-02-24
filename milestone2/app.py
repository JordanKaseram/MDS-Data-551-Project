# Import packages
from dash import Dash, html, dcc, Input, Output
from data import df

import charts as ch
import altair as alt

alt.data_transformers.enable("default")

# Allow Altair to embed larger datasets (otherwise it may error when df has many rows)
alt.data_transformers.disable_max_rows()
alt.renderers.enable("html")

def apply_filters(df_in, year, region):
    d = df_in.copy()
    if year != "ALL":
        d = d[d["year"] == year]
    if region != "ALL":
        d = d[d["region"] == region]
    return d

# Initialize the app
app = Dash(__name__)

year_options = (
    [{"label": "All Years", "value": "ALL"}] +
    [{"label": str(y), "value": y} for y in sorted(df["year"].dropna().unique())]
)
region_options = [{"label": r, "value": r} for r in sorted(df["region"].dropna().unique())]

app.layout = html.Div(
    [
        html.H1("Retail Dashboard"),
        # Stores filter state so multiple callbacks can share it
        dcc.Store(id="filters-store", data={"year": "ALL", "region": "ALL"}),


        # Top filter bar
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
                        html.Div("Region", style={"marginRight": "8px"}),
                        dcc.Dropdown(
                            id="region-dropdown",
                            options=[{"label": "All Regions", "value": "ALL"}] + region_options,
                            value="ALL",
                            clearable=False,
                            style={"width": "180px"},
                        ),
                    ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                )
            ],
                style={"display": "flex", "alignItems": "center", "gap": "100px"}
        ),

        # Top charts row (side by side) 
        html.Div(
            [   
                # Charts section 1
                html.Iframe(
                    id="section1-frame",
                    style={
                        "border": "0",
                        "width": "100%",
                        "height": "450px",
                    },
                ),
                # Charts section 2
                html.Iframe(
                    id="section2-frame",
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
                "marginTop": "16px",
            },
        ),

                html.Div(
            [   
                # Charts section 3
                html.Iframe(
                    id="sales-trend-frame",
                    style={
                        "border": "0",
                        "width": "100%",
                        "height": "450px",
                    },
                ),
                # Charts section 4
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
                "marginTop": "16px",
            },
        ),

    ],
)


@app.callback(
    Output("section1-frame", "srcDoc"),
    Output("section2-frame", "srcDoc"),
    Output("sales-trend-frame", "srcDoc"),
    Output("profit-trend-frame", "srcDoc"),
    Input("year-dropdown", "value"),
    Input("region-dropdown", "value"),
)
def update_all_charts(year, region):
    d = apply_filters(df, year, region)

    # section 1 plots
    s_trend = ch.sales_trend(d)
    p_trend = ch.profit_trend(d)
    m_trend = ch.margin_trend(d)
    c_sales = ch.catagory_sales(d)
    d_margin = ch.discount_margin(d)

    # section 2 plots
    h_profit = ch.hero_profitability(d)

    section1_table = ((s_trend | p_trend | m_trend) & (c_sales | d_margin))

    return (
        section1_table.to_html(),
        h_profit.to_html(),
        s_trend.to_html(),
        p_trend.to_html(),
    )

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
