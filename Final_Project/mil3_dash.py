import dash
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output
import os

from db import get_db


FLASK_URL = "http://127.0.0.1:5000"

COIN_MAP = {
    "BITC": "Bitcoin",
    "ETHE": "Ethereum",
    "SOLA": "Solana",
    "CARD": "Cardano",
    "DOGE": "Dogecoin",
    "RIPP": "Ripple",
    "LITE": "Litecoin",
    "POLK": "Polkadot",
    "TRON": "Tron",
    "CHAI": "Chainlink"
}
GLASS_STYLE = {
                    "background": "rgba(255,255,255,0.06)",
                    "backdropFilter": "blur(18px)",
                    "WebkitBackdropFilter": "blur(18px)",
                    "border": "1px solid rgba(255,255,255,0.15)",
                    "borderRadius": "22px",
                    "boxShadow": "0 8px 30px rgba(0,0,0,0.35)",
                    "padding": "18px"
                }
DATA_DIR = "data"

def load_price_series_db(coin, start_date, end_date, window=14):
    conn = get_db()

    q = """
    SELECT date, price FROM price_history
    WHERE coin_id = (
        SELECT coin_id FROM coins WHERE coin_name=?
    )
    AND date BETWEEN ? AND ?
    ORDER BY date
    """

    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    df = pd.read_sql(q, conn, params=(coin, start_str, end_str))
    conn.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    df["returns"] = df["price"].pct_change()
    df["volatility"] = (
        df["returns"].rolling(window=window).std()
        * np.sqrt(365) * 100
    )

    return df.dropna()



# def load_price_series(coin_id, start_date, end_date, window=14):
#     file_path = os.path.join(DATA_DIR, f"milestone1_{coin_id}_history.csv")

#     if not os.path.exists(file_path):
#         return pd.DataFrame()

#     df = pd.read_csv(file_path)
#     df["date"] = pd.to_datetime(df["date"])
#     df = df.set_index("date").sort_index()

#     # 🔥 LOAD EXTRA DAYS BEFORE START
#     buffer_days = window * 2
#     buffered_start = start_date - pd.Timedelta(days=buffer_days)

#     df = df.loc[buffered_start:end_date]

#     df["returns"] = df["price"].pct_change()
#     df["volatility"] = (
#         df["returns"]
#         .rolling(window=window)
#         .std() * np.sqrt(365) * 100
#     )

#     # 🔥 FINAL CUT → ONLY USER RANGE
#     df = df.loc[start_date:end_date]

#     return df.dropna()




def get_risk_data(days):
    r = requests.get(f"{FLASK_URL}/api/risk-metrics?days={days}")
    return r.json()

def kpi_block(value, label):
    return html.Div(
        style={
            **GLASS_STYLE,
            "textAlign": "center"
        },
        children=[
            html.H3(value, style={"color": "#00ffad", "margin": "0"}),
            html.P(label, style={"color": "#cfd8dc", "marginTop": "6px"})
        ]
    )


def init_dash(flask_app):

    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        routes_pathname_prefix="/dash3/"
    )
   


    dash_app.layout = html.Div(
        style={
        "padding": "24px",
        "minHeight": "100vh",
        "background": "linear-gradient(135deg,#02050B,#071a2f,#02050B)"
        },
        children=[

            # ================= CONTROLS =================
            html.Div(
                style={
                    "display": "flex",
                    "gap": "20px",
                    "marginBottom": "22px"
                },
                children=[

                    dcc.Dropdown(
                        id="coin-select",
                        options=[
                            {"label": v, "value": k}
                            for k, v in COIN_MAP.items()
                        ],
                        value=["BITC","ETHE", "SOLA", "CARD", "DOGE"],
                        multi=True,
                        clearable=False,
                        style={
                            "width": "600px",
                            "height": "92px",
                            "background": "rgba(255,255,255,0.08)",
                            "borderRadius": "16px",
                            "border": "1px solid rgba(255,255,255,0.15)",
                            
                        },
                        className="text-dark"       
                    ),

                    # dcc.Dropdown(
                    #     id="days-select",
                    #     options=[
                    #         {"label": "30 Days", "value": 30},
                    #         {"label": "90 Days", "value": 90},
                    #         {"label": "1 Year", "value": 365},
                    #     ],
                    #     value=30,
                    #     clearable=False,
                    #     style={"width": "200px"}
                    # ),
                    dcc.DatePickerRange(
                        id="date-range",
                        start_date=pd.Timestamp.today() - pd.Timedelta(days=30),
                        end_date=pd.Timestamp.today(),
                        display_format="YYYY-MM-DD",
                        style={"background": "rgba(255,255,255,0.08)",
                               "borderRadius": "16px",
                               "border": "1px solid rgba(255,255,255,0.15)",
                               "padding": "8px 12px"
                              }
                    ),
                    

                ]
            ),

            # ================= CHARTS =================
            html.Div(
                        style={**GLASS_STYLE, "marginBottom": "22px"},
                        children=[
                            dcc.Graph(id="price-vol", )
                        ]
                    ),

            html.Div(
                        style={**GLASS_STYLE},
                        children=[
                            dcc.Graph(id="risk-return", )
                        ]
                    ),


            # ================= KPI =================
            html.Div(
                id="kpi-row",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(4,1fr)",
                    "gap": "14px",
                    "marginTop": "20px"
                }
            )
        ]
    )

    # ================= CALLBACK =================
    @dash_app.callback(
        Output("price-vol", "figure"),
        Output("risk-return", "figure"),
        Output("kpi-row", "children"),
        Input("coin-select", "value"),
        # Input("days-select", "value"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        
    )
    def update_dashboard(selected_coins, start_date, end_date):

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        fig_vol = go.Figure()
        fig_scatter = go.Figure()

        # btc_df = load_price_series("bitcoin", start, end, window=14)
        btc_df = load_price_series_db("bitcoin", start, end)

        btc_returns = btc_df["returns"]


        vols, sharpes, betas = [], [], []

        for coin_code in selected_coins:
            coin_name = COIN_MAP[coin_code]
            coin_id = coin_name.lower()

            # df = load_price_series(coin_id, start, end, window=14)
            df = load_price_series_db(coin_id, start, end)


            if df.empty:
                continue

           # ---- Volatility Time-Series ----
            fig_vol.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["price"],
                    mode="lines",
                    name=f"{coin_name} Price",
                    line=dict(width=2),
                    yaxis="y1",
                    hovertemplate=
                    "<b>%{text}</b><br>" +
                    "Date: %{x|%Y-%m-%d}<br>" +
                    "Price: %{y:.2f}<extra></extra>",
                    text=[coin_name]*len(df)
                )
            )


            avg_vol = df["volatility"].mean()
            avg_return = df["returns"].mean() * 365
            # Sharpe using risk-free rate (annualized)
            vol_decimal = avg_vol / 100
            sharpe = (avg_return - 0.04) / vol_decimal if vol_decimal else 0


            # ✅ Correct Beta
            beta = (
                np.cov(df["returns"], btc_returns)[0][1] /
                np.var(btc_returns)
            ) if np.var(btc_returns) else 0
            


            fig_scatter.add_trace(
                go.Scatter(
                    x=[avg_vol],
                    y=[avg_return],
                    mode="markers+text",
                    text=[coin_name],
                    textposition="top center",
                    marker=dict(
                        size=18,
                        opacity=0.85,
                        line=dict(width=1, color="white")
                    )
                )
            )
            fig_vol.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["volatility"],
                    mode="lines",
                    name=f"{coin_name} Volatility",
                    line=dict(width=2, dash="dot"),
                    yaxis="y2",
                    hovertemplate=
                    "<b>%{text}</b><br>" +
                    "Date: %{x|%Y-%m-%d}<br>" +
                    "Volatility: %{y:.2f}%<extra></extra>",
                    text=[coin_name]*len(df)
                )
            )



            vols.append(avg_vol)
            sharpes.append(sharpe)
            betas.append(beta)

            fig_vol.update_layout(
            title="Price & Volatility Trends",
            template="plotly_dark",

            # xaxis=dict(
            #     title="Date",
            #     range=[start, end],
            #     showgrid=False
            # ),
            xaxis=dict(
                title="Date",
                range=[df.index.min(), df.index.max()],
                showgrid=False
            ),


            yaxis=dict(
                title="Price",
                showgrid=False
            ),

            yaxis2=dict(
                title="Volatility (%)",
                overlaying="y",
                side="right",
                showgrid=False
            ),

            hovermode="x unified",
             # 🔥 LEGEND BELOW CHART
            legend=dict(
                orientation="h",        # horizontal
                yanchor="top",
                y=-0.25,                # chart ke neeche
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(b=120)         # bottom space for legend
        )


        fig_scatter.update_layout(
            title="Risk–Return Analysis",
            template="plotly_dark",
            # paper_bgcolor="rgba(0,0,0,0)",
            # plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                title="Volatility (%)",
                gridcolor="rgba(255,255,255,0.08)"
            ),
            yaxis=dict(
                title="Annualized Return",
                gridcolor="rgba(255,255,255,0.08)"
            )
        )


        kpis = [
            kpi_block(f"{np.mean(vols) if vols else 0:.2f}%", "Avg Volatility"),
            kpi_block(f"{np.mean(sharpes) if sharpes else 0:.2f}", "Avg Sharpe"),
            kpi_block(f"{np.mean(betas) if betas else 0:.2f}", "Beta vs BTC"),
            kpi_block("Low" if np.mean(vols)<30 else "Medium" if np.mean(vols)<60 else "High","Risk Level")
        ]

        return fig_vol, fig_scatter, kpis

    return dash_app
