import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import get_supabase_data

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# 📅 Data ophalen uit Supabase view inclusief delta's
df = get_supabase_data("sp500_view_delta")

if df.empty:
    st.warning("Geen data opgehaald van Supabase.")
    st.stop()

# 🧹 Datacleaning
df["date"] = pd.to_datetime(df["date"])
df.sort_values("date", inplace=True)
df["close"] = pd.to_numeric(df["close"], errors="coerce")
df["delta_abs"] = pd.to_numeric(df["delta_abs"], errors="coerce")
df["delta_pct"] = pd.to_numeric(df["delta_pct"], errors="coerce")
df.dropna(subset=["close", "delta_abs", "delta_pct"], inplace=True)

# 🗓️ Datumfilter
min_date = df["date"].min().date()
max_date = df["date"].max().date()

# Slider om datumrange te selecteren
date_range = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date)
)

# Filter op datum
df_filtered = df[(df["date"].dt.date >= date_range[0]) & (df["date"].dt.date <= date_range[1])].copy()

# 📏 MA-instelling
ma_period = st.number_input("Selecteer MA-periode", min_value=1, max_value=200, value=20)
df_filtered["MA"] = df_filtered["close"].rolling(ma_period).mean()

# 📊 Close + MA grafiek
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["close"], mode="lines", name="Close"))
fig1.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered["MA"], mode="lines", name=f"MA {ma_period}"))
fig1.update_layout(title="S&P 500 Close + MA", xaxis_title="Datum", yaxis_title="Prijs")

# 🔘 Keuze tussen absolute of procentuele verandering
weergave_optie = st.radio("Kies veranderingstype", ["Absoluut", "%"], horizontal=True)

# 📊 Staafdiagram verandering (kleurcodering)
fig2 = go.Figure()
if weergave_optie == "Absoluut":
    kleuren = ["green" if x >= 0 else "red" for x in df_filtered["delta_abs"]]
    fig2.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["delta_abs"], name="Δ absoluut", marker_color=kleuren))
    fig2.update_layout(title="Dagelijkse Verandering (Absoluut)", yaxis_title="Verandering (punten)")
else:
    kleuren = ["green" if x >= 0 else "red" for x in df_filtered["delta_pct"]]
    fig2.add_trace(go.Bar(x=df_filtered["date"], y=df_filtered["delta_pct"], name="Δ %", marker_color=kleuren))
    fig2.update_layout(title="Dagelijkse Verandering (%)", yaxis_title="Verandering (%)")

fig2.update_layout(xaxis_title="Datum", barmode="group")

# 📉 Histogrammen met mediaan
st.subheader("📊 Histogrammen van Dagelijkse Veranderingen")
hist_fig_abs = go.Figure()
hist_data_abs = df_filtered["delta_abs"]
mediaan_abs = hist_data_abs.median()
hist_fig_abs.add_trace(go.Histogram(x=hist_data_abs, nbinsx=30, marker_color="green", name="Verdeling Δ absoluut"))
hist_fig_abs.add_vline(x=mediaan_abs, line_dash="dash", line_color="red", annotation_text=f"Mediaan: {mediaan_abs:.2f}", annotation_position="top right")
hist_fig_abs.update_layout(title="Histogram Δ absoluut", xaxis_title="Verandering (punten)", yaxis_title="Frequentie")

hist_fig_pct = go.Figure()
hist_data_pct = df_filtered["delta_pct"]
mediaan_pct = hist_data_pct.median()
hist_fig_pct.add_trace(go.Histogram(x=hist_data_pct, nbinsx=30, marker_color="blue", name="Verdeling Δ %"))
hist_fig_pct.add_vline(x=mediaan_pct, line_dash="dash", line_color="red", annotation_text=f"Mediaan: {mediaan_pct:.2f}%", annotation_position="top right")
hist_fig_pct.update_layout(title="Histogram Δ %", xaxis_title="Verandering (%)", yaxis_title="Frequentie")

# 📈 Visualisaties tonen
st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
st.plotly_chart(hist_fig_abs, use_container_width=True)
st.plotly_chart(hist_fig_pct, use_container_width=True)
