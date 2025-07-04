import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
from dotenv import load_dotenv
import os
import plotly.express as px

# 🔐 .env laden
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 📥 Data ophalen
response = supabase.table("sp500_data").select("*").execute()
data = pd.DataFrame(response.data)

# 🧹 Datum opschonen
data["date"] = pd.to_datetime(data["date"], errors="coerce")
data = data.dropna(subset=["date"])
data = data.sort_values("date")

# 📆 Slider-grenzen bepalen
min_date = data["date"].min()
max_date = data["date"].max()

# 🎛️ Slider renderen
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# 📊 Filter en visualiseer
filtered = data[(data["date"] >= start_date) & (data["date"] <= end_date)]
fig = px.line(filtered, x="date", y="close", labels={"date": "Datum", "close": "Slotkoers"}, title="S&P 500 Slotkoers")
st.plotly_chart(fig, use_container_width=True)
