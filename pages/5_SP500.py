# ✅ Volledige gegenereerde code voor de gehele pagina

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 🔐 Supabase credentials
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 🔄 Data ophalen in chunks
all_data = []
batch_size = 1000
offset = 0
while True:
    response = (
        supabase.table("sp500_data")
        .select("*")
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    data = response.data
    if not data:
        break
    all_data.extend(data)
    offset += batch_size

# 🎉 DataFrame voorbereiden
df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "open", "high", "low", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date

# ⌚️ Datumselectie
min_date = df["date"].min()
max_date = df["date"].max()
default_start = max_date - timedelta(days=90)

st.markdown("### 🗓️ Selecteer datumrange")
date_range = st.slider("Kies datumrange", min_value=min_date, max_value=max_date,
                       value=(default_start, max_date), format="YYYY-MM-DD")
start_date, end_date = date_range

# 🔄 Data filteren
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()

# Indicatoren berekenen
df_filtered["ema_8"] = df_filtered["close"].ewm(span=8, adjust=False).mean()
df_filtered["ema_21"] = df_filtered["close"].ewm(span=21, adjust=False).mean()
df_filtered["ema_55"] = df_filtered["close"].ewm(span=55, adjust=False).mean()
df_filtered["ma_50"] = df_filtered["close"].rolling(window=50).mean()
df_filtered["ma_200"] = df_filtered["close"].rolling(window=200).mean()
df_filtered["bollinger_mid"] = df_filtered["close"].rolling(window=20).mean()
df_filtered["bollinger_std"] = df_filtered["close"].rolling(window=20).std()
df_filtered["bollinger_upper"] = df_filtered["bollinger_mid"] + 2 * df_filtered["bollinger_std"]
df_filtered["bollinger_lower"] = df_filtered["bollinger_mid"] - 2 * df_filtered["bollinger_std"]
delta = df_filtered["close"].diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
df_filtered["rsi"] = 100 - (100 / (1 + rs))
df_filtered["delta_pct"] = df_filtered["close"].pct_change() * 100
df_filtered["rolling_volatility"] = df_filtered["delta"].rolling(window=14).std()

# 📊 YTD en PYTD berekening
try:
    ytd_start = datetime(max_date.year, 1, 1).date()
    pytd_start = datetime(max_date.year - 1, 1, 1).date()
    ytd_data = df[df["date"] >= ytd_start]
    pytd_data = df[(df["date"] >= pytd_start) & (df["date"] < ytd_start)]
    ytd_return_abs = ytd_data["close"].iloc[-1] - ytd_data["close"].iloc[0]
    ytd_return_pct = (ytd_return_abs / ytd_data["close"].iloc[0]) * 100
    pytd_return_abs = pytd_data["close"].iloc[-1] - pytd_data["close"].iloc[0]
    pytd_return_pct = (pytd_return_abs / pytd_data["close"].iloc[0]) * 100
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("YTD #", f"{ytd_return_abs:.2f}")
    col2.metric("YTD %", f"{ytd_return_pct:.2f}%")
    col3.metric("PYTD #", f"{pytd_return_abs:.2f}")
    col4.metric("PYTD %", f"{pytd_return_pct:.2f}%")
except:
    st.warning("Niet genoeg data beschikbaar voor YTD/PYTD berekening.")

# 📈 TA-grafieken
st.subheader("📈 Technische Analyse: Heikin-Ashi, EMA, MA, Bollinger & RSI")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.7, 0.3], vertical_spacing=0.05,
                    subplot_titles=("Candlestick met indicatoren", "RSI"))
fig.add_trace(go.Candlestick(x=df_filtered["date"], open=df_filtered["open"], high=df_filtered["high"],
                             low=df_filtered["low"], close=df_filtered["close"], name="Candles"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_8"], name="EMA 8"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_21"], name="EMA 21"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ema_55"], name="EMA 55"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ma_50"], name="MA 50"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["ma_200"], name="MA 200"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["bollinger_upper"], name="Boll Upper", line=dict(dash="dot", color="gray")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["bollinger_lower"], name="Boll Lower", line=dict(dash="dot", color="gray")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["rsi"], name="RSI", line=dict(color="purple")), row=2, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_layout(height=850, xaxis_rangeslider_visible=False, legend=dict(
    orientation="v", yanchor="bottom", y=0, xanchor="right", x=1
))
st.plotly_chart(fig, use_container_width=True)

# 📊 Histogrammen
col1, col2 = st.columns(2)
with col1:
    st.subheader("📉 Dagelijkse delta (absoluut)")
    fig_hist = go.Figure(go.Histogram(x=df_filtered["delta"], nbinsx=40, marker_color="orange"))
    fig_hist.update_layout(xaxis_title="Delta", yaxis_title="Frequentie")
    st.plotly_chart(fig_hist, use_container_width=True)
with col2:
    st.subheader("📊 Dagelijkse delta (%)")
    fig_pct = go.Figure(go.Histogram(x=df_filtered["delta_pct"], nbinsx=40, marker_color="skyblue"))
    fig_pct.update_layout(xaxis_title="Delta %", yaxis_title="Frequentie")
    st.plotly_chart(fig_pct, use_container_width=True)

# 📈 Rolling Volatility
st.subheader("📈 Rolling Volatility (14d)")
fig_vol = go.Figure(go.Scatter(x=df_filtered["date"], y=df_filtered["rolling_volatility"], mode="lines", name="Volatiliteit"))
fig_vol.update_layout(xaxis_title="Datum", yaxis_title="Standaarddeviatie")
st.plotly_chart(fig_vol, use_container_width=True)

# 🔔 Strategie-alerts
alerts = []
if df_filtered["rsi"].iloc[-1] > 70:
    alerts.append("⚠️ RSI boven 70: mogelijk overbought!")
elif df_filtered["rsi"].iloc[-1] < 30:
    alerts.append("⚠️ RSI onder 30: mogelijk oversold!")
if (df_filtered["ema_8"].iloc[-1] > df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] <= df_filtered["ema_21"].iloc[-2]):
    alerts.append("✅ EMA8 kruist boven EMA21: bullish signaal")
elif (df_filtered["ema_8"].iloc[-1] < df_filtered["ema_21"].iloc[-1]) and (df_filtered["ema_8"].iloc[-2] >= df_filtered["ema_21"].iloc[-2]):
    alerts.append("🔻 EMA8 kruist onder EMA21: bearish signaal")
if alerts:
    st.subheader("📣 Strategie Alerts")
    for msg in alerts:
        st.info(msg)

# ✅ Export
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download gefilterde data (CSV)", csv, "sp500_filtered.csv", "text/csv")

# 🧪 Backtest & Strategie Analyse
st.markdown("---")
st.header("🧪 Backtest & Strategie Analyse")
df_bt = df_filtered.copy()
df_bt["position_rsi"] = 0
df_bt.loc[df_bt["rsi"] < 30, "position_rsi"] = 1
df_bt.loc[df_bt["rsi"] > 70, "position_rsi"] = 0
df_bt["position_rsi"] = df_bt["position_rsi"].ffill()
df_bt["return_rsi"] = df_bt["position_rsi"] * df_bt["close"].pct_change()
df_bt["cum_rsi"] = (1 + df_bt["return_rsi"]).cumprod()
df_bt["position_ema"] = 0
df_bt.loc[df_bt["ema_8"] > df_bt["ema_21"], "position_ema"] = 1
df_bt["return_ema"] = df_bt["position_ema"] * df_bt["close"].pct_change()
df_bt["cum_ema"] = (1 + df_bt["return_ema"]).cumprod()
fig_bt = go.Figure()
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_rsi"], mode="lines", name="RSI Strategie"))
fig_bt.add_trace(go.Scatter(x=df_bt["date"], y=df_bt["cum_ema"], mode="lines", name="EMA Crossover"))
fig_bt.update_layout(title="Strategieën (Cumulatief)", xaxis_title="Datum", yaxis_title="Groei", width=1200)
st.plotly_chart(fig_bt, use_container_width=False)

def strategie_stats(series, naam):
    total_return = series.iloc[-1] - 1
    volatility = series.pct_change().std() * (252 ** 0.5)
    sharpe = total_return / volatility if volatility != 0 else 0
    return naam, f"{total_return:.2%}", f"{volatility:.2%}", f"{sharpe:.2f}"

rsi_stats = strategie_stats(df_bt["cum_rsi"], "RSI")
ema_stats = strategie_stats(df_bt["cum_ema"], "EMA")

st.subheader("📊 Strategie Statistieken")
st.table(pd.DataFrame([rsi_stats, ema_stats], columns=["Strategie", "Totale Return", "Volatiliteit", "Sharpe Ratio"]))
