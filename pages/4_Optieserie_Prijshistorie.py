import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Set page config
st.set_page_config(page_title="📈 Prijsontwikkeling van een Optieserie", layout="wide")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch all filtered contract symbols in chunks
@st.cache_data(ttl=3600)
def get_filtered_contract_symbols(table_name, type_optie=None, expiration=None, strike=None, batch_size=1000):
    offset = 0
    all_symbols = set()
    st.write(f"Filtering with: type_optie={type_optie}, expiration={expiration}, strike={strike}")  # Debug
    while True:
        try:
            query = supabase.table(table_name).select("contract_symbol, type, expiration, strike").range(offset, offset + batch_size - 1)
            if type_optie:
                query = query.eq("type", type_optie)
            if expiration:
                query = query.eq("expiration", expiration)
            if strike:
                query = query.eq("strike", strike)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                symbol = row.get("contract_symbol")
                if symbol:
                    all_symbols.add(symbol)
            offset += batch_size
        except Exception as e:
            st.error(f"Fout bij ophalen van contractsymbol: {e}")
            break
    return sorted(all_symbols)

# Fetch data for a specific contract_symbol
@st.cache_data(ttl=3600)
def fetch_contract_data(table_name, contract_symbol):
    try:
        response = supabase.table(table_name).select("snapshot_date, bid, ask, last_price, implied_volatility").eq("contract_symbol", contract_symbol).order("snapshot_date").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
            return df.sort_values("snapshot_date")
    except Exception as e:
        st.error(f"Fout bij ophalen van data voor {contract_symbol}: {e}")
    return pd.DataFrame()

st.title("📈 Prijsontwikkeling van een Optieserie")

# Sidebar filters
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=1)  # Standaard op 'put' gezet
expiration_input = st.sidebar.text_input("Expiratiedatum (YYYY-MM-DD)", value="2025-06-20")
expiration = expiration_input if expiration_input else None
strike_input = st.sidebar.text_input("Strike (bijv. 617.07)", value="618")  # Aangepast naar 618 voor SPX250620P06180000
strike = float(strike_input) if strike_input and strike_input.replace('.', '').isdigit() else None

# Cache refresh button
if st.button("Vernieuw cache"):
    st.cache_data.clear()

# Select contract_symbol
contract_symbols = get_filtered_contract_symbols("spx_options2", type_optie, expiration, strike)
if not contract_symbols:
    st.error("Geen optieseries gevonden voor de opgegeven filters.")
    # Debug: Toon eerste rijen om te controleren
    response = supabase.table("spx_options2").select("contract_symbol, type, expiration, strike").limit(5).execute()
    st.write("Eerste 5 rijen uit tabel:", response.data)
    st.stop()

selected_symbol = st.selectbox("Selecteer een optieserie (contract_symbol):", contract_symbols)

# Fetch data
df = fetch_contract_data("spx_options2", selected_symbol)

if df.empty:
    st.warning("Geen data beschikbaar voor de geselecteerde optieserie.")
    st.stop()

# Plot line charts
st.subheader(f"Prijsontwikkeling voor: {selected_symbol}")

chart = alt.Chart(df).transform_fold(
    ["bid", "ask", "last_price"],  # Aangepast naar last_price
    as_=["Type", "Prijs"]
).mark_line(point=True).encode(
    x=alt.X("snapshot_date:T", title="Peildatum"),
    y=alt.Y("Prijs:Q", title="Optieprijs"),
    color=alt.Color("Type:N", title="Prijssoort", scale=alt.Scale(scheme="category10")),
    tooltip=["snapshot_date:T", "Type:N", "Prijs:Q"]
).properties(
    height=500,
    title="Bid, Ask en LastPrice door de tijd"
)

st.altair_chart(chart, use_container_width=True)

# Toon ook implied volatility indien beschikbaar
if "implied_volatility" in df.columns and df["implied_volatility"].notna().any():  # Aangepast naar implied_volatility
    st.subheader("Implied Volatility (IV)")
    iv_chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("implied_volatility:Q", title="IV"),  # Aangepast naar implied_volatility
        tooltip=["snapshot_date:T", "implied_volatility:Q"]
    ).properties(height=300)

    st.altair_chart(iv_chart, use_container_width=True)

# Debug info
st.write("Aantal datapunten:", len(df))
st.write("Data voorbeeld:")
st.dataframe(df.head())