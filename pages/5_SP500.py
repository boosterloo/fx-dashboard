import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# 🔐 Load secrets from .env
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 🔄 Chunked ophalen van SP500 data
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

# 🧹 Data voorbereiden
df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date  # voor de slider

# 🎛️ Slider instellen
min_date = df["date"].min()
max_date = df["date"].max()
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# 🔎 Filter op geselecteerde datums
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# 🔴🟢 Kleurcodering voor delta
colors = ["green" if delta > 0 else "red" for delta in df_filtered["delta"]]

# 📊 Delta staafdiagram
fig = go.Figure()

fig.add_trace(go.Bar(
    x=df_filtered["date"],
    y=df_filtered["delta"],
    marker_color=colors,
    name="Dagelijkse Delta",
))

fig.update_layout(
    title="Dagelijkse S&P 500 Delta",
    xaxis_title="Datum",
    yaxis_title="Delta",
    showlegend=False,
    height=500,
)

st.plotly_chart(fig, use_container_width=True)
