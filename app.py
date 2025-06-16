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
        with st.expander("📊 Data ophalen log"):
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
        # Hernoem kolommen naar conventionele notatie zonder omrekening
        column_mapping = {
            "eur_usd": "EUR/USD",
            "usd_jpy": "USD/JPY",
            "gbp_usd": "GBP/USD",
            "aud_usd": "AUD/USD",
            "usd_chf": "USD/CHF"
        }
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]  # Kopieer waarde zonder omrekening
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
currency_columns = [col for col in df.columns if "/" in col]  # Gebruik de nieuwe omgenaamde kolommen
if not currency_columns:
    st.error("Geen valutaparen gevonden in de data.")
    st.stop()

# === 5. Datumfilter ===
st.sidebar.header("Datumfilter")
def get_default_range():
    default_end = max_date  # Standaard de meest recente datum
    default_start = default_end - pd.DateOffset(months=3)  # 3 maanden ervoor
    return default_start, default_end

start_default, end_default = get_default_range()
st.sidebar.write("Beschikbaar:", min_date, "→", max_date)
start_date = st.sidebar.date_input("Startdatum", value=start_default, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Einddatum", value=end_default, min_value=min_date, max_value=max_date)

start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

if start_date > end_date:
    st.sidebar.error("❌ Startdatum moet vóór einddatum liggen.")
    st.stop()

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()

# === 6. EMA instellingen ===
st.sidebar.header("EMA-instellingen")
ema_periods = st.sidebar.multiselect("📐 Kies EMA-periodes", [20, 50, 100], default=[20])

# === 7. Overlay grafiek met dual-axis ===
default_pairs = [p for p in ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF"] if p in currency_columns]
selected_pairs = st.multiselect("Selecteer valutaparen voor overlay", currency_columns, default=default_pairs[:2])  # Max 2 voor dual-axis
if selected_pairs:
    fig = go.Figure()
    for i, pair in enumerate(selected_pairs):
        # Voeg de eerste valuta toe aan de linker Y-as
        if i == 0:
            fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered[pair], name=pair, yaxis="y1"))
        # Voeg de tweede valuta toe aan de rechter Y-as
        elif i == 1:
            fig.add_trace(go.Scatter(x=df_filtered["date"], y=df_filtered[pair], name=pair, yaxis="y2"))
    
    # Configureer de dual-axis
    fig.update_layout(
        title="Overlay van geselecteerde valutaparen",
        yaxis=dict(title=selected_pairs[0] if selected_pairs else "", side="left"),
        yaxis2=dict(title=selected_pairs[1] if len(selected_pairs) > 1 else "", overlaying="y", side="right"),
        xaxis=dict(title="Datum"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# === 8. Aparte grafieken per paar met EMA ===
st.subheader("📊 Koersontwikkeling per valutapaar met EMA")
for pair in currency_columns:
    st.markdown(f"#### {pair}")
    df_pair = df_filtered[["date", pair]].copy()
    for periode in ema_periods:
        df_pair[f"EMA{periode}"] = df_pair[pair].ewm(span=periode, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_pair["date"], y=df_pair[pair], name=pair, line=dict(color="blue")))
    for periode in ema_periods:
        fig.add_trace(go.Scatter(x=df_pair["date"], y=df_pair[f"EMA{periode}"], name=f"EMA{periode}", line=dict(color="red", dash="dash")))
    fig.update_layout(
        title=pair,
        yaxis=dict(title="Koers"),
        xaxis=dict(title="Datum"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="metric">Laatste koers ({pair})<br>{df_pair[pair].iloc[-1]:.4f}</div>', unsafe_allow_html=True)

# === 9. Downloadoptie ===
st.download_button("⬇️ Download als CSV", data=df_filtered.to_csv(index=False), file_name="fx_data.csv")