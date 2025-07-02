import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client
import os
from datetime import datetime, timedelta

# Set page config
st.set_page_config(page_title="Prijsontwikkeling van een Optieserie", layout="wide")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase configuratie ontbreekt. Controleer SUPABASE_URL en SUPABASE_KEY.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Haal unieke expiraties en strikes op in batches
@st.cache_data(ttl=3600)
def get_unique_values_chunked(table_name, column, batch_size=1000):
    offset = 0
    all_values = set()
    while True:
        try:
            query = supabase.table(table_name).select(column).range(offset, offset + batch_size - 1)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                if column in row:
                    all_values.add(row[column])
            offset += batch_size
        except Exception as e:
            st.warning(f"Fout bij ophalen van waarden voor {column}: {e}")
            break
    return sorted(all_values)

# Fetch data for specific filters in chunks
@st.cache_data(ttl=3600)
def fetch_filtered_option_data(table_name, type_optie=None, expiration=None, strike=None, batch_size=1000):
    offset = 0
    all_data = []
    while True:
        try:
            query = supabase.table(table_name).select("snapshot_date, bid, ask, last_price, implied_volatility, underlying_price, vix, type, expiration, strike, ppd").range(offset, offset + batch_size - 1)
            response = query.execute()
            if not response.data:
                break
            for row in response.data:
                if (type_optie is None or row.get("type") == type_optie) and \
                   (expiration is None or row.get("expiration") == expiration) and \
                   (strike is None or row.get("strike") == strike):
                    all_data.append(row)
            offset += batch_size
        except Exception as e:
            st.error(f"Fout bij ophalen van data: {e}")
            break
    df = pd.DataFrame(all_data)
    if not df.empty and "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
        df = df.sort_values("snapshot_date")
    return df

st.title(":chart_with_upwards_trend: Prijsontwikkeling van een Optieserie")

# Sidebar filters
st.sidebar.header(":mag: Filters")
defaultexp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# Haal beschikbare expiraties en strikes op
expirations = get_unique_values_chunked("spx_options2", "expiration")
strikes = get_unique_values_chunked("spx_options2", "strike")

# Filters
type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=1)
expiration = st.sidebar.selectbox("Expiratiedatum", expirations, index=0 if defaultexp not in expirations else expirations.index(defaultexp)) if expirations else None
strike = st.sidebar.selectbox("Strike (bijv. 5700)", strikes, index=0 if 5700 not in strikes else strikes.index(5700)) if strikes else None

# Fetch data based on filters
df = fetch_filtered_option_data("spx_options2", type_optie, expiration, strike)

if df.empty:
    st.error("Geen data gevonden voor de opgegeven filters.")
    st.stop()

# Format datum
df["formatted_date"] = pd.to_datetime(df["snapshot_date"]).dt.strftime("%Y-%m-%d")

# Bereken aanvullende metrics
underlying = df["underlying_price"].iloc[-1] if "underlying_price" in df.columns else None
df["intrinsieke_waarde"] = df.apply(lambda row: max(0, row["strike"] - row["underlying_price"]) if row["type"] == "put" else max(0, row["underlying_price"] - row["strike"]), axis=1)
df["tijdswaarde"] = df["last_price"] - df["intrinsieke_waarde"]

# Implied Volatility + VIX
with st.expander(":chart_with_upwards_trend: Implied Volatility (IV) en VIX", expanded=True):
    if "implied_volatility" in df.columns and df["implied_volatility"].notna().any():
        base_iv = alt.Chart(df).encode(x=alt.X("formatted_date:T", title="Peildatum (datum)", timeUnit="yearmonthdate"))
        iv_line = base_iv.mark_line(point=True).encode(
            y=alt.Y("implied_volatility:Q", title="Implied Volatility"),
            color=alt.value("#1f77b4"),
            tooltip=["formatted_date:T", "implied_volatility"]
        ).properties(title="Implied Volatility")

        vix_line = base_iv.mark_line(point=True).encode(
            y=alt.Y("vix:Q", axis=alt.Axis(title="VIX"), scale=alt.Scale(zero=False)),
            color=alt.value("#ff7f0e"),
            tooltip=["formatted_date:T", "vix"]
        ).properties(title="VIX")

        legend_data = pd.DataFrame({
            "Legende": ["Implied Volatility", "VIX"],
            "kleur": ["#1f77b4", "#ff7f0e"],
            "dummy_x": [df["formatted_date"].iloc[-1]] * 2,
            "dummy_y": [df["implied_volatility"].max(), df["vix"].max()]
        })

        legend = alt.Chart(legend_data).mark_point(filled=True, size=100).encode(
            x="dummy_x:T",
            y="dummy_y:Q",
            color=alt.Color("Legende:N", scale=alt.Scale(domain=legend_data["Legende"], range=legend_data["kleur"]))
        ).properties(title="Legenda")

        iv_chart = alt.layer(iv_line, vix_line, legend).resolve_scale(y="independent").properties(height=300)

        st.altair_chart(iv_chart, use_container_width=True)

# Analyse van Optiewaarden
with st.expander(":chart_with_upwards_trend: Analyse van Optiewaarden", expanded=True):
    analyse_kolommen = ["formatted_date"]
    for kolom in ["intrinsieke_waarde", "tijdswaarde", "ppd"]:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")
            if df[kolom].notna().any():
                analyse_kolommen.append(kolom)
            else:
                st.warning(f"Waarschuwing: Kolom {kolom} bevat geen geldige numerieke waarden.")

    if len(analyse_kolommen) > 1:
        analysis_df = df[analyse_kolommen].dropna(subset=analyse_kolommen[1:], how="any")

        if not analysis_df.empty and analysis_df[analyse_kolommen[1:]].apply(lambda x: pd.api.types.is_numeric_dtype(x)).all():
            try:
                base = alt.Chart(analysis_df).encode(
                    x=alt.X("formatted_date:T", title="Peildatum (datum)", timeUnit="yearmonthdate")
                )
                charts = []
                for col in analyse_kolommen[1:]:
                    chart = base.mark_line(point=True).encode(
                        y=alt.Y(f"{col}:Q", title="Waarde"),
                        color=alt.value({
                            "intrinsieke_waarde": "#1f77b4",
                            "tijdswaarde": "#ff7f0e",
                            "ppd": "#2ca02c"
                        }.get(col)),
                        tooltip=["formatted_date:T", f"{col}:Q"]
                    ).properties(title=col)
                    charts.append(chart)

                legend_df = pd.DataFrame({
                    "Legende": analyse_kolommen[1:],
                    "kleur": ["#1f77b4", "#ff7f0e", "#2ca02c"][:len(analyse_kolommen)-1],
                    "dummy_x": [analysis_df["formatted_date"].iloc[-1]] * (len(analyse_kolommen)-1),
                    "dummy_y": [analysis_df[col].max() for col in analyse_kolommen[1:]]
                })

                legend = alt.Chart(legend_df).mark_point(filled=True, size=100).encode(
                    x="dummy_x:T",
                    y="dummy_y:Q",
                    color=alt.Color("Legende:N", scale=alt.Scale(domain=legend_df["Legende"], range=legend_df["kleur"]))
                ).properties(title="Legenda")

                combined_chart = alt.layer(*charts, legend).resolve_scale(y="independent").properties(
                    height=400,
                    title="Tijdswaarde en premium per dag (PPD)"
                )
                st.altair_chart(combined_chart, use_container_width=True)
            except Exception as e:
                st.error(f"Fout: {e}")
        else:
            st.info("Geen geldige numerieke data.")
    else:
        st.info("Niet genoeg data beschikbaar voor analysegrafiek.")
