import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Supabase credentials
load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

# Load data in batches
all_data = []
batch_size = 1000
offset = 0
while True:
    res = supabase.table('sp500_data').select('*').range(offset, offset + batch_size - 1).execute()
    batch = res.data
    if not batch:
        break
    all_data.extend(batch)
    offset += batch_size

# Prepare DataFrame
df = pd.DataFrame(all_data)
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date', 'open', 'high', 'low', 'close', 'delta'])
df = df.sort_values('date')
df['date'] = df['date'].dt.date

# Global date boundaries
min_date = df['date'].min()
max_date = df['date'].max()

# Calculate YTD and PYTD using full dataset
try:
    ytd_start = datetime(max_date.year, 1, 1).date()
    pytd_start = datetime(max_date.year - 1, 1, 1).date()
    ytd_data = df[df['date'] >= ytd_start]
    pytd_data = df[(df['date'] >= pytd_start) & (df['date'] < ytd_start)]
    ytd_abs = ytd_data['close'].iloc[-1] - ytd_data['close'].iloc[0]
    ytd_pct = (ytd_abs / ytd_data['close'].iloc[0]) * 100
    pytd_abs = pytd_data['close'].iloc[-1] - pytd_data['close'].iloc[0]
    pytd_pct = (pytd_abs / pytd_data['close'].iloc[0]) * 100
except Exception:
    ytd_abs = ytd_pct = pytd_abs = pytd_pct = None

# Date range filter
default_start = max_date - timedelta(days=365)
st.markdown('### Select date range')
start_date, end_date = st.slider(
    'Date range', min_value=min_date, max_value=max_date,
    value=(default_start, max_date), format='YYYY-MM-DD'
)
mask = (df['date'] >= start_date) & (df['date'] <= end_date)
df_filtered = df.loc[mask].copy()

# Display metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric('YTD #', f"{ytd_abs:.2f}" if ytd_abs is not None else '-')
col2.metric('YTD %', f"{ytd_pct:.2f}%" if ytd_pct is not None else '-')
col3.metric('PYTD #', f"{pytd_abs:.2f}" if pytd_abs is not None else '-')
col4.metric('PYTD %', f"{pytd_pct:.2f}%" if pytd_pct is not None else '-')

# Calculate technical indicators on filtered data
df_filtered['ema8'] = df_filtered['close'].ewm(span=8, adjust=False).mean()
df_filtered['ema21'] = df_filtered['close'].ewm(span=21, adjust=False).mean()
df_filtered['ema55'] = df_filtered['close'].ewm(span=55, adjust=False).mean()
# Moving averages
df_filtered['ma50'] = df_filtered['close'].rolling(window=50).mean()
df_filtered['ma200'] = df_filtered['close'].rolling(window=200).mean()
# Bollinger Bands
bband_mid = df_filtered['close'].rolling(window=20).mean()
bband_std = df_filtered['close'].rolling(window=20).std()
df_filtered['bb_upper'] = bband_mid + 2 * bband_std
df_filtered['bb_mid'] = bband_mid
df_filtered['bb_lower'] = bband_mid - 2 * bband_std
# RSI
delta = df_filtered['close'].diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
df_filtered['rsi'] = 100 - (100 / (1 + rs))
# ATR
df_filtered['atr'] = (df_filtered['high'] - df_filtered['low']).rolling(window=14).mean()
# MACD
df_filtered['macd'] = df_filtered['close'].ewm(span=12, adjust=False).mean() - df_filtered['close'].ewm(span=26, adjust=False).mean()
df_filtered['macd_sig'] = df_filtered['macd'].ewm(span=9, adjust=False).mean()

# Plot Technical Analysis
st.subheader('📈 Technical Analysis')
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.7, 0.3], vertical_spacing=0.05)
fig.add_trace(
    go.Candlestick(
        x=df_filtered['date'], open=df_filtered['open'],
        high=df_filtered['high'], low=df_filtered['low'],
        close=df_filtered['close'], name='Price'
    ), row=1, col=1
)
# Plot indicators
for name, series in {
    'EMA8': 'ema8', 'EMA21': 'ema21', 'EMA55': 'ema55',
    'MA50': 'ma50', 'MA200': 'ma200',
    'BB Upper': 'bb_upper', 'BB Mid': 'bb_mid', 'BB Lower': 'bb_lower'
}.items():
    fig.add_trace(
        go.Scatter(
            x=df_filtered['date'], y=df_filtered[series],
            name=name,
            line=dict(dash='dash' if 'MA' in name else 'solid')
        ),
        row=1, col=1
    )
# RSI subplot
fig.add_trace(
    go.Scatter(x=df_filtered['date'], y=df_filtered['rsi'], name='RSI', line=dict(color='purple')),
    row=2, col=1
)
fig.update_yaxes(title_text='RSI', row=2, col=1, range=[0, 100])
fig.update_layout(
    height=800,
    xaxis_rangeslider_visible=False,
    legend=dict(x=1, y=0, xanchor='right', yanchor='bottom')
)
st.plotly_chart(fig, use_container_width=True)

# Plot histograms
st.subheader('📉 Histogram of Daily Delta')
col_a, col_b = st.columns(2)
with col_a:
    fig1 = go.Figure(go.Histogram(x=df_filtered['delta'], nbinsx=40))
    fig1.update_layout(xaxis_title='Delta', yaxis_title='Frequency', bargap=0.1)
    st.plotly_chart(fig1, use_container_width=True)
with col_b:
    df_filtered['delta_pct'] = df_filtered['close'].pct_change() * 100
    fig2 = go.Figure(go.Histogram(x=df_filtered['delta_pct'], nbinsx=40))
    fig2.update_layout(xaxis_title='Delta %', yaxis_title='Frequency', bargap=0.1)
    st.plotly_chart(fig2, use_container_width=True)

# Display statistics
st.subheader('📊 Statistics')
avg = df_filtered['delta'].mean()
std = df_filtered['delta'].std()
pos = (df_filtered['delta'] > 0).sum()
neg = (df_filtered['delta'] < 0).sum()
col_x, col_y, col_z = st.columns(3)
col_x.metric('Avg Delta', f"{avg:.4f}")
col_y.metric('Std Delta', f"{std:.4f}")
col_z.metric('+/- Days', f"{pos}/{neg}")

fig3 = go.Figure(go.Scatter(
    x=df_filtered['date'], y=df_filtered['delta'].rolling(window=14).std(),
    mode='lines', name='Rolling Volatility (14d)'
))
fig3.update_layout(title='Rolling Volatility (14d)', xaxis_title='Date', yaxis_title='Volatility')
st.plotly_chart(fig3, use_container_width=True)
