import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# 🔐 Laad .env
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

# 🧼 Data voorbereiden
df = pd.DataFrame(all_data)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "close", "delta"])
df = df.sort_values("date")
df["date"] = df["date"].dt.date  # voor slider

# 📅 Slider instellen
min_date = df["date"].min()
max_date = df["date"].max()
start_date, end_date = st.slider(
    "Selecteer datumrange",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# 🔍 Filter op datum
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# 🟢🔴 Kleur voor delta's
colors = ["green" if d > 0 else "red" for d in df_filtered["delta"]]

# 📈 Maak gecombineerde grafiek
fig = go.Figure()

# ➕ Slotkoerslijn
fig.add_trace(go.Scatter(
    x=df_filtered["date"],
    y=df_filtered["close"],
    mode="lines",
    name="Slotkoers",
    line=dict(color="blue")
))

# ➕ Delta-staafjes (als overlay)
fig.add_trace(go.Bar(
    x=df_filtered["date"],
    y=df_filtered["delta"],
    marker_color=colors,
    name="Dagelijkse Delta",
    yaxis="y2",
    opacity=0.4
))

# 🎨 Layout aanpassen met 2 assen
fig.update_layout(
    title="S&P 500 Slotkoers + Dagelijkse Delta",
    xaxis_title="Datum",
    yaxis=dict(title="Slotkoers", side="left"),
    yaxis2=dict(
        title="Delta",
        overlaying="y",
        side="right",
        showgrid=False
    ),
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
