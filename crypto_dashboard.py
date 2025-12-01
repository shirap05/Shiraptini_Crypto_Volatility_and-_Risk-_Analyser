# crypto_dashboard.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# ========== CONFIG ==========
# 8 coins total (CoinGecko IDs)
coins = ["bitcoin", "ethereum", "solana", "litecoin", "ripple", "polkadot", "cardano", "dogecoin"]
vs_currency = "usd"

# CoinGecko simple price endpoint allows getting price, 24h change, 24h vol, and last updated
simple_price_url = "https://api.coingecko.com/api/v3/simple/price"

# ========== FETCH SUMMARY DATA ==========
params = {
    "ids": ",".join(coins),
    "vs_currencies": vs_currency,
    "include_24hr_change": "true",
    "include_24hr_vol": "true",
    "include_last_updated_at": "true"
}
resp = requests.get(simple_price_url, params=params)
resp.raise_for_status()
data = resp.json()

# Transform into DataFrame
rows = []
for coin in coins:
    entry = data.get(coin, {})
    price = entry.get(vs_currency)
    change_24h = entry.get(f"{vs_currency}_24h_change")  # percent
    vol_24h = entry.get(f"{vs_currency}_24h_vol")
    last_updated_at = entry.get("last_updated_at")  # unix timestamp (seconds)
    rows.append({
        "coin": coin,
        "price_usd": price,
        "change_24h_pct": change_24h,
        "volume_24h_usd": vol_24h,
        "last_updated_at": last_updated_at
    })

df = pd.DataFrame(rows)

# Format numbers
df["price_usd"] = df["price_usd"].map(lambda x: f"${x:,.2f}" if x is not None else "N/A")
df["volume_24h_usd"] = df["volume_24h_usd"].map(lambda x: f"${x:,.0f}" if x is not None else "N/A")

# ========== Task 2: Format 24h Change with arrows ==========
def fmt_change(val):
    if val is None:
        return "N/A"
    # val is percent (like 1.2345)
    arrow = "▲" if val >= 0 else "▼"
    sign = "+" if val >= 0 else ""
    return f"{arrow} {sign}{val:.2f}%"

df["24h Change"] = df["change_24h_pct"].apply(fmt_change)

# Keep columns for display
display_df = df[["coin", "price_usd", "24h Change", "volume_24h_usd", "last_updated_at"]].copy()
display_df.rename(columns={
    "coin": "Coin (id)",
    "price_usd": "Price (USD)",
    "volume_24h_usd": "24h Volume (USD)",
    "last_updated_at": "last_updated_unix"
}, inplace=True)

# Convert last_updated_unix to a readable IST string for display (Asia/Kolkata = UTC+5:30)
def unix_to_ist_str(ts):
    if not ts:
        return "N/A"
    # ts is seconds since epoch (UTC)
    dt_utc = datetime.utcfromtimestamp(ts)
    dt_ist = dt_utc + timedelta(hours=5, minutes=30)
    return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")

display_df["Last Updated (IST)"] = display_df["last_updated_unix"].apply(unix_to_ist_str)

# Drop the raw unix column for neat display
display_df = display_df.drop(columns=["last_updated_unix"])

# Save table to CSV
display_df.to_csv("crypto_summary.csv", index=False)
print("Saved summary table to crypto_summary.csv")
print(display_df.to_string(index=False))

# ========== Task 3: SOL 7-day line chart (historical API) ==========
# Use /coins/{id}/market_chart endpoint to get price history for last 7 days
coin_for_chart = "solana"
market_chart_url = f"https://api.coingecko.com/api/v3/coins/{coin_for_chart}/market_chart"
params_chart = {"vs_currency": vs_currency, "days": 7}
r = requests.get(market_chart_url, params=params_chart)
r.raise_for_status()
chart_json = r.json()

# 'prices' is a list of [timestamp_ms, price]
prices = chart_json.get("prices", [])
if not prices:
    raise RuntimeError("No price data returned for SOL")

times = [datetime.utcfromtimestamp(p[0] / 1000.0) + timedelta(hours=5, minutes=30) for p in prices]  # IST conversion
values = [p[1] for p in prices]

# Determine last updated time: use the last_updated_at from the summary if present
sol_last_unix = next((row["last_updated_at"] for row in rows if row["coin"] == coin_for_chart), None)
if sol_last_unix:
    sol_last_str = unix_to_ist_str(sol_last_unix)
else:
    # fallback to last timestamp in chart
    sol_last_str = times[-1].strftime("%Y-%m-%d %H:%M:%S IST")

# Plot 7-day line chart for SOL
plt.figure(figsize=(10, 5))
plt.plot(times, values)  # matplotlib default colors (do not hardcode)
plt.title(f"Solana (SOL) — 7-day price (USD) — Last Updated: {sol_last_str}")
plt.xlabel("Date (IST)")
plt.ylabel("Price (USD)")
plt.gcf().autofmt_xdate()
plt.grid(True)
plt.tight_layout()
plt.savefig("sol_7day_line.png")
print("Saved SOL 7-day chart to sol_7day_line.png")
plt.show()

# ========== Bonus: bar chart comparing 24h volume of all 8 coins ==========
# Prepare numeric volume values (for plotting)
def to_numeric_vol(x):
    try:
        return float(x.replace("$", "").replace(",", ""))
    except Exception:
        return 0.0

plot_df = df[["coin", "volume_24h_usd", "change_24h_pct"]].copy()
plot_df["vol_numeric"] = plot_df["volume_24h_usd"].map(lambda s: to_numeric_vol(s) if isinstance(s, str) else (s or 0.0))

plt.figure(figsize=(10, 5))
plt.bar(plot_df["coin"], plot_df["vol_numeric"])
plt.title("24h Volume (USD) — comparison")
plt.ylabel("24h Volume (USD)")
plt.xlabel("Coin (id)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("24h_volume_comparison.png")
print("Saved 24h volume bar chart to 24h_volume_comparison.png")
plt.show()

# ========== Done ==========
print("\nAll done. Files created:")
print("- crypto_summary.csv")
print("- sol_7day_line.png")
print("- 24h_volume_comparison.png (bonus)")
