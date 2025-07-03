# utils.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

@staticmethod
def init_supabase() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)

def get_supabase_data(table_name: str):
    supabase = init_supabase()
    response = supabase.table(table_name).select("*").execute()
    return response.data
