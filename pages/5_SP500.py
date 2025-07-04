import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client
from datetime import datetime

# Supabase instellingen
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Ophalen van data vanaf 2010
response = supabase.table("sp500").select("*").gte("date", "2010-01-01").execute()
data = pd.DataFrame(response.data)

# Omzetten van datum
data["date"] = pd.to_datetime(data["date"])
data = data.sort_values("date")

# Controle: laat enkele rijen zien
st.write(data.head())

# Datumrange slider
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=data["date"].min().date(),
    max_value=data["date"].max().date(),
    value=(data["date"].min().date(), data["date"].max().date()),
    format="YYYY-MM-DD"
)

# Filter op geselecteerde datumrange
filtered_data = data[(data["date"] >= pd.to_datetime(start_date)) & (data["date"] <= pd.to_datetime(end_date))]

# Plot maken
chart = alt.Chart(filtered_data).mark_line(color="blue").encode(
    x=alt.X("date:T", title="Datum"),
    y=alt.Y("close:Q", title="Slotkoers"),
    tooltip=["date:T", "close:Q"]
).properties(
    title="S&P 500 Slotkoers"
)

st.altair_chart(chart, use_container_width=True)
