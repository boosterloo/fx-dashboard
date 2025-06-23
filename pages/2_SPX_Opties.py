import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Set page config
st.set_page_config(page_title="SPX Opties", layout="wide")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cache data fetch
@st.cache_data(ttl=3600)  # Cache voor 1 uur
def fetch_data(table_name, type_optie):
    response = supabase.table(table_name).select("*").eq("type", type_optie).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce").dt.date
        return df
    return pd.DataFrame()

# Load data
table_name = "spx_options2"
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"])

df = fetch_data(table_name, type_optie)

# Apply additional filters
beschikbare_expiraties = sorted(df["expiration"].dropna().unique())
expiratie = st.sidebar.selectbox("Expiratiedatum", beschikbare_expiraties)
df_expiration = df[df["expiration"] == expiratie]

beschikbare_strikes = sorted(df_expiration["strike"].dropna().unique())
strike = st.sidebar.selectbox("Strike", beschikbare_strikes)
df_filtered = df_expiration[df_expiration["strike"] == strike].sort_values("snapshot_date")

st.write("Gefilterde rijen:", len(df_filtered))  # Debug: Toon aantal gefilterde rijen

if not df_filtered.empty:
    st.dataframe(df_filtered[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]])

    # Chart
    chart = alt.Chart(df_filtered).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
        tooltip=["snapshot_date", "ppd", "last_price", "bid", "ask"]
    ).interactive().properties(
        title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}",
        height=400
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.write("Geen data gevonden voor de geselecteerde filters.")