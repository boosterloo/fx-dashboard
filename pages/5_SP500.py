import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Simuleer een voorbeeld dataframe met datum en slotkoers
np.random.seed(42)
dates = pd.date_range(start="2024-01-01", periods=100)
close_prices = np.cumsum(np.random.randn(100)) + 100
df = pd.DataFrame({'date': dates, 'close': close_prices})

# Bereken Heikin Ashi waarden
df['open_ha'] = (df['close'].shift(1) + df['close'].shift(1)) / 2
df['close_ha'] = (df['close'] + df['close'].shift(1)) / 2
df['high_ha'] = df[['close', 'close_ha', 'open_ha']].max(axis=1)
df['low_ha'] = df[['close', 'close_ha', 'open_ha']].min(axis=1)

# Bereken EMA's
df['EMA_5'] = df['close'].ewm(span=5, adjust=False).mean()
df['EMA_15'] = df['close'].ewm(span=15, adjust=False).mean()
df['EMA_30'] = df['close'].ewm(span=30, adjust=False).mean()

# Plot HA + EMA
fig = go.Figure(data=[
    go.Candlestick(
        x=df['date'],
        open=df['open_ha'],
        high=df['high_ha'],
        low=df['low_ha'],
        close=df['close_ha'],
        increasing_line_color='cyan',
        decreasing_line_color='red',
        name='Heikin Ashi'
    ),
    go.Scatter(x=df['date'], y=df['EMA_5'], line=dict(color='blue', width=1), name='EMA 5'),
    go.Scatter(x=df['date'], y=df['EMA_15'], line=dict(color='orange', width=1), name='EMA 15'),
    go.Scatter(x=df['date'], y=df['EMA_30'], line=dict(color='red', width=1), name='EMA 30')
])

fig.update_layout(
    title="Heikin Ashi + EMA",
    xaxis_title="Datum",
    yaxis_title="Prijs",
    height=500,
    width=1000,
    xaxis_rangeslider_visible=False
)

fig.show()
