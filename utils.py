# utils.py
import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# === Supabase initiëren ===
load_dotenv()  # .env laden

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL of KEY ontbreekt in het .env bestand.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_data(table_name: str) -> pd.DataFrame:
    try:
        response = supabase.table(table_name).select("*").execute()
        data = response.data
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ Fout bij ophalen Supabase data: {e}")
        return pd.DataFrame()
