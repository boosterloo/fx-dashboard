import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os
from datetime import date

# Set page config
st.set_page_config(page_title="SPX Opties", layout="wide")

# Cache data loading to improve performance
@st.cache_data
def load_data():
    try:
        # Validate environment variables
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
            return None

        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Fetch data
        table_name = "spx_options2"
        response = supabase.table(table_name).select("*").execute()

        # Check for errors in response
        if response.data is None:
            st.error(f"Fout bij ophalen data: {response}")
            return None

        # Create DataFrame
        df = pd.DataFrame(response.data)
        
        # Validate required columns
        required_columns = ["snapshot_date", "expiration", "type", "strike", "ppd"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Ontbrekende kolommen in data: {', '.join(missing_columns)}")
            return None

        # Convert columns
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
        df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce").dt.date
        return df
    except Exception as e:
        st.error(f"Unexpected error loading data: {str(e)}")
        return None

# Load data
df = load_data()
if df is None or df.empty:
    st.warning("Geen data beschikbaar in Supabase-tabel.")
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Option type filter
type_optie = st.sidebar.selectbox(
    "Type optie",
    sorted(df["type"].dropna().unique()),
    help="Selecteer het type optie (Call/Put)"
)

# Filter by type
df_type = df[df["type"] == type_optie]

# Expiration date filter
beschikbare_expiraties = sorted(df_type["expiration"].dropna().unique())
if not beschikbare_expiraties:
    st.warning(f"Geen expiraties beschikbaar voor {type_optie}.")
    st.stop()
expiratie = st.sidebar.selectbox(
    "Expiratiedatum",
    beschikbare_expiraties,
    format_func=lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else x,
    help="Selecteer de expiratiedatum"
)

# Strike filter
df_expiration = df_type[df_type["expiration"] == expiratie]
beschikbare_strikes = sorted(df_expiration["strike"].dropna().unique())
if not beschikbare_strikes:
    st.warning(f"Geen strikes beschikbaar voor {type_optie} met expiratie {expiratie}.")
    st.stop()
strike = st.sidebar.selectbox(
    "Strike",
    beschikbare_strikes,
    help="Selecteer de strike prijs"
)

# Filter data
df_filtered = df_expiration[df_expiration["strike"] == strike].sort_values("snapshot_date")

# Display
st.title("📈 SPX Opties: PPD-verloop per Strike")
st.markdown(f"🔍 {len(df_filtered)} rijen gevonden voor {type_optie.upper()} {strike} exp. {expiratie}")

# Show data table
st.dataframe(
    df_filtered[["snapshot_date", "ppd", "last_price", "bid", "ask", "implied_volatility"]],
    use_container_width=True
)

# Create Altair chart (use line for time-series)
chart = alt.Chart(df_filtered).mark_line(point=True).encode(
    x=alt.X("snapshot_date:T", title="Peildatum"),
    y=alt.Y("ppd:Q", title="Premium per dag (PPD)"),
    tooltip=[
        alt.Tooltip("snapshot_date:T", title="Datum", format="%Y-%m-%d"),
        alt.Tooltip("ppd:Q", title="PPD", format=".2f"),
        alt.Tooltip("last_price:Q", title="Laatste prijs", format=".2f"),
        alt.Tooltip("bid:Q", title="Bid", format=".2f"),
        alt.Tooltip("ask:Q", title="Ask", format=".2f")
    ]
).interactive().properties(
    title=f"PPD-verloop — {type_optie.upper()} {strike} exp. {expiratie}",
    height=400
)

st.altair_chart(chart, use_container_width=True)