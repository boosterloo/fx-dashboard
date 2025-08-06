# utils.py
import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# === Credentials ophalen (eerst Streamlit secrets, dan .env als fallback) ===
def get_supabase_client() -> Client:
    load_dotenv()  # Alleen nodig als .env gebruikt wordt

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        print("🔐 Streamlit secrets geladen.")
    except KeyError:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        print("🔐 .env gebruikt (lokale omgeving).")

    # Debug check (alleen voor eerste 10 tekens van de key)
    print("🔍 SUPABASE_URL:", url)
    print("🔍 SUPABASE_KEY start:", key[:10] if key else "❌")

    if not url or not key:
        raise ValueError("❌ Supabase URL of KEY ontbreekt in zowel Streamlit secrets als .env bestand.")

    return create_client(url, key)

# === Supabase client initiëren ===
supabase: Client = get_supabase_client()

# === Data ophalen ===
def get_supabase_data(table_name: str) -> pd.DataFrame:
    try:
        response = supabase.table(table_name).select("*").execute()
        data = response.data
        if not data or not isinstance(data, list):
            print(f"⚠️ Geen data in '{table_name}' of data is ongeldig.")
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ Fout bij ophalen Supabase data uit '{table_name}': {e}")
        return pd.DataFrame()
