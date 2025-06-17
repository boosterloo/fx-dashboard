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

# === Sidebar Navigatie ===
st.sidebar.header("Navigatie")
menu = st.sidebar.radio("Kies onderdeel:", [
    "FX Rates",
    "SPX Opties",
    "SP500 Index",
    "AEX Index",
    "Macro",
    "Commodity",
    "Sectoren"
])

# === Functie: FX Dashboard ===
def fx_dashboard():
    st.title("💱 FX Dashboard met EMA")
    # ... (fx-dashboard code hier, paginatie, filters, EMA, etc.)
    # brevity; hergebruik je bestaande FX-sectie

# === Functie: SPX Opties ===
def spx_opties():
    st.title("📈 SPX Optieprijzen")
    symbol = "^GSPC"
    col1, col2 = st.sidebar.columns(2)
    with col1:
        expiry = st.sidebar.date_input("Expiry datum", value=pd.to_datetime("today").date())
    with col2:
        strike = st.sidebar.number_input("Min strike", min_value=0.0, value=4000.0)
    data = yf.Ticker(symbol).option_chain(expiry.strftime("%Y-%m-%d")).calls
    df = data[data['strike'] >= strike]
    st.write(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['strike'], y=df['lastPrice'], mode='lines+markers', name='Optieprijs'))
    fig.update_layout(title=f"SPX Calls {expiry}", xaxis_title="Strike", yaxis_title="Last Price")
    st.plotly_chart(fig, use_container_width=True)

# === Functie: SP500 Index ===
def sp500_index():
    st.title("📊 S&P 500 Index")
    df = yf.download('^GSPC', period='1y', interval='1d')
    st.line_chart(df['Close'])

# === Functie: AEX Index ===
def aex_index():
    st.title("📊 AEX Index")
    df = yf.download('^AEX', period='1y', interval='1d')
    st.line_chart(df['Close'])

# === Functie: Macro ===
def macro():
    st.title("📋 Macro Indicatoren")
    st.write("# TODO: Voeg macro data toe")

# === Functie: Commodity ===
def commodity():
    st.title("⛽ Commodity Prijzen")
    st.write("# TODO: Voeg commodity data toe")

# === Functie: Sectoren ===
def sectoren():
    st.title("🏷️ Sector Performance")
    st.write("# TODO: Voeg sector data toe")

# === Roep juiste sectie aan ===
if menu == "FX Rates":
    fx_dashboard()
elif menu == "SPX Opties":
    spx_opties()
elif menu == "SP500 Index":
    sp500_index()
elif menu == "AEX Index":
    aex_index()
elif menu == "Macro":
    macro()
elif menu == "Commodity":
    commodity()
elif menu == "Sectoren":
    sectoren()
