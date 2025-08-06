import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import get_supabase_data_in_chunks

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# 🔄 Data ophalen uit Supabase
with st.spinner("Ophalen van S&P 500 data..."):
    df = get_supabase_data_in_chunks("sp500_delta_view")

if df.empty:
    st.warning("⚠️ Geen data opgehaald van Supabase.")
    st.stop()

# 🔧 Conversies
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values("date")
else:
    st.warning("⚠️ Kolom 'date' ontbreekt in de data.")
    st.stop()

# 📆 Datumselectie
min_date, max_date = df['date'].min(), df['date'].max()
date_range = st.slider("Selecteer datumrange", min_value=min_date.to_pydatetime(), max_value=max_date.to_pydatetime(), value=(max_date.to_pydatetime() - pd.Timedelta(days=120), max_date.to_pydatetime()))
df_filtered = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])]

# 📈 Lijngrafiek met MA en staafdiagram delta
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['close'], mode='lines', name='Close'), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['close'].rolling(window=20).mean(), mode='lines', name='MA20'), row=1, col=1)
fig.add_trace(go.Bar(x=df_filtered['date'], y=df_filtered['daily_delta_abs'], name='Delta abs', marker_color=['green' if x >= 0 else 'red' for x in df_filtered['daily_delta_abs']]), row=2, col=1)

fig.update_layout(height=600, title_text="S&P 500 Closing Price met MA20 en Dagelijkse Verandering")
st.plotly_chart(fig, use_container_width=True)

# 📊 Histogrammen naast elkaar
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Histogram van Absolute Delta")
    st.plotly_chart(go.Figure(go.Histogram(x=df_filtered['daily_delta_abs'], nbinsx=30)).update_layout(title='Absolute Delta Histogram', xaxis_title='Absolute Delta', yaxis_title='Aantal'), use_container_width=True)
    st.markdown(f"**Mediaan:** {df_filtered['daily_delta_abs'].median():.2f}, **Gemiddelde:** {df_filtered['daily_delta_abs'].mean():.2f}")

with col2:
    st.subheader("📊 Histogram van Procentuele Delta")
    st.plotly_chart(go.Figure(go.Histogram(x=df_filtered['daily_delta_pct'], nbinsx=30)).update_layout(title='Procentuele Delta Histogram', xaxis_title='Procentuele Delta (%)', yaxis_title='Aantal'), use_container_width=True)
    st.markdown(f"**Mediaan:** {df_filtered['daily_delta_pct'].median():.2f}%, **Gemiddelde:** {df_filtered['daily_delta_pct'].mean():.2f}%")
