import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

# === Omgeving laden ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Navigatie ===
st.sidebar.header("🔍 Navigatie")
section = st.sidebar.radio(
    "Kies onderdeel:",
    ["SPX Opties", "FX Rates", "SP500 Index", "AEX Index", "Macro", "Commodity", "Sectoren", "Yield Curve"],
    index=0
)
if section != "SPX Opties":
    st.title(f"📌 Sectie '{section}' nog in ontwikkeling")
    st.stop()

# === Titel ===
st.markdown(
    '<h1 style="text-align:center; color:#1E90FF;">📊 SPX Optie-analyse</h1>', unsafe_allow_html=True
)

# === Data ophalen ===
@st.cache_data(ttl=3600)
def load_data():
    all_data = []
    offset = 0
    limit = 1000
    while True:
        resp = supabase.table("spx_options").select("*").range(offset, offset + limit - 1).execute()
        chunk = resp.data or []
        if not chunk:
            break
        all_data.extend(chunk)
        offset += limit
    df = pd.DataFrame(all_data)
    if df.empty:
        return df
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], errors='coerce')
    df = df.dropna(subset=['snapshot_date'])
    df['ppd'] = df['last_price'] / df['days_to_exp'].replace(0, 0.01)  # fallback om deling door 0 te vermijden
    return df

df_all = load_data()
if df_all.empty:
    st.error("Geen optie-data gevonden.")
    st.stop()

# === Filters ===
st.sidebar.header("🔎 Filters")
strike_keuze = st.sidebar.selectbox("Kies strike", sorted(df_all['strike'].dropna().unique()))
expiratie_keuze = st.sidebar.selectbox("Kies expiratie", sorted(df_all['expiration'].dropna().unique()))

# === Filteren op selectie ===
df_filtered = df_all[(df_all['strike'] == strike_keuze) & (df_all['expiration'] == expiratie_keuze)]
if df_filtered.empty:
    st.warning("Geen data voor deze combinatie.")
    st.stop()

# === Grafiek PPD door de tijd ===
st.subheader("📈 Premie per Dag (PPD) door de tijd")
fig = px.line(df_filtered, x='snapshot_date', y='ppd', title="PPD (USD) door de tijd")
fig.update_layout(xaxis_title="Peildatum", yaxis_title="PPD", hovermode="x")
st.plotly_chart(fig, use_container_width=True)

# === Suggesties voor andere grafieken ===
with st.expander("📌 Andere suggesties"):
    st.markdown("""
    - 🔍 **PPD vs Strike** op een vaste datum
    - 📉 **Implied Volatility vs PPD**
    - 💰 **Totale waarde open interest** (_open_interest * last_price_)
    - 🟰 **Break-even grafiek** bij long/short combo's
    - 📊 **PPD-verhouding short/long** strategie
    """)
