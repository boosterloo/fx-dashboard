import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
from utils import get_supabase_data

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# 🔄 Data ophalen
with st.spinner("Ophalen van S&P 500 data..."):
    df = get_supabase_data("sp500_view")

# 📅 Date opschonen en sorteren
df = df.dropna(subset=['date', 'close'])
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# 📊 Berekeningen
df['delta'] = df['close'].diff()
df['delta_pct'] = df['close'].pct_change() * 100

# 🟢 Kies MA-periode
ma_period = st.selectbox("Selecteer MA-periode", [5, 10, 20, 50, 100, 200], index=2)
df['ma'] = df['close'].rolling(window=ma_period).mean()

# 📅 Datum slider
min_date = df['date'].min().date()
max_date = df['date'].max().date()
start_date = max_date - timedelta(days=60)
date_range = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(start_date, max_date)
)

# 🔍 Filter data op geselecteerde range
df_filtered = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]

# 📈 Grafiek: Close + MA
fig_close = go.Figure()
fig_close.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['close'], mode='lines', name='Close'))
fig_close.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['ma'], mode='lines', name=f'MA {ma_period}'))
fig_close.update_layout(title="S&P 500 Close + MA", xaxis_title="Datum", yaxis_title="Prijs")
st.plotly_chart(fig_close, use_container_width=True)

# 📊 Histogram: Δ en Δ %
fig_delta = go.Figure()
fig_delta.add_trace(go.Bar(x=df_filtered['date'], y=df_filtered['delta'].abs(), name='Δ Absoluut'))
fig_delta.add_trace(go.Bar(x=df_filtered['date'], y=df_filtered['delta_pct'].abs(), name='Δ %'))
fig_delta.update_layout(
    title="Dagelijkse Verandering (Absoluut en %)",
    xaxis_title="Datum",
    yaxis_title="Verandering",
    barmode='group'
)
st.plotly_chart(fig_delta, use_container_width=True)
