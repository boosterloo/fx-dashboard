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
df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ma50'] = df['close'].rolling(window=50).mean()
df['ma200'] = df['close'].rolling(window=200).mean()
df['bb_mid'] = df['close'].rolling(window=20).mean()
df['bb_std'] = df['close'].rolling(window=20).std()
df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

delta = df['close'].diff()
up = delta.where(delta>0,0).rolling(14).mean()
down = -delta.where(delta<0,0).rolling(14).mean()
rs = up/down
df['rsi'] = 100 - (100/(1+rs))
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['macd'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
df['macd_signal'] = df['macd'].ewm(span=9).mean()

# Generate alerts
alerts = []
if df['rsi'].iat[-1] > 70:
    alerts.append('RSI > 70: overbought')
elif df['rsi'].iat[-1] < 30:
    alerts.append('RSI < 30: oversold')
if df['ema8'].iat[-1] > df['ema21'].iat[-1] and df['ema8'].iat[-2] <= df['ema21'].iat[-2]:
    alerts.append('EMA8 crossed above EMA21')
elif df['ema8'].iat[-1] < df['ema21'].iat[-1] and df['ema8'].iat[-2] >= df['ema21'].iat[-2]:
    alerts.append('EMA8 crossed below EMA21')
if df['close'].iat[-1] > df['bb_upper'].iat[-1]:
    alerts.append('Price above BB upper')
elif df['close'].iat[-1] < df['bb_lower'].iat[-1]:
    alerts.append('Price below BB lower')
if df['ma50'].iat[-1] > df['ma200'].iat[-1] and df['ma50'].iat[-2] <= df['ma200'].iat[-2]:
    alerts.append('Golden Cross MA50/MA200')
elif df['ma50'].iat[-1] < df['ma200'].iat[-1] and df['ma50'].iat[-2] >= df['ma200'].iat[-2]:
    alerts.append('Death Cross MA50/MA200')
if df['atr'].iat[-1] > 1.5 * df['atr'].mean():
    alerts.append('High ATR: increased volatility')
if df['macd'].iat[-1] > df['macd_signal'].iat[-1] and df['macd'].iat[-2] <= df['macd_signal'].iat[-2]:
    alerts.append('MACD bullish crossover')
elif df['macd'].iat[-1] < df['macd_signal'].iat[-1] and df['macd'].iat[-2] >= df['macd_signal'].iat[-2]:
    alerts.append('MACD bearish crossover')

if alerts:
    st.subheader('Strategy Alerts')
    for a in alerts:
        st.info(a)

# Plot price and MACD with markers
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.05)
fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'],
              low=df['low'], close=df['close'], name='Price'), row=1, col=1)
# Add EMA crossover markers
for i in range(1, len(df)):
    if df['ema8'].iat[i] > df['ema21'].iat[i] and df['ema8'].iat[i-1] <= df['ema21'].iat[i-1]:
        fig.add_annotation(x=df['date'].iat[i], y=df['low'].iat[i], text='▲', showarrow=False, font_color='green')
    if df['ema8'].iat[i] < df['ema21'].iat[i] and df['ema8'].iat[i-1] >= df['ema21'].iat[i-1]:
        fig.add_annotation(x=df['date'].iat[i], y=df['high'].iat[i], text='▼', showarrow=False, font_color='red')
fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD'), row=2, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['macd_signal'], name='Signal'), row=2, col=1)
fig.update_layout(showlegend=True, legend=dict(x=1,y=0,xanchor='right',yanchor='bottom'), height=800)
st.plotly_chart(fig, use_container_width=True)

# Backtests for strategies
df_bt = df.copy()
# RSI strategy
df_bt['pos_rsi'] = 0
df_bt.loc[df_bt['rsi'] < 30, 'pos_rsi'] = 1
df_bt.loc[df_bt['rsi'] > 70, 'pos_rsi'] = 0
df_bt['ret_rsi'] = df_bt['pos_rsi'] * df_bt['close'].pct_change()
df_bt['cum_rsi'] = (1 + df_bt['ret_rsi']).cumprod()
# EMA strategy
df_bt['pos_ema'] = 0
df_bt.loc[df_bt['ema8'] > df_bt['ema21'], 'pos_ema'] = 1
df_bt['ret_ema'] = df_bt['pos_ema'] * df_bt['close'].pct_change()
df_bt['cum_ema'] = (1 + df_bt['ret_ema']).cumprod()
# MACD strategy
df_bt['pos_macd'] = 0
df_bt.loc[df_bt['macd'] > df_bt['macd_signal'], 'pos_macd'] = 1
df_bt['ret_macd'] = df_bt['pos_macd'] * df_bt['close'].pct_change()
df_bt['cum_macd'] = (1 + df_bt['ret_macd']).cumprod()
# ATR strategy
df_bt['pos_atr'] = 0
atr_diff = df_bt['atr'].diff()
df_bt.loc[(df_bt['close'] > df_bt['ma50']) & (atr_diff > 0), 'pos_atr'] = 1
df_bt['ret_atr'] = df_bt['pos_atr'] * df_bt['close'].pct_change()
df_bt['cum_atr'] = (1 + df_bt['ret_atr']).cumprod()

# Plot backtest performance
st.subheader('Backtest Performance')
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_bt['date'], y=df_bt['cum_rsi'], name='RSI'))
fig2.add_trace(go.Scatter(x=df_bt['date'], y=df_bt['cum_ema'], name='EMA'))
fig2.add_trace(go.Scatter(x=df_bt['date'], y=df_bt['cum_macd'], name='MACD'))
fig2.add_trace(go.Scatter(x=df_bt['date'], y=df_bt['cum_atr'], name='ATR'))
fig2.update_layout(title='Cumulative Strategy Performance', xaxis_title='Date', yaxis_title='Growth')
st.plotly_chart(fig2, use_container_width=True)

# Strategy statistics
def strategy_stats(series):
    total = series.iloc[-1] - 1
    vol = series.pct_change().std() * (252**0.5)
    sharpe = total/vol if vol!=0 else 0
    return total, vol, sharpe

stats = []
for name, col in [('RSI','cum_rsi'),('EMA','cum_ema'),('MACD','cum_macd'),('ATR','cum_atr')]:
    total, vol, sharpe = strategy_stats(df_bt[col])
    stats.append({'Strategy': name, 'Return': f"{total:.2%}", 'Volatility': f"{vol:.2%}", 'Sharpe': f"{sharpe:.2f}"})
st.table(pd.DataFrame(stats))
