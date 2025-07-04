import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# 🌱 Laad .env
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 🔄 Haal SP500 data in chunks op
all_data = []
batch_size = 1000
offset = 0

while True:
    response = (
        supabase.table("sp500_data")
        .select("*")
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    batch = response.data
    if not batch:
        break
    all_data.extend(batch)
    offset += batch_size

# 📊 Data verwerken
data = pd.DataFrame(all_data)
data["date"] = pd.to_datetime(data["date"], errors="coerce")
data = data.dropna(subset=["date"])
data = data.sort_values("date")
data["date"] = data["date"].dt.date  # date-only type for slider

# 🗓️ Datum slider
min_date = data["date"].min()
max_date = data["date"].max()

start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# 🔍 Filter
filtered = data[(data["date"] >= start_date) & (data["date"] <= end_date)]

# 📈 Plot
fig = px.line(
    filtered,
    x="date",
    y="close",
    title="S&P 500 Slotkoers",
    labels={"date": "Datum", "close": "Slotkoers"}
)
st.plotly_chart(fig, use_container_width=True)
