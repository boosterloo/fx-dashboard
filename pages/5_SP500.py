import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import get_supabase_data

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# 🔄 Data ophalen uit Supabase-view
with st.spinner("Ophalen van S&P 500 data..."):
    df = get_supabase_data("sp500_view")

# ✅ Optioneel: delta-kolom toevoegen (prijsverandering)
# df['delta'] = df['close'].diff()

# ✅ Controleer op lege data en vereiste kolommen
df = df.dropna(subset=['date', 'open', 'high', 'low', 'close', 'volume'])

if df.empty:
    st.error("Geen data opgehaald van Supabase. Controleer of de view goed is ingesteld en gevuld.")
    st.text("Kolommen beschikbaar:")
    st.write(df.columns.tolist())
    st.stop()

# 📅 Datumfilter toevoegen
unique_dates = sorted(df['date'].unique(), reverse=True)
default_start = unique_dates[min(30, len(unique_dates)-1)] if unique_dates else None
selected_dates = st.multiselect("Selecteer data", unique_dates, default=[default_start] if default_start else [])

if selected_dates:
    df = df[df['date'].isin(selected_dates)]

# 📊 Plotly-grafiek maken met OHLC data
ohlc_fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.01)
ohlc_fig.add_trace(go.Candlestick(
    x=df['date'],
    open=df['open'],
    high=df['high'],
    low=df['low'],
    close=df['close'],
    name="S&P 500"
))
ohlc_fig.update_layout(title="S&P 500 OHLC", xaxis_title="Datum", yaxis_title="Prijs", xaxis_rangeslider_visible=False)
st.plotly_chart(ohlc_fig, use_container_width=True)

# 📉 Volume grafiek
volume_fig = go.Figure()
volume_fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name="Volume"))
volume_fig.update_layout(title="S&P 500 Volume", xaxis_title="Datum", yaxis_title="Volume")
st.plotly_chart(volume_fig, use_container_width=True)
