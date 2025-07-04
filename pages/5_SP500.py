import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import os

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

# Supabase connectie
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data
def load_data():
    response = supabase.table("sp500_data").select("*").execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"], format='%Y-%m-%d')  # Zorg voor consistent datumformaat
    df = df.sort_values("date")
    return df

df = load_data()

# Slider voor datumselectie
min_date = df["date"].min()
max_date = df["date"].max()

# Gebruik pandas Timestamps direct voor de slider
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filteren op geselecteerde range
filtered_df = df[(df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))]
st.write(filtered_df)  # Debug: Controleer de gefilterde data

# Plot van slotkoersen
if not filtered_df.empty:
    fig = px.line(
        filtered_df,
        x="date",
        y="close",
        title="S&P 500 Slotkoers",
        labels={"date": "Datum", "close": "Slotkoers"},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Geen data beschikbaar voor de geselecteerde datumrange.")