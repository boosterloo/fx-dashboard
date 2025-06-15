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
st.set_page_config(layout="wide")
st.title("💱 FX Dashboard met EMA")

# === 3. Data ophalen ===
@st.cache_data
def load_data():
    response = supabase.table("fx_rates").select("*").order("date", desc=False).execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# === 4. Valutaparen bepalen ===
currency_columns = [col for col in df.columns if col not in ["id", "date"]]

# === 5. Datumfilter ===
default_start = df["date"].max() - pd.DateOffset(months=3)
selected_range = st.date_input("📅 Selecteer een periode", value=(default_start, df["date"].max()))
start_date, end_date = pd.to_datetime(selected_range[0]), pd.to_datetime(selected_range[1])
df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# === 6. EMA instellingen ===
st.sidebar.header("📐 EMA-instellingen")
ema_periods = st.sidebar.multiselect("Kies periodes", [20, 50, 100], default=[20])

# === 7. Overlay van meerdere valutaparen ===
with st.expander("📈 Vergelijk meerdere valutaparen"):
    selected_pairs = st.multiselect("Valutaparen", currency_columns, default=["eur_usd", "jpy_usd"])
    if selected_pairs:
        fig_overlay = px.line(df_filtered, x="date", y=selected_pairs, title="Overlay van geselecteerde paren")
        st.plotly_chart(fig_overlay, use_container_width=True)

# === 8. Aparte grafieken met EMA ===
st.subheader("📊 Grafieken per valutapaar")

for pair in currency_columns:
    st.markdown(f"### {pair.upper()}")
    df_pair = df_filtered[["date", pair]].copy()

    for p in ema_periods:
        df_pair[f"EMA{p}"] = df_pair[pair].ewm(span=p, adjust=False).mean()

    fig = px.line(df_pair, x="date", y=[pair] + [f"EMA{p}" for p in ema_periods],
                  labels={"value": "Koers", "variable": "Lijn"}, title=f"{pair.upper()} met EMA")
    st.plotly_chart(fig, use_container_width=True)

    laatste_koers = df_pair[pair].iloc[-1]
    st.metric(label=f"Laatste koers ({pair.upper()})", value=f"{laatste_koers:.4f}")

# === 9. Downloadknop ===
st.download_button('⬇️ Download als CSV', data=df_filtered.to_csv(index=False), file_name="fx_data.csv")
