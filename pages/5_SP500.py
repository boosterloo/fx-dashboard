import streamlit as st
import pandas as pd
from utils import get_supabase_data

st.set_page_config(page_title="📈 S&P 500 Dashboard", layout="wide")
st.title("📈 S&P 500 Dashboard")

df = get_supabase_data("sp500_data")

st.subheader("✅ Debug output")
st.write("Type:", type(df))
st.write("Is DataFrame:", isinstance(df, pd.DataFrame))
st.write("Aantal rijen:", len(df) if isinstance(df, pd.DataFrame) else "nvt")
st.write(df.head())
