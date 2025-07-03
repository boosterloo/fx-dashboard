import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client
import os
from datetime import datetime

# === Supabase-instellingen ===
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

def load_data():
    response = supabase.table("sp500_data").select("*").execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df

st.title("📈 S&P 500 Dashboard")

df = load_data()

# === Filter op datum ===
date_range = st.date_input("Selecteer datumrange", [df["date"].min(), df["date"].max()])
if isinstance(date_range, list) and len(date_range) == 2:
    df = df[(df["date"] >= pd.to_datetime(date_range[0])) & (df["date"] <= pd.to_datetime(date_range[1]))]

# === EMA toevoegen ===
df["EMA20"] = df["close"].ewm(span=20).mean()
df["EMA50"] = df["close"].ewm(span=50).mean()

# === Heikin-Ashi berekening ===
df_ha = df.copy()
df_ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
for i in range(1, len(df)):
    ha_open.append((ha_open[i-1] + df_ha["ha_close"].iloc[i-1]) / 2)
df_ha["ha_open"] = ha_open
df_ha["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
df_ha["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

# === Plot: Heikin-Ashi candles ===
fig = go.Figure(data=[
    go.Candlestick(
        x=df_ha["date"],
        open=df_ha["ha_open"],
        high=df_ha["ha_high"],
        low=df_ha["ha_low"],
        close=df_ha["ha_close"],
        name="Heikin-Ashi",
        increasing_line_color='green',
        decreasing_line_color='red',
        showlegend=True
    ),
    go.Scatter(
        x=df["date"],
        y=df["EMA20"],
        mode="lines",
        name="EMA20",
        line=dict(color="orange")
    ),
    go.Scatter(
        x=df["date"],
        y=df["EMA50"],
        mode="lines",
        name="EMA50",
        line=dict(color="blue")
    )
])

fig.update_layout(title="S&P 500 Heikin-Ashi + EMA", xaxis_title="Datum", yaxis_title="Prijs")
st.plotly_chart(fig, use_container_width=True)

# === Plot: Delta staafgrafiek ===
st.subheader("📉 Dagelijkse Delta")
delta_chart = go.Figure()
delta_chart.add_trace(go.Bar(x=df["date"], y=df["delta"], name="Delta", marker_color="purple"))
delta_chart.update_layout(title="Dagelijkse Delta (Close - Open)", xaxis_title="Datum", yaxis_title="Delta")
st.plotly_chart(delta_chart, use_container_width=True)

# === Download optie ===
st.download_button("📥 Download data als CSV", data=df.to_csv(index=False), file_name="sp500_data.csv")
