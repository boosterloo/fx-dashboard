import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

# Set page config
st.set_page_config(page_title="SPX Opties - PPD per Days to Maturity", layout="wide")

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

# Fetch all data in chunks
@st.cache_data(ttl=3600)
def fetch_all_data(table_name, type_optie=None, snapshot_date=None, strike=None, batch_size=1000):
    offset = 0
    all_data = []
    query = supabase.table(table_name).select("*")
    if type_optie:
        query = query.eq("type", type_optie)
    if snapshot_date:
        query = query.eq("snapshot_date", str(snapshot_date))
    if strike:
        query = query.eq("strike", strike)
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

# Sidebar filters
st.sidebar.header("🔍 Filters voor PPD per Days to Maturity")
type_optie = st.sidebar.selectbox("Type optie (Put/Call)", ["call", "put"])
snapshot_dates = get_unique_values("spx_options2", "snapshot_date")
selected_snapshot_date = st.sidebar.selectbox("Selecteer Peildatum", snapshot_dates) if snapshot_dates else None
strikes = get_unique_values("spx_options2", "strike")
strike = st.sidebar.slider("Strike", min_value=float(min(strikes)) if strikes else 0.0, max_value=float(max(strikes)) if strikes else 10000.0, value=6000.0, step=100.0) if strikes else 6000.0

# Fetch data with filters
df_all_data = fetch_all_data("spx_options2", type_optie, selected_snapshot_date, strike)

st.header("PPD per Days to Maturity")
if not df_all_data.empty:
    df_maturity = df_all_data.copy()
    
    df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
    df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]  # Only filter out invalid days
    df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)
    
    # Chart (top)
    chart2 = alt.Chart(df_maturity).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        tooltip=["expiration", "days_to_maturity", "ppd", "strike"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity — {selected_snapshot_date} | {type_optie.upper()} | Strike {strike}",
        height=400
    )
    st.altair_chart(chart2, use_container_width=True)
    
    # Tables and debug info (bottom)
    initial_rows = len(df_maturity)
    st.write("Aantal rijen na filtering:", initial_rows)
    invalid_ppd = df_maturity["ppd"].isna().sum()
    st.write(f"Aantal rijen met ongeldige PPD (NaN): {invalid_ppd}")
    st.write("Unieke days_to_maturity waarden:", sorted(df_maturity["days_to_maturity"].unique()))
    st.write("Gefilterde data:", df_maturity)
    
    if not df_maturity["ppd"].empty:
        max_ppd = df_maturity["ppd"].max()
        best_maturity = df_maturity.loc[df_maturity["ppd"].idxmax(), "days_to_maturity"]
        st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")
else:
    st.write("Geen data gevonden voor de geselecteerde filters.")