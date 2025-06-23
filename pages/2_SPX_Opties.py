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

# Fetch data
table_name = "spx_options2"
response = supabase.table(table_name).select("*").execute()

if response.data is None:
    st.error(f"Fout bij ophalen data: {response}")
    st.stop()

df = pd.DataFrame(response.data)
st.write("Alle geladen data:", df)  # Debug: Toon alle geladen data

# Convert columns
df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce").dt.date

# Sidebar filters
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", sorted(df["type"].dropna().unique()))
df_type = df[df["type"] == type_optie]

beschikbare_expiraties = sorted(df_type["expiration"].dropna().unique())
expiratie = st.sidebar.selectbox("Expiratiedatum", beschikbare_expiraties)
df_expiration = df_type[df_type["expiration"] == expiratie]

beschikbare_strikes = sorted(df_expiration["strike"].dropna().unique())
strike = st.sidebar.selectbox("Strike", beschikbare_strikes)

# Filter data
df_filtered = df_expiration[df_expiration["strike"] == strike].sort_values("snapshot_date")
st.write("Gefilterde data:", df_filtered)  # Debug: Toon gefilterde data

# Display
st.title("📈 SPX Opties: PPD-verloop per Strike")
st.markdown(f"🔍 {len(df_filtered)} rijen gevonden voor {type_optie.upper()} {strike} exp. {expiratie}")

st.dataframe(df_filtered[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]])

chart = alt.Chart(df_filtered).mark_line(point=True).encode(
    x=alt.X("snapshot_date:T", title="Peildatum"),
    y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
    tooltip=["snapshot_date", "ppd", "last_price", "bid", "ask"]
).interactive().properties(
    title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}",
    height=400
)

st.altair_chart(chart, use_container_width=True)