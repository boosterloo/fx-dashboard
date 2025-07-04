import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# Config
st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")

# Supabase secrets
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# Titel
st.title("📈 S&P 500 Dashboard")

# Data ophalen vanaf 2010 (i.v.m. betrouwbaarheid en performance)
response = supabase.table("sp500_data").select("*").gte("date", "2010-01-01").execute()
df = pd.DataFrame(response.data)

# Data goed formatteren
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')
df['close'] = pd.to_numeric(df['close'], errors='coerce')

# Datumrange slider
min_date = df['date'].min()
max_date = df['date'].max()
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filteren op geselecteerde datumrange
filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

# Plot slotkoers
st.subheader("S&P 500 Slotkoers")
fig = px.line(filtered_df, x='date', y='close', labels={"date": "Datum", "close": "Slotkoers"}, template="plotly_white")
st.plotly_chart(fig, use_container_width=True)
