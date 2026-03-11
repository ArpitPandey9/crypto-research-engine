from src.data.fetch_prices import fetch_daily_prices

btc = fetch_daily_prices("bitcoin", days=30)
eth = fetch_daily_prices("ethereum", days=30)

print("BTC sample:\n", btc.head(), "\n")
print("ETH sample:\n", eth.head(), "\n")
print("BTC shape:", btc.shape)
print("ETH shape:", eth.shape)
print("BTC unique dates:", btc["date"].nunique())
print("ETH unique dates:", eth["date"].nunique())