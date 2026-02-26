from dash import Dash, html, dcc, Input, Output
import pandas as pd
import altair as alt
import traceback

import src.charts as ch
from src.data import df
from src.mba import get_mba_rules, prepare_rules_table

app = Dash(__name__)
server = app.server


# -------------------------
# Altair -> iframe srcDoc helper (works even when to_html(full_html=...) fails)
# -------------------------
def altair_srcdoc(chart):
    spec = chart.to_dict()
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
      <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
      <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
      <style>
        body {{ margin:0; background:#151823; }}
        #vis {{ width:100%; height:100%; }}
      </style>
    </head>
    <body>
      <div id="vis"></div>
      <script>
        const spec = {spec};
        vegaEmbed('#vis', spec, {{actions:false}});
      </script>
    </body>
    </html>
    """


def error_srcdoc(title, err_text):
    safe = (
        err_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""
    <!doctype html>
    <html>
    <body style="margin:0;padding:12px;background:#151823;color:#d7dbe7;font-family:Arial;">
      <h3 style="margin:0 0 8px 0;color:#ffb3b3;">{title} failed</h3>
      <pre style="white-space:pre-wrap;">{safe}</pre>
    </body>
    </html>
    """


# -------------------------
# Dropdown options
# -------------------------
year_options = [{"label": "All Years", "value": "ALL"}] + [
    {"label": str(y), "value": str(y)} for y in sorted(df["year"].unique())
]

region_options = [{"label": "All Regions", "value": "ALL"}] + [
    {"label": r, "value": r} for r in sorted(df["region"].dropna().unique())
]

segment_options = [{"label": "All Segments", "value": "ALL"}] + [
    {"label": s, "value": s} for s in sorted(df["segment"].dropna().unique())
]

season_options = [
    {"label": "All Seasons", "value": "ALL"},
    {"label": "Winter", "value": "Winter"},
    {"label": "Spring", "value": "Spring"},
    {"label": "Summer", "value": "Summer"},
    {"label": "Fall", "value": "Fall"},
]


# -------------------------
# Filter helper
# -------------------------
def apply_filters(df_in, year, region, segment, season):
    d = df_in.copy()

    if year != "ALL":
        d = d[d["year"] == int(year)]

    if region != "ALL":
        d = d[d["region"] == region]

    if segment != "ALL":
        d = d[d["segment"] == segment]

    if season != "ALL":
        d = d[d["season"] == season]

    return d


# -------------------------
# Layout (matches your sketch)
# -------------------------
app.layout = html.Div(
    [
        html.Div(
            [
                html.H2("Campaign Optimize Profit Strategy", className="title"),
                html.Div(
                    [
                        dcc.Dropdown(id="year-dropdown", options=year_options, value="ALL", clearable=False),
                        dcc.Dropdown(id="region-dropdown", options=region_options, value="ALL", clearable=False),
                        dcc.Dropdown(id="segment-dropdown", options=segment_options, value="ALL", clearable=False),
                        dcc.Dropdown(id="season-dropdown", options=season_options, value="ALL", clearable=False),
                    ],
                    className="filters-row",
                ),
            ],
            className="header",
        ),

        # KPI bar
        html.Iframe(id="kpi-frame", className="kpi-frame"),

        # Main 2x2 grid
        html.Div(
            [
                html.Iframe(id="bubble-frame", className="panel"),
                html.Iframe(id="bundle-frame", className="panel"),
                html.Iframe(id="product-frame", className="panel"),
                html.Iframe(id="discount-frame", className="panel"),
            ],
            className="main-grid",
        ),
    ],
    className="page",
)


# -------------------------
# Callback: update 5 graphs
# -------------------------
@app.callback(
    Output("kpi-frame", "srcDoc"),
    Output("bubble-frame", "srcDoc"),
    Output("bundle-frame", "srcDoc"),
    Output("product-frame", "srcDoc"),
    Output("discount-frame", "srcDoc"),
    Input("year-dropdown", "value"),
    Input("region-dropdown", "value"),
    Input("segment-dropdown", "value"),
    Input("season-dropdown", "value"),
)
def update_dashboard(year, region, segment, season):
    d = apply_filters(df, year, region, segment, season)

    if d.empty:
        msg = """
        <html><body style="margin:0;padding:12px;background:#151823;color:#d7dbe7;font-family:Arial;">
          <h3>No data for these filters. Try ALL.</h3>
        </body></html>
        """
        return msg, msg, msg, msg, msg

    # 1) KPI
    try:
        kpi_html = altair_srcdoc(ch.kpi_strip(d))
    except Exception:
        kpi_html = error_srcdoc("KPI", traceback.format_exc())

    # 2) Bubble discovery
    try:
        bubble_html = altair_srcdoc(ch.subcat_bubble(d))
    except Exception:
        bubble_html = error_srcdoc("Bubble", traceback.format_exc())

    # 3) Bundle strategy (MBA)
    try:
        rules = get_mba_rules(d, segment="ALL", min_support=0.002)
        table = prepare_rules_table(rules, top_n=10, min_lift=1.5, min_conf=0.05)

        if table is None or table.empty:
            placeholder = ch._apply_dark_theme(
                alt.Chart(pd.DataFrame({"msg": ["No bundle rules for these filters (try ALL or lower min_support)."]}))
                .mark_text(align="left", fontSize=14, color="#d7dbe7")
                .encode(text="msg:N")
                .properties(width=520, height=260, title="Top Bundle Pairs")
            )
            bundle_html = altair_srcdoc(placeholder)
        else:
            mba_df = table.rename(columns={"prod1": "sub_cat1", "prod2": "sub_cat2"}).copy()
            mba_df["support"] = (mba_df["support"] * 100).round(2)
            mba_df["confidence"] = (mba_df["confidence"] * 100).round(2)
            mba_df["lift"] = mba_df["lift"].round(2)

            bundle_html = altair_srcdoc(ch.bundle_table_chart(mba_df, top_n=10))

    except Exception:
        bundle_html = error_srcdoc("Bundle (MBA)", traceback.format_exc())

    # 4) Product panel
    try:
        product_html = altair_srcdoc(ch.top_products_panel(d, top_n=5))
    except Exception:
        product_html = error_srcdoc("Products", traceback.format_exc())

    # 5) Discount guardrail heatmap
    try:
        discount_html = altair_srcdoc(ch.discount_guardrail(d, top_n=15))
    except Exception:
        discount_html = error_srcdoc("Discount guardrail", traceback.format_exc())

    return kpi_html, bubble_html, bundle_html, product_html, discount_html


if __name__ == "__main__":
    app.run(debug=True)