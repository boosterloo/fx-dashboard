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

# === Navigatie ===
st.sidebar.header("🔍 Navigatie")
section = st.sidebar.radio(
    "Kies onderdeel:",
    ["FX Rates", "SPX Opties", "SP500 Index", "AEX Index", "Macro", "Commodity", "Sectoren", "Yield Curve"],
    index=0
)
if section != "FX Rates":
    st.title(f"📌 Sectie '{section}' nog in ontwikkeling")
    st.stop()

# === 2. Titel ===
st.markdown(
    '<h1 style="text-align:center; color:#1E90FF;">💱 FX Dashboard met EMA</h1>', unsafe_allow_html=True
)

# === 3. Datumfilter in sidebar ===
min_resp = supabase.table("fx_rates").select("date").order("date", desc=False).limit(1).execute()
max_resp = supabase.table("fx_rates").select("date").order("date", desc=True).limit(1).execute()
if not min_resp.data or not max_resp.data:
    st.error("Geen data beschikbaar.")
    st.stop()
min_date = pd.to_datetime(min_resp.data[0]["date"]).date()
max_date = pd.to_datetime(max_resp.data[0]["date"]).date()
st.sidebar.write(f"📆 Beschikbaar: {min_date} → {max_date}")

st.sidebar.header("📅 Datumfilter")
def default_range():
    end = max_date
    start = end - pd.DateOffset(years=5)
    return start.date(), end

start_def, end_def = default_range()
start = st.sidebar.date_input("Startdatum", value=start_def, min_value=min_date, max_value=max_date)
end = st.sidebar.date_input("Einddatum", value=end_def, min_value=min_date, max_value=max_date)

start, end = pd.to_datetime(start), pd.to_datetime(end)
if start > end:
    st.sidebar.error("Startdatum moet voor Einddatum zijn.")
    st.stop()

# === 4. Data ophalen met server-side filtering en paginatie ===
@st.cache_data(ttl=3600)
def load_data(start_date, end_date):
    all_data = []
    offset = 0
    limit = 1000
    while True:
        resp = (
            supabase.table("fx_rates")
            .select("*")
            .gte("date", start_date.strftime('%Y-%m-%d'))
            .lte("date", end_date.strftime('%Y-%m-%d'))
            .order("date", asc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        chunk = resp.data or []
        if not chunk:
            break
        all_data.extend(chunk)
        offset += limit
    df = pd.DataFrame(all_data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    # Omrekening ratios
    df["EUR/USD"] = 1 / df["eur_usd"]
    df["USD/JPY"] = df["usd_jpy"]
    df["GBP/USD"] = 1 / df["gbp_usd"]
    df["AUD/USD"] = 1 / df["aud_usd"]
    df["USD/CHF"] = df["usd_chf"]
    return df

# Haal gefilterde data op
df = load_data(start, end)
if df.empty:
    st.warning("Geen FX-data gevonden voor deze periode.")
    st.stop()

# === 5. EMA instellingen ===
st.sidebar.header("📐 EMA-instellingen")
ema_periods = st.sidebar.multiselect("Kies EMA-periodes", [20, 50, 100], default=[20])

# === 6. Overlay grafiek ===
st.subheader("📈 Overlay van valutaparen (max 2)")
avail = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF"]
defs = ["EUR/USD", "USD/JPY"]
selected = st.multiselect("Selecteer valutaparen", avail, default=defs)
if selected:
    fig = px.line(df, x="date", y=selected)
    fig.update_layout(yaxis_title="Koers", xaxis_title="Datum")
    st.plotly_chart(fig, use_container_width=True)

# === 7. Individuele grafieken + EMA ===
st.subheader("📊 Koersontwikkeling per valutapaar met EMA")
for pair in avail:
    st.markdown(f"### {pair}")
    d = df[["date", pair]].copy()
    for p in ema_periods:
        d[f"EMA{p}"] = d[pair].ewm(span=p, adjust=False).mean()
    fig = px.line(d, x="date", y=[pair] + [f"EMA{p}" for p in ema_periods])
    fig.update_layout(yaxis_title="Koers", xaxis_title="Datum")
    st.plotly_chart(fig, use_container_width=True)
    st.metric(f"Laatste koers {pair}", f"{d[pair].iloc[-1]:.4f}")

# === 8. Download ===
st.download_button("⬇️ Download CSV", data=df.to_csv(index=False), file_name="fx_data.csv")
