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

# Unieke snapshot_dates met formatting voor dropdown
@st.cache_data(ttl=3600)
def get_unique_snapshot_dates(table_name):
    response = supabase.table(table_name).select("snapshot_date").execute()
    if response.data:
        raw_values = [row["snapshot_date"] for row in response.data if row["snapshot_date"] is not None]
        dt_values = pd.to_datetime(raw_values, utc=True, errors="coerce").dropna()
        unique_dt_values = sorted(list(set(dt_values)))
        display_values = [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in unique_dt_values]
        return display_values, unique_dt_values
    return [], []

# Ophalen van actieve strikes op basis van bid > 0.01 en gekozen snapshot_dates
@st.cache_data(ttl=3600)
def get_active_strikes(table_name, snapshot_dates=None, min_bid=0.01):
    query = supabase.table(table_name).select("strike", "snapshot_date", "bid")
    if snapshot_dates and len(snapshot_dates) > 0:
        query = query.in_("snapshot_date", [str(s) for s in snapshot_dates])
    response = query.execute()
    if response.data:
        df = pd.DataFrame(response.data)
        df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        df = df.dropna(subset=["bid", "strike"])
        df = df[df["bid"] >= min_bid]
        unique_strikes = sorted(df["strike"].unique().astype(int))
        return unique_strikes
    return []

# Ophalen van gefilterde data
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
        query = query.eq("strike", int(strike))
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
type_optie = st.sidebar.selectbox("Type optie (Put/Call)", ["call", "put"], index=1)

# Snapshot date filter
display_dates, actual_dates = get_unique_snapshot_dates("spx_options2")
if display_dates:
    selected_display_dates = st.sidebar.multiselect("Selecteer Peildatum(s)", display_dates, default=[display_dates[0]])
    selected_snapshot_dates = [actual_dates[display_dates.index(s)] for s in selected_display_dates if s in display_dates]
else:
    selected_snapshot_dates = []
    st.sidebar.write("Geen peildata beschikbaar.")

# Strike filter met alleen actieve strikes (bid > 0.01)
strikes = get_active_strikes("spx_options2", selected_snapshot_dates, min_bid=0.01)
if strikes and len(strikes) > 0:
    min_strike = min(strikes)
    max_strike = max(strikes)
    strike = st.sidebar.slider("Strike", min_value=min_strike, max_value=max_strike, value=5500, step=1)
    st.sidebar.write(f"Debug - Selected strike: {strike}")
else:
    strike = 5500
    st.sidebar.write("Debug - Geen actieve strikes gevonden, gebruik default: 5500")

# Data ophalen
df_all_data = fetch_filtered_data("spx_options2", type_optie, selected_snapshot_dates, strike)

# Hoofdsectie
st.header("PPD per Days to Maturity")
if not df_all_data.empty:
    df_maturity = df_all_data.copy()
    df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
    df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]
    df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)

    # Grafiek volledig bereik
    chart2_main = alt.Chart(df_maturity).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        color=alt.Color("snapshot_date:T", title="Peildatum", scale=alt.Scale(scheme="category10")),
        tooltip=["snapshot_date", "days_to_maturity", "ppd", "strike"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity (Overzicht) — {type_optie.upper()} | Strike {strike}",
        height=700
    )
    st.altair_chart(chart2_main, use_container_width=True)

    # Korte termijn grafiek
    max_days = st.sidebar.slider("Max Days to Maturity (Tweede Grafiek)", 1, int(df_maturity["days_to_maturity"].max()) if not df_maturity["days_to_maturity"].empty else 21, 21)
    df_short_term = df_maturity[df_maturity["days_to_maturity"] <= max_days]
    if not df_short_term.empty:
        chart2_short = alt.Chart(df_short_term).mark_line(point=True).encode(
            x=alt.X("days_to_maturity:Q", title=f"Dagen tot Maturity (0-{max_days})", sort=None),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
            color=alt.Color("snapshot_date:T", title="Peildatum", scale=alt.Scale(scheme="category10")),
            tooltip=["snapshot_date", "days_to_maturity", "ppd", "strike"]
        ).interactive().properties(
            title=f"PPD per Dag tot Maturity (0-{max_days} dagen)",
            height=400
        )
        st.altair_chart(chart2_short, use_container_width=True)
    else:
        st.write(f"Geen data beschikbaar voor dagen tot maturity ≤ {max_days}.")

    # Tabel en debug info
    st.write("Aantal rijen na filtering:", len(df_maturity))
    st.write(f"Aantal rijen met ongeldige PPD (NaN): {df_maturity['ppd'].isna().sum()}")
    st.write("Unieke days_to_maturity waarden:", sorted(df_maturity["days_to_maturity"].unique()))
    st.write("Gefilterde data:", df_maturity)

    if not df_maturity["ppd"].empty:
        max_ppd = df_maturity["ppd"].max()
        best_maturity = df_maturity.loc[df_maturity["ppd"].idxmax(), "days_to_maturity"]
        st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")
else:
    st.write("Geen data gevonden voor de geselecteerde filters. Debug: Check Supabase data or filter values.")
