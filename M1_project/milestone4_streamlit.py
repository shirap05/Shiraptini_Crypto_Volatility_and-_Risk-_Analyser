import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Milestone 4 – Risk Classification & Reporting",
    layout="wide"
)

# =========================================================
# THEME (MATCH IMAGE)
# =========================================================
st.markdown("""
<style>
html, body, [data-testid="stApp"] {
    background: radial-gradient(circle at top, #0f1b3d, #0b1220, #050914);
    color: #e5e7eb;
}

.block-container {
    padding: 2.5rem;
}

.panel {
    background: rgba(255,255,255,0.04);
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 0 25px rgba(0,0,0,0.3);
}

.card {
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
    font-weight: bold;
    color: white;
}

.high { background: linear-gradient(135deg, #7f1d1d, #dc2626); }
.medium { background: linear-gradient(135deg, #92400e, #f59e0b); }
.low { background: linear-gradient(135deg, #065f46, #22c55e); }

h1, h2, h3 {
    color: #60a5fa;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data
def load_data():
    df = pd.read_csv("crypto_processed.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

df = load_data()

# =========================================================
# USE LATEST 30-DAY VOLATILITY (INDUSTRY STANDARD)
# =========================================================
latest = (
    df.sort_values("Date")
      .groupby("Crypto")
      .tail(30)
      .groupby("Crypto")
      .agg({
          "Volatility": "mean",
          "Sharpe_Ratio": "mean"
      })
      .reset_index()
)

# =========================================================
# RISK THRESHOLDS (AUTO, IMAGE-CONSISTENT)
# =========================================================
high_th = latest["Volatility"].quantile(0.66)
low_th  = latest["Volatility"].quantile(0.33)

def classify(v):
    if v >= high_th:
        return "High"
    elif v >= low_th:
        return "Medium"
    else:
        return "Low"

latest["Risk"] = latest["Volatility"].apply(classify)

high_risk = latest[latest["Risk"] == "High"]
med_risk  = latest[latest["Risk"] == "Medium"]
low_risk  = latest[latest["Risk"] == "Low"]

# =========================================================
# HEADER
# =========================================================
st.markdown("## 🔷 Milestone 4: Risk Classification & Reporting")
st.markdown("**Final Analysis – Crypto Volatility and Risk Analyzer**")

# =========================================================
# LAYOUT
# =========================================================
left, right = st.columns([1.1, 2.4])

# =========================================================
# LEFT PANEL
# =========================================================
with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.markdown("### 📋 Requirements")
    st.markdown("""
    • Risk thresholds for classification  
    • Visual highlighting of high-risk assets  
    • Summary reports (CSV, PNG, PDF)  
    • System validation & documentation  
    """)

    st.markdown("### 📤 Outputs")
    st.markdown("""
    • Complete dashboard with risk classification  
    • Categorized risk report with metrics  
    • Documentation & deployment guide  
    """)

    st.markdown("### 📊 Project Completion Status")

    progress_fig = go.Figure(
        data=[go.Bar(
            x=["Milestone 1", "Milestone 2", "Milestone 3", "Milestone 4"],
            y=[100, 100, 100, 100],
            marker_color="#22c55e"
        )]
    )

    progress_fig.update_layout(
        height=240,
        template="plotly_dark",
        yaxis=dict(title="Completion (%)", range=[0,100]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(progress_fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# RIGHT PANEL
# =========================================================
with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.markdown("### 📊 Risk Classification Dashboard")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 🔴 High Risk")
        for _, r in high_risk.iterrows():
            st.markdown(
                f'<div class="card high">{r["Crypto"]}<br>{r["Volatility"]*100:.2f}%</div>',
                unsafe_allow_html=True
            )

    with c2:
        st.markdown("### 🟡 Medium Risk")
        for _, r in med_risk.iterrows():
            st.markdown(
                f'<div class="card medium">{r["Crypto"]}<br>{r["Volatility"]*100:.2f}%</div>',
                unsafe_allow_html=True
            )

    with c3:
        st.markdown("### 🟢 Low Risk")
        for _, r in low_risk.iterrows():
            st.markdown(
                f'<div class="card low">{r["Crypto"]}<br>{r["Volatility"]*100:.2f}%</div>',
                unsafe_allow_html=True
            )

    # =====================================================
    # RISK SUMMARY REPORT
    # =====================================================
    st.markdown("### 📑 Risk Summary Report")

    colA, colB = st.columns([1.3,1])

    with colA:
        st.markdown(f"""
        **Total Cryptocurrencies:** {len(latest)}  
        **Average Volatility:** {latest["Volatility"].mean()*100:.2f}%  
        **Risk Distribution:**  
        {len(high_risk)} High / {len(med_risk)} Medium / {len(low_risk)} Low
        """)

        st.download_button(
            "⬇ Export CSV",
            latest.to_csv(index=False),
            file_name="risk_summary.csv"
        )

    with colB:
        donut = go.Figure(
            data=[go.Pie(
                labels=["High Risk", "Medium Risk", "Low Risk"],
                values=[len(high_risk), len(med_risk), len(low_risk)],
                hole=0.55,
                textinfo="percent",
                textfont=dict(size=18, color="white"),
                marker_colors=["#dc2626", "#f59e0b", "#22c55e"]
            )]
        )

        donut.update_layout(
            height=380,
            width=380,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="white", size=14))
        )

        st.plotly_chart(donut, use_container_width=False)

    st.markdown("</div>", unsafe_allow_html=True)
