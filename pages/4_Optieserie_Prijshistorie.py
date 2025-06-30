import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Pagina-instellingen
st.set_page_config(page_title="Optieserie Prijsontwikkeling", layout="wide")

# Supabase-client initialiseren
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=3600)
def get_unique_values(table_name, column):
    response = supabase.table(table_name).select(column).execute()
    if response.data:
        return sorted(set(row[column] for row in response.data if row[column] is not None))
    return []

@st.cache_data(ttl=3600)
def fetch_option_series_data(table_name, contract_symbol):
    response = supabase.table(table_name).select("*").eq("contractSymbol", contract_symbol).order("snapshot_date").execute()
    if response.data:
        df = pd.DataFrame(response.data)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True)
        return df.sort_values("snapshot_date")
    return pd.DataFrame()

st.title("📈 Optieserie Prijsontwikkeling")

contract_symbols = get_unique_values("spx_options2", "contractSymbol")
selected_symbol = st.selectbox("Selecteer Optieserie (contractSymbol)", contract_symbols)

df = fetch_option_series_data("spx_options2", selected_symbol)

if not df.empty:
    st.write(f"Toon prijsontwikkeling voor: `{selected_symbol}`")

    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("bid:Q", title="Bidprijs"),
        tooltip=["snapshot_date:T", "bid"]
    ).properties(
        title="Bidprijs door de tijd voor geselecteerde optieserie",
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

    st.write("Aantal observaties:", len(df))
else:
    st.warning("Geen data gevonden voor de geselecteerde optieserie.")
