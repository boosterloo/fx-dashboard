import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client

# === Supabase verbinden via secrets ===
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

# === Titel
st.markdown('<h1 style="text-align:center; color:#1E90FF;">💱 FX Dashboard met EMA</h1>', unsafe_allow_html=True)

# === Datumfilter ophalen
min_resp = supabase.table("fx_rates").select("date").order("date").limit(1).execute()
max_resp = supabase.table("fx_rates").select("date").order("date", desc=True).limit(1).execute()
if not min_resp.data or not max_resp.data:
    st.error("Geen data beschikbaar.")
    st.stop()

min_date = pd.to_datetime(min_resp.data[0]["date"]).date()
max_date = pd.to_datetime(max_resp.data[0]["date"]).date()
st.sidebar.write(f"📆 Beschikbaar: {min_date} → {max_date}")

# === Datumselectie
st.sidebar.header("📅 Datumfilter")
start_def = max_date - pd.DateOffset(months=3)
start = st.sidebar.date_input("Startdatum", value=start_def.date(), min_value=min_date, max_value=max_date)
end = st.sidebar.date_input("Einddatum", value=max_date, min_value=min_date, max_value=max_date)
start, end = pd.to_datetime(start), pd.to_datetime(end)
if start > end:
    st.sidebar.error("Startdatum moet voor Einddatum zijn.")
    st.stop()

# === Data ophalen
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
            .order("date")
            .range(offset, offset + limit - 1)
            .execute()
        )
        chunk = resp.data or []
        if not chunk:
            break
        all_data.extend(chunk)
        offset += limit
    df = pd.DataFrame(all_data)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["date"]).sort_values("date")
    df["EUR/USD"] = 1 / df.get("eur_usd", pd.NA)
    df["USD/JPY"] = df.get("usd_jpy", pd.NA)
    df["GBP/USD"] = 1 / df.get("gbp_usd", pd.NA)
    df["AUD/USD"] = 1 / df.get("aud_usd", pd.NA)
    df["USD/CHF"] = df.get("usd_chf", pd.NA)
    return df

df = load_data(start, end)
if df.empty:
    st.warning("Geen FX-data gevonden voor deze periode.")
    st.stop()

# === EMA instellingen
st.sidebar.header("📐 EMA-instellingen")
ema_periods = st.sidebar.multiselect("Kies EMA-periodes", [20, 50, 100], default=[20])

# === Overlay
st.subheader("📈 Overlay van valutaparen (max 2)")
avail = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF"]
selected = st.multiselect("Selecteer valutaparen", avail, default=["EUR/USD", "USD/JPY"])
if selected:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df[selected[0]], name=selected[0], yaxis="y1"))
    if len(selected) > 1:
        fig.add_trace(go.Scatter(x=df["date"], y=df[selected[1]], name=selected[1], yaxis="y2"))
    fig.update_layout(
        xaxis=dict(title="Datum"),
        yaxis=dict(title=selected[0], side="left"),
        yaxis2=dict(title=selected[1], overlaying="y", side="right") if len(selected) > 1 else {},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# === Grafieken per paar met EMA
st.subheader("📊 Koersontwikkeling per valutapaar met EMA")
for pair in avail:
    st.markdown(f"### {pair}")
    d = df[["date", pair]].copy()
    for p in ema_periods:
        d[f"EMA{p}"] = d[pair].ewm(span=p, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d[pair], name=pair, line=dict(color="blue")))
    for p in ema_periods:
        fig.add_trace(go.Scatter(x=d["date"], y=d[f"EMA{p}"], name=f"EMA{p}", line=dict(dash="dash")))
    fig.update_layout(xaxis_title="Datum", yaxis_title="Koers")
    st.plotly_chart(fig, use_container_width=True)
    st.metric(f"Laatste koers {pair}", f"{d[pair].iloc[-1]:.4f}")

# === Download
st.download_button("⬇️ Download CSV", data=df.to_csv(index=False), file_name="fx_data.csv")
