import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Pagina-instellingen
st.set_page_config(page_title="📈 Optieserie Prijsontwikkeling", layout="wide")

# Supabase-configuratie ophalen uit omgevingsvariabelen
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Functie om unieke waardes op te halen
@st.cache_data(ttl=3600)
def get_unique_values(table_name, column):
    response = supabase.table(table_name).select(f"{column}").execute()
    if response.data:
        values = [row[column] for row in response.data if row[column] is not None]
        return sorted(set(values))
    return []

# Data ophalen voor gekozen optieserie
@st.cache_data(ttl=3600)
def fetch_option_data(contract_symbol):
    all_data = []
    offset = 0
    batch_size = 1000
    while True:
        query = supabase.table("spx_options2").select("snapshot_date, bid, ask, lastPrice").eq("contractSymbol", contract_symbol).range(offset, offset + batch_size - 1)
        response = query.execute()
        if not response.data:
            break
        all_data.extend(response.data)
        offset += batch_size
    if all_data:
        df = pd.DataFrame(all_data)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
        return df.sort_values("snapshot_date")
    return pd.DataFrame()

st.header("📈 Prijsontwikkeling van een Optieserie")

contract_symbols = get_unique_values("spx_options2", "contractSymbol")
if contract_symbols:
    default_contract = contract_symbols[0] if "SPXW250701P05550000" not in contract_symbols else "SPXW250701P05550000"
    selected_contract = st.selectbox("Kies een optieserie (contractSymbol)", contract_symbols, index=contract_symbols.index(default_contract))
    df_option = fetch_option_data(selected_contract)

    if not df_option.empty:
        base = alt.Chart(df_option).encode(
            x=alt.X("snapshot_date:T", title="Peildatum"),
            tooltip=["snapshot_date:T", "bid", "ask", "lastPrice"]
        )

        line_bid = base.mark_line(color="#1f77b4", point=True).encode(y=alt.Y("bid:Q", title="Optieprijs (Bid)"))
        line_ask = base.mark_line(color="#ff7f0e", point=True).encode(y=alt.Y("ask:Q"))
        line_last = base.mark_line(color="#2ca02c", point=True).encode(y=alt.Y("lastPrice:Q"))

        chart = alt.layer(line_bid, line_ask, line_last).resolve_scale(y='independent').properties(
            title=f"Prijsontwikkeling voor {selected_contract}",
            height=500
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Geen data beschikbaar voor de geselecteerde optieserie.")
else:
    st.warning("Geen contractSymbol-waarden beschikbaar in de database.")
