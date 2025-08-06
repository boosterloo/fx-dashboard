import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

def get_supabase_client() -> Client:
    # Probeer eerst via Streamlit secrets
    url = os.environ.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        load_dotenv()  # .env fallback
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("❌ Supabase URL of KEY ontbreekt in zowel Streamlit secrets als .env bestand.")

    return create_client(url, key)

supabase: Client = get_supabase_client()

def get_supabase_data_in_chunks(table_name: str, chunk_size: int = 1000) -> pd.DataFrame:
    all_data = []
    offset = 0

    while True:
        response = (
            supabase.table(table_name)
            .select("*")
            .range(offset, offset + chunk_size - 1)
            .execute()
        )

        data = response.data
        if not data:
            break

        all_data.extend(data)
        offset += chunk_size

    return pd.DataFrame(all_data)
