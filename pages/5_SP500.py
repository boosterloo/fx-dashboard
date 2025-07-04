import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_supabase_data

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
df = get_supabase_data("sp500_data")

# Converteer lijst naar DataFrame
if isinstance(df, list):
    df = pd.DataFrame(df)

# Controleer of data geldig is
if df is None or df.empty:
    st.warning("Geen data beschikbaar.")
    st.stop()

# Datumkolom verwerken
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

# === Simpele datum schuifregelaar ===
min_date = df["date"].min()
max_date = df["date"].max()

start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(max_date - pd.DateOffset(years=3), max_date),
    format="YYYY-MM-DD"
)

# Filter de data
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# === Lijngrafiek (datum vs close) ===
fig = px.line(df_filtered, x="date", y="close", title="S&P 500 - Slotkoers")
fig.update_layout(xaxis_title="Datum", yaxis_title="Close", height=500)

st.plotly_chart(fig, use_container_width=True)
