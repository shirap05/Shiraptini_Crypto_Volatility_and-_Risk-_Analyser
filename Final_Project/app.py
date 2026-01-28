from flask import Flask, render_template, jsonify, request, send_file
import requests
import pandas as pd
import numpy as np
import os


import time
from datetime import datetime, timedelta, UTC

from flask import redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from mil3_dash import init_dash as init_dash_m3
from mil4_dash import init_dash as init_dash_m4



from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

from threading import Lock, Thread


from db import get_db, create_tables, DB_PATH



app = Flask(__name__)
app.secret_key = "cvara-secret"
#🟢 QUICK MEMORY TRICK

# Imports → CONFIG → Constants → Cache → Functions → Routes → app.run

# =====================================================
# CONFIG
# =====================================================
API_KEY = "CG-j36Jb6fjM7XXadA6CDJPLLAU"

COINS = [
    "bitcoin", "ethereum", "solana", "cardano", "dogecoin",
    "ripple", "litecoin", "polkadot", "tron", "chainlink"
]
SYMBOL_MAP = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "cardano": "ADA",
    "dogecoin": "DOGE",
    "ripple": "XRP",
    "litecoin": "LTC",
    "polkadot": "DOT",
    "tron": "TRX",
    "chainlink": "LINK"
}
REVERSE_SYMBOL_MAP = {v: k for k, v in SYMBOL_MAP.items()}


VS_CURRENCY = "usd"

RISK_FREE_RATE = 0.04   # 4% yearly (used in Sharpe ratio)
TRADING_DAYS = 365
# DATA_DIR = "data"
# os.makedirs(DATA_DIR, exist_ok=True)


# =====================================================
# CACHE + RATE LIMIT CONTROL
# =====================================================
CACHE = {
    "market": {"data": [], "time": 0},
    "history": {},
    "risk": {"data": {}, "time": 0}
}




CACHE_TTL_MARKET = 90        # seconds-1.5 minutes
CACHE_TTL_HISTORY = 300     # seconds-5 minutes
CACHE_TTL_RISK = 300  # 5 minutes

api_lock = Lock()
db_init_lock = Lock()
db_write_lock = Lock()
db_initialized = False
startup_tasks_started = False
startup_tasks_lock = Lock()

def run_startup_tasks():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM price_history LIMIT 1")
        has_rows = cur.fetchone() is not None
        conn.close()
        if not has_rows:
            init_database_data()
    except Exception:
        pass

    try:
        update_today_prices_and_cleanup()
    except Exception:
        pass

def kick_off_startup_tasks():
    global startup_tasks_started
    with startup_tasks_lock:
        if startup_tasks_started:
            return
        startup_tasks_started = True
        Thread(target=run_startup_tasks, daemon=True).start()

@app.before_request
def ensure_db_ready():
    global db_initialized
    if db_initialized:
        return
    with db_init_lock:
        if db_initialized:
            return
        create_tables()
        kick_off_startup_tasks()

        db_initialized = True

def ensure_coin_id(cur, coin):
    cur.execute("SELECT coin_id FROM coins WHERE coin_name=?", (coin,))
    row = cur.fetchone()
    if row:
        return row[0]
    symbol = SYMBOL_MAP.get(coin, coin[:3].upper())
    cur.execute(
        "INSERT INTO coins (coin_name, symbol) VALUES (?,?)",
        (coin, symbol)
    )
    return cur.lastrowid

def save_current_price(cur, coin, price, date_str):
    coin_id = ensure_coin_id(cur, coin)
    cur.execute("""
    SELECT 1 FROM price_history
    WHERE coin_id=? AND date=?
    """, (coin_id, date_str))
    if cur.fetchone():
        cur.execute("""
        UPDATE price_history
        SET price=?
        WHERE coin_id=? AND date=?
        """, (price, coin_id, date_str))
    else:
        cur.execute("""
        INSERT INTO price_history (coin_id, date, price)
        VALUES (?,?,?)
        """, (coin_id, date_str, price))

def save_market_snapshot(cur, coin, price, change_24h, volume, fetched_at):
    coin_id = ensure_coin_id(cur, coin)
    cur.execute("""
    INSERT INTO market_snapshot (coin_id, fetched_at, price, change_24h, volume)
    VALUES (?,?,?,?,?)
    """, (coin_id, fetched_at, price, change_24h, volume))

def cleanup_market_snapshot(cur, cutoff_dt):
    cur.execute("""
    DELETE FROM market_snapshot
    WHERE fetched_at < ?
    """, (cutoff_dt,))

def cleanup_price_history(cur, cutoff_date):
    cur.execute("""
    DELETE FROM price_history
    WHERE date < ?
    """, (cutoff_date,))

def update_today_prices_and_cleanup():
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    cutoff_date = (datetime.now(UTC) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    cutoff_dt = (datetime.now(UTC) - pd.Timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    conn = None
    with db_write_lock:
        try:
            conn = get_db()
            cur = conn.cursor()
            for coin in COINS[:10]:
                try:
                    r = requests.get(
                        "https://api.coingecko.com/api/v3/coins/markets",
                        params={
                            "vs_currency": VS_CURRENCY,
                            "ids": coin,
                            "price_change_percentage": "24h"
                        },
                        headers={"x-cg-demo-api-key": API_KEY},
                        timeout=10
                    )
                    data = r.json()[0]
                    save_current_price(cur, coin, data["current_price"], date_str)
                    save_market_snapshot(
                        cur,
                        coin,
                        data["current_price"],
                        data.get("price_change_percentage_24h", 0),
                        data["total_volume"],
                        fetched_at
                    )
                except Exception:
                    continue
            cleanup_price_history(cur, cutoff_date)
            cleanup_market_snapshot(cur, cutoff_dt)
            conn.commit()
        finally:
            if conn:
                conn.close()

def save_risk_metrics_snapshot(cur, coin, days, metrics, computed_at):
    coin_id = ensure_coin_id(cur, coin)
    cur.execute("""
    INSERT INTO risk_metrics_snapshot (
        coin_id, days, computed_at, volatility, sharpe, beta, var
    )
    VALUES (?,?,?,?,?,?,?)
    """, (
        coin_id,
        days,
        computed_at,
        metrics["volatility"],
        metrics["sharpe"],
        metrics["beta"],
        metrics["var"]
    ))

def cleanup_risk_metrics_snapshot(cur, cutoff_dt):
    cur.execute("""
    DELETE FROM risk_metrics_snapshot
    WHERE computed_at < ?
    """, (cutoff_dt,))

def save_risk_snapshot(rows, days, computed_at):
    with db_write_lock:
        conn = get_db()
        try:
            cur = conn.cursor()
            for row in rows:
                # row["coin"] is symbol; map back to coin name
                coin_name = REVERSE_SYMBOL_MAP.get(row["coin"], row["coin"].lower())
                save_risk_metrics_snapshot(cur, coin_name, days, row, computed_at)
            cutoff_dt = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            cleanup_risk_metrics_snapshot(cur, cutoff_dt)
            conn.commit()
        finally:
            conn.close()

def compute_risk_payload(days):
    btc_df = load_price_from_db("bitcoin", days)
    if btc_df.empty:
        return None, "No BTC data. Run /api/init-history first."
    btc_returns = btc_df["returns"]

    metrics = {
        "labels": [],
        "volatility": [],
        "sharpe": [],
        "beta": [],
        "var": []
    }

    table = []

    for coin in COINS:
        df = load_price_from_db(coin, days)
        if df.empty:
            continue

        returns = df["returns"]

        volatility = returns.std() * np.sqrt(365) * 100
        sharpe = (
            (returns.mean() * 365 - RISK_FREE_RATE) /
            (returns.std() * np.sqrt(365))
        ) if returns.std() else 0
        beta = (
            np.cov(returns, btc_returns)[0][1] /
            np.var(btc_returns)
        ) if np.var(btc_returns) else 0
        var95 = abs(np.percentile(returns, 5)) * 100

        symbol = SYMBOL_MAP.get(coin, coin.upper())

        metrics["labels"].append(symbol)
        metrics["volatility"].append(round(volatility, 2))
        metrics["sharpe"].append(round(sharpe, 2))
        metrics["beta"].append(round(beta, 2))
        metrics["var"].append(round(var95, 2))

        table.append({
            "coin": symbol,
            "volatility": round(volatility, 2),
            "sharpe": round(sharpe, 2),
            "beta": round(beta, 2),
            "var": round(var95, 2)
        })

    payload = {
        "metrics": metrics,
        "table": table
    }
    return payload, None
@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    password = generate_password_hash(password)

    with db_write_lock:
        retries = 3
        for attempt in range(retries):
            try:
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM user WHERE email=?", (email,))
                if cursor.fetchone():
                    conn.close()
                    return "Email already registered"

                cursor.execute(
                    "INSERT INTO user (username, email, password) VALUES (?,?,?)",
                    (username, email, password)
                )
                conn.commit()
                conn.close()
                break
            except Exception as e:
                try:
                    conn.close()
                except Exception:
                    pass
                if "database is locked" in str(e).lower() and attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                raise

    return redirect(url_for("auth"))


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, password FROM user WHERE email=?",
            (email,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session["id"] = user[0]
            session["username"] = user[1]
            return redirect(url_for("Base"))

        return render_template("auth.html", error="Invalid email or password")

    return render_template("auth.html")


# ---------------- MILESTONE 1 ----------------
# Generate & save historical price CSV (365 days base data)


@app.route("/api/crypto")
def get_crypto_data():
    records = []
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    cutoff_dt = (datetime.now(UTC) - pd.Timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    cutoff_date = (datetime.now(UTC) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")

    conn = None
    with db_write_lock:
        try:
            conn = get_db()
            cur = conn.cursor()

            for coin in COINS[:10]:
                try:
                    r = requests.get(
                        "https://api.coingecko.com/api/v3/coins/markets",
                        params={
                            "vs_currency": VS_CURRENCY,
                            "ids": coin,
                            "price_change_percentage": "24h"
                        },
                        headers={"x-cg-demo-api-key": API_KEY},
                        timeout=10
                    )
                    data = r.json()[0]

                    records.append({
                        "id": data["id"],                # REQUIRED
                        "name": data["name"],
                        "symbol": data["symbol"],
                        "current_price": data["current_price"],
                        "price_change_percentage_24h": round(
                            data.get("price_change_percentage_24h", 0), 2
                        ),
                        "total_volume": data["total_volume"]
                    })

                    save_current_price(cur, coin, data["current_price"], date_str)
                    save_market_snapshot(
                        cur,
                        coin,
                        data["current_price"],
                        data.get("price_change_percentage_24h", 0),
                        data["total_volume"],
                        fetched_at
                    )
                except Exception:
                    continue

            cleanup_market_snapshot(cur, cutoff_dt)
            cleanup_price_history(cur, cutoff_date)
            conn.commit()
        finally:
            if conn:
                conn.close()

    return jsonify(records)


# =====================================================
# 7-DAY MULTI-COIN HISTORY (ALL SELECTED COINS)
# =====================================================
@app.route("/api/history")
def history():
    coin_param = request.args.get("coins")
    if not coin_param:
        return jsonify({"dates": [], "prices": {}})

    coins = coin_param.split(",")
    now = time.time()

    dates = []
    prices = {}

    for coin in coins:
        try:
            res = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart",
                params={"vs_currency": VS_CURRENCY, "days": 7},
                headers={"x-cg-demo-api-key": API_KEY},
                timeout=15
            )

            if res.status_code == 429:
                print(f"⚠️ Rate limit hit (history) → {coin}")
                prices[coin] = CACHE["history"].get(coin, {}).get("prices", [])
                continue

            res.raise_for_status()
            raw = res.json().get("prices", [])

            # ✅ TAKE 1 DATA POINT PER DAY (EVERY 24 HOURS)
            daily_prices = raw[::24][:7]

            
            dates = [f"Day{i+1}" for i in range(len(daily_prices))]

            prices[coin] = [round(p[1], 2) for p in daily_prices]

            # Save real data snapshot for milestone-1 chart
            conn = None
            with db_write_lock:
                try:
                    conn = get_db()
                    cur = conn.cursor()
                    for p in daily_prices:
                        date_str = datetime.fromtimestamp(p[0] / 1000).strftime("%Y-%m-%d")
                        save_current_price(cur, coin, p[1], date_str)
                    conn.commit()
                finally:
                    if conn:
                        conn.close()
            


            CACHE["history"][coin] = {
                "dates": dates,
                "prices": prices[coin],
                "time": now
            }

        except Exception as e:
            print(f"History API error for {coin}:", e)
            prices[coin] = CACHE["history"].get(coin, {}).get("prices", [])

    return jsonify({"dates": dates, "prices": prices})
# ---------------- MILESTONE 1 ---------------- 
# Generate & save historical price CSV (365 days base data) 
# def generate_history_csv(coin, days):
#     url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
#     file_path = os.path.join(DATA_DIR, f"milestone1_{coin}_history.csv")

#     # 🛑 prevent re-fetch
#     if os.path.exists(file_path):
#         return True
         
#     params = {"vs_currency": "usd", "days": days} 
#     r = requests.get(
#                 url,
#                 params=params,
#                 headers={"x-cg-demo-api-key": API_KEY},
#                 timeout=15
#             )
 
#     if r.status_code != 200: return False
#     raw = r.json().get("prices", []) 
#     if not raw: return False 
#     df = pd.DataFrame(raw, columns=["time", "price"])
#     df["date"] = pd.to_datetime(df["time"], unit="ms") 
#     df = df[["date", "price"]]
#     df["coin"] = coin 
#     file_path = os.path.join(DATA_DIR, f"milestone1_{coin}_history.csv")
#     df.to_csv(file_path, index=False)
#     return True






def save_price_history(conn, coin, days=365):
    cur = conn.cursor()

    # coin master
    cur.execute("SELECT coin_id FROM coins WHERE coin_name=?", (coin,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO coins (coin_name, symbol) VALUES (?,?)",
            (coin, coin[:3].upper())
        )
        coin_id = cur.lastrowid
    else:
        coin_id = row[0]

    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart",
            params={"vs_currency": "usd", "days": days},
            headers={"x-cg-demo-api-key": API_KEY},
            timeout=15
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
    except Exception:
        return False

    for p in prices:
        date = datetime.fromtimestamp(p[0]/1000).strftime("%Y-%m-%d")
        price = p[1]

        cur.execute("""
        SELECT 1 FROM price_history
        WHERE coin_id=? AND date=?
        """, (coin_id, date))

        if not cur.fetchone():
            cur.execute("""
            INSERT INTO price_history (coin_id, date, price)
            VALUES (?,?,?)
            """, (coin_id, date, price))
    return True



def init_database_data():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")

    for coin in COINS:
        try:
            save_price_history(conn, coin, days=365)
        except Exception:
            continue

    conn.commit()
    conn.close()




# ---------------- MILESTONE 2 ----------------
# Load Milestone 1 data + apply day filter

# def load_milestone1_data(coin, days):
#     file_path = os.path.join(DATA_DIR, f"milestone1_{coin}_history.csv")

#     # Auto-generate if missing
#     if not os.path.exists(file_path):
#         generate_history_csv(coin, days=365)

#     df = pd.read_csv(file_path)
#     df["date"] = pd.to_datetime(df["date"])

#     # Apply 30 / 90 / 365 days logic
#     df = df.sort_values("date").tail(days)

#     df["returns"] = df["price"].pct_change()
#     return df.dropna()




def load_price_from_db(coin, days):
    from db import get_db

    conn = get_db()
    q = """
    SELECT date, price FROM price_history
    WHERE coin_id = (
        SELECT coin_id FROM coins WHERE coin_name=?
    )
    ORDER BY date DESC
    LIMIT ?
    """
    df = pd.read_sql(q, conn, params=(coin, days))
    conn.close()

    if df.empty:
        return df

    df = df.sort_values("date")
    df["returns"] = df["price"].pct_change()
    return df.dropna()





@app.route("/api/risk-metrics")
def risk_metrics():
    try:
        days = int(request.args.get("days", 30))
        if days not in [7, 30, 90, 365]:
            days = 30
    except:
        days = 30

    now = time.time()
    if days in CACHE["risk"]["data"] and now - CACHE["risk"]["time"] < CACHE_TTL_RISK:
        return jsonify(CACHE["risk"]["data"][days])

    payload, err = compute_risk_payload(days)
    if err:
        return jsonify({"error": err}), 400

    computed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    save_risk_snapshot(payload["table"], days, computed_at)

    CACHE["risk"]["data"][days] = payload
    CACHE["risk"]["time"] = now

    return jsonify(payload)


@app.route("/api/risk-metrics-latest")
def risk_metrics_latest():
    try:
        days = int(request.args.get("days", 30))
        if days not in [7, 30, 90, 365]:
            days = 30
    except:
        days = 30

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT MAX(computed_at) FROM risk_metrics_snapshot WHERE days=?",
        (days,)
    )
    row = cur.fetchone()
    if not row or not row[0]:
        conn.close()
        return jsonify({"table": [], "computed_at": None})

    computed_at = row[0]
    q = """
    SELECT c.coin_name, c.symbol, r.volatility, r.sharpe, r.beta, r.var
    FROM risk_metrics_snapshot r
    JOIN coins c ON r.coin_id = c.coin_id
    WHERE r.days=? AND r.computed_at=?
    """
    df = pd.read_sql(q, conn, params=(days, computed_at))
    conn.close()

    table = []
    for _, r in df.iterrows():
        # Prefer canonical symbol map; fall back to stored symbol if valid
        symbol = SYMBOL_MAP.get(r["coin_name"], None)
        if not symbol:
            symbol = r["symbol"] or r["coin_name"].upper()
        table.append({
            "coin": symbol,
            "coin_name": r["coin_name"],
            "volatility": round(float(r["volatility"]), 2),
            "sharpe": round(float(r["sharpe"]), 2),
            "beta": round(float(r["beta"]), 2),
            "var": round(float(r["var"]), 2)
        })

    return jsonify({"table": table, "computed_at": computed_at, "days": days})


@app.route("/api/risk-metrics-batch")
def risk_metrics_batch():
    slots = [7, 30, 90, 365]
    computed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    results = {}

    for days in slots:
        payload, err = compute_risk_payload(days)
        if err:
            results[str(days)] = {"error": err}
            continue
        save_risk_snapshot(payload["table"], days, computed_at)
        results[str(days)] = {"rows": len(payload["table"])}

        CACHE["risk"]["data"][days] = payload
        CACHE["risk"]["time"] = time.time()

    return jsonify({"status": "ok", "computed_at": computed_at, "slots": results})




@app.route("/dashboard-metrics")
def dashboard_metrics():
    start = time.time()

    # Simulate or calculate metrics
    metrics = {
        "visualization": 4,    # number of graphs
        "ui": 8,               # UI quality score
        "interactivity": 3,    # dropdown + date picker + hover
        "risk": 3,             # volatility, returns, risk-return
        "performance": round(10 - (time.time() - start)*5, 1)
    }

    return jsonify(metrics)


@app.route("/api/init-history")
def init_history():
    with db_write_lock:
        conn = get_db()
        try:
            for coin in COINS:
                save_price_history(conn, coin, days=365)
            conn.commit()
        finally:
            conn.close()
    return jsonify({"status": "ok", "days": 365, "coins": len(COINS)})





# =====================================================
# ROUTES
# =====================================================
@app.route("/")
def home():
    return redirect(url_for("auth"))

@app.route("/Base")
def Base():
    if "id" not in session:
        return redirect(url_for("auth"))
    return render_template("Base.html", username=session["username"])




@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))

# @app.route("/milestone1")
# def milestone1():
#     missing = []

#     for coin in COINS:
#         file_path = os.path.join(DATA_DIR, f"milestone1_{coin}_history.csv")

#         # ⚡ already exists → skip API
#         if not os.path.exists(file_path):
#             generate_history_csv(coin, days=365)
#             missing.append(coin)

#     print("Generated for:", missing)
#     return render_template("milestone1.html")


@app.route("/milestone1")
def milestone1():
    return render_template("milestone1.html")

@app.route("/milestone2")
def milestone2():
    return render_template("milestone2.html" )  

@app.route("/milestone3")
def milestone3():
    # Dash will render here
    return render_template("milestone3.html")

@app.route("/milestone4")
def milestone4():
    return render_template("milestone4.html")


# @app.route("/api/refresh-data")
# def refresh_data():
    
#     status = {}

#     for coin in COINS:
#         success = generate_history_csv(coin, days=365)
#         status[coin] = "ok" if success else "failed"

#     return jsonify(status)

# ---------- INIT DASH ----------
  
init_dash_m3(app)   # url: /dash3/
init_dash_m4(app)   # url: /dash4/


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
   kick_off_startup_tasks()
   # Disable reloader to avoid duplicate processes locking SQLite.
   app.run(debug=True, use_reloader=False)
