import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

st.set_page_config(page_title="📈 Prijsontwikkeling van een Optieserie", layout="wide")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=3600)
def get_filtered_contract_symbols(table_name, type_optie=None, expiration=None, strike=None, batch_size=1000):
    offset = 0
    all_symbols = set()
    st.write(f"Filtering with: type_optie={type_optie}, expiration={expiration}, strike={strike}")
    while True:
        try:
            query = supabase.table(table_name).select("symbol, type, expiration, strike").range(offset, offset + batch_size - 1)
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
                symbol = row.get("symbol")
                if symbol:
                    all_symbols.add(symbol)
            offset += batch_size
        except Exception as e:
            st.error(f"Fout bij ophalen van contractsymbol: {e}")
            break
    return sorted(all_symbols)

@st.cache_data(ttl=3600)
def fetch_contract_data(table_name, contract_symbol):
    try:
        response = supabase.table(table_name).select("snapshot_date, bid, ask, lastPrice, impliedVolatility").eq("symbol", contract_symbol).order("snapshot_date").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
            return df.sort_values("snapshot_date")
    except Exception as e:
        st.error(f"Fout bij ophalen van data voor {contract_symbol}: {e}")
    return pd.DataFrame()

st.title("📈 Prijsontwikkeling van een Optieserie")

st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=0)
expiration_input = st.sidebar.text_input("Expiratiedatum (YYYY-MM-DD)", value="2025-07-31")
expiration = expiration_input if expiration_input else None
strike_input = st.sidebar.text_input("Strike (bijv. 5500)", value="5500")
strike = int(strike_input) if strike_input and strike_input.isdigit() else None

if st.button("Vernieuw cache"):
    st.cache_data.clear()

contract_symbols = get_filtered_contract_symbols("spx_options2", type_optie, expiration, strike)
if not contract_symbols:
    st.error("Geen optieseries gevonden voor de opgegeven filters.")
    st.stop()

selected_symbol = st.selectbox("Selecteer een optieserie (contractsymbol):", contract_symbols)

df = fetch_contract_data("spx_options2", selected_symbol)

if df.empty:
    st.warning("Geen data beschikbaar voor de geselecteerde optieserie.")
    st.stop()

st.subheader(f"Prijsontwikkeling voor: {selected_symbol}")

chart = alt.Chart(df).transform_fold(
    ["bid", "ask", "lastPrice"],
    as_=["Type", "Prijs"]
).mark_line(point=True).encode(
    x=alt.X("snapshot_date:T", title="Peildatum"),
    y=alt.Y("Prijs:Q", title="Optieprijs"),
    color=alt.Color("Type:N", title="Prijssoort", scale=alt.Scale(scheme="category10")),
    tooltip=["snapshot_date:T", "Type:N", "Prijs:Q"]
).properties(height=500, title="Bid, Ask en LastPrice door de tijd")

st.altair_chart(chart, use_container_width=True)

if "impliedVolatility" in df.columns and df["impliedVolatility"].notna().any():
    st.subheader("Implied Volatility (IV)")
    iv_chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("impliedVolatility:Q", title="IV"),
        tooltip=["snapshot_date:T", "impliedVolatility:Q"]
    ).properties(height=300)
    st.altair_chart(iv_chart, use_container_width=True)

st.write("Aantal datapunten:", len(df))
st.write("Data voorbeeld:")
st.dataframe(df.head())