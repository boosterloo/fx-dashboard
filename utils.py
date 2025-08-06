import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("❌ Supabase URL of KEY ontbreekt in zowel Streamlit secrets als .env bestand.")
    return create_client(url, key)

supabase: Client = get_supabase_client()

def get_supabase_data_in_chunks(table: str, chunk_size: int = 1000) -> pd.DataFrame:
    all_data = []
    offset = 0

    while True:
        query = supabase.table(table).select("*").range(offset, offset + chunk_size - 1)
        response = query.execute()
        data_chunk = response.data

        if not data_chunk:
            break

        all_data.extend(data_chunk)
        offset += chunk_size

    if not all_data:
        return pd.DataFrame()

    return pd.DataFrame(all_data)
