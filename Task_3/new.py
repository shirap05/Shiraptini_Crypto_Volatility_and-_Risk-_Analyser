# task 1: Install Required Libraries
#pip install yfinance pandas matplotlib
#Task 2: Import Libraries
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
#Task 3: Fetch Crypto Data
#Fetch Bitcoin data from 1.Jan 2025-to December a 2025, and print the first 5 rows of the dataset.
crypto_symbol = "BTC-USD"
start_date = "2025-01-01"
end_date = "2025-12-03"
crypto_data = yf.download(crypto_symbol, start=start_date, end=end_date)
crypto_data.head()
#Task 4: Check & Handle Missing Values
#Check for misaing values in the dataset. Fill them (sing frit
print(crypto_data.isnull().sum())
crypto_data.fillna(method ="ffill", inplace=True)
#Task 5: Save Data
crypto_data.to_csv("crypto_data.csv")
print("Data saved successfully!")
#Task 6: Visualize Data
#Plot the closing price of Bitcoin over time.
plt.figure(figsize=(12, 6))     
plt.plot(crypto_data['Close'])
plt.title('Bitcoin Closing Price in 2025')
plt.xlabel('Date')
plt.ylabel('Closing Price (USD)')
plt.grid(True)
plt.show()
