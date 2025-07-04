import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import get_supabase_data

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
df = get_supabase_data("sp500_data")

# === Validatie & Cleanup ===
if df is None or not isinstance(df, pd.DataFrame) or df.empty:
    st.warning("Geen data beschikbaar.")
    st.stop()

# Zorg dat kolommen correct zijn
required_cols = {"date", "open", "high", "low", "close"}
if not required_cols.issubset(df.columns):
    st.error(f"Vereiste kolommen ontbreken in de data: {required_cols - set(df.columns)}")
    st.stop()

# Zet 'date' om naar datetime
df["date"] = pd.to_datetime(df["date"], errors='coerce')
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

# === EMA toevoegen ===
df_ha["ema_20"] = df_ha["close"].ewm(span=20, adjust=False).mean()
df_ha["ema_50"] = df_ha["close"].ewm(span=50, adjust=False).mean()

# === Plotten ===
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

fig.update_layout(
    title="S&P 500 met Heikin-Ashi Candles en EMA's",
    xaxis_title="Datum",
    yaxis_title="Prijs",
    xaxis_rangeslider_visible=False,
    height=600
)

st.plotly_chart(fig, use_container_width=True)
