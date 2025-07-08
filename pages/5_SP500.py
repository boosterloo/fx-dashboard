import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

🔐 Supabase credentials

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

🔄 Data ophalen in chunks

all_data = []
batch_size = 1000
offset = 0
while True:
response = (
supabase.table("sp500_data")
.select("*")
.range(offset, offset + batch_size - 1)
.execute()
)
data = response.data
if not data:
break
all_data.extend(data)
offset += batch_size

🎉 DataFrame voorbereiden

df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "open", "high", "low", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date

⌚️ Datumselectie

min_date = df["date"].min()
max_date = df["date"].max()
default_start = max_date - timedelta(days=90)

st.markdown("### 🗓️ Selecteer datumrange")
date_range = st.slider("Kies datumrange", min_value=min_date, max_value=max_date,
value=(default_start, max_date), format="YYYY-MM-DD")
start_date, end_date = date_range

🔄 Data filteren

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()

📊 Indicatoren berekenen

df_filtered["ema_8"] = df_filtered["close"].ewm(span=8, adjust=False).mean()
df_filtered["ema_21"] = df_filtered["close"].ewm(span=21, adjust=False).mean()
df_filtered["ma_50"] = df_filtered["close"].rolling(window=50).mean()
df_filtered["ma_200"] = df_filtered["close"].rolling(window=200).mean()
df_filtered["boll_mid"] = df_filtered["close"].rolling(window=20).mean()
df_filtered["boll_std"] = df_filtered["close"].rolling(window=20).std()
df_filtered["boll_upper"] = df_filtered["boll_mid"] + 2 * df_filtered["boll_std"]
df_filtered["boll_lower"] = df_filtered["boll_mid"] - 2 * df_filtered["boll_std"]
df_filtered["rsi"] = 100 - (100 / (1 + df_filtered["close"].diff().clip(lower=0).rolling(14).mean() /
-df_filtered["close"].diff().clip(upper=0).rolling(14).mean()))
df_filtered["atr"] = (df_filtered["high"] - df_filtered["low"]).rolling(14).mean()
df_filtered["macd"] = df_filtered["close"].ewm(span=12).mean() - df_filtered["close"].ewm(span=26).mean()
df_filtered["macd_signal"] = df_filtered["macd"].ewm(span=9).mean()

📣 Strategie Alerts

alerts = []
if df_filtered["rsi"].iloc[-1] > 70:
alerts.append("⚠️ RSI boven 70: mogelijk overbought!")
elif df_filtered["rsi"].iloc[-1] < 30:
alerts.append("⚠️ RSI onder 30: mogelijk oversold!")
if (df_filtered["ema_8"].iloc[-1] > df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] <= df_filtered["ema_21"].iloc[-2]):
alerts.append("✅ EMA8 kruist boven EMA21: bullish signaal")
elif (df_filtered["ema_8"].iloc[-1] < df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] >= df_filtered["ema_21"].iloc[-2]):
alerts.append("🔻 EMA8 kruist onder EMA21: bearish signaal")
if df_filtered["close"].iloc[-1] > df_filtered["boll_upper"].iloc[-1]:
alerts.append("📈 Koers boven Bollinger-band")
elif df_filtered["close"].iloc[-1] < df_filtered["boll_lower"].iloc[-1]:
alerts.append("📉 Koers onder Bollinger-band")
if (df_filtered["ma_50"].iloc[-1] > df_filtered["ma_200"].iloc[-1]) and (df_filtered["ma_50"].iloc[-2] <= df_filtered["ma_200"].iloc[-2]):
alerts.append("✅ Golden Cross: MA50 boven MA200")
elif (df_filtered["ma_50"].iloc[-1] < df_filtered["ma_200"].iloc[-1]) and (df_filtered["ma_50"].iloc[-2] >= df_filtered["ma_200"].iloc[-2]):
alerts.append("🔻 Death Cross: MA50 onder MA200")
if df_filtered["atr"].iloc[-1] > 1.5 * df_filtered["atr"].mean():
alerts.append("⚠️ Hoge ATR: verhoogde volatiliteit")
if (df_filtered["macd"].iloc[-1] > df_filtered["macd_signal"].iloc[-1]) and (df_filtered["macd"].iloc[-2] <= df_filtered["macd_signal"].iloc[-2]):
alerts.append("✅ MACD bullish crossover")
elif (df_filtered["macd"].iloc[-1] < df_filtered["macd_signal"].iloc[-1]) and (df_filtered["macd"].iloc[-2] >= df_filtered["macd_signal"].iloc[-2]):
alerts.append("🔻 MACD bearish crossover")

if alerts:
st.subheader("📣 Strategie Alerts")
for msg in alerts:
st.info(msg)

📈 Backtest van RSI, EMA, MACD en ATR strategieën

df_bt = df_filtered.copy()

RSI Strategie

df_bt["pos_rsi"] = 0
df_bt.loc[df_bt["rsi"] < 30, "pos_rsi"] = 1
df_bt.loc[df_bt["rsi"] > 70, "pos_rsi"] = 0
df_bt["pos_rsi"] = df_bt["pos_rsi"].ffill()
df_bt["ret_rsi"] = df_bt["pos_rsi"] * df_bt["close"].pct_change()
df_bt["cum_rsi"] = (1 + df_bt["ret_rsi"]).cumprod()

EMA Strategie

df_bt["pos_ema"] = 0
df_bt.loc[df_bt["ema_8"] > df_bt["ema_21"], "pos_ema"] = 1
df_bt["ret_ema"] = df_bt["pos_ema"] * df_bt["close"].pct_change()
df_bt["cum_ema"] = (1 + df_bt["ret_ema"]).cumprod()

MACD Strategie

df_bt["pos_macd"] = 0
df_bt.loc[df_bt["macd"] > df_bt["macd_signal"], "pos_macd"] = 1
df_bt["ret_macd"] = df_bt["pos_macd"] * df_bt["close"].pct_change()
df_bt["cum_macd"] = (1 + df_bt["ret_macd"]).cumprod()

ATR Strategie (trendvolgend: koop als close > MA50 en ATR stijgt)

df_bt["pos_atr"] = 0
atr_slope = df_bt["atr"].diff()
df_bt.loc[(df_bt["close"] > df_bt["ma_50"]) & (atr_slope > 0), "pos_atr"] = 1
df_bt["ret_atr"] = df_bt["pos_atr"] * df_bt["close"].pct_change()
df_bt["cum_atr"] = (1 + df_bt["ret_atr"]).cumprod()

📊 Visualisatie Strategieën

st.subheader("📈 Strategie Backtests")
fig_bt = go.Figure()
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_rsi"], name="RSI"))
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_ema"], name="EMA"))
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_macd"], name="MACD"))
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_atr"], name="ATR"))
fig_bt.update_layout(title="Cumulatieve Performance", xaxis_title="Datum", yaxis_title="Groei")
st.plotly_chart(fig_bt, use_container_width=True)

📋 Statistieken

st.subheader("📊 Strategie Statistieken")
def strategy_stats(series, naam):
total = series.iloc[-1] - 1
vol = series.pct_change().std() * (252 ** 0.5)
sharpe = total / vol if vol != 0 else 0
return [naam, f"{total:.2%}", f"{vol:.2%}", f"{sharpe:.2f}"]

data_stats = [
strategy_stats(df_bt["cum_rsi"], "RSI"),
strategy_stats(df_bt["cum_ema"], "EMA"),
strategy_stats(df_bt["cum_macd"], "MACD"),
strategy_stats(df_bt["cum_atr"], "ATR")
]
st.table(pd.DataFrame(data_stats, columns=["Strategie", "Totale Return", "Volatiliteit", "Sharpe Ratio"]))

