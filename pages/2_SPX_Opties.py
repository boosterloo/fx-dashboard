import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os
from datetime import timedelta

# === Pagina-instellingen ===
st.set_page_config(page_title="SPX Opties", layout="wide")

# === Supabase-instellingen ===
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Data ophalen ===
def fetch_data():
    response = supabase.table("spx_options2").select("*").execute()
    if hasattr(response, "error") and response.error:
        st.error(f"Fout bij ophalen data: {response.error}")
        st.stop()
    df = pd.DataFrame(response.data)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
    df["expiration"] = pd.to_datetime(df["expiration"], utc=True, errors="coerce")
    return df

df = fetch_data()
if df.empty:
    st.warning("Geen data beschikbaar in Supabase-tabel.")
    st.stop()

# === Filters ===
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", sorted(df["type"].dropna().unique()))
df_type = df[df["type"] == type_optie]

expiraties = sorted(df_type["expiration"].dropna().unique())
expiratie = st.sidebar.selectbox("Expiratiedatum", expiraties)

strikes = sorted(df_type[df_type["expiration"] == expiratie]["strike"].dropna().unique())
strike = st.sidebar.selectbox("Strike", strikes)

# === Tabbladen ===
tab1, tab2 = st.tabs(["PPD per Peildatum", "PPD per Days to Maturity"])

# === Tab 1: PPD per Peildatum ===
with tab1:
    st.title("📈 SPX Opties: PPD-verloop per Strike")
    df_filtered = df_type[(df_type["expiration"] == expiratie) & (df_type["strike"] == strike)].copy()
    df_filtered = df_filtered.sort_values("snapshot_date")

    if df_filtered.empty:
        st.warning("Geen data gevonden voor de gekozen combinatie.")
    else:
        df_filtered["days_to_maturity"] = (df_filtered["expiration"] - df_filtered["snapshot_date"]).dt.days
        df_filtered = df_filtered[df_filtered["days_to_maturity"] > 0]
        df_filtered["ppd"] = df_filtered["bid"] / df_filtered["days_to_maturity"].replace(0, 0.01)

        st.markdown(f"🔍 {len(df_filtered)} rijen gevonden voor {type_optie.upper()} {strike} exp. {expiratie.date()}")
        st.dataframe(df_filtered[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]])

        chart = alt.Chart(df_filtered).mark_line(point=True).encode(
            x=alt.X("snapshot_date:T", title="Peildatum"),
            y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
            tooltip=["snapshot_date", "ppd", "last_price", "bid", "ask"]
        ).interactive().properties(
            title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie.date()}",
            height=400
        )
        st.altair_chart(chart, use_container_width=True)

# === Tab 2: PPD per Days to Maturity (op peildatum) ===
with tab2:
    st.title("📊 PPD per Days to Maturity")

    snapshot_dates = sorted(df_type["snapshot_date"].dropna().unique(), reverse=True)
    selected_snapshot = st.selectbox("Selecteer peildatum", snapshot_dates)
    df_snap = df_type[df_type["snapshot_date"] == selected_snapshot].copy()

    df_snap["days_to_maturity"] = (df_snap["expiration"] - df_snap["snapshot_date"]).dt.days
    df_snap = df_snap[df_snap["days_to_maturity"] > 0]
    df_snap["ppd"] = df_snap["bid"] / df_snap["days_to_maturity"].replace(0, 0.01)

    if df_snap.empty:
        st.warning("Geen opties beschikbaar op deze peildatum.")
    else:
        chart2 = alt.Chart(df_snap).mark_circle(size=60).encode(
            x=alt.X("days_to_maturity:Q", title="Dagen tot Expiratie"),
            y=alt.Y("ppd:Q", title="PPD"),
            color="type:N",
            tooltip=["expiration", "strike", "ppd", "bid"]
        ).interactive().properties(
            title=f"PPD per Days to Maturity op {pd.to_datetime(selected_snapshot).date()}",
            height=400
        )
        st.altair_chart(chart2, use_container_width=True)
        st.dataframe(df_snap[["expiration", "strike", "bid", "days_to_maturity", "ppd"]])
