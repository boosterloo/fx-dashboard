import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import load_sp500_data, calculate_heikin_ashi
from datetime import datetime

# Laad data
st.title("📈 S&P 500 Dashboard")
df = load_sp500_data()
df.dropna(subset=["close"], inplace=True)
df = df.drop_duplicates(subset=["date"])
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")
df["delta"] = df["close"].diff()

# Datumselectie: slider en invoervelden naast elkaar
col1, col2 = st.columns([1, 1])
with col1:
    start_input = st.date_input("Startdatum", value=df["date"].min(), min_value=df["date"].min(), max_value=df["date"].max())
with col2:
    end_input = st.date_input("Einddatum", value=df["date"].max(), min_value=df["date"].min(), max_value=df["date"].max())

# Filter
filtered_df = df[(df["date"] >= pd.to_datetime(start_input)) & (df["date"] <= pd.to_datetime(end_input))]

# 1. Slotkoers + Delta
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df["date"], y=filtered_df["close"], name="Slotkoers", line=dict(color="blue")))
fig.add_trace(go.Bar(x=filtered_df["date"], y=filtered_df["delta"], name="Delta", 
                     marker_color=["green" if d > 0 else "red" for d in filtered_df["delta"]]))
fig.update_layout(title="S&P 500 Slotkoers + Dagelijkse Delta", xaxis_title="Datum", yaxis_title="Koers", height=400)
st.plotly_chart(fig, use_container_width=True)

# 2. Heikin Ashi + EMA's
ha_df = calculate_heikin_ashi(filtered_df)
ha_df["EMA_5"] = ha_df["close"].ewm(span=5).mean()
ha_df["EMA_21"] = ha_df["close"].ewm(span=21).mean()
ha_df["EMA_55"] = ha_df["close"].ewm(span=55).mean()

ha_fig = go.Figure()
ha_fig.add_trace(go.Candlestick(x=ha_df["date"], open=ha_df["ha_open"], high=ha_df["ha_high"],
                                low=ha_df["ha_low"], close=ha_df["ha_close"], name="Heikin Ashi"))
ha_fig.add_trace(go.Scatter(x=ha_df["date"], y=ha_df["EMA_5"], mode="lines", name="EMA 5"))
ha_fig.add_trace(go.Scatter(x=ha_df["date"], y=ha_df["EMA_21"], mode="lines", name="EMA 21"))
ha_fig.add_trace(go.Scatter(x=ha_df["date"], y=ha_df["EMA_55"], mode="lines", name="EMA 55"))
ha_fig.update_layout(title="Heikin Ashi + EMA", xaxis_title="Datum", yaxis_title="Koers", height=400)
st.plotly_chart(ha_fig, use_container_width=True)

# 3. Histogram van Delta
hist_fig = go.Figure()
hist_fig.add_trace(go.Histogram(x=filtered_df["delta"], marker_color="#66c2a5", name="Delta verdeling"))
hist_fig.update_layout(title="📊 Histogram van Dagelijkse Delta", xaxis_title="Delta", yaxis_title="Frequentie", height=300)
st.plotly_chart(hist_fig, use_container_width=True)
