import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_supabase_data
from datetime import date

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
df = get_supabase_data("sp500_data")

# Converteer lijst naar DataFrame indien nodig
if isinstance(df, list):
    df = pd.DataFrame(df)

# Controleer of data geldig is
if df is None or df.empty:
    st.warning("Geen data beschikbaar.")
    st.stop()

# Datumkolom verwerken
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

# === Datumschuifregelaar ===
min_date = df["date"].min().date()
max_date = df["date"].max().date()
default_start = (df["date"].max() - pd.DateOffset(years=3)).date()

start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(default_start, max_date),
    format="YYYY-MM-DD"
)

# Filteren op gekozen datumrange
df_filtered = df[
    (df["date"] >= pd.to_datetime(start_date)) &
    (df["date"] <= pd.to_datetime(end_date))
].copy()

if df_filtered.empty:
    st.warning("Geen data in de geselecteerde periode.")
    st.stop()

# === Slotkoersgrafiek ===
fig = px.line(
    df_filtered,
    x="date",
    y="close",
    title="S&P 500 Slotkoers",
    labels={"date": "Datum", "close": "Close"}
)
fig.update_layout(height=500)

st.plotly_chart(fig, use_container_width=True)
