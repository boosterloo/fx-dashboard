import streamlit as st
import pandas as pd
import plotly.express as px
from utils import supabase

# Titel
st.title("📈 S&P 500 Dashboard")

# Data ophalen
response = supabase.table("sp500_data").select("*").gte("date", "2010-01-01").execute()
data = pd.DataFrame(response.data)

# Datumkolom goed zetten
data["date"] = pd.to_datetime(data["date"])

# Zet datumwaarden naar date objecten voor slider
min_date = data["date"].min().date()
max_date = data["date"].max().date()

# Slider voor datumbereik
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filter de data
filtered_data = data[
    (data["date"] >= pd.to_datetime(start_date)) &
    (data["date"] <= pd.to_datetime(end_date))
]

# Plot
fig = px.line(filtered_data, x="date", y="close", title="S&P 500 Slotkoers", labels={"close": "Slotkoers", "date": "Datum"})
st.plotly_chart(fig, use_container_width=True)
