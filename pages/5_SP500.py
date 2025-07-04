import streamlit as st
import pandas as pd
import plotly.express as px
from utils import supabase  # ← gebruik de bestaande Supabase-client

# Titel
st.title("📈 S&P 500 Dashboard")

# Data ophalen vanaf 2010
response = supabase.table("sp500_data").select("*").gte("date", "2010-01-01").execute()
data = pd.DataFrame(response.data)

# Datumkolom goed zetten
data["date"] = pd.to_datetime(data["date"])

# Slider voor datumbereik
min_date = data["date"].min()
max_date = data["date"].max()

start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filter de data
filtered_data = data[(data["date"] >= start_date) & (data["date"] <= end_date)]

# Plot
fig = px.line(filtered_data, x="date", y="close", title="S&P 500 Slotkoers", labels={"close": "Slotkoers", "date": "Datum"})
st.plotly_chart(fig, use_container_width=True)
