import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 🔐 Supabase credentials
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 🔄 Data ophalen in chunks
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

# 🎉 DataFrame voorbereiden
df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "open", "high", "low", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date

# ⌚️ Datumselectie
min_date = df["date"].min()
max_date = df["date"].max()
default_start = max_date - timedelta(days=90)

st.markdown("### 🗓️ Selecteer datumrange")
date_range = st.slider("Kies datumrange", min_value=min_date, max_value=max_date,
                       value=(default_start, max_date), format="YYYY-MM-DD")
start_date, end_date = date_range

# 🔄 Data filteren
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()

# Indicatorberekening voor strategie-alerts en backtest
df_filtered["ema_8"] = df_filtered["close"].ewm(span=8, adjust=False).mean()
df_filtered["ema_21"] = df_filtered["close"].ewm(span=21, adjust=False).mean()
df_filtered["rsi"] = 100 - (100 / (1 + (df_filtered["close"].diff().clip(lower=0).rolling(14).mean() /
                                        -df_filtered["close"].diff().clip(upper=0).rolling(14).mean())))

# 📊 YTD en PYTD berekening op basis van volledige data
try:
    ytd_start = datetime(max_date.year, 1, 1).date()
    pytd_start = datetime(max_date.year - 1, 1, 1).date()
    ytd_data = df[df["date"] >= ytd_start]
    pytd_data = df[(df["date"] >= pytd_start) & (df["date"] < ytd_start)]

    ytd_return_abs = ytd_data["close"].iloc[-1] - ytd_data["close"].iloc[0]
    ytd_return_pct = (ytd_return_abs / ytd_data["close"].iloc[0]) * 100
    pytd_return_abs = pytd_data["close"].iloc[-1] - pytd_data["close"].iloc[0]
    pytd_return_pct = (pytd_return_abs / pytd_data["close"].iloc[0]) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("YTD #", f"{ytd_return_abs:.2f}")
    col2.metric("YTD %", f"{ytd_return_pct:.2f}%")
    col3.metric("PYTD #", f"{pytd_return_abs:.2f}")
    col4.metric("PYTD %", f"{pytd_return_pct:.2f}%")
except:
    st.warning("Niet genoeg data beschikbaar voor YTD/PYTD berekening.")

# 🔔 Strategie-alerts
alerts = []
if df_filtered["rsi"].iloc[-1] > 70:
    alerts.append("⚠️ RSI boven 70: mogelijk overbought!")
elif df_filtered["rsi"].iloc[-1] < 30:
    alerts.append("⚠️ RSI onder 30: mogelijk oversold!")

if (df_filtered["ema_8"].iloc[-1] > df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] <= df_filtered["ema_21"].iloc[-2]):
    alerts.append("✅ EMA8 kruist boven EMA21: bullish signaal")
elif (df_filtered["ema_8"].iloc[-1] < df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] >= df_filtered["ema_21"].iloc[-2]):
    alerts.append("🔻 EMA8 kruist onder EMA21: bearish signaal")

if alerts:
    st.subheader("📣 Strategie Alerts")
    for msg in alerts:
        st.info(msg)

# ✅ Export-optie
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download gefilterde data (CSV)", csv, "sp500_filtered.csv", "text/csv")

# 📈 Backtest en strategie-analyse
st.markdown("---")
st.header("🧪 Backtest & Strategie Analyse")

# Simpele voorbeeldstrategie: koop bij RSI < 30, verkoop bij RSI > 70
df_bt = df_filtered.copy()
df_bt["position"] = 0
df_bt.loc[df_bt["rsi"] < 30, "position"] = 1
df_bt.loc[df_bt["rsi"] > 70, "position"] = 0
df_bt["position"] = df_bt["position"].ffill()
df_bt["strategy_return"] = df_bt["position"] * df_bt["close"].pct_change()
df_bt["cumulative"] = (1 + df_bt["strategy_return"]).cumprod()

fig_bt = go.Figure()
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cumulative"], mode="lines", name="Strategie rendement"))
fig_bt.update_layout(title="Strategie cumulatief rendement (RSI-based)", xaxis_title="Datum", yaxis_title="Groei", width=1200)
st.plotly_chart(fig_bt, use_container_width=False)
