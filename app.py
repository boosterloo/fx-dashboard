```python
import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import yfinance as yf

# === 1. Omgevingsvariabelen laden ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === 2. Sidebar navigatie ===
st.sidebar.title("Navigatie")
section = st.sidebar.radio(
    "Kies onderdeel:",
    [
        "FX Rates",
        "SPX Opties",
        "SP500 Index",
        "AEX Index",
        "Macro",
        "Commodity",
        "Sectoren",
        "Yield Curve",
    ],
)

# === FX sectie ===
def show_fx():
    st.markdown('<h1 style="text-align:center;">💱 FX Dashboard met EMA</h1>', unsafe_allow_html=True)
    # Data ophalen
    all_data = []
    offset = 0
    limit = 1000
    while True:
        resp = (
            supabase
            .table("fx_rates")
            .select("*")
            .order("date", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
        batch = resp.data
        if not batch:
            break
        all_data.extend(batch)
        offset += limit
    df = pd.DataFrame(all_data)
    if df.empty:
        st.error("Geen FX data gevonden.")
        return
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Beschikbare datums
    min_d, max_d = df.date.min().date(), df.date.max().date()
    st.write(f"📆 Beschikbare datums: {min_d} → {max_d}")

    # Datumfilter
    st.sidebar.header("Datumfilter")
    start = st.sidebar.date_input(
        "Startdatum", value=max_d - pd.DateOffset(months=3), min_value=min_d, max_value=max_d
    )
    end = st.sidebar.date_input(
        "Einddatum", value=max_d, min_value=min_d, max_value=max_d
    )
    df_filt = df[(df.date >= pd.to_datetime(start)) & (df.date <= pd.to_datetime(end))]

    # EMA instellingen
    st.sidebar.header("EMA-instellingen")
    ema_periods = st.sidebar.multiselect(
        "Kies EMA-periodes", [20, 50, 100], default=[20]
    )

    # Overlay grafiek (max 2)
    with st.expander("Overlay FX paren (max 2)"):
        pairs = [c for c in df_filt.columns if c.endswith("_usd") or c.startswith("usd_")]
        sel = st.multiselect("Valutaparen:", pairs, default=pairs[:2])
        if sel:
            fig = go.Figure()
            for i, p in enumerate(sel):
                axis = 'y' if i == 0 else 'y2'
                fig.add_trace(go.Scatter(x=df_filt.date, y=df_filt[p], name=p, yaxis=axis))
            fig.update_layout(
                yaxis2=dict(overlaying='y', side='right'),
                legend=dict(orientation='h', y=1.1, x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

    # Aparte grafieken per paar met EMA
    st.subheader("Koersontwikkeling per FX paar met EMA")
    for p in pairs:
        st.markdown(f"### {p}")
        d = df_filt[["date", p]].copy()
        for per in ema_periods:
            d[f"EMA{per}"] = d[p].ewm(span=per, adjust=False).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d.date, y=d[p], name=p))
        for per in ema_periods:
            fig.add_trace(
                go.Scatter(
                    x=d.date,
                    y=d[f"EMA{per}"],
                    name=f"EMA{per}",
                    line_dash='dash'
                )
            )
        st.plotly_chart(fig, use_container_width=True)

# === Sectie logica ===
if section == "FX Rates":
    show_fx()
elif section == "SPX Opties":
    st.write("SPX Opties - nog in te vullen")
elif section == "SP500 Index":
    st.write("SP500 Index - nog in te vullen")
elif section == "AEX Index":
    st.write("AEX Index - nog in te vullen")
elif section == "Macro":
    st.write("Macro - nog in te vullen")
elif section == "Commodity":
    st.write("Commodity - nog in te vullen")
elif section == "Sectoren":
    st.write("Sectoren - nog in te vullen")
elif section == "Yield Curve":
    st.write("Yield Curve - nog in te vullen")
```
