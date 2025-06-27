import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Set page config
st.set_page_config(page_title="SPX Opties - PPD per Peildatum", layout="wide")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch unique values for filters
@st.cache_data(ttl=3600)
def get_unique_values(table_name, column):
    response = supabase.table(table_name).select(column).execute()
    if response.data:
        values = list(set(row[column] for row in response.data if row[column] is not None))
        st.write(f"Debug - {column} values: {values[:10]}")
        if column == "expiration" or column == "snapshot_date":
            return sorted(values, key=lambda x: pd.to_datetime(x))
        else:
            return sorted(values, key=lambda x: float(x) if isinstance(x, (int, float, str)) and x.replace('.', '').replace('-', '').isdigit() else 0)
    return []

# Fetch all data in chunks with optional filter
@st.cache_data(ttl=3600)
def fetch_all_data(table_name, type_optie=None, batch_size=1000):
    offset = 0
    all_data = []
    query = supabase.table(table_name).select("*")
    if type_optie:
        query = query.eq("type", type_optie)
    while True:
        response = query.range(offset, offset + batch_size - 1).execute()
        if not response.data:
            break
        all_data.extend(response.data)
        offset += batch_size
    if all_data:
        df = pd.DataFrame(all_data)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
        df["expiration"] = pd.to_datetime(df["expiration"], utc=True, errors="coerce")
        return df.sort_values("snapshot_date")
    return pd.DataFrame()

# Sidebar filter
st.sidebar.header("🔍 Filters voor PPD per Peildatum")
type_optie = st.sidebar.selectbox("Type optie (Put/Call)", ["call", "put", None], index=2)  # None als default

# Fetch data
df_all_data = fetch_all_data("spx_options2", type_optie)

st.header("PPD per Peildatum")
if not df_all_data.empty:
    df_filtered_tab1 = df_all_data.copy()
    df_filtered_tab1["days_to_maturity"] = (df_filtered_tab1["expiration"] - df_filtered_tab1["snapshot_date"]).dt.days
    df_filtered_tab1 = df_filtered_tab1[df_filtered_tab1["days_to_maturity"] > 0]
    df_filtered_tab1["ppd"] = df_filtered_tab1["bid"] / df_filtered_tab1["days_to_maturity"].replace(0, 0.01)
    
    # Chart (top)
    chart1 = alt.Chart(df_filtered_tab1).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Peildatum"),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        tooltip=["snapshot_date", "ppd", "bid", "ask", "days_to_maturity"]
    ).interactive().properties(
        title="PPD-verloop — Alle Data" + (f" | {type_optie.upper()}" if type_optie else ""),
        height=400
    )
    st.altair_chart(chart1, use_container_width=True)
    
    # Tables and debug info (bottom)
    st.write("Aantal rijen na filtering:", len(df_filtered_tab1))
    invalid_ppd = df_filtered_tab1["ppd"].isna().sum()
    st.write(f"Aantal rijen met ongeldige PPD (NaN): {invalid_ppd}")
    st.write("Gefilterde data:", df_filtered_tab1)
else:
    st.write("Geen data gevonden in Supabase.")

# Move Strikes list to the bottom of the page
strikes = get_unique_values("spx_options2", "strike")
st.write("Debug - Strikes list:", strikes)