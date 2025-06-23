import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os

st.set_page_config(page_title="SPX Opties", layout="wide")

# === Supabase instellingen ===
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Gegevens ophalen uit de nieuwe SPX-tabel ===
table_name = "spx_options2"
response = supabase.table(table_name).select("*").execute()

if hasattr(response, "error") and response.error:
    st.error(f"Fout bij ophalen data: {response.error}")
    st.stop()

# === DataFrame maken ===
df = pd.DataFrame(response.data)

if df.empty:
    st.warning("Geen data beschikbaar in Supabase-tabel.")
    st.stop()

# === Conversie kolommen ===
df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
df["expiration"] = pd.to_datetime(df["expiration"]).dt.date

# === Filters ===
st.sidebar.header("🔍 Filters")
type_optie = st.sidebar.selectbox("Type optie", sorted(df["type"].dropna().unique()))

# Eerst filteren op type, zodat expiraties en strikes rijker gevuld zijn
df_type = df[df["type"] == type_optie]

# Expiraties op basis van alleen het type
beschikbare_expiraties = sorted(df_type["expiration"].dropna().unique())
expiratie = st.sidebar.selectbox("Expiratiedatum", beschikbare_expiraties)

# Strikes op basis van alle data voor type + expiratie, ongeacht snapshot moment
df_exp = df_type[df_type["expiration"] == expiratie]
beschikbare_strikes = sorted(df_exp["strike"].dropna().unique())
strike = st.sidebar.selectbox("Strike", beschikbare_strikes)

# === Filteren ===
df_filtered = df[(df["type"] == type_optie) & (df["expiration"] == expiratie) & (df["strike"] == strike)]
df_filtered = df_filtered.sort_values("snapshot_date")

# === Weergave ===
st.title("📈 SPX Opties: PPD-verloop per Strike")
st.markdown(f"🔍 {len(df_filtered)} rijen gevonden voor {type_optie.upper()} {strike} exp. {expiratie}")

st.dataframe(df_filtered[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]])

chart = alt.Chart(df_filtered).mark_circle(size=80).encode(
    x=alt.X("snapshot_date:T", title="Peildatum"),
    y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
    tooltip=["snapshot_date", "ppd", "last_price", "bid", "ask"]
).interactive().properties(
    title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}"
)

st.altair_chart(chart, use_container_width=True)
