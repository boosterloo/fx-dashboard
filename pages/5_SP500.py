import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import get_supabase_data

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
df = get_supabase_data("sp500_data")

if isinstance(df, list):
    df = pd.DataFrame(df)

if df is None or df.empty:
    st.warning("Geen data beschikbaar uit Supabase.")
    st.stop()

# Kolomcheck
required = {"date", "open", "high", "low", "close", "volume", "delta"}
if not required.issubset(df.columns):
    st.error(f"Ontbrekende kolommen: {required - set(df.columns)}")
    st.stop()

# Format & sortering
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

# EMA & signalen
df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
df["crossover"] = df["ema_20"] - df["ema_50"]
df["signal"] = 0
df.loc[df["crossover"] > 0, "signal"] = 1
df.loc[df["crossover"] < 0, "signal"] = -1
df["cross_up"] = df["signal"].diff() == 2
df["cross_down"] = df["signal"].diff() == -2

# === Datumschuif op echte datums ===
min_date = df["date"].min()
max_date = df["date"].max()

default_start = max_date - pd.DateOffset(years=3)
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(default_start, max_date),
    format="YYYY-MM-DD"
)

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()
if df_filtered.empty:
    st.warning("Geen data in geselecteerde periode.")
    st.stop()

# === Candlestick chart met EMA's en crossovers ===
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df_filtered["date"],
    open=df_filtered["open"],
    high=df_filtered["high"],
    low=df_filtered["low"],
    close=df_filtered["close"],
    name="OHLC",
))

fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_20"], mode="lines", name="EMA 20"))
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_50"], mode="lines", name="EMA 50"))

fig.add_trace(go.Scatter(
    x=df_filtered[df_filtered["cross_up"]]["date"],
    y=df_filtered[df_filtered["cross_up"]]["close"],
    mode="markers",
    marker=dict(color="green", size=10),
    name="Bullish crossover"
))
fig.add_trace(go.Scatter(
    x=df_filtered[df_filtered["cross_down"]]["date"],
    y=df_filtered[df_filtered["cross_down"]]["close"],
    mode="markers",
    marker=dict(color="red", size=10),
    name="Bearish crossover"
))

fig.update_layout(
    title="S&P 500 met EMA's en Crossovers",
    xaxis_title="Datum",
    yaxis_title="Prijs",
    xaxis_rangeslider_visible=False,
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# === Volume grafiek ===
st.subheader("📊 Volume")
fig_vol = go.Figure()
fig_vol.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["volume"].clip(upper=5e9), name="Volume"))
fig_vol.update_layout(xaxis_title="Datum", yaxis_title="Volume", height=250)
st.plotly_chart(fig_vol, use_container_width=True)

# === Delta grafiek ===
st.subheader("📈 Delta (dagelijkse koersverandering)")
fig_delta = go.Figure()
fig_delta.add_trace(go.Scatter(
    x=df_filtered["date"],
    y=df_filtered["delta"].clip(upper=50, lower=-50),
    mode="lines",
    name="Delta"
))
fig_delta.update_layout(xaxis_title="Datum", yaxis_title="Δ Prijs", height=250)
st.plotly_chart(fig_delta, use_container_width=True)
