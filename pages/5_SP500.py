import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# === 1. Setup en Supabase connectie ===
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# === 2. Data ophalen in chunks ===
data = []
batch_size = 1000
offset = 0
while True:
    response = (
        supabase.table("sp500_data")
        .select("*")
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    batch = response.data
    if not batch:
        break
    data.extend(batch)
    offset += batch_size

# === 3. Data voorbereiden ===
df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "close", "delta"])
df = df.sort_values("date")

# EMA's berekenen
df["ema_8"] = df["close"].ewm(span=8, adjust=False).mean()
df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
df["ema_55"] = df["close"].ewm(span=55, adjust=False).mean()

# Heikin-Ashi berekening
df["open"] = df["close"] - 1.0  # ruwe benadering voor voorbeeld
df["high"] = df[["open", "close"]].max(axis=1) + 0.5
df["low"] = df[["open", "close"]].min(axis=1) - 0.5
df["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
for i in range(1, len(df)):
    ha_open.append((ha_open[i - 1] + df["ha_close"].iloc[i - 1]) / 2)
df["ha_open"] = ha_open
df["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
df["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

# === 4. Streamlit layout en filters ===
st.set_page_config(layout="wide")
st.title("\U0001F4C8 S&P 500 Dashboard")

min_date = df["date"].min().date()
max_date = df["date"].max().date()

col1, col2 = st.columns([3, 1])
with col1:
    start_date, end_date = st.slider("Selecteer datumrange", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="YYYY-MM-DD")
with col2:
    st.write(":calendar: Geselecteerd: ")
    st.date_input("Startdatum", value=start_date, key="start_manual")
    st.date_input("Einddatum", value=end_date, key="end_manual")

# Filteren op datum
df_filtered = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

# === 5. Slotkoers en delta grafiek ===
colors = ["green" if d > 0 else "red" for d in df_filtered["delta"]]
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["close"], mode="lines", name="Slotkoers", line=dict(color="blue")))
fig1.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["delta"], marker_color=colors, name="Delta", yaxis="y2", opacity=0.4))
fig1.update_layout(
    title="S&P 500 Slotkoers + Dagelijkse Delta",
    xaxis_title="Datum",
    yaxis=dict(title="Slotkoers", side="left"),
    yaxis2=dict(title="Delta", overlaying="y", side="right", showgrid=False),
    height=500
)
st.plotly_chart(fig1, use_container_width=True)

# === 6. Heikin-Ashi + EMA grafiek ===
fig2 = go.Figure()
fig2.add_trace(go.Candlestick(x=df_filtered["date"], open=df_filtered["ha_open"], high=df_filtered["ha_high"], low=df_filtered["ha_low"], close=df_filtered["ha_close"], name="Heikin-Ashi"))
fig2.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_8"], mode="lines", name="EMA 8"))
fig2.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_21"], mode="lines", name="EMA 21"))
fig2.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_55"], mode="lines", name="EMA 55"))
fig2.update_layout(title="Heikin-Ashi Candles + EMA's", xaxis_title="Datum", yaxis_title="Prijs", height=500)
st.plotly_chart(fig2, use_container_width=True)

# === 7. Histogram van delta ===
fig3 = go.Figure()
fig3.add_trace(go.Histogram(x=df_filtered["delta"], nbinsx=50, marker_color="skyblue"))
fig3.update_layout(title="Histogram van Dagelijkse Delta", xaxis_title="Delta", yaxis_title="Frequentie", height=400)
st.plotly_chart(fig3, use_container_width=True)
