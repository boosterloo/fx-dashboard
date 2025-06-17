```python
import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go

# === 1. Omgevingsvariabelen laden ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === 2. Titel ===
st.markdown(
    '<h1 style="text-align:center; color:#1E90FF;">💱 FX Dashboard met EMA</h1>',
    unsafe_allow_html=True
)

# === 3. Data ophalen ===
def load_data():
    all_data = []
    offset = 0
    limit = 1000
    # Haal batches op om limiet van Supabase te omzeilen
    while True:
        resp = (supabase.table("fx_rates")
                .select("*")
                .order("date", desc=False)
                .range(offset, offset + limit - 1)
                .execute())
        batch = resp.data
        if not batch:
            break
        all_data.extend(batch)
        offset += limit
    df = pd.DataFrame(all_data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Converteer raw kolommen naar juiste forex quotes
    PAIR_MAP = {
        "eur_usd": ("EUR/USD", lambda x: 1/x),   # raw: EUR per USD → USD per EUR
        "usd_jpy": ("USD/JPY", lambda x: x),     # raw: JPY per USD → USD/JPY OK
        "gbp_usd": ("GBP/USD", lambda x: 1/x),   # raw: GBP per USD → USD per GBP
        "aud_usd": ("AUD/USD", lambda x: 1/x),   # raw: AUD per USD → USD per AUD
        "usd_chf": ("USD/CHF", lambda x: x),     # raw: CHF per USD → USD/CHF OK
    }
    for raw, (label, func) in PAIR_MAP.items():
        if raw in df.columns:
            df[label] = df[raw].apply(func)
    return df

# Cache met korte TTL, herlaadknop available
@st.cache_data(ttl=300)
def get_data():
    return load_data()

df = get_data()
if df.empty:
    st.error("Geen FX-data beschikbaar.")
    st.stop()

# Handmatige herlaadknop
if st.button("🔄 Herlaad data van Supabase"):
    get_data.clear()
    st.experimental_rerun()

# Beschikbare datums tonen
min_date = df["date"].min().date()
max_date = df["date"].max().date()
st.markdown(f"📆 Beschikbare datums: **{min_date} → {max_date}**")

# --- Sidebar: Datumfilter & EMA-instellingen ---
st.sidebar.header("Datumfilter")
start = st.sidebar.date_input("Startdatum", min_value=min_date, max_value=max_date, value=min_date)
end = st.sidebar.date_input("Einddatum", min_value=min_date, max_value=max_date, value=max_date)
if pd.to_datetime(start) > pd.to_datetime(end):
    st.sidebar.error("Startdatum moet vóór einddatum liggen.")
    st.stop()
df_filt = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]

st.sidebar.header("EMA-instellingen")
ema_periods = st.sidebar.multiselect("📐 Kies EMA-periodes", [20, 50, 100], default=[20])

# --- Overlay grafiek ---
st.subheader("Overlay van valutaparen (max 2)")
labels = [lbl for lbl, _ in [v for v in PAIR_MAP.values()]]
selected = st.multiselect("Selecteer valutaparen", labels, default=["EUR/USD", "USD/JPY"])
if selected:
    fig = go.Figure()
    for i, pair in enumerate(selected[:2]):
        axis = "y1" if i == 0 else "y2"
        fig.add_trace(go.Scatter(x=df_filt["date"], y=df_filt[pair], name=pair, yaxis=axis))
    fig.update_layout(
        xaxis=dict(title="Datum"),
        yaxis=dict(title=selected[0], side="left"),
        yaxis2=dict(title=selected[1] if len(selected)>1 else "", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Aparte grafieken met EMA ---
st.subheader("Koersontwikkeling per valutapaar met EMA")
for pair in labels:
    st.markdown(f"#### {pair}")
    df_pair = df_filt[["date", pair]].copy()
    for p in ema_periods:
        df_pair[f"EMA{p}"] = df_pair[pair].ewm(span=p, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_pair["date"], y=df_pair[pair], name=pair))
    for p in ema_periods:
        fig.add_trace(go.Scatter(x=df_pair["date"], y=df_pair[f"EMA{p}"], name=f"EMA{p}", line=dict(dash="dash")))
    fig.update_layout(xaxis_title="Datum", yaxis_title="Koers", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    st.metric(label=f"Laatste koers ({pair})", value=f"{df_pair[pair].iloc[-1]:.4f}")

# --- Downloadoptie ---
st.download_button("⬇️ Download als CSV", data=df_filt.to_csv(index=False), file_name="fx_data.csv")
```
