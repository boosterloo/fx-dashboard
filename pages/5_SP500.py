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

# Kolomcontrole
required_cols = {"date", "open", "high", "low", "close", "volume", "delta"}
if not required_cols.issubset(df.columns):
    st.error(f"Kolommen ontbreken: {required_cols - set(df.columns)}")
    st.write("Kolommen:", df.columns.tolist())
    st.stop()

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])

# === Datumfilter ===
date_min = df["date"].min()
date_max = df["date"].max()

start_date, end_date = st.date_input(
    "Selecteer datumrange",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
    format="YYYY-MM-DD"
)

mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
df_filtered = df.loc[mask].copy()

if df_filtered.empty:
    st.warning("Geen data binnen de geselecteerde periode.")
    st.stop()

# === Heikin-Ashi berekening ===
df_ha = df_filtered.copy()
df_ha["ha_close"] = (df_ha["open"] + df_ha["high"] + df_ha["low"] + df_ha["close"]) / 4
ha_open = [(df_ha["open"].iloc[0] + df_ha["close"].iloc[0]) / 2]
for i in range(1, len(df_ha)):
    ha_open.append((ha_open[i - 1] + df_ha["ha_close"].iloc[i - 1]) / 2)
df_ha["ha_open"] = ha_open
df_ha["ha_high"] = df_ha[["high", "ha_open", "ha_close"]].max(axis=1)
df_ha["ha_low"] = df_ha[["low", "ha_open", "ha_close"]].min(axis=1)

# === EMA & crossover berekening ===
df_ha["ema_20"] = df_ha["close"].ewm(span=20, adjust=False).mean()
df_ha["ema_50"] = df_ha["close"].ewm(span=50, adjust=False).mean()
df_ha["crossover"] = df_ha["ema_20"] - df_ha["ema_50"]

# Crossover-signalen
df_ha["signal"] = 0
df_ha.loc[df_ha["crossover"] > 0, "signal"] = 1  # bullish
df_ha.loc[df_ha["crossover"] < 0, "signal"] = -1  # bearish

df_ha["cross_up"] = (df_ha["signal"].diff() == 2)
df_ha["cross_down"] = (df_ha["signal"].diff() == -2)

# === Hoofdgrafiek met EMA's en crossovers ===
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df_ha["date"],
    open=df_ha["ha_open"],
    high=df_ha["ha_high"],
    low=df_ha["ha_low"],
    close=df_ha["ha_close"],
    name="Heikin-Ashi"
))

fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_20"], mode="lines", name="EMA 20"))
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_50"], mode="lines", name="EMA 50"))

# Crossover bolletjes
fig.add_trace(go.Scatter(
    x=df_ha[df_ha["cross_up"]]["date"],
    y=df_ha[df_ha["cross_up"]]["close"],
    mode="markers",
    marker=dict(color="green", size=10),
    name="Bullish Crossover"
))

fig.add_trace(go.Scatter(
    x=df_ha[df_ha["cross_down"]]["date"],
    y=df_ha[df_ha["cross_down"]]["close"],
    mode="markers",
    marker=dict(color="red", size=10),
    name="Bearish Crossover"
))

fig.update_layout(
    title="S&P 500 met Heikin-Ashi, EMA's & Crossovers",
    xaxis_title="Datum",
    yaxis_title="Prijs",
    xaxis_rangeslider_visible=False,
    height=700
)

st.plotly_chart(fig, use_container_width=True)

# === Volume-grafiek ===
st.subheader("📊 Volume")
fig_vol = go.Figure()
fig_vol.add_trace(go.Bar(x=df_ha["date"], y=df_ha["volume"], name="Volume"))
fig_vol.update_layout(xaxis_title="Datum", yaxis_title="Volume", height=300)
st.plotly_chart(fig_vol, use_container_width=True)

# === Delta-grafiek ===
st.subheader("📈 Delta (dagelijkse koersverandering)")
fig_delta = go.Figure()
fig_delta.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["delta"], mode="lines", name="Delta"))
fig_delta.update_layout(xaxis_title="Datum", yaxis_title="Δ Prijs", height=300)
st.plotly_chart(fig_delta, use_container_width=True)
