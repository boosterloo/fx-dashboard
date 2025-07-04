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

# 📅 Datumselectie: slider én invoer
min_date = df["date"].min()
max_date = df["date"].max()
st.markdown("### 📅 Selecteer datumrange")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Startdatum", min_value=min_date, max_value=max_date, value=min_date)
with col2:
    end_date = st.date_input("Einddatum", min_value=min_date, max_value=max_date, value=max_date)

st.slider("📆 Datumrange (extra zoomoptie)", min_value=min_date, max_value=max_date,
          value=(start_date, end_date), format="YYYY-MM-DD")

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# ========== 📈 Deel 1: TA Grafieken ==========
st.subheader("📈 Technische Analyse: Heikin-Ashi, EMA's & RSI")

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

# RSI berekening
delta = df_ha["close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df_ha["rsi"] = 100 - (100 / (1 + rs))

# Subplots: Heikin-Ashi en RSI
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.7, 0.3], vertical_spacing=0.05,
                    subplot_titles=("Heikin-Ashi met EMA’s", "RSI (14-dagen)"))

fig.add_trace(go.Candlestick(
    x=df_ha["date"],
    open=df_ha["ha_open"],
    high=df_ha["ha_high"],
    low=df_ha["ha_low"],
    close=df_ha["ha_close"],
    name="Heikin-Ashi",
    increasing_line_color="green",
    decreasing_line_color="red"
), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_8"], name="EMA 8", line=dict(width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_21"], name="EMA 21", line=dict(width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_55"], name="EMA 55", line=dict(width=1.5)), row=1, col=1)

fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["rsi"], name="RSI", line=dict(color="purple", width=2)), row=2, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_layout(height=800, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

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

# ========== 📈 Deel 3: Statistieken ==========
st.subheader("📊 Statistieken van Delta")
avg_delta = df_filtered["delta"].mean()
std_delta = df_filtered["delta"].std()
positive_days = (df_filtered["delta"] > 0).sum()
negative_days = (df_filtered["delta"] < 0).sum()
rolling_volatility = df_filtered["delta"].rolling(window=14).std()

col1, col2, col3 = st.columns(3)
col1.metric("Gemiddelde Delta", f"{avg_delta:.4f}")
col2.metric("Standaarddeviatie Delta", f"{std_delta:.4f}")
col3.metric("+ / - Dagen", f"{positive_days} / {negative_days}")

fig_vol = go.Figure()
fig_vol.add_trace(go.Scatter(x=df_filtered["date"], y=rolling_volatility, mode="lines", name="Rolling Volatility (14d)", line=dict(color="gray")))
fig_vol.update_layout(title="📉 Rolling Volatility (14-daags)", xaxis_title="Datum", yaxis_title="Volatiliteit")
st.plotly_chart(fig_vol, use_container_width=True)
