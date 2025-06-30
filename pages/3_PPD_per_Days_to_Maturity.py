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
                datetime_values = pd.to_datetime(values, utc=True, errors="coerce")
                return sorted(datetime_values.dropna().unique())
            elif column == "strike":
                return sorted(list(set([int(float(x)) for x in values if isinstance(x, (int, float)) and float(x) > 0 and float(x) < 10000])))
            else:
                return sorted(values, key=lambda x: float(x) if isinstance(x, (int, float)) else 0)
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
    snapshot_dates_sorted = sorted(snapshot_dates, reverse=True)
    default_snapshot = [snapshot_dates_sorted[0]]
    selected_snapshot_dates = st.sidebar.multiselect("Selecteer Peildatum(s)", snapshot_dates_sorted, default=default_snapshot)
else:
    selected_snapshot_dates = []
    st.sidebar.write("Geen peildata beschikbaar.")
strikes = get_unique_values("spx_options2", "strike")
if strikes and len(strikes) > 0:
    strike = st.sidebar.selectbox("Strike (alleen actief)", strikes, index=strikes.index(5500) if 5500 in strikes else 0)
    st.sidebar.write(f"Debug - Selected strike: {strike}")
else:
    strike = 5500
    st.sidebar.write("Debug - No valid strikes found, using default: 5500")

# Fetch data with filters
df_all_data = fetch_filtered_data("spx_options2", type_optie, selected_snapshot_dates, strike)

st.header("PPD per Days to Maturity")
if not df_all_data.empty:
    df_maturity = df_all_data.copy()
    df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
    df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]
    df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)

    # Main chart (lijn)
    chart2_main = alt.Chart(df_maturity).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity"),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)"),
        color=alt.Color("snapshot_date:T", title="Peildatum", scale=alt.Scale(scheme="category10")),
        tooltip=["snapshot_date", "days_to_maturity", "ppd", "strike"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity (Overzicht) — {type_optie.upper()} | Strike {strike}",
        height=700
    )
    st.altair_chart(chart2_main, use_container_width=True)

    # Tweede grafiek (balken per dag met peildatum als kleur)
    max_days = st.sidebar.slider("Max Days to Maturity (Tweede Grafiek)", 1, int(df_maturity["days_to_maturity"].max()), 21)
    df_short_term = df_maturity[df_maturity["days_to_maturity"] <= max_days]

    if not df_short_term.empty:
        df_short_term["days_to_maturity"] = df_short_term["days_to_maturity"].astype(str)
        df_short_term["snapshot_display"] = df_short_term["snapshot_date"].dt.strftime("%Y-%m-%d")

        chart2_short = alt.Chart(df_short_term).mark_bar().encode(
            x=alt.X("days_to_maturity:N", title=f"Dagen tot Maturity (0-{max_days})", sort=alt.EncodingSortField(field="days_to_maturity", order="ascending")),
            y=alt.Y("ppd:Q", title="Premium per Dag (PPD)"),
            color=alt.Color("snapshot_display:N", title="Peildatum", scale=alt.Scale(scheme="category10")),
            column=alt.Column("snapshot_display:N", title="Peildatum"),
            tooltip=["snapshot_display", "days_to_maturity", "ppd", "strike"]
        ).properties(
            title=f"PPD per Dag tot Maturity (0-{max_days} dagen)",
            height=400
        )
        st.altair_chart(chart2_short, use_container_width=True)
    else:
        st.write(f"Geen data beschikbaar voor dagen tot maturity ≤ {max_days}.")

    st.write("Aantal rijen na filtering:", len(df_maturity))
    st.write("Aantal rijen met ongeldige PPD (NaN):", df_maturity["ppd"].isna().sum())
    st.write("Unieke days_to_maturity waarden:", sorted(df_maturity["days_to_maturity"].unique()))
    st.write("Gefilterde data:", df_maturity)

    if not df_maturity["ppd"].empty:
        max_ppd = df_maturity["ppd"].max()
        best_maturity = df_maturity.loc[df_maturity["ppd"].idxmax(), "days_to_maturity"]
        st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")
else:
    st.write("Geen data gevonden voor de geselecteerde filters. Debug: Check Supabase data or filter values.")
