import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os
from datetime import datetime, timedelta

# Set page config
st.set_page_config(page_title="Prijsontwikkeling van een Optieserie", layout="wide")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Haal unieke expiraties en strikes op in batches
@st.cache_data(ttl=3600)
def get_unique_values_chunked(table_name, column, batch_size=1000):
    offset = 0
    all_values = set()
    while True:
        try:
            query = supabase.table(table_name).select(column).range(offset, offset + batch_size - 1)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                if column in row:
                    all_values.add(row[column])
            offset += batch_size
        except Exception as e:
            st.warning(f"Fout bij ophalen van waarden voor {column}: {e}")
            break
    return sorted(all_values)

# Fetch data for specific filters in chunks
@st.cache_data(ttl=3600)
def fetch_filtered_option_data(table_name, type_optie=None, expiration=None, strikes=None, batch_size=1000):
    offset = 0
    all_data = []
    while True:
        try:
            query = supabase.table(table_name).select("snapshot_date, bid, ask, last_price, implied_volatility, underlying_price, vix, type, expiration, strike, ppd").range(offset, offset + batch_size - 1)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                if (type_optie is None or row.get("type") == type_optie) and \
                   (expiration is None or row.get("expiration") == expiration) and \
                   (strikes is None or row.get("strike") in strikes):
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

st.title("\U0001F4C8 Prijsontwikkeling van een Optieserie")

# Sidebar filters
st.sidebar.header("\U0001F50D Filters")
defaultexp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# Haal beschikbare expiraties en strikes op
expirations = get_unique_values_chunked("spx_options2", "expiration")
strikes = get_unique_values_chunked("spx_options2", "strike")

# Filters
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=1)
expiration = st.sidebar.selectbox("Expiratiedatum", expirations, index=0 if defaultexp not in expirations else expirations.index(defaultexp)) if expirations else None
selected_strikes = st.sidebar.multiselect("Strike(s) (bijv. 5700)", strikes, default=[5700]) if strikes else []

# Countdown tot expiratie
if expiration:
    days_to_exp = (pd.to_datetime(expiration) - datetime.now()).days
    st.sidebar.metric("Dagen tot expiratie", days_to_exp)

# Fetch data based on filters
df = fetch_filtered_option_data("spx_options2", type_optie, expiration, selected_strikes)

if df.empty:
    st.error("Geen data gevonden voor de opgegeven filters.")
    st.stop()

# Format datum
df["formatted_date"] = pd.to_datetime(df["snapshot_date"]).dt.strftime("%Y-%m-%d")

# Bereken aanvullende metrics
underlying = df["underlying_price"].iloc[-1] if "underlying_price" in df.columns else None

df["intrinsieke_waarde"] = df.apply(lambda row: max(0, row["strike"] - row["underlying_price"]) if row["type"] == "put" else max(0, row["underlying_price"] - row["strike"]), axis=1)
df["tijdswaarde"] = df["last_price"] - df["intrinsieke_waarde"]
df["ppd/tijdswaarde"] = df["ppd"] / df["tijdswaarde"].replace(0, pd.NA)
df["iv/vix"] = df["implied_volatility"] / df["vix"].replace(0, pd.NA)

# Export knop
st.download_button("📥 Download CSV", df.to_csv(index=False), "optiedata.csv")
