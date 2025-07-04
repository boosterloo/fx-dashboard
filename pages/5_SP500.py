import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from datetime import datetime
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

# 🥳 DataFrame voorbereiden
df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "open", "high", "low", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date

# 🗕️ Slider
min_date = df["date"].min()
max_date = df["date"].max()
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# ========== 📈 Deel 1: TA Grafieken ==========
st.subheader("📈 Technische Analyse: Heikin-Ashi & EMA's")

# Heikin-Ashi berekening
df_ha = df_filtered.copy()
df_ha["ha_close"] = (df_ha["open"] + df_ha["high"] + df_ha["low"] + df_ha["close"]) / 4
ha_open = [(df_ha["open"].iloc[0] + df_ha["close"].iloc[0]) / 2]
for i in range(1, len(df_ha)):
    ha_open.append((ha_open[i - 1] + df_ha["ha_close"].iloc[i - 1]) / 2)
df_ha["ha_open"] = ha_open
df_ha["ha_high"] = df_ha[["high", "ha_open", "ha_close"]].max(axis=1)
df_ha["ha_low"] = df_ha[["low", "ha_open", "ha_close"]].min(axis=1)

# EMA's toevoegen
df_ha["ema_8"] = df_ha["close"].ewm(span=8, adjust=False).mean()
df_ha["ema_21"] = df_ha["close"].ewm(span=21, adjust=False).mean()
df_ha["ema_55"] = df_ha["close"].ewm(span=55, adjust=False).mean()

# Heikin-Ashi grafiek
fig_ha = go.Figure()
fig_ha.add_trace(go.Candlestick(
    x=df_ha["date"],
    open=df_ha["ha_open"],
    high=df_ha["ha_high"],
    low=df_ha["ha_low"],
    close=df_ha["ha_close"],
    name="Heikin-Ashi",
    increasing_line_color="green",
    decreasing_line_color="red"
))
fig_ha.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_8"], name="EMA 8", line=dict(width=1.5)))
fig_ha.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_21"], name="EMA 21", line=dict(width=1.5)))
fig_ha.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_55"], name="EMA 55", line=dict(width=1.5)))
fig_ha.update_layout(
    title="Heikin-Ashi met EMA’s (8, 21, 55)",
    xaxis_title="Datum",
    yaxis_title="Prijs",
    xaxis_rangeslider_visible=False,
    height=600
)
st.plotly_chart(fig_ha, use_container_width=True)

# ========== 📉 Deel 2: Histogram van Delta ==========
st.subheader("📉 Histogram van dagelijkse delta’s")
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(
    x=df_filtered["delta"],
    nbinsx=40,
    marker_color="orange",
    name="Delta verdeling"
))
fig_hist.update_layout(
    xaxis_title="Delta",
    yaxis_title="Frequentie",
    bargap=0.1
)
st.plotly_chart(fig_hist, use_container_width=True)
