import streamlit as st

st.set_page_config(page_title="Eastwood Quantum Analytics", layout="wide")

st.sidebar.title("🔍 Navigatie")
selection = st.sidebar.radio("Kies onderdeel:", [
    "FX Rates", "SPX Opties", "SP500 Index", "AEX Index",
    "Macro", "Commodity", "Sectoren", "Yield Curve"
])

if selection == "SPX Opties":
    import spx_opties
else:
    st.markdown(f"📌 Sectie '{selection}' nog in ontwikkeling")
