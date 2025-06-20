import streamlit as st

# Pagina-instellingen
st.set_page_config(page_title="Eastwood Dashboard", layout="wide")

# Welkomsttekst en navigatie
st.markdown("""
# 📊 Welkom bij het Eastwood Dashboard

Welkom! Gebruik de navigatie links óf onderstaande links om een dashboard te kiezen:

---

### 📂 Beschikbare Dashboards

- [💱 FX Rates](?page=1_FX_Rates)
- [📈 SPX Opties](?page=2_SPX_Opties)
- 🧪 Macro, Indexen, Sectoren (binnenkort)

---

""", unsafe_allow_html=True)
