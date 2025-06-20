import streamlit as st

# === Pagina-instellingen
st.set_page_config(page_title="FX Dashboard", layout="wide")

# === Sidebar navigatie
st.sidebar.title("📊 Navigatie")
page = st.sidebar.selectbox("Kies een pagina", ["Home", "SPX Opties"])

# === Routing
if page == "Home":
    st.title("Welkom bij het FX Dashboard")
    st.write("Gebruik de sidebar om een pagina te kiezen.")

elif page == "SPX Opties":
    import spx_opties
