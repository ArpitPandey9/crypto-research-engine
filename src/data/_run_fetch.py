from src.data.fetch_prices import fetch_btc_prices
df = fetch_btc_prices(days=30)
print(df.head())
print(df.tail())
print(df.shape)