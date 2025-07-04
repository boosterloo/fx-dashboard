import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_supabase_data
from datetime import date

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# === Data ophalen ===
df = get_supabase_data("sp500_data")

if isinstance(df, list):
    df = pd.DataFrame(df)

if df is None or df.empty:
    st.warning("Geen data beschikbaar.")
    st.stop()

# === Datum kolom verwerken als datetime64
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

# === Slider: werk met date() voor interface, maar filter met datetime
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

# === Filteren
df_filtered = df[
    (df["date"] >= pd.to_datetime(start_date)) &
    (df["date"] <= pd.to_datetime(end_date))
].copy()

if df_filtered.empty:
    st.warning("Geen data in de geselecteerde periode.")
    st.stop()

# === Forceer juiste type voor x-as
df_filtered["date"] = pd.to_datetime(df_filtered["date"])  # Ensure datetime64[ns]

# === Plot
fig = px.line(
    df_filtered,
    x="date",
    y="close",
    title="S&P 500 Slotkoers",
    labels={"date": "Datum", "close": "Slotkoers"},
    template="plotly_white",
    line_shape="linear",           # voorkomt rare curven
    render_mode="svg"              # stabieler voor veel data
)

fig.update_layout(
    height=500,
    xaxis_title="Datum",
    yaxis_title="Slotkoers",
    xaxis=dict(
        type="date",               # Forceert tijdlijn
        tickformat="%b %Y"        # Maand + jaar
    )
)

st.plotly_chart(fig, use_container_width=True)
