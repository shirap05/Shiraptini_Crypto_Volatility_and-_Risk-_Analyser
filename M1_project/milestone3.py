import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Crypto Risk Analytics Dashboard",
    layout="wide"
)

# ==========================================================
# DARK BLUE DASHBOARD THEME
# ==========================================================
st.markdown("""
<style>
html, body, [data-testid="stApp"] {
    background: radial-gradient(circle at top, #0f1b3d 0%, #0b1220 45%, #050914 100%);
    color: #e5e7eb;
}

.block-container {
    padding: 2rem;
}

div[data-testid="column"] > div {
    background: rgba(255,255,255,0.04);
    border-radius: 18px;
    padding: 22px;
}

.card {
    background: linear-gradient(145deg,
        rgba(56,189,248,0.18),
        rgba(14,165,233,0.06)
    );
    border-radius: 16px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 0 20px rgba(56,189,248,0.15);
}

h1, h2, h3 {
    color: #60a5fa;
}

ul {
    color: #c7d2fe;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# LOAD DATA
# ==========================================================
@st.cache_data
def load_data():
    df = pd.read_csv("crypto_processed.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

data = load_data()

# ==========================================================
# TITLE
# ==========================================================
st.markdown("## 🔷 Milestone 3: Visualization Dashboard")

# ==========================================================
# LAYOUT
# ==========================================================
left, right = st.columns([1.1, 2.4])

# ==========================================================
# LEFT PANEL
# ==========================================================
with left:
    st.markdown("### 📋 Requirements")
    st.markdown("""
    • Interactive visualizations (Plotly)  
    • Time-series price & volatility  
    • Risk–return scatter plots  
    • Multi-asset comparison  
    """)

    st.markdown("### 📤 Outputs")
    st.markdown("""
    • Interactive crypto dashboard  
    • Volatility vs Sharpe visualization  
    • Responsive UI with filters  
    """)

    st.markdown("### 🔄 Controls")

    selected_crypto = st.multiselect(
        "Assets",
        options=data["Crypto"].unique(),
        default=data["Crypto"].unique()
    )

    start_date = st.date_input("Start Date", data["Date"].min())
    end_date = st.date_input("End Date", data["Date"].max())

    st.markdown(
        f"<small>Last Updated: {pd.Timestamp.now()}</small>",
        unsafe_allow_html=True
    )

# ==========================================================
# FILTER DATA
# ==========================================================
filtered = data[
    (data["Crypto"].isin(selected_crypto)) &
    (data["Date"] >= pd.to_datetime(start_date)) &
    (data["Date"] <= pd.to_datetime(end_date))
]

# ==========================================================
# RIGHT PANEL
# ==========================================================
with right:

    # ------------------------------------------------------
    # PRICE & VOLATILITY (DUAL AXIS)
    # ------------------------------------------------------
    st.markdown("### 📈 Price & Volatility Trends")

    fig = go.Figure()

    for coin in filtered["Crypto"].unique():
        dfc = filtered[filtered["Crypto"] == coin]

        fig.add_trace(go.Scatter(
            x=dfc["Date"],
            y=dfc["Close"],
            name=f"{coin} Price",
            mode="lines"
        ))

        fig.add_trace(go.Scatter(
            x=dfc["Date"],
            y=dfc["Volatility"],
            name=f"{coin} Volatility",
            mode="lines",
            yaxis="y2",
            line=dict(dash="dot")
        ))

    fig.update_layout(
        template="plotly_dark",
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Price"),
        yaxis2=dict(title="Volatility", overlaying="y", side="right"),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )

    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------
    # RISK–RETURN SCATTER (BIG POINTS)
    # ------------------------------------------------------
    st.markdown("### 🎯 Risk–Return Analysis")

    rr = (
        filtered
        .groupby("Crypto")
        .agg({
            "Returns": "mean",
            "Volatility": "mean"
        })
        .reset_index()
    )

    scatter = px.scatter(
        rr,
        x="Volatility",
        y="Returns",
        color="Crypto",
        template="plotly_dark"
    )

    # ✅ BIG POINTS FIX
    scatter.update_traces(
        marker=dict(
            size=20,
            opacity=0.9,
            line=dict(width=1.5, color="white")
        )
    )

    scatter.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(scatter, use_container_width=True)

    # ------------------------------------------------------
    # KPI CARDS
    # ------------------------------------------------------
    avg_vol = filtered["Volatility"].mean()
    avg_ret = filtered["Returns"].mean()
    avg_sharpe = filtered["Sharpe_Ratio"].mean()

    if avg_vol < 0.3:
        risk_level = "Low"
    elif avg_vol < 0.6:
        risk_level = "Medium"
    else:
        risk_level = "High"

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"<div class='card'><h2>{avg_vol:.2%}</h2><p>Volatility</p></div>", unsafe_allow_html=True)

    with k2:
        st.markdown(f"<div class='card'><h2>{avg_sharpe:.2f}</h2><p>Sharpe Ratio</p></div>", unsafe_allow_html=True)

    with k3:
        st.markdown(f"<div class='card'><h2>{avg_ret:.2%}</h2><p>Avg Return</p></div>", unsafe_allow_html=True)

    with k4:
        st.markdown(f"<div class='card'><h2>{risk_level}</h2><p>Risk Level</p></div>", unsafe_allow_html=True)
