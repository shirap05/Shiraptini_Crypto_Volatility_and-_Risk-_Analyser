# -----------------------------------------
# Data Acquisition Module – Assignment
# Course: Crypto Volatility & Risk Analysis
# -----------------------------------------

# Task 2: Import Libraries
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# Task 3: Fetch Crypto Data
crypto_symbol = "BTC-USD"
start_date = "2025-01-01"
end_date = "2025-12-03"

# Download data
crypto_data = yf.download(crypto_symbol, start=start_date, end=end_date)

# Print first 5 rows
print("First 5 rows of the dataset:")
print(crypto_data.head())

# Task 4: Check & Handle Missing Values
print("\nMissing values before filling:")
print(crypto_data.isnull().sum())

# Fill missing values using forward fill
crypto_data.fillna(method='ffill', inplace=True)

print("\nMissing values after filling:")
print(crypto_data.isnull().sum())

# Task 5: Save Data
crypto_data.to_csv('crypto_data.csv')
print("\nData saved successfully to 'crypto_data.csv'.")

# Task 6: Visualization (Closing Price Trend)
plt.figure(figsize=(12,6))
plt.plot(crypto_data['Close'])
plt.title("Bitcoin Closing Price Trend (2025)")
plt.xlabel("Date")
plt.ylabel("Closing Price (USD)")
plt.grid(True)
plt.show()
