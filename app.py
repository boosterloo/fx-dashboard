import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import plotly.express as px

# === 1. Omgevingsvariabelen laden ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === 2. Titel ===
st.title("💱 FX Dashboard")

# === 3. Data ophalen uit Supabase ===
@st.cache_data
def load_data():
    response = supabase.table("fx_rates").select("*").order("date", desc=False).execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# === 4. Valutaparen beschikbaar in kolommen ===
currency_columns = [col for col in df.columns if col not in ["id", "date"]]

# === 5. Gebruikerselectie ===
selected_pair = st.selectbox("Valutapaar kiezen", currency_columns, index=currency_columns.index("eur_usd") if "eur_usd" in currency_columns else 0)

# === 6. Lijngrafiek tekenen ===
fig = px.line(df, x="date", y=selected_pair, title=f"{selected_pair.upper()} Koersontwikkeling")
st.plotly_chart(fig, use_container_width=True)

# === 7. Laatste koers tonen ===
latest_value = df[selected_pair].iloc[-1]
st.metric(label=f"Laatste koers ({selected_pair.upper()})", value=f"{latest_value:.4f}")
