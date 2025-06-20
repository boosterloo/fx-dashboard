import streamlit as st
import pandas as pd
import plotly.express as px
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# === Load .env variables (Supabase URL + Key)
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# === Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Pagina configuratie
st.set_page_config(page_title="SPX Opties", layout="wide")
st.title("SPX Opties Analyse")

# === Data ophalen uit Supabase
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("spx_options").select("*").execute()
    df = pd.DataFrame(response.data)
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['expiration'] = pd.to_datetime(df['expiration'])
    df['PPD'] = ((df['bid'] + df['ask']) / 2) / df['days_to_exp']
    return df

df = load_data()

# === Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    selected_date = st.selectbox("Snapshot Date", sorted(df['snapshot_date'].dt.date.unique(), reverse=True))
    selected_exp = st.selectbox("Expiration Date", sorted(df['expiration'].dt.date.unique()))

# === Data filteren
filtered_df = df[
    (df['snapshot_date'].dt.date == selected_date) &
    (df['expiration'].dt.date == selected_exp)
]

# === Grafiek
if filtered_df.empty:
    st.warning("Geen data beschikbaar voor deze selectie.")
else:
    fig = px.scatter(
        filtered_df,
        x="strike",
        y="PPD",
        color="type",
        size="openInterest",
        hover_data=["contractSymbol", "impliedVolatility", "volume"],
        title=f"Premium per Dag (PPD) per Strike — {selected_date}, Exp: {selected_exp}"
    )
    fig.update_layout(height=600, xaxis_title="Strike", yaxis_title="PPD", legend_title="Optietype")
    st.plotly_chart(fig, use_container_width=True)
