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
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Load data in batches
all_data = []
batch_size = 1000
offset = 0
while True:
    res = supabase.table("sp500_data").select("*").range(offset, offset + batch_size - 1).execute()
    batch = res.data
    if not batch:
        break
    all_data.extend(batch)
    offset += batch_size

# Prepare DataFrame
df = pd.DataFrame(all_data)
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date','open','high','low','close','delta'])
df = df.sort_values('date')
df['date'] = df['date'].dt.date

# Date filter
min_date = df['date'].min()
max_date = df['date'].max()
start_default = max_date - timedelta(days=90)
st.markdown("### Select date range")
start_date, end_date = st.slider("Date range", min_value=min_date, max_value=max_date,
                                 value=(start_default, max_date), format="YYYY-MM-DD")
mask = (df['date'] >= start_date) & (df['date'] <= end_date)
df_filtered = df.loc[mask].copy()

# Calculate indicators
df_filtered['ema8'] = df_filtered['close'].ewm(span=8, adjust=False).mean()
df_filtered['ema21'] = df_filtered['close'].ewm(span=21, adjust=False).mean()
df_filtered['ema55'] = df_filtered['close'].ewm(span=55, adjust=False).mean()
df_filtered['ma50'] = df_filtered['close'].rolling(window=50).mean()
df_filtered['ma200'] = df_filtered['close'].rolling(window=200).mean()
df_filtered['bb_mid'] = df_filtered['close'].rolling(window=20).mean()
df_filtered['bb_std'] = df_filtered['close'].rolling(window=20).std()
df_filtered['bb_upper'] = df_filtered['bb_mid'] + 2 * df_filtered['bb_std']
df_filtered['bb_lower'] = df_filtered['bb_mid'] - 2 * df_filtered['bb_std']

delta = df_filtered['close'].diff()
up = delta.where(delta>0,0).rolling(14).mean()
down = -delta.where(delta<0,0).rolling(14).mean()
rs = up/down
df_filtered['rsi'] = 100 - (100/(1+rs))
df_filtered['atr'] = (df_filtered['high'] - df_filtered['low']).rolling(14).mean()
df_filtered['macd'] = df_filtered['close'].ewm(span=12, adjust=False).mean() - df_filtered['close'].ewm(span=26, adjust=False).mean()
df_filtered['macd_signal'] = df_filtered['macd'].ewm(span=9, adjust=False).mean()

# Technical Analysis Chart
st.subheader('Technical Analysis')
fig_ta = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.05)
fig_ta.add_trace(go.Candlestick(
    x=df_filtered['date'], open=df_filtered['open'], high=df_filtered['high'],
    low=df_filtered['low'], close=df_filtered['close'], name='Candlestick'
), row=1, col=1)
fig_ta.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['ema8'], name='EMA 8'), row=1, col=1)
fig_ta.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['ema21'], name='EMA 21'), row=1, col=1)
fig_ta.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['ema55'], name='EMA 55'), row=1, col=1)
fig_ta.add_trace(go.Scatter(x=df_filtered['date'], y=df_filtered['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig_ta.update_yaxes(title_text='RSI', row=2, col=1, range=[0,100])
fig_ta.update_layout(height=800, xaxis_rangeslider_visible=False,
                     legend=dict(x=1, y=0, xanchor='right', yanchor='bottom'))
st.plotly_chart(fig_ta, use_container_width=True)

# Strategy Alerts
alerts = []
if df_filtered['rsi'].iat[-1] > 70:
    alerts.append('RSI > 70: overbought')
elif df_filtered['rsi'].iat[-1] < 30:
    alerts.append('RSI < 30: oversold')
if df_filtered['ema8'].iat[-1] > df_filtered['ema21'].iat[-1] and df_filtered['ema8'].iat[-2] <= df_filtered['ema21'].iat[-2]:
    alerts.append('EMA8 crossed above EMA21')
elif df_filtered['ema8'].iat[-1] < df_filtered['ema21'].iat[-1] and df_filtered['ema8'].iat[-2] >= df_filtered['ema21'].iat[-2]:
    alerts.append('EMA8 crossed below EMA21')
if df_filtered['close'].iat[-1] > df_filtered['bb_upper'].iat[-1]:
    alerts.append('Price above BB upper')
elif df_filtered['close'].iat[-1] < df_filtered['bb_lower'].iat[-1]:
    alerts.append('Price below BB lower')
if df_filtered['ma50'].iat[-1] > df_filtered['ma200'].iat[-1] and df_filtered['ma50'].iat[-2] <= df_filtered['ma200'].iat[-2]:
    alerts.append('Golden Cross MA50/MA200')
elif df_filtered['ma50'].iat[-1] < df_filtered['ma200'].iat[-1] and df_filtered['ma50'].iat[-2] >= df_filtered['ma200'].iat[-2]:
    alerts.append('Death Cross MA50/MA200')
if df_filtered['atr'].iat[-1] > 1.5 * df_filtered['atr'].mean():
    alerts.append('High ATR: increased volatility')
if df_filtered['macd'].iat[-1] > df_filtered['macd_signal'].iat[-1] and df_filtered['macd'].iat[-2] <= df_filtered['macd_signal'].iat[-2]:
    alerts.append('MACD bullish crossover')
elif df_filtered['macd'].iat[-1] < df_filtered['macd_signal'].iat[-1] and df_filtered['macd'].iat[-2] >= df_filtered['macd_signal'].iat[-2]:
    alerts.append('MACD bearish crossover')

if alerts:
    st.subheader('Strategy Alerts')
    for a in alerts:
        st.info(a)

# Price Chart with EMA markers and MACD panel
def plot_signal_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    for i in range(1, len(df)):
        if df['ema8'].iat[i] > df['ema21'].iat[i] and df['ema8'].iat[i-1] <= df['ema21'].iat[i-1]:
            fig.add_annotation(x=df['date'].iat[i], y=df['low'].iat[i], text='▲', showarrow=False, font_color='green')
        if df['ema8'].iat[i] < df['ema21'].iat[i] and df['ema8'].iat[i-1] >= df['ema21'].iat[i-1]:
            fig.add_annotation(x=df['date'].iat[i], y=df['high'].iat[i], text='▼', showarrow=False, font_color='red')
    fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['macd_signal'], name='Signal'), row=2, col=1)
    fig.update_layout(showlegend=True, legend=dict(x=1,y=0,xanchor='right',yanchor='bottom'), height=800)
    return fig

st.subheader('Price & MACD Signals')
st.plotly_chart(plot_signal_chart(df_filtered), use_container_width=True)

# Backtests and Performance
st.subheader('Backtest Performance')

df_bt = df_filtered.copy()
# RSI strategy
df_bt['pos_rsi'] = 0
df_bt.loc[df_bt['rsi'] < 30, 'pos_rsi'] = 1
df_bt.loc[df_bt['rsi'] > 70, 'pos_rsi'] = 0
df_bt['ret_rsi'] = df_bt['pos_rsi'] * df_bt['close'].pct_change()
