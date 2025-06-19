import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os
from dotenv import load_dotenv

# === Setup Supabase ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📈 SPX Optieanalyse")

# === Data ophalen ===
@st.cache_data(ttl=3600)
def load_spx_data():
    all_data = []
    offset = 0
    limit = 1000
    while True:
        resp = (
            supabase.table("spx_options")
            .select("*")
            .order("snapshot_date")
            .range(offset, offset + limit - 1)
            .execute()
        )
        data = resp.data or []
        if not data:
            break
        all_data.extend(data)
        offset += limit
    df = pd.DataFrame(all_data)
    if df.empty:
        return df
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["expiration"] = pd.to_datetime(df["expiration"])
    df = df[df["days_to_exp"] > 0]
    df["ppd"] = df["last_price"] / df["days_to_exp"]
    return df

df = load_spx_data()
if df.empty:
    st.warning("Geen SPX-data beschikbaar.")
    st.stop()

# === Filters ===
st.sidebar.header("🔧 Filters")
available_dates = df["expiration"].dt.date.dropna().unique()
selected_exp = st.sidebar.selectbox("Kies expiratie", sorted(available_dates))
available_strikes = df[df["expiration"].dt.date == selected_exp]["strike"].unique()
selected_strike = st.sidebar.selectbox("Kies strike", sorted(available_strikes))

# === Filter dataset ===
df_filtered = df[(df["expiration"].dt.date == selected_exp) & (df["strike"] == selected_strike)]

# === Visualisatie: PPD ontwikkeling ===
st.subheader(f"📊 PPD Ontwikkeling voor strike {selected_strike} met exp. {selected_exp}")
fig = px.line(
    df_filtered,
    x="snapshot_date",
    y="ppd",
    title="Premie Per Dag (PPD) over de tijd",
    labels={"snapshot_date": "Datum", "ppd": "Premie Per Dag (USD)"}
)
st.plotly_chart(fig, use_container_width=True)

# === Suggesties voor andere grafieken ===
with st.expander("📌 Andere suggesties"):
    st.markdown("""
    - 🔍 **PPD vs Strike** op een vaste datum
    - 📉 **Implied Volatility vs PPD**
    - 💸 **Totale waarde open interest** (open_interest * last_price)
    - 🧮 **Break-even grafiek** bij long/short combo's
    - 🔁 **PPD-verhouding short/long** strategie
    """)
