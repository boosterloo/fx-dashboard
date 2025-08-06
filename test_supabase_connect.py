import httpx

SUPABASE_URL = "https://iojddecmsygazpraaafa.supabase.co/rest/v1/"
try:
    response = httpx.get(SUPABASE_URL, timeout=10)
    print("✅ Verbonden met Supabase:", response.status_code)
except Exception as e:
    print("❌ Verbindingsfout:", e)
