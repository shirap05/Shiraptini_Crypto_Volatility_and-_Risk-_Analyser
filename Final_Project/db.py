import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "cvara.db")

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    cur = conn.cursor()

    # USER TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # COINS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS coins (
        coin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_name TEXT UNIQUE,
        symbol TEXT
    )
    """)

    # PRICE HISTORY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_id INTEGER,
        date TEXT,
        price REAL,
        FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
    )
    """)

    # MARKET SNAPSHOT (current metrics)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_id INTEGER,
        fetched_at TEXT,
        price REAL,
        change_24h REAL,
        volume REAL,
        FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
    )
    """)

    # RISK METRICS SNAPSHOT (milestone 2)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_metrics_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_id INTEGER,
        days INTEGER,
        computed_at TEXT,
        volatility REAL,
        sharpe REAL,
        beta REAL,
        var REAL,
        FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
    )
    """)

    # DASHBOARD TIMESERIES SNAPSHOT (milestone 3)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_timeseries_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        computed_at TEXT,
        avg_volatility REAL,
        avg_return REAL,
        sharpe REAL,
        beta REAL,
        FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
    )
    """)

    # RISK CLASSIFICATION SNAPSHOT (milestone 4)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_classification_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_id INTEGER,
        days INTEGER,
        computed_at TEXT,
        volatility REAL,
        sharpe REAL,
        beta REAL,
        var REAL,
        risk TEXT,
        FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
    )
    """)
    

    conn.commit()
    conn.close()
