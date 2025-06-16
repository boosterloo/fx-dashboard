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

# === 3. Data ophalen met paginatie ===
def load_data():
    try:
        all_data = []
        offset = 0
        limit = 1000
        while True:
            response = supabase.table("fx_rates") \
                .select("*") \
                .order("date", desc=False) \
                .range(offset, offset + limit - 1) \
                .execute()
            batch = response.data
            if not batch:
                break
            all_data.extend(batch)
            offset += limit
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        # Kolomnamen hernoemen en omkeren waar nodig
        mapping = {
            'eur_usd': ('EUR/USD', True),   # 1 USD→EUR => omgekeerd voor EUR/USD
            'jpy_usd': ('USD/JPY', False),  # 1 USD→JPY is correct voor USD/JPY
            'gbp_usd': ('GBP/USD', True),   # 1 USD→GBP => omgekeerd voor GBP/USD
            'aud_usd': ('AUD/USD', True),   # 1 USD→AUD => omgekeerd voor AUD/USD
            'chf_usd': ('USD/CHF', False)   # 1 USD→CHF is correct voor USD/CHF
        }
        for old_col, (new_col, invert) in mapping.items():
            if old_col in df.columns:
                rates = df[old_col].astype(float)
                df[new_col] = 1/rates if invert else rates
        return df
    except Exception as e:
        st.error("❌ Data ophalen mislukt.")
        st.exception(e)
        return pd.DataFrame()

# Laad data
title = st.spinner("Data ophalen uit Supabase...")
df = load_data()

# Herlaadknop
if st.button("🔄 Herlaad data van Supabase"):
    st.experimental_rerun()

if df.empty:
    st.stop()

# Beschikbare datums tonen
min_date = df['date'].min().date()
max_date = df['date'].max().date()
st.write(f"📆 Beschikbare datums: {min_date} → {max_date}")

# === 4. Valutaparen bepalen ===
currency_columns = [c for c in df.columns if '/' in c]
if not currency_columns:
    st.error("Geen valutaparen gevonden in de data.")
    st.stop()

# === 5. Datumfilter ===
st.sidebar.header("Datumfilter")
def default_range():
    end = max_date
    start = end - pd.DateOffset(months=3)
    return start.date(), end
start_def, end_def = default_range()
st.sidebar.write(f"Beschikbaar: {min_date} → {max_date}")
start_date = st.sidebar.date_input("Startdatum", value=start_def, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Einddatum", value=end_def, min_value=min_date, max_value=max_date)
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)
if start_date > end_date:
    st.sidebar.error("Startdatum moet vóór einddatum liggen.")
    st.stop()
# Filter data
df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()

# === 6. EMA instellingen ===
st.sidebar.header("EMA-instellingen")
ema_periods = st.sidebar.multiselect("📐 Kies EMA-periodes", [20, 50, 100], default=[20])

# === 7. Overlay grafiek ===
st.subheader("📈 Overlay van valutaparen (max 2)")
default_pairs = [p for p in ['EUR/USD', 'USD/JPY'] if p in currency_columns]
sel_pairs = st.multiselect("Selecteer valutaparen", currency_columns, default=default_pairs[:2])
if sel_pairs:
    fig = go.Figure()
    for i, pair in enumerate(sel_pairs):
        trace = go.Scatter(x=df_filtered['date'], y=df_filtered[pair], name=pair, yaxis='y2' if i==1 else 'y1')
        fig.add_trace(trace)
    fig.update_layout(
        xaxis=dict(title='Datum'),
        yaxis=dict(title=sel_pairs[0] if sel_pairs else '', side='left', anchor='x'),
        yaxis2=dict(title=sel_pairs[1] if len(sel_pairs)>1 else '', overlaying='y', side='right', anchor='x'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# === 8. Aparte grafieken per paar met EMA ===
st.subheader("📊 Koersontwikkeling met EMA")
for pair in currency_columns:
    st.markdown(f"#### {pair}")
    df_pair = df_filtered[['date', pair]].copy()
    for p in ema_periods:
        df_pair[f"EMA{p}"] = df_pair[pair].ewm(span=p, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_pair['date'], y=df_pair[pair], name=pair))
    for p in ema_periods:
        fig.add_trace(go.Scatter(x=df_pair['date'], y=df_pair[f"EMA{p}"], name=f"EMA{p}", line=dict(dash='dash')))
    fig.update_layout(xaxis_title='Datum', yaxis_title='Koers', legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<div class='metric'>Laatste koers ({pair}): {df_pair[pair].iloc[-1]:.4f}</div>", unsafe_allow_html=True)

# === 9. Downloadoptie ===
st.download_button("⬇️ Download als CSV", data=df_filtered.to_csv(index=False), file_name="fx_data.csv")
