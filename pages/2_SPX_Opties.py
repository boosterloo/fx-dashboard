import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# === Supabase via Streamlit secrets
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

st.title("📈 SPX Opties: PPD-verloop per Strike")

# === Data ophalen
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("spx_options").select("*").execute()
    df = pd.DataFrame(response.data)
    df.columns = [col.lower() for col in df.columns]
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['expiration'] = pd.to_datetime(df['expiration'])
    df = df[df['days_to_exp'] > 0]
    df['ppd'] = ((df['bid'] + df['ask']) / 2) / df['days_to_exp']
    return df

df = load_data()

# === Sidebar
with st.sidebar:
    st.header("🔎 Filters")
    option_type = st.selectbox("Type optie", sorted(df["type"].dropna().unique()))
    expiration = st.selectbox("Expiratiedatum", sorted(df["expiration"].dt.date.unique()))
    filtered_strikes = df[
        (df["type"] == option_type) &
        (df["expiration"].dt.date == expiration)
    ]["strike"].dropna().unique()
    if len(filtered_strikes) == 0:
        st.warning("⚠️ Geen strikes gevonden.")
        st.stop()
    strike = st.selectbox("Strike", sorted(filtered_strikes))

# === Filter
filtered_df = df[
    (df["type"] == option_type) &
    (df["expiration"].dt.date == expiration) &
    (df["strike"] == strike)
].sort_values("snapshot_date")

# === Debug info
st.write(f"🔍 {len(filtered_df)} rijen gevonden voor {option_type.upper()} {strike} exp. {expiration}")
st.dataframe(filtered_df[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]].head(10))

# === Plot
if filtered_df.empty:
    st.warning("⚠️ Geen data gevonden.")
else:
    fig = px.line(
        filtered_df,
        x="snapshot_date",
        y="ppd",
        markers=True,
        title=f"PPD-verloop — {option_type.upper()} {strike} exp. {expiration}"
    )
    fig.update_layout(
        xaxis_title="Peildatum",
        yaxis_title="Premium per dag (PPD)",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
