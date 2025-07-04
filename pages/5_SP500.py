import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import timedelta

# Simuleer voorbeeld SP500-data met delta's
np.random.seed(42)
dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
prices = np.cumsum(np.random.normal(0, 1, len(dates))) + 4000
deltas = np.diff(prices, prepend=prices[0])
df = pd.DataFrame({"date": dates, "close": prices, "delta": deltas})

# Bereken enkele EMA's
df["ema_8"] = df["close"].ewm(span=8, adjust=False).mean()
df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
df["ema_55"] = df["close"].ewm(span=55, adjust=False).mean()

# Simuleer Heikin-Ashi
df["open"] = df["close"] - np.random.uniform(0.5, 2.0, len(df))
df["high"] = df[["open", "close"]].max(axis=1) + np.random.uniform(0, 1, len(df))
df["low"] = df[["open", "close"]].min(axis=1) - np.random.uniform(0, 1, len(df))
df["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
for i in range(1, len(df)):
    ha_open.append((ha_open[i - 1] + df["ha_close"].iloc[i - 1]) / 2)
df["ha_open"] = ha_open
df["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
df["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

# Toon voorbeeld-dataframe
import ace_tools as tools; tools.display_dataframe_to_user(name="Voorbeeld SP500 Data", dataframe=df)

