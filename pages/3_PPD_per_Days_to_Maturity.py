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
        try:
            if column == "expiration" or column == "snapshot_date":
                return sorted(set(values), key=lambda x: pd.to_datetime(x))
            elif column == "strike":
                df = pd.DataFrame(response.data)
                if "openInterest" in df.columns:
                    df = df[df["openInterest"] > 0]  # Alleen strikes met open interest
                return sorted(df["strike"].dropna().unique().astype(int).tolist())
            else:
                return sorted(set(values), key=lambda x: float(x) if isinstance(x, (int, float, str)) and str(x).replace('.', '').replace('-', '').isdigit() else 0)
        except Exception as e:
            st.write(f"Debug - Error processing {column} values: {e}")
            return values
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
        query = query.eq("strike", int(strike))
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
type_optie = st.sidebar.selectbox("Type optie (Put/Call)", ["call", "put"], index=1)
snapshot_dates = get_unique_values("spx_options2", "snapshot_date")
if snapshot_dates:
    snapshot_dates_sorted = sorted(snapshot_dates, key=lambda x: pd.to_datetime(x), reverse=True)
    default_snapshots = [snapshot_dates_sorted[0]]
    selected_snapshot_dates = st.sidebar.multiselect("Selecteer Peildatum(s)", snapshot_dates_sorted, default=default_snapshots)
else:
    selected_snapshot_dates = []
strikes = get_unique_values("spx_options2", "strike")
if strikes:
    strike = st.sidebar.selectbox("Strike (alleen actief)", strikes, index=strikes.index(5500) if 5500 in strikes else 0, format_func=lambda x: f"{x:.0f}")
    st.sidebar.write(f"Debug - Selected strike: {strike}")
else:
    strike = 5500
    st.sidebar.write("Geen actieve strikes gevonden, default = 5500")

# Fetch data
df_all_data = fetch_filtered_data("spx_options2", type_optie, selected_snapshot_dates, strike)

st.header("PPD per Days to Maturity")
if not df_all_data.empty:
    df = df_all_data.copy()
    df["days_to_maturity"] = (df["expiration"] - df["snapshot_date"]).dt.days
    df = df[df["days_to_maturity"] > 0]
    df["ppd"] = df["bid"] / df["days_to_maturity"].replace(0, 0.01)

    df = df[df["snapshot_date"].isin(selected_snapshot_dates)]

    color_scale = alt.Scale(domain=[str(d) for d in selected_snapshot_dates], scheme="category10")

    # Eerste grafiek (lijn)
    chart_line = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort="ascending"),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        color=alt.Color("snapshot_date:N", title="Peildatum", scale=color_scale),
        tooltip=["snapshot_date:T", "days_to_maturity", "ppd"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity (Overzicht) — {type_optie.upper()} | Strike {strike:.0f}",
        height=500
    )
    st.altair_chart(chart_line, use_container_width=True)

    # Tweede grafiek (staaf)
    max_days = st.sidebar.slider("Max Days to Maturity (Tweede Grafiek)", 1, int(df["days_to_maturity"].max()), 21)
    df_short = df[df["days_to_maturity"] <= max_days].copy()
    df_short = df_short.sort_values(by=["days_to_maturity", "snapshot_date"])

    if not df_short.empty:
        bar_chart = alt.Chart(df_short).mark_bar(size=15).encode(
            x=alt.X("days_to_maturity:O", title=f"Dagen tot Maturity (0-{max_days})", sort=list(map(str, sorted(df_short["days_to_maturity"].unique())))),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True)),
            color=alt.Color("snapshot_date:N", title="Peildatum", scale=color_scale),
            tooltip=["snapshot_date:T", "days_to_maturity", "ppd"]
        ).properties(
            title=f"PPD per Dag tot Maturity (0-{max_days} dagen)",
            height=400
        )
        st.altair_chart(bar_chart, use_container_width=True)
    else:
        st.write(f"Geen data beschikbaar voor dagen tot maturity ≤ {max_days}.")

    # Debug info
    st.write("Aantal rijen na filtering:", len(df))
    st.write("Aantal rijen met ongeldige PPD (NaN):", df["ppd"].isna().sum())
else:
    st.warning("Geen data gevonden voor de geselecteerde filters.")
