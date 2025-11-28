import yfinance as yf


btc= yf.Ticker("BTC-USD")
data = btc.history(period="1mo")    
print(data.head())

data.to_csv("crypto_prices1.csv",index=True)
print("CSV created successfully: crypto_prices1.csv")