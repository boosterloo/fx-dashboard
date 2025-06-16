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

# === 2. Styling en titel ===
st.markdown(
    """
    <style>
    .title {
        color: #1E90FF;
        font-size: 40px;
        text-align: center;
        margin-bottom: 20px;
    }
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .metric {
        text-align: center;
        font-size: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown('<h1 class="title">💱 FX Dashboard met EMA</h1>', unsafe_allow_html=True)

# === 3. Data ophalen ===
def load_data():
    try:
        all_data = []
        offset = 0
        limit = 1000
        while True:
            response = supabase.table("fx_rates").select("*").order("date", desc=False).range(offset, offset + limit - 1).execute()
            data = response.data
            if not data:
                break
            all_data.extend(data)
            offset += limit
            st.write(f"Gehaalde rijen: {offset}, laatste datum: {data[-1]['date']}")
        df = pd.DataFrame(all_data)
        with st.expander("📊 Debug-informatie"):
            st.write("Aantal rijen geladen:", len(df))
            st.write("Ruwe response data (eerste 5 rijen):", all_data[:5])
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        st.write("Geladen datums:", df["date"].min().date(), "tot", df["date"].max().date())
        return df
    except Exception as e:
        st.error("❌ Data ophalen mislukt.")
        st.exception(e)
        return pd.DataFrame()

df = load_data()

# === Herlaadknop ===
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
start_date = st.sidebar.date_input("Startdatum", value=start_default, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Einddatum", value=end_default, min_value=min_value, max_value=max_date)

start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

if start_date > end_date:
    st.sidebar.error("❌ Startdatum moet vóór einddatum liggen.")
    st.stop()

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# === 6. EMA instellingen ===
st.sidebar.header("EMA-instellingen")
ema_periods = st.sidebar.multiselect("📐 Kies EMA-periodes", [20, 50, 100], default=[20])

# === 7. Overlay grafiek ===
selected_pairs = st.selectbox("Selecteer valutaparen voor overlay", currency_columns, default=["eur_usd", "usd_jpy"])
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
    st.markdown(f'<div class="metric">Laatste koers ({pair.upper()})<br>{df_pair[pair].iloc[-1]:.4f}</div>', unsafe_allow_html=True)

# === 9. Downloadoptie ===
st.download_button("⬇️ Download als CSV", data=df_filtered.to_csv(index=False), file_name="fx_data.csv")