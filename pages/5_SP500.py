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
default_start = max_date - timedelta(days=365)

st.markdown("### 🗓️ Selecteer datumrange")
date_range = st.slider("Kies datumrange", min_value=min_date, max_value=max_date,
                       value=(default_start, max_date), format="YYYY-MM-DD")
start_date, end_date = date_range

# 🔄 Data filteren
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# 📊 YTD en PYTD berekening op basis van volledige data
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

# ========== 📈 Deel 1: TA Grafieken ==========
st.subheader("📈 Technische Analyse: Heikin-Ashi, EMA's, MA's & RSI")

# Heikin-Ashi
df_ha = df_filtered.copy()
df_ha["ha_close"] = (df_ha["open"] + df_ha["high"] + df_ha["low"] + df_ha["close"]) / 4
ha_open = [(df_ha["open"].iloc[0] + df_ha["close"].iloc[0]) / 2]
for i in range(1, len(df_ha)):
    ha_open.append((ha_open[i - 1] + df_ha["ha_close"].iloc[i - 1]) / 2)
df_ha["ha_open"] = ha_open
df_ha["ha_high"] = df_ha[["high", "ha_open", "ha_close"]].max(axis=1)
df_ha["ha_low"] = df_ha[["low", "ha_open", "ha_close"]].min(axis=1)

# Indicatoren
df_ha["ema_8"] = df_ha["close"].ewm(span=8, adjust=False).mean()
df_ha["ema_21"] = df_ha["close"].ewm(span=21, adjust=False).mean()
df_ha["ema_55"] = df_ha["close"].ewm(span=55, adjust=False).mean()
df_ha["ma_50"] = df_ha["close"].rolling(window=50).mean()
df_ha["ma_200"] = df_ha["close"].rolling(window=200).mean()
df_ha["bollinger_mid"] = df_ha["close"].rolling(window=20).mean()
df_ha["bollinger_std"] = df_ha["close"].rolling(window=20).std()
df_ha["bollinger_upper"] = df_ha["bollinger_mid"] + 2 * df_ha["bollinger_std"]
df_ha["bollinger_lower"] = df_ha["bollinger_mid"] - 2 * df_ha["bollinger_std"]

# RSI
delta = df_ha["close"].diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
df_ha["rsi"] = 100 - (100 / (1 + rs))

# Signalen bij MA crossovers
signals = df_ha[(df_ha["ma_50"].notnull()) & (df_ha["ma_200"].notnull())]
signals = signals.assign(cross=(signals["ma_50"] > signals["ma_200"]).astype(int))
signals["signal"] = signals["cross"].diff().fillna(0)

# Subplots maken
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.7, 0.3], vertical_spacing=0.05,
                    subplot_titles=("Heikin-Ashi met Indicatoren", "RSI (14-dagen)"))

fig.add_trace(go.Candlestick(x=df_ha["date"], open=df_ha["ha_open"], high=df_ha["ha_high"],
    low=df_ha["ha_low"], close=df_ha["ha_close"], name="Heikin-Ashi",
    increasing_line_color="green", decreasing_line_color="red"), row=1, col=1)

fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_8"], name="EMA 8"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_21"], name="EMA 21"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ema_55"], name="EMA 55"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ma_50"], name="MA 50", line=dict(dash="dash")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["ma_200"], name="MA 200", line=dict(dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["bollinger_upper"], name="Bollinger Upper", line=dict(color="gray", width=1, dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["bollinger_lower"], name="Bollinger Lower", line=dict(color="gray", width=1, dash="dot")), row=1, col=1)

# Signal markers
for _, row in signals.iterrows():
    if row["signal"] == 1:
        fig.add_trace(go.Scatter(x=[row["date"]], y=[row["close"]], mode="markers", marker_symbol="triangle-up", marker_color="green", marker_size=10, name="Golden Cross"), row=1, col=1)
    elif row["signal"] == -1:
        fig.add_trace(go.Scatter(x=[row["date"]], y=[row["close"]], mode="markers", marker_symbol="triangle-down", marker_color="red", marker_size=10, name="Death Cross"), row=1, col=1)

fig.add_trace(go.Scatter(x=df_ha["date"], y=df_ha["rsi"], name="RSI", line=dict(color="purple")), row=2, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_layout(height=900, xaxis_rangeslider_visible=False, legend=dict(
    orientation="v", yanchor="bottom", y=0, xanchor="right", x=1
))
st.plotly_chart(fig, use_container_width=True)

# ========== 📉 Deel 2: Histogrammen ==========
df_filtered["delta_pct"] = df_filtered["close"].pct_change() * 100
col1, col2 = st.columns(2)

with col1:
    st.subheader("📉 Histogram van dagelijkse delta (absoluut)")
    fig_hist = go.Figure(go.Histogram(x=df_filtered["delta"], nbinsx=40, marker_color="orange"))
    fig_hist.update_layout(xaxis_title="Delta", yaxis_title="Frequentie", bargap=0.1)
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    st.subheader("📊 Histogram van dagelijkse delta (%)")
    fig_pct = go.Figure(go.Histogram(x=df_filtered["delta_pct"], nbinsx=40, marker_color="skyblue"))
    fig_pct.update_layout(xaxis_title="Delta (%)", yaxis_title="Frequentie", bargap=0.1)
    st.plotly_chart(fig_pct, use_container_width=True)

# ========== 📈 Deel 3: Rolling Volatility ==========
st.subheader("📈 Rolling Volatility (14d)")
df_filtered["rolling_volatility"] = df_filtered["delta"].rolling(window=14).std()
fig_vol = go.Figure(go.Scatter(x=df_filtered["date"], y=df_filtered["rolling_volatility"], mode="lines", name="Volatiliteit"))
fig_vol.update_layout(xaxis_title="Datum", yaxis_title="Standaarddeviatie")
st.plotly_chart(fig_vol, use_container_width=True)

# ✅ Export-optie
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download gefilterde data (CSV)", csv, "sp500_filtered.csv", "text/csv")
