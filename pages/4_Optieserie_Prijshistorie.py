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

# Fetch data for specific filters in chunks
@st.cache_data(ttl=3600)
def fetch_filtered_option_data(table_name, type_optie=None, expiration=None, strike=None, batch_size=1000):
    offset = 0
    all_data = []
    while True:
        try:
            query = supabase.table(table_name).select("snapshot_date, bid, ask, lastPrice, impliedVolatility, type, expiration, strike").range(offset, offset + batch_size - 1)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                if (type_optie is None or row.get("type") == type_optie) and \
                   (expiration is None or row.get("expiration") == expiration) and \
                   (strike is None or row.get("strike") == strike):
                    all_data.append(row)
            offset += batch_size
        except Exception as e:
            st.error(f"Fout bij ophalen van data: {e}")
            break
    df = pd.DataFrame(all_data)
    if not df.empty and "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
        df = df.sort_values("snapshot_date")
    return df

st.title("📈 Prijsontwikkeling van een Optieserie")

# Sidebar filters
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=0)
expiration_input = st.sidebar.text_input("Expiratiedatum (YYYY-MM-DD)")
expiration = expiration_input if expiration_input else None
strike_input = st.sidebar.text_input("Strike (bijv. 5500)")
strike = int(strike_input) if strike_input and strike_input.isdigit() else None

# Fetch data based on filters
df = fetch_filtered_option_data("spx_options2", type_optie, expiration, strike)

if df.empty:
    st.error("Geen data gevonden voor de opgegeven filters.")
    st.stop()

# Plot line charts
st.subheader("Prijsontwikkeling van de geselecteerde Optieserie")

chart = alt.Chart(df).transform_fold(
    ["bid", "ask", "lastPrice"],
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
if "impliedVolatility" in df.columns and df["impliedVolatility"].notna().any():
    st.subheader("Implied Volatility (IV)")
    iv_chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("impliedVolatility:Q", title="IV"),
        tooltip=["snapshot_date:T", "impliedVolatility:Q"]
    ).properties(height=300)

    st.altair_chart(iv_chart, use_container_width=True)

# Debug info
st.write("Aantal datapunten:", len(df))
st.write("Data voorbeeld:")
st.dataframe(df.head())
