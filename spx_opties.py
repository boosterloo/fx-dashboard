import streamlit as st
import pandas as pd
import plotly.express as px
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pathlib

# === .env inladen
env_path = pathlib.Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# === Supabase client aanmaken
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Pagina setup
st.title("📈 SPX Opties Analyse")
st.markdown("Visualisatie van premium per dag (PPD) per strike")

# === Data ophalen
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("spx_options").select("*").execute()
    df = pd.DataFrame(response.data)
    
    # Zet kolomnamen naar snake_case voor consistentie
    df.columns = [col.lower() for col in df.columns]

    # Datums goed zetten
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['expiration'] = pd.to_datetime(df['expiration'])

    # Bereken Premium per Dag (PPD)
    df['PPD'] = ((df['bid'] + df['ask']) / 2) / df['days_to_exp']

    return df

df = load_data()

# === Sidebar filters
with st.sidebar:
    st.header("📅 Filters")
    date_options = sorted(df['snapshot_date'].dt.date.unique(), reverse=True)
    exp_options = sorted(df['expiration'].dt.date.unique())

    selected_date = st.selectbox("Snapshot Date", date_options)
    selected_exp = st.selectbox("Expiration Date", exp_options)

# === Filteren op selectie
filtered_df = df[
    (df['snapshot_date'].dt.date == selected_date) &
    (df['expiration'].dt.date == selected_exp)
]

# === Plot
if filtered_df.empty:
    st.warning("⚠️ Geen data beschikbaar voor deze selectie.")
else:
    fig = px.scatter(
        filtered_df,
        x="strike",
        y="PPD",
        color="type",
        size="open_interest",
        hover_data=["contract_symbol", "implied_volatility", "volume"],
        title=f"PPD per Strike — Snapshot: {selected_date}, Exp: {selected_exp}"
    )
    fig.update_layout(
        height=600,
        xaxis_title="Strike",
        yaxis_title="Premium per Dag (PPD)",
        legend_title="Type Optie"
    )
    st.plotly_chart(fig, use_container_width=True)
