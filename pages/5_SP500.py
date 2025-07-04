import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")

# Supabase connectie
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Gegevens ophalen
@st.cache_data
def load_data():
    response = supabase.table("sp500_data").select("*").execute()
    df = pd.DataFrame(response.data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values("date")
    df['delta'] = df['close'].diff()
    df['color'] = df['delta'].apply(lambda x: 'green' if x >= 0 else 'red')
    return df

df = load_data()

# Datumselectie
min_date = df["date"].min().date()
max_date = df["date"].max().date()

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.write("**Geselecteerd:**")
with col2:
    start_date_input = st.date_input("Startdatum", value=min_date)
with col3:
    end_date_input = st.date_input("Einddatum", value=max_date)

filtered_df = df[(df["date"] >= pd.to_datetime(start_date_input)) & (df["date"] <= pd.to_datetime(end_date_input))]

st.title("📈 S&P 500 Dashboard")

# Slotkoers + Delta
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df["date"], y=filtered_df["close"], mode="lines", name="Slotkoers", line=dict(color="blue")))
fig.add_trace(go.Bar(x=filtered_df["date"], y=filtered_df["delta"], name="Delta", marker_color=filtered_df['color']))
fig.update_layout(title="S&P 500 Slotkoers + Dagelijkse Delta", xaxis_title="Datum", yaxis_title="Slotkoers", barmode='overlay', height=500, width=1200)
st.plotly_chart(fig, use_container_width=True)

# Heikin Ashi + EMA's
def heikin_ashi(df):
    ha_df = pd.DataFrame()
    ha_df['date'] = df['date']
    ha_df['close_ha'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open_ha'] = 0.0
    ha_df['open_ha'].iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_df['open_ha'].iloc[i] = (ha_df['open_ha'].iloc[i - 1] + ha_df['close_ha'].iloc[i - 1]) / 2
    ha_df['high_ha'] = df[['high', 'open', 'close']].max(axis=1)
    ha_df['low_ha'] = df[['low', 'open', 'close']].min(axis=1)
    return ha_df

ha_df = heikin_ashi(filtered_df.copy())
ha_df['EMA_5'] = filtered_df['close'].ewm(span=5, adjust=False).mean()
ha_df['EMA_15'] = filtered_df['close'].ewm(span=15, adjust=False).mean()
ha_df['EMA_30'] = filtered_df['close'].ewm(span=30, adjust=False).mean()
ha_df = ha_df.dropna()

fig_ha = go.Figure()
fig_ha.add_trace(go.Candlestick(
    x=ha_df['date'],
    open=ha_df['open_ha'],
    high=ha_df['high_ha'],
    low=ha_df['low_ha'],
    close=ha_df['close_ha'],
    increasing_line_color='cyan',
    decreasing_line_color='red',
    name='Heikin Ashi'
))
fig_ha.add_trace(go.Scatter(x=ha_df['date'], y=ha_df['EMA_5'], line=dict(color='blue', width=1), name='EMA 5'))
fig_ha.add_trace(go.Scatter(x=ha_df['date'], y=ha_df['EMA_15'], line=dict(color='orange', width=1), name='EMA 15'))
fig_ha.add_trace(go.Scatter(x=ha_df['date'], y=ha_df['EMA_30'], line=dict(color='red', width=1), name='EMA 30'))
fig_ha.update_layout(title="Heikin Ashi + EMA", xaxis_title="Datum", yaxis_title="Prijs", xaxis_rangeslider_visible=False, height=500, width=1200)
st.plotly_chart(fig_ha, use_container_width=True)

# Histogram van delta
fig_hist = go.Figure(data=[go.Histogram(x=filtered_df['delta'], nbinsx=50, marker_color='skyblue')])
fig_hist.update_layout(title='Histogram van Dagelijkse Delta', xaxis_title='Delta', yaxis_title='Frequentie', height=400, width=1200)
st.plotly_chart(fig_hist, use_container_width=True)
