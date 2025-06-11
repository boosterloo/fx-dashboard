import os
import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv
import altair as alt

# Load environment variables
load_dotenv()

# Database connection
conn = psycopg2.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD")
)

st.set_page_config(page_title="💱 FX Dashboard", page_icon="💱", layout="centered")
st.title("💱 FX Rates Dashboard")
st.markdown("""
    Bekijk de meest recente wisselkoersen.
    Dit dashboard toont een overzicht van de EUR/USD koersen uit de database.
""")

try:
    df = pd.read_sql("SELECT * FROM fx_rates ORDER BY date DESC LIMIT 30", conn)
    df = df.sort_values("date")  # voor grafiek in chronologische volgorde

    # Toon data tabel
    st.subheader("📅 Data Tabel")
    st.dataframe(df, use_container_width=True)

    # Grafiek
    st.subheader("📊 EUR/USD Over Tijd")
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("date:T", title="Datum"),
        y=alt.Y("eur_usd:Q", title="EUR/USD Koers"),
        tooltip=["date:T", "eur_usd:Q"]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)

except Exception as e:
    st.error(f"❌ Fout bij ophalen van data: {e}")

finally:
    conn.close()

st.markdown("""
---
👨‍💻 Gemaakt met Streamlit | Data uit Supabase PostgreSQL
""")
# python -m streamlit run app.py
