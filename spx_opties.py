import streamlit as st
import pandas as pd
import plotly.express as px
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pathlib

# === Load .env
env_path = pathlib.Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Titel
st.title("📈 SPX Opties: PPD-verloop per Strike")

# === Data ophalen
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("spx_options").select("*").execute()
    df = pd.DataFrame(response.data)
    df.columns = [col.lower() for col in df.columns]
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['expiration'] = pd.to_datetime(df['expiration'])
    df['ppd'] = ((df['bid'] + df['ask']) / 2) / df['days_to_exp']
    return df

df = load_data()

# === Sidebar filters ===
with st.sidebar:
    st.header("🔎 Filter")
    option_type = st.selectbox("Type optie", sorted(df["type"].unique()))
    expiration = st.selectbox("Expiratiedatum", sorted(df["expiration"].dt.date.unique()))
    
    # Alleen strikes tonen die passen bij type+expiry
    strikes = df[
        (df["type"] == option_type) &
        (df["expiration"].dt.date == expiration)
    ]["strike"].unique()
    strike = st.selectbox("Strike", sorted(strikes))

# === Filter dataset op selectie
filtered_df = df[
    (df["type"] == option_type) &
    (df["expiration"].dt.date == expiration) &
    (df["strike"] == strike)
].sort_values("snapshot_date")

if filtered_df.empty:
    st.warning("⚠️ Geen data gevonden voor deze combinatie.")
else:
    fig = px.line(
        filtered_df,
        x="snapshot_date",
        y="ppd",
        markers=True,
        title=f"PPD-verloop — {option_type.upper()} {strike} exp. {expiration}"
    )
    fig.update_layout(
        xaxis_title="Peildatum",
        yaxis_title="Premium per dag (PPD)",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(filtered_df[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]])
