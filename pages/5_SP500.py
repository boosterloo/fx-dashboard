# 5_SP500.py

import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
import plotly.express as px

st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")

# Titel
st.title("📈 S&P 500 Dashboard")

# Supabase instellingen
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Data ophalen
@st.cache_data
def load_data():
    response = supabase.table("sp500_data").select("*").execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"]).dt.date  # Convert to datetime.date
    df = df.sort_values("date")
    return df

df = load_data()

# Slider voor datumrange
min_date = min(df["date"])
max_date = max(df["date"])

start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filter de data op geselecteerde range
filtered_df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# Plot slotkoers
fig = px.line(filtered_df, x="date", y="close", title="S&P 500 Slotkoers", labels={"date": "Datum", "close": "Slotkoers"})
fig.update_traces(line=dict(color="royalblue", width=1))
st.plotly_chart(fig, use_container_width=True)
