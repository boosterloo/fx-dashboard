# pages/5_SP500.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils import get_supabase_data

st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
data = get_supabase_data("sp500_data")
df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# === Datumfilter UI ===
min_datum = df["date"].min().date()
max_datum = df["date"].max().date()
daterange = st.date_input("Selecteer datumrange", [min_datum, max_datum], min_value=min_datum, max_value=max_datum)

df = df[(df["date"].dt.date >= daterange[0]) & (df["date"].dt.date <= daterange[1])]

# === Heikin-Ashi berekening ===
df_ha = df.copy()
df_ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
df_ha["ha_open"] = df_ha["ha_close"].shift(1)
df_ha["ha_open"].iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
df_ha["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
df_ha["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

# === EMA ===
df_ha["ema20"] = df_ha["ha_close"].ewm(span=20).mean()
df_ha["ema50"] = df_ha["ha_close"].ewm(span=50).mean()

# === Plot Heikin-Ashi met EMA ===
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df_ha["date"],
    open=df_ha["ha_open"],
    high=df_ha["ha_high"],
    low=df_ha["ha_low"],
    close=df_ha["ha_close"],
    name="Heikin-Ashi"
))
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema20"], mode="lines", name="EMA20"))
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema50"], mode="lines", name="EMA50"))

fig.update_layout(
    title="📉 S&P 500 Heikin-Ashi + EMA",
    xaxis_title="Datum",
    yaxis_title="Prijs"
)
st.plotly_chart(fig, use_container_width=True)

# === Delta plot ===
st.subheader("📊 Dagelijkse Delta")
delta_chart = go.Figure()
delta_chart.add_trace(go.Bar(x=df["date"], y=df["delta"], name="Delta", marker_color="purple"))
delta_chart.update_layout(title="Dagelijkse Delta (Close - Open)", xaxis_title="Datum", yaxis_title="Delta")
st.plotly_chart(delta_chart, use_container_width=True)

# === Downloadknop ===
st.download_button("⬇️ Download data als CSV", data=df.to_csv(index=False), file_name="sp500_data.csv")
