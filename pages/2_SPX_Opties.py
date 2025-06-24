import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os
from datetime import timedelta

# Set page config
st.set_page_config(page_title="SPX Opties", layout="wide")

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
        values = list(set(row[column] for row in response.data if row[column] is not None))  # Ensure distinct values
        st.write(f"Debug - {column} values: {values[:10]}")  # Debug output for first 10 values
        if column == "expiration":
            return sorted(values, key=lambda x: pd.to_datetime(x))
        else:
            return sorted(values, key=lambda x: float(x) if isinstance(x, (int, float, str)) and (isinstance(x, str) and x.replace('.', '').replace('-', '').isdigit() or isinstance(x, (int, float))) else 0)
    return []

# Fetch data in chunks
@st.cache_data(ttl=3600)
def fetch_data_in_chunks(table_name, type_optie, expiratie=None, strike=None, batch_size=1000):
    offset = 0
    all_data = []
    query = supabase.table(table_name).select("*").eq("type", type_optie)
    if expiratie:
        query = query.eq("expiration", str(expiratie))
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
st.sidebar.header("🔍 Filters voor PPD per Peildatum")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"])
expiraties = get_unique_values("spx_options2", "expiration")
expiratie = st.sidebar.selectbox("Expiratiedatum", expiraties)
strikes = get_unique_values("spx_options2", "strike")
st.write("Debug - Strikes list:", strikes)
if strikes and all(isinstance(s, (int, float)) for s in strikes):
    min_strike = float(min(strikes))
    max_strike = float(max(strikes))
    default_strike = 6000.0
    if default_strike < min_strike or default_strike > max_strike:
        default_strike = min_strike
    strike = st.sidebar.slider("Strike", min_value=min_strike, max_value=max_strike, value=default_strike, step=100.0)
else:
    strike = 6000.0
    st.warning("Geen geldige numerieke strike-waarden gevonden. Standaardwaarde 6000 wordt gebruikt.")

# Fetch data
df_filtered_tab1 = fetch_data_in_chunks("spx_options2", type_optie, expiratie, strike)
df_filtered_tab2 = fetch_data_in_chunks("spx_options2", type_optie, None, strike)

# Tabs for different views
tab1, tab2 = st.tabs(["PPD per Peildatum", "PPD per Days to Maturity"])

with tab1:
    st.header("PPD per Peildatum")
    if not df_filtered_tab1.empty:
        df_filtered_tab1["days_to_maturity"] = (df_filtered_tab1["expiration"] - df_filtered_tab1["snapshot_date"]).dt.days
        df_filtered_tab1 = df_filtered_tab1[df_filtered_tab1["days_to_maturity"] > 0]
        df_filtered_tab1["ppd"] = df_filtered_tab1["bid"] / df_filtered_tab1["days_to_maturity"].replace(0, 0.01)
        
        st.write("Aantal rijen na filtering:", len(df_filtered_tab1))
        invalid_ppd = df_filtered_tab1["ppd"].isna().sum()
        st.write(f"Aantal rijen met ongeldige PPD (NaN): {invalid_ppd}")
        
        st.write("Gefilterde data:", df_filtered_tab1)
        
        chart1 = alt.Chart(df_filtered_tab1).mark_line(point=True).encode(
            x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity"),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
            tooltip=["expiration", "ppd", "bid", "ask", "days_to_maturity"]
        ).interactive().properties(
            title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}",
            height=400
        )
        st.altair_chart(chart1, use_container_width=True)
    else:
        st.write("Geen data gevonden voor de geselecteerde filters.")

with tab2:
    st.header("PPD per Days to Maturity")
    snapshot_dates = get_unique_values("spx_options2", "snapshot_date")
    if snapshot_dates:
        snapshot_dates_sorted = sorted(snapshot_dates, key=lambda x: pd.to_datetime(x), reverse=True)
        default_snapshot = snapshot_dates_sorted[0]
        selected_snapshot_date = st.selectbox("Selecteer Peildatum", snapshot_dates_sorted, index=0, key="snapshot_date_tab2")
    else:
        selected_snapshot_date = None
        st.write("Geen peildata beschikbaar.")
    
    days_to_maturity_filter = st.slider("Dagen tot Maturity", min_value=1, max_value=100, value=30, step=1)
    if not df_filtered_tab2.empty and selected_snapshot_date:
        df_maturity = df_filtered_tab2[df_filtered_tab2["snapshot_date"] == pd.to_datetime(selected_snapshot_date, utc=True)].copy()
        
        df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
        df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]
        df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)
        
        initial_rows = len(df_maturity)
        st.write("Aantal rijen na snapshot-filter:", initial_rows)
        invalid_ppd = df_maturity["ppd"].isna().sum()
        st.write(f"Aantal rijen met ongeldige PPD (NaN): {invalid_ppd}")
        
        tolerance = 5
        df_maturity_filtered = df_maturity[
            (df_maturity["days_to_maturity"] >= days_to_maturity_filter - tolerance) &
            (df_maturity["days_to_maturity"] <= days_to_maturity_filter + tolerance)
        ]
        filtered_rows = len(df_maturity_filtered)
        st.write("Aantal rijen na dagen-filter:", filtered_rows)
        
        st.write("Gefilterde data:", df_maturity_filtered)
        
        chart2 = alt.Chart(df_maturity_filtered).mark_line(point=True).encode(
            x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
            tooltip=["expiration", "days_to_maturity", "ppd", "strike"]
        ).interactive().properties(
            title=f"PPD per Dag tot Maturity — {type_optie.upper()} {strike}",
            height=400
        )
        st.altair_chart(chart2, use_container_width=True)
        
        if not df_maturity_filtered["ppd"].empty:
            max_ppd = df_maturity_filtered["ppd"].max()
            best_maturity = df_maturity_filtered.loc[df_matury_filtered["ppd"].idxmax(), "days_to_maturity"]
            st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")
    else:
        st.write("Geen data gevonden voor de geselecteerde filters.")