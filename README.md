# 📊 Cryptocurrency Volatility & Risk Analyzer

A full-stack **data analytics and visualization project** that analyzes **cryptocurrency price trends, volatility, and financial risk metrics** using Python, Flask, Dash, and SQLite.  
This project integrates multiple milestones into a single web application with interactive dashboards.

---

## 🚀 Features

### 🔐 Authentication
- User registration and login
- Secure password hashing
- Session-based authentication

### 📈 Live Market Data
- Real-time cryptocurrency prices using the **CoinGecko API**
- 24-hour price change and trading volume
- API caching to handle rate limits efficiently

### 🗂️ Historical Data Management
- Stores up to **365 days of historical price data**
- SQLite database with WAL mode enabled
- Automatic cleanup of outdated records

### 📉 Risk Metrics Calculation
- Volatility
- Sharpe Ratio
- Beta (relative to Bitcoin)
- Value at Risk (VaR)

### 📊 Interactive Dashboards
#### Milestone 3 – Risk & Performance Dashboard
- Price and volatility time-series graphs
- Risk–return scatter plots
- Coin selection and date-range filters

#### Milestone 4 – Risk Classification Dashboard
- Asset classification into **Low / Medium / High risk**
- Interactive charts and summaries
- Export reports as **CSV and PDF**

---

## 🛠️ Tech Stack

| Category | Technology |
|--------|------------|
| Backend | Flask |
| Frontend | HTML, CSS |
| Dashboards | Dash, Plotly |
| Database | SQLite |
| Data Analysis | Pandas, NumPy |
| API | CoinGecko |
| Reporting | ReportLab |

---

## 📁 Project Structure

FINAL_PROJECT/
│
├── app.py # Main Flask application
├── db.py # Database schema & connection
├── mil3_dash.py # Dash app (Milestone 3)
├── mil4_dash.py # Dash app (Milestone 4)
├── requirements.txt # Project dependencies
├── README.md # Documentation
│
├── database/
│ └── cvara.db # SQLite database (auto-generated)
│
├── templates/
│ ├── auth.html
│ ├── Base.html
│ ├── milestone1.html
│ ├── milestone2.html
│ ├── milestone3.html

│ └── milestone4.html
│
└── static/
└── css / assets
Dashboard ---
<img width="1911" height="915" alt="Screenshot 2026-01-29 193548" src="https://github.com/user-attachments/assets/23cb0651-8faf-47ad-b651-2ec892d6d377" />
