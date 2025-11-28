import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
#import streamlit as st
data = pd.read_csv("crypto_prices1.csv")

data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)

print(data.head())
data['Return'] = data['Close'].pct_change()
daily_volatility = data['Return'].std()
print("Daily Volatility:", daily_volatility)
annual_volatility = daily_volatility * np.sqrt(252)
print("Annual Volatility:", annual_volatility)
confidence_level = 0.05   # 5% worst-case

VaR = data['Return'].quantile(confidence_level)
print("Value at Risk (5%):", VaR)
plt.figure(figsize=(12,6))
plt.plot(data.index, data['Close'], label='Close Price')
plt.title("Crypto Price Trend")
plt.xlabel("Date")
plt.ylabel("Price")
plt.legend()
plt.show()
plt.figure(figsize=(12,6))
sns.histplot(data['Return'].dropna(), bins=50, kde=True)
plt.title("Return Distribution")
plt.xlabel("Return")
#plt.ylabel("Frequency")
plt.show()
plt.figure(figsize=(12,6))
data['Cumulative'] = (1 + data['Return']).cumprod()
plt.plot(data.index, data['Cumulative'])
#data["Return"].dropna.cumsum().plot()
plt.title("Cumulative Return")
plt.xlabel("Date")
plt.ylabel("Cumulative Growth")
plt.show()
data.to_csv("crypto_analysis_output2.csv")