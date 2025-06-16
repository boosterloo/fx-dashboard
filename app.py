import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import plotly.express as px

# === 1. Omgevingsvariabelen laden ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === 2. Titel ===
st.title("\U0001F4B1 FX Dashboard met EMA")

# === 3. Data ophalen ===
@st.cache_data(ttl=300)
def load_data():
    try:
        response = supabase.table("fx_rates").select("*").order("date", desc=False).execute()
        df = pd.DataFrame(response.data)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        return df
    except Exception as e:
        st.error("❌ Data ophalen mislukt.")
        st.exception(e)
        return pd.DataFrame()

df = load_data()

# === Herlaadknop voor handmatige refresh ===
if st.button("🔄 Herlaad data van Supabase"):
    try:
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error("❌ Herladen mislukt.")
        st.exception(e)

if df.empty:
    st.stop()

min_date, max_date = df["date"].min().date(), df["date"].max().date()
st.write("📆 Beschikbare datums:", min_date, "→", max_date)

# === 4. Valutaparen bepalen ===
currency_columns = [col for col in df.columns if col not in ["id", "date"]]

# === 5. Datumfilter ===
st.sidebar.header("Datumfilter")
def get_default_range():
    default_end = max_date
    default_start = default_end - pd.DateOffset(months=3)
    return default_start.date(), default_end

start_default, end_default = get_default_range()
st.sidebar.write("Beschikbaar:", min_date, "→", max_date)
selected_range = st.sidebar.slider("📅 Selecteer een periode:",
                                    min_value=min_date,
                                    max_value=max_date,
                                    value=(start_default, end_default))

start_date, end_date = pd.to_datetime(selected_range[0]), pd.to_datetime(selected_range[1])
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# === 6. EMA instellingen ===
st.sidebar.header("EMA-instellingen")
ema_periods = st.sidebar.multiselect("📐 Kies EMA-periodes", [20, 50, 100], default=[20])

# === 7. Overlay grafiek ===
with st.expander("📈 Overlay van valutaparen"):
    default_pairs = [p for p in ["eur_usd", "jpy_usd"] if p in currency_columns]
    selected_pairs = st.multiselect("Valutaparen", currency_columns, default=default_pairs)
    if selected_pairs:
        fig = px.line(df_filtered, x="date", y=selected_pairs)
        st.plotly_chart(fig, use_container_width=True)

# === 8. Aparte grafieken per paar met EMA ===
st.subheader("📊 Koersontwikkeling per valutapaar met EMA")

for pair in currency_columns:
    st.markdown(f"#### {pair.upper()}")

    df_pair = df_filtered[["date", pair]].copy()
    for periode in ema_periods:
        df_pair[f"EMA{periode}"] = df_pair[pair].ewm(span=periode, adjust=False).mean()

    fig = px.line(df_pair, x="date", y=[pair] + [f"EMA{p}" for p in ema_periods],
                  labels={"value": "Koers", "variable": "Lijn"}, title=pair.upper())
    st.plotly_chart(fig, use_container_width=True)

    laatste_koers = df_pair[pair].iloc[-1]
    st.metric(label=f"Laatste koers ({pair.upper()})", value=f"{laatste_koers:.4f}")

# === 9. Downloadoptie ===
st.download_button("⬇️ Download als CSV", data=df_filtered.to_csv(index=False), file_name="fx_data.csv")
