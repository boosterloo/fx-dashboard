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
        return sorted(list(set(row[column] for row in response.data if row[column] is not None)))
    return []

# Fetch data in chunks
@st.cache_data(ttl=3600)
def fetch_data_in_chunks(table_name, type_optie, expiratie, strike, batch_size=500):
    offset = 0
    all_data = []
    while True:
        response = supabase.table(table_name).select("*").eq("type", type_optie).eq("expiration", str(expiratie)).eq("strike", strike).range(offset, offset + batch_size - 1).execute()
        if not response.data:
            break
        all_data.extend(response.data)
        offset += batch_size
    if all_data:
        df = pd.DataFrame(all_data)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce")
        return df.sort_values("snapshot_date")
    return pd.DataFrame()

# Sidebar filters (shared)
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"])
expiraties = get_unique_values("spx_options2", "expiration")
expiratie = st.sidebar.selectbox("Expiratiedatum", expiraties)
strikes = get_unique_values("spx_options2", "strike")
strike = st.sidebar.selectbox("Strike", strikes)

# Fetch data
df_filtered = fetch_data_in_chunks("spx_options2", type_optie, expiratie, strike)

# Tabs for different views
tab1, tab2 = st.tabs(["PPD per Peildatum", "PPD per Days to Maturity"])

with tab1:
    st.header("PPD per Peildatum")
    if not df_filtered.empty:
        st.write("Aantal peildata:", len(df_filtered))
        chart1 = alt.Chart(df_filtered).mark_line(point=True).encode(
            x=alt.X("snapshot_date:T", title="Peildatum"),
            y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
            tooltip=["snapshot_date", "ppd", "last_price", "bid", "ask"]
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
    snapshot_date = st.selectbox("Peildatum", sorted(snapshot_dates), key="snapshot_date_tab2")
    if not df_filtered.empty:
        # Filter for selected snapshot date
        df_maturity = df_filtered[df_filtered["snapshot_date"] == snapshot_date].copy()
        # Calculate days to maturity
        df_maturity["days_to_maturity"] = (df_maturity["expiration"] - pd.to_datetime(snapshot_date)).dt.days
        df_maturity["ppd_per_day_to_maturity"] = df_maturity["ppd"] / df_maturity["days_to_maturity"].replace(0, 1)  # Avoid division by zero

        st.write("Aantal peildata:", len(df_maturity))
        chart2 = alt.Chart(df_maturity).mark_line(point=True).encode(
            x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity"),
            y=alt.Y("ppd_per_day_to_maturity:Q", title="PPD per Dag tot Maturity"),
            tooltip=["snapshot_date", "days_to_maturity", "ppd_per_day_to_maturity", "strike"]
        ).interactive().properties(
            title=f"PPD per Dag tot Maturity — {type_optie.upper()} {strike} exp. {expiratie}",
            height=400
        )
        st.altair_chart(chart2, use_container_width=True)
        # Suggestie voor gunstige maturity
        if not df_maturity["ppd_per_day_to_maturity"].empty:
            max_ppd_per_day = df_maturity["ppd_per_day_to_maturity"].max()
            best_maturity = df_maturity.loc[df_maturity["ppd_per_day_to_maturity"].idxmax(), "days_to_maturity"]
            st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD per dag: {max_ppd_per_day:.4f})")
    else:
        st.write("Geen data gevonden voor de geselecteerde filters.")