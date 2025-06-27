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

# Fetch unique values for filters with error handling
@st.cache_data(ttl=3600)
def get_unique_values(table_name, column):
    response = supabase.table(table_name).select(column).execute()
    if response.data:
        values = [row[column] for row in response.data if row[column] is not None]
        st.write(f"Debug - {column} raw values: {values[:10]}")
        try:
            if column == "expiration" or column == "snapshot_date":
                return sorted(values, key=lambda x: pd.to_datetime(x))
            elif column == "strike":
                # Safe conversion to float, filter out invalid values, round to integer
                valid_strikes = [int(float(x)) for x in values if isinstance(x, (int, float, str)) and str(x).replace('.', '').replace('-', '').isdigit()]
                return sorted(list(set(valid_strikes))) if valid_strikes else [0]  # Unique integers
            else:
                return sorted(values, key=lambda x: float(x) if isinstance(x, (int, float, str)) and str(x).replace('.', '').replace('-', '').isdigit() else 0)
        except Exception as e:
            st.write(f"Debug - Error processing {column} values: {e}")
            return values  # Fallback to raw values if conversion fails
    return []

# Fetch data in chunks with filters
@st.cache_data(ttl=3600)
def fetch_filtered_data(table_name, type_optie=None, snapshot_dates=None, strike=None, batch_size=1000):
    offset = 0
    all_data = []
    query = supabase.table(table_name).select("*")
    if type_optie:
        query = query.eq("type", type_optie)
    if snapshot_dates and len(snapshot_dates) > 0:
        query = query.in_("snapshot_date", [str(s) for s in snapshot_dates])
    if strike is not None:
        query = query.eq("strike", int(strike))  # Use integer for strike
    while True:
        response = query.range(offset, offset + batch_size - 1).execute()
        if not response.data:
            break
        all_data.extend(response.data)
        offset += batch_size
    if all_data:
        df = pd.DataFrame(all_data)
        st.write("Debug - Fetched data shape:", df.shape)
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
        df["expiration"] = pd.to_datetime(df["expiration"], utc=True, errors="coerce")
        return df.sort_values("snapshot_date")
    st.write("Debug - No data fetched. Check filters or Supabase connection.")
    return pd.DataFrame()

# Sidebar filters
st.sidebar.header("🔍 Filters voor PPD per Days to Maturity")
type_optie = st.sidebar.selectbox("Type optie (Put/Call)", ["call", "put"], index=1)  # Default to "put"
snapshot_dates = get_unique_values("spx_options2", "snapshot_date")
if snapshot_dates:
    snapshot_dates_sorted = sorted(snapshot_dates, key=lambda x: pd.to_datetime(x), reverse=True)
    selected_snapshot_dates = st.sidebar.multiselect("Selecteer Peildatum(s)", snapshot_dates_sorted, default=[snapshot_dates_sorted[0]])  # Default to most recent
else:
    selected_snapshot_dates = []
    st.sidebar.write("Geen peildata beschikbaar.")
strikes = get_unique_values("spx_options2", "strike")
if strikes and len(strikes) > 0:
    min_strike = min(strikes)
    max_strike = max(strikes)
    strike = st.sidebar.slider("Strike", min_value=min_strike, max_value=max_strike, value=5500, step=1)  # Default 5500, integer step
    st.sidebar.write(f"Debug - Selected strike: {strike}")  # Debug to confirm filter
else:
    strike = 5500  # Default if no valid strikes
    st.sidebar.write("Debug - No valid strikes found, using default: 5500")

# Fetch data with filters
df_all_data = fetch_filtered_data("spx_options2", type_optie, selected_snapshot_dates, strike)

st.header("PPD per Days to Maturity")
if not df_all_data.empty:
    df_maturity = df_all_data.copy()
    
    df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
    df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]  # Only filter out invalid days
    df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)
    
    # Group by snapshot_date to ensure unique lines
    df_maturity = df_maturity.groupby(["snapshot_date", "days_to_maturity"]).agg({"ppd": "mean", "strike": "first", "bid": "first", "expiration": "first"}).reset_index()
    
    # Main chart (full range) with increased Y-axis space and colored lines
    chart2_main = alt.Chart(df_maturity).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        color=alt.Color("snapshot_date:T", title="Peildatum", scale=alt.Scale(scheme="category10")),  # Categorical color scheme
        tooltip=["snapshot_date", "days_to_maturity", "ppd", "strike"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity (Overzicht) — {type_optie.upper()} | Strike {strike}",
        height=700  # Further increased height for more Y-axis space
    )
    st.altair_chart(chart2_main, use_container_width=True)
    
    # Second chart for adjustable range with colored lines
    max_days = st.sidebar.slider("Max Days to Maturity (Tweede Grafiek)", 1, int(df_maturity["days_to_maturity"].max()) if not df_maturity["days_to_maturity"].empty else 21, 21)
    df_short_term = df_maturity[df_maturity["days_to_maturity"] <= max_days]
    if not df_short_term.empty:
        chart2_short = alt.Chart(df_short_term).mark_line(point=True).encode(
            x=alt.X("days_to_maturity:Q", title=f"Dagen tot Maturity (0-{max_days})", sort=None),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
            color=alt.Color("snapshot_date:T", title="Peildatum", scale=alt.Scale(scheme="category10")),  # Categorical color scheme
            tooltip=["snapshot_date", "days_to_maturity", "ppd", "strike"]
        ).interactive().properties(
            title=f"PPD per Dag tot Maturity (0-{max_days} dagen)",
            height=400
        )
        st.altair_chart(chart2_short, use_container_width=True)
    else:
        st.write(f"Geen data beschikbaar voor dagen tot maturity ≤ {max_days}.")
    
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
    st.write("Geen data gevonden voor de geselecteerde filters. Debug: Check Supabase data or filter values.")