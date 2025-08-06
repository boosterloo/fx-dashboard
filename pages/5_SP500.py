import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import get_supabase_data

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# 📅 Data ophalen
df = get_supabase_data("sp500_data")

if df.empty:
    st.warning("Geen data opgehaald van Supabase.")
    st.stop()

# 🧹 Datacleaning
df["date"] = pd.to_datetime(df["date"])
df.sort_values("date", inplace=True)
df["close"] = pd.to_numeric(df["close"], errors="coerce")
df.dropna(subset=["close"], inplace=True)

# 🗓️ Datumfilter (compatibel met Streamlit slider)
df["date_only"] = df["date"].dt.date
min_date = df["date_only"].min()
max_date = df["date_only"].max()
default_start = max_date - pd.Timedelta(days=90).to_pytimedelta()

date_range = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(default_start, max_date)
)

# Filter op datum
df_filtered = df[(df["date_only"] >= date_range[0]) & (df["date_only"] <= date_range[1])].copy()

# 📏 MA-instelling
ma_period = st.number_input("Selecteer MA-periode", min_value=1, max_value=200, value=20)
df_filtered["MA"] = df_filtered["close"].rolling(ma_period).mean()

# 📉 Dagelijkse veranderingen
df_filtered["delta_abs"] = df_filtered["close"].diff()
df_filtered["delta_pct"] = df_filtered["close"].pct_change() * 100

# 📊 Close + MA grafiek
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["close"], mode="lines", name="Close"))
fig1.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["MA"], mode="lines", name=f"MA {ma_period}"))
fig1.update_layout(title="S&P 500 Close + MA", xaxis_title="Datum", yaxis_title="Prijs")

# 📊 Histogram verandering
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["delta_abs"], name="Δ absoluut"))
fig2.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["delta_pct"], name="Δ %"))

fig2.update_layout(
    title="Dagelijkse Verandering (Absoluut en %)",
    barmode="group",
    xaxis_title="Datum",
    yaxis_title="Verandering",
)

# 📈 Visualisaties tonen
st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
