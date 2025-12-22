import requests
import pandas as pd
import numpy as np
from datetime import datetime

COINS = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "Solana": "SOLUSDT",
    "Cardano": "ADAUSDT",
    "Dogecoin": "DOGEUSDT"
}

DAYS = 180   # last 6 months

rows = []

for crypto, symbol in COINS.items():
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1d",
        "limit": DAYS
    }

    data = requests.get(url, params=params).json()

    closes = [float(d[4]) for d in data]
    dates = [datetime.fromtimestamp(d[0]/1000) for d in data]

    returns = np.diff(np.log(closes))
    volatility = pd.Series(returns).rolling(7).std()
    sharpe = returns.mean() / (returns.std() + 1e-9)

    for i in range(1, len(dates)):
        rows.append({
            "Date": dates[i],
            "Crypto": crypto,
            "Close": closes[i],
            "Returns": returns[i-1],
            "Volatility": volatility.iloc[i-1],
            "Sharpe_Ratio": sharpe
        })

df = pd.DataFrame(rows)
df.to_csv("crypto_processed.csv", index=False)

print("✅ crypto_processed.csv generated successfully")
