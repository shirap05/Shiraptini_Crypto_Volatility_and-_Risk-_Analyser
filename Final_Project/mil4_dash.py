import dash
from dash import html, dcc, Input, Output, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime
import io

from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import A4

# ================= CONFIG =================
API_URL = "http://127.0.0.1:5000/api/risk-metrics"

COLORS = {
    "high": "#dc2626",
    "medium": "#f59e0b",
    "low": "#22c55e"
}
GLASS = {
    "background": "rgba(255,255,255,0.06)",
    "backdropFilter": "blur(18px)",
    "WebkitBackdropFilter": "blur(18px)",
    "border": "1px solid rgba(255,255,255,0.15)",
    "borderRadius": "22px",
    "boxShadow": "0 8px 30px rgba(0,0,0,0.4)"
}

# ---------------- COIN CODE MAPS (for robust matching) ----------------
CODE_TO_ID = {
    "BITC": "bitcoin",
    "ETHE": "ethereum",
    "SOLA": "solana",
    "CARD": "cardano",
    "DOGE": "dogecoin",
    "XRPE": "ripple",
    "DOTE": "polkadot",
    "LTCE": "litecoin",
    "LINKE": "chainlink",
    "TRXE": "tron"
}
CODE_TO_SYMBOL = {
    "BITC": "BTC",
    "ETHE": "ETH",
    "SOLA": "SOL",
    "CARD": "ADA",
    "DOGE": "DOGE",
    "XRPE": "XRP",
    "DOTE": "DOT",
    "LTCE": "LTC",
    "LINKE": "LINK",
    "TRXE": "TRX"
}
# reverse maps
NAME_TO_CODE = {v: k for k, v in CODE_TO_ID.items()}
SYMBOL_TO_CODE = {v: k for k, v in CODE_TO_SYMBOL.items()}

# ================= FETCH DATA =================
def fetch_data(days=30):
    try:
        r = requests.get(f"{API_URL}?days={days}", timeout=10)
        r.raise_for_status()
        return pd.DataFrame(r.json()["table"])
    except:
        return pd.DataFrame()



# ================= INIT DASH =================
def init_dash(flask_app):

    app = dash.Dash(
        __name__,
        server=flask_app,
        routes_pathname_prefix="/dash4/",
        external_stylesheets=[dbc.themes.DARKLY],
        suppress_callback_exceptions=True
    )

    app.title = "Milestone 4 – Risk Classification"

    # ================= LAYOUT =================
    app.layout = dbc.Container(fluid=True, 
    
        style={
                "padding": "24px",
                "minHeight": "100vh",
                "background": "linear-gradient(135deg,#02050B,#071a2f,#02050B)"             
        },
        children=[
            dcc.Dropdown(
                id="coin-select",
                options=[
                    {"label": "Bitcoin (BTC)", "value": "BITC"},
                    {"label": "Ethereum (ETH)", "value": "ETHE"},
                    {"label": "Solana (SOL)", "value": "SOLA"},
                    {"label": "Cardano (ADA)", "value": "CARD"},
                    {"label": "Dogecoin (DOGE)", "value": "DOGE"},
                    {"label": "Ripple (XRP)", "value": "XRPE"},
                    {"label": "Polkadot (DOT)", "value": "DOTE"},
                    {"label": "Litecoin (LTC)", "value": "LTCE"},
                    {"label": "Chainlink (LINK)", "value": "LINKE"},
                    {"label": "Tron (TRX)", "value": "TRXE"},
                ],
                value=["BITC", "ETHE", "SOLA", "CARD", "DOGE"],
                multi=True,
                clearable=False,
                style={
                            "background": "rgba(255,255,255,0.08)",
                            "borderRadius": "16px",
                            "border": "1px solid rgba(255,255,255,0.15)",
                            "color": "white"
                        

                        },
                className="text-dark"        
            ),

            html.Br(),

            dbc.Row([
                dbc.Col(dbc.Button("🔄 Refresh", id="btn-refresh", color="primary"), width="auto"),
                dbc.Col(dbc.Button("⬇ CSV", id="btn-csv", color="secondary"), width="auto"),
                dbc.Col(dbc.Button("⬇ PDF", id="btn-pdf", color="secondary"), width="auto"),
                dbc.Col(html.Span(html.Small(id="last-update")), style={"marginLeft": "20px"}),
            ]),

            html.Br(),

            dbc.Row([
                dbc.Col(id="high-risk", md=4),
                dbc.Col(id="medium-risk", md=4),
                dbc.Col(id="low-risk", md=4),
            ]),

            html.Br(),

            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Risk Summary Report"),
                    html.P(id="total-assets"),
                    html.P(id="avg-vol"),
                    html.P(id="risk-dist"),
                    ]),
                    style=GLASS
                ), md=4),

                dbc.Col(dbc.Card(dbc.CardBody(
                    dcc.Graph(id="risk-pie",
                              config={
                                    "displayModeBar": True,
                                    "displaylogo": False
                                }
                              )
                ),
                 style=GLASS
                ),
                  md=8)
            ]),

            dcc.Download(id="download-csv"),
            dcc.Download(id="download-pdf")
        ])

    # ================= CALLBACK =================
    @app.callback(
        [
            Output("high-risk", "children"),
            Output("medium-risk", "children"),
            Output("low-risk", "children"),
            Output("total-assets", "children"),
            Output("avg-vol", "children"),
            Output("risk-dist", "children"),
            Output("risk-pie", "figure"),
            Output("last-update", "children"),
            # Output("status-text", "children"),
            Output("download-csv", "data"),
            Output("download-pdf", "data"),
        ],
        [
            Input("btn-refresh", "n_clicks"),
            Input("btn-csv", "n_clicks"),
            Input("btn-pdf", "n_clicks"),
            Input("coin-select", "value")
        ]
    )
    def update_dashboard(_, n_csv, n_pdf, coins):

        df = fetch_data()
        now = datetime.now().strftime("%H:%M:%S")

        if df.empty or not coins:
            return (
                risk_card("High Risk", pd.DataFrame(), COLORS["high"]),
                risk_card("Medium Risk", pd.DataFrame(), COLORS["medium"]),
                risk_card("Low Risk", pd.DataFrame(), COLORS["low"]),
                "-", "-", "-",
                go.Figure(),
                f"Last update: {now}",
                # "🟡 No data",
                no_update,
                no_update
            )

        # ---------------- Normalize coin identifiers so filtering works ----------------
        # Create a normalized code column (e.g., "BITC", "ETHE", ...)
        df["coin_str"] = df["coin"].astype(str)
        # try mapping by full name (e.g., "bitcoin") -> code
        df["coin_code"] = df["coin_str"].str.lower().map(NAME_TO_CODE)
        # if not matched, try mapping by symbol (e.g., "BTC") -> code
        unmatched = df["coin_code"].isna()
        if unmatched.any():
            df.loc[unmatched, "coin_code"] = df.loc[unmatched, "coin_str"].str.upper().map(SYMBOL_TO_CODE)
        # fallback: if still NaN, use uppercased original (so if API already provides codes it still works)
        df["coin_code"] = df["coin_code"].fillna(df["coin_str"].str.upper())

        # Filter using dropdown values (which are codes like "BITC", "ETHE", ...)
        df = df[df["coin_code"].isin(coins)]

        # use coin_code for display in cards
        df["coin_display"] = df["coin_code"]

        if df.empty:
            return (
                risk_card("High Risk", pd.DataFrame(), COLORS["high"]),
                risk_card("Medium Risk", pd.DataFrame(), COLORS["medium"]),
                risk_card("Low Risk", pd.DataFrame(), COLORS["low"]),
                "-", "-", "-",
                go.Figure(),
                f"Last update: {now}",
                no_update,
                no_update
            )

        high = df[df.volatility >= 70]
        medium = df[(df.volatility >= 35) & (df.volatility < 70)]
        low = df[df.volatility < 35]

        # when building cards, use coin_display field
        # ================= CARD UI =================
        def risk_card(title, df_part, color):
            if df_part.empty:
                return dbc.Card(
                    dbc.CardBody([
                        html.H5(title, style={
                            "textAlign": "center",
                            "marginBottom": "10px",
                            "color": color,
                            "fontWeight": "700"
                        }),
                        html.P("No data", style={"textAlign": "center", "color": "#9ca3af"})
                    ]),
                    style={**GLASS, "padding": "14px"}
                )

            return dbc.Card(
                dbc.CardBody([
                    # 🔥 HEADING
                    html.H5(
                        title,
                        style={
                            "textAlign": "center",
                            "marginBottom": "12px",
                            "color": color,
                            "fontWeight": "700",
                            "letterSpacing": "0.5px"
                        }
                    ),

                    html.Hr(style={"borderColor": "rgba(255,255,255,0.15)"}),

                    # 🔥 COIN LIST
                    *[
                        html.Div(
                            f"{row.coin_display} : {row.volatility:.2f}%",
                            style={
                                "background": color,
                                "padding": "6px",
                                "borderRadius": "6px",
                                "marginBottom": "6px",
                                "color": "white",
                                "fontWeight": "600",
                                "textAlign": "center"
                            }
                        )
                        for _, row in df_part.iterrows()
                    ]
                ]),
                style={**GLASS, "padding": "14px"},
            )

        fig = go.Figure(go.Pie(
            labels=["High", "Medium", "Low"],
            values=[len(high), len(medium), len(low)],
            hole=0.6,
            marker_colors=[COLORS["high"], COLORS["medium"], COLORS["low"]]
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="white"))
        )


      # ---------------- prepare CLEAN report (ONLY REQUIRED COLUMNS) ----------------

        df_report = df.copy()

        # Risk classification
        df_report["risk"] = df_report["volatility"].apply(
            lambda v: "High" if v >= 70 else ("Medium" if v >= 35 else "Low")
        )

        # Coin Name mapping (code → full name)
        CODE_TO_NAME = {
            "BITC": "Bitcoin",
            "ETHE": "Ethereum",
            "SOLA": "Solana",
            "CARD": "Cardano",
            "DOGE": "Dogecoin",
            "XRPE": "Ripple",
            "DOTE": "Polkadot",
            "LTCE": "Litecoin",
            "LINKE": "Chainlink",
            "TRXE": "Tron"
        }

        # Coin Symbol (BTC, ETH, SOL...)
        df_report["coin_symbol"] = df_report["coin_code"].map(CODE_TO_SYMBOL)

        # Coin Name
        df_report["coin_name"] = df_report["coin_code"].map(CODE_TO_NAME)


        # 🔥 FINAL REPORT (ONLY REQUIRED COLUMNS)
        df_report = df_report[
            [
                "coin_symbol",     # Coin
                "coin_name",     # Coin Name
                "volatility",    # Volatility
                "beta",          # Beta
                "sharpe",        # Sharpe Ratio
                "var",           # Value at Risk
                "risk"           # Risk Classification
            ]
        ]

        # Optional rounding (looks professional)
        df_report["volatility"] = df_report["volatility"].round(2)
        df_report["beta"] = df_report["beta"].round(2)
        df_report["sharpe"] = df_report["sharpe"].round(2)
        df_report["var"] = df_report["var"].round(2)


        csv_out = pdf_out = no_update

        if ctx.triggered_id == "btn-csv":
            csv_out = dcc.send_data_frame(
                df_report.to_csv,
                "milestone4_risk_report.csv",
                index=False
            )

        if ctx.triggered_id == "btn-pdf":
            buffer = io.BytesIO()
            pdf_doc = SimpleDocTemplate(buffer, pagesize=A4)
            table_data = [df_report.columns.tolist()] + df_report.values.tolist()
            pdf_doc.build([Table(table_data)])
            buffer.seek(0)
            pdf_out = dcc.send_bytes(
                buffer.getvalue(),
                "milestone4_risk_report.pdf"
            )

        return (
            risk_card("🔴 High Risk", high, COLORS["high"]),
            risk_card("🟡 Medium Risk", medium, COLORS["medium"]),
            risk_card("🟢 Low Risk", low, COLORS["low"]),
            f"Total Cryptocurrencies: {len(df)}",
            f"Average Volatility: {df.volatility.mean():.2f}%",
            f"{len(high)} High / {len(medium)} Medium / {len(low)} Low",
            fig,
            f"Last update: {now}",
            # "🟢 Connected to Milestone-3 API",
            csv_out,
            pdf_out
        )

    return app





