import os
from supabase import create_client
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def get_supabase_data_in_chunks(table_name: str, chunk_size: int = 1000) -> pd.DataFrame:
    all_data = []
    offset = 0
    while True:
        response = (
            supabase.table(table_name)
            .select("*")
            .range(start=offset, end=offset + chunk_size - 1)
            .execute()
        )
        if not response.data:
            break
        all_data.extend(response.data)
        offset += chunk_size
    return pd.DataFrame(all_data)
