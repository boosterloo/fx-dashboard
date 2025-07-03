import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
from utils import get_supabase_data  # als je die helper gebruikt

st.title("📈 S&P 500 Dashboard")

# == Ophalen data ==
df = get_supabase_data("sp500_data")

if df.empty:
    st.error("❌ Geen data gevonden")
    st.stop()

# == Zet datum om en sorteer ==
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# == Selecteer datumrange ==
min_date, max_date = df["date"].min(), df["date"].max()
daterange = st.date_input("Selecteer datumrange", [min_date, max_date], min_value=min_date, max_value=max_date)

# == Filter op datum ==
start_date, end_date = pd.to_datetime(daterange[0]), pd.to_datetime(daterange[1])
df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# == Bereken EMA op Close ==
df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()

# == Heikin-Ashi candlestick ==
required_columns = ["open", "high", "low", "close"]
if all(col in df.columns for col in required_columns):
    df_ha = df.copy()

    df_ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    df_ha["ha_open"] = df["open"]
    for i in range(1, len(df_ha)):
        df_ha.at[df_ha.index[i], "ha_open"] = (
            df_ha.at[df_ha.index[i - 1], "ha_open"] + df_ha.at[df_ha.index[i - 1], "ha_close"]
        ) / 2

    df_ha["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
    df_ha["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

    # === Plot Heikin-Ashi + EMA ===
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_ha["date"],
        open=df_ha["ha_open"],
        high=df_ha["ha_high"],
        low=df_ha["ha_low"],
        close=df_ha["ha_close"],
        name="Heikin-Ashi"
    ))
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["EMA_20"],
        mode="lines",
        line=dict(color="orange", width=1.5),
        name="EMA 20"
    ))
    fig.update_layout(title="📊 S&P 500 Heikin-Ashi + EMA", xaxis_title="Datum", yaxis_title="Prijs")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("❌ Vereiste kolommen ontbreken in dataset")

# == Plot Delta bar chart ==
st.subheader("📉 Dagelijkse Delta")
delta_chart = go.Figure()
delta_chart.add_trace(go.Bar(x=df["date"], y=df["delta"], name="Delta", marker_color="purple"))
delta_chart.update_layout(title="Dagelijkse Delta (Close - Open)", xaxis_title="Datum", yaxis_title="Delta")
st.plotly_chart(delta_chart, use_container_width=True)

# == Downloadoptie ==
st.download_button("⬇️ Download data als CSV", data=df.to_csv(index=False), file_name="sp500_data.csv")
