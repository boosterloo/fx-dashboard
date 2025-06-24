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
        values = [row[column] for row in response.data if row[column] is not None]
        st.write(f"Debug - {column} values: {values[:10]}")  # Debug output for first 10 values
        if column == "expiration":
            # Sort expiration values as datetimes
            return sorted(values, key=lambda x: pd.to_datetime(x))
        else:
            # Sort other columns (e.g., strike) as floats
            return sorted(values, key=lambda x: float(x) if isinstance(x, (int, float, str)) and x.replace('.', '').replace('-', '').isdigit() else 0)
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

# Sidebar filters (for tab 1)
st.sidebar.header("🔍 Filters voor PPD per Peildatum")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"])
expiraties = get_unique_values("spx_options2", "expiration")
expiratie = st.sidebar.selectbox("Expiratiedatum", expiraties)
# Dynamic strike with 6000 as default, using a slider with validation
strikes = get_unique_values("spx_options2", "strike")
if strikes and all(isinstance(s, (int, float)) for s in strikes):
    min_strike = min(strikes)
    max_strike = max(strikes)
    default_strike = 6000
    if default_strike < min_strike or default_strike > max_strike:
        default_strike = min_strike
    strike = st.sidebar.slider("Strike", min_value=min_strike, max_value=max_strike, value=default_strike, step=100)
else:
    strike = 6000  # Fallback if no valid strikes
    st.warning("Geen geldige numerieke strike-waarden gevonden. Standaardwaarde 6000 wordt gebruikt.")

# Fetch data for tab 1 with expiration filter
df_filtered_tab1 = fetch_data_in_chunks("spx_options2", type_optie, expiratie, strike)

# Fetch data for tab 2 without expiration filter
df_filtered_tab2 = fetch_data_in_chunks("spx_options2", type_optie, None, strike)

# Tabs for different views
tab1, tab2 = st.tabs(["PPD per Peildatum", "PPD per Days to Maturity"])

with tab1:
    st.header("PPD per Peildatum")
    if not df_filtered_tab1.empty:
        # Calculate days to maturity
        df_filtered_tab1["days_to_maturity"] = (df_filtered_tab1["expiration"] - df_filtered_tab1["snapshot_date"]).dt.days
        df_filtered_tab1 = df_filtered_tab1[df_filtered_tab1["days_to_maturity"] > 0]
        # Calculate PPD using bid and prevent division by zero
        df_filtered_tab1["ppd"] = df_filtered_tab1["bid"] / df_filtered_tab1["days_to_maturity"].replace(0, 0.01)
        
        # Chart
        chart1 = alt.Chart(df_filtered_tab1).mark_line(point=True).encode(
            x=alt.X("snapshot_date:T", title="Peildatum"),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)"),
            tooltip=["snapshot_date", "ppd", "bid", "ask"]
        ).interactive().properties(
            title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}",
            height=400
        )
        st.altair_chart(chart1, use_container_width=True)
        
        # Move table/data info below the chart
        st.write("Aantal peildata:", len(df_filtered_tab1))
        st.write("Gefilterde data:", df_filtered_tab1)
    else:
        st.write("Geen data gevonden voor de geselecteerde filters.")

with tab2:
    st.header("PPD per Days to Maturity")
    snapshot_dates = get_unique_values("spx_options2", "snapshot_date")
    selected_snapshot_date = st.selectbox("Selecteer Peildatum", sorted(snapshot_dates), key="snapshot_date_tab2")
    # Add adjustable Days to Maturity filter with default 30
    days_to_maturity_filter = st.slider("Dagen tot Maturity", min_value=1, max_value=100, value=30, step=1)
    if not df_filtered_tab2.empty:
        # Filter for selected snapshot date
        df_maturity = df_filtered_tab2[df_filtered_tab2["snapshot_date"] == pd.to_datetime(selected_snapshot_date, utc=True)].copy()
        
        # Debug: Show the filtered dataframe
        st.write("Gefilterde data:", df_maturity)

        # Check for valid datetime values
        if df_maturity["expiration"].isna().any() or df_maturity["snapshot_date"].isna().any():
            st.write("Waarschuwing: Sommige datums zijn ongeldig. Controleer de data.")
        else:
            # Ensure both columns are in datetime format with UTC
            df_maturity["expiration"] = pd.to_datetime(df_maturity["expiration"], utc=True)
            df_maturity["snapshot_date"] = pd.to_datetime(df_maturity["snapshot_date"], utc=True)
            
            # Calculate days to maturity for all expirations
            df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
            # Filter out invalid or negative days and apply Days to Maturity filter with tolerance
            tolerance = 5
            df_maturity = df_maturity[
                (df_maturity["days_to_maturity"] > 0) &
                (df_maturity["days_to_maturity"] >= days_to_maturity_filter - tolerance) &
                (df_maturity["days_to_maturity"] <= days_to_maturity_filter + tolerance)
            ]
            # Calculate PPD using bid and prevent division by zero
            df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)

            st.write("Aantal peildata na filtering:", len(df_maturity))
            # Chart showing development over days to maturity with auto-scaled Y-axis
            chart2 = alt.Chart(df_maturity).mark_line(point=True).encode(
                x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
                y=alt.Y("ppd:Q", title="Premium per Dag (PPD)"),
                tooltip=["expiration", "days_to_maturity", "ppd", "strike"]
            ).interactive().properties(
                title=f"PPD per Dag tot Maturity — {type_optie.upper()} {strike}",
                height=400
            )
            st.altair_chart(chart2, use_container_width=True)
            # Suggestie voor gunstige maturity
            if not df_maturity["ppd"].empty:
                max_ppd = df_maturity["ppd"].max()
                best_maturity = df_maturity.loc[df_maturity["ppd"].idxmax(), "days_to_maturity"]
                st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")
    else:
        st.write("Geen data gevonden voor de geselecteerde filters.")