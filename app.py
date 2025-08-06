# app.py
import streamlit as st
from streamlit_extras.switch_page_button import switch_page

st.set_page_config(page_title="Eastwood Dashboard", layout="wide")

st.markdown("""
# 📊 Market & Macro Dashboard

Welkom! Gebruik de navigatie links of onderstaande knoppen om een dashboard te openen:
""")

col1, col2 = st.columns(2)

with col1:
    if st.button("💱 Naar FX Rates"):
        switch_page("1_FX_Rates")

with col2:
    if st.button("📈 PPD_per_Days_to_Maturity"):
        switch_page("3_PPD_per_Days_to_Maturity.py")

st.markdown("---")
st.markdown("🧪 Macro, Indexen en Sectoren volgen binnenkort.")
