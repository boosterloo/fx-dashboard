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

@st.cache_data(ttl=3600)
def fetch_filtered_option_data(table_name, type_optie=None, expiration=None, strike=None):
    query = supabase.table(table_name).select("snapshot_date, bid, ask, last_price, implied_volatility, underlying_price, vix, type, expiration, strike, ppd")
    if type_optie:
        query = query.eq("type", type_optie)
    if expiration:
        query = query.eq("expiration", expiration)
    if strike:
        query = query.eq("strike", strike)

    try:
        response = query.execute()
        df = pd.DataFrame(response.data)
        if not df.empty and "snapshot_date" in df.columns:
            df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], utc=True, errors="coerce")
            df = df.sort_values("snapshot_date")
        return df
    except Exception as e:
        st.error(f"Fout bij ophalen van data: {e}")
        return pd.DataFrame()

st.title(":chart_with_upwards_trend: Prijsontwikkeling van een Optieserie")

st.sidebar.header(":mag: Filters")
defaultexp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

expirations = get_unique_values_chunked("spx_options2", "expiration")
strikes = get_unique_values_chunked("spx_options2", "strike")

type_optie = st.sidebar.selectbox("Type optie", ["call", "put"], index=1)
expiration = st.sidebar.selectbox("Expiratiedatum", expirations, index=0 if defaultexp not in expirations else expirations.index(defaultexp)) if expirations else None
strike = st.sidebar.selectbox("Strike (bijv. 5700)", strikes, index=0 if 5700 not in strikes else strikes.index(5700)) if strikes else None

df = fetch_filtered_option_data("spx_options2", type_optie, expiration, strike)

if df.empty:
    st.error("Geen data gevonden voor de opgegeven filters.")
    st.stop()

# Filter null underlying_price weg
df = df[df["underlying_price"].notnull()]

df["formatted_date"] = pd.to_datetime(df["snapshot_date"]).dt.date

min_date = df["snapshot_date"].min().date()
max_date = df["snapshot_date"].max().date()
date_range = st.slider("Selecteer peildatum range", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="%Y-%m-%d")
df = df[(df["snapshot_date"].dt.date >= date_range[0]) & (df["snapshot_date"].dt.date <= date_range[1])]

underlying = df["underlying_price"].iloc[-1] if "underlying_price" in df.columns else None

# Vectorized berekeningen
is_put = df["type"] == "put"
df["intrinsieke_waarde"] = (df["strike"] - df["underlying_price"]).clip(lower=0).where(is_put, (df["underlying_price"] - df["strike"]).clip(lower=0))
df["tijdswaarde"] = df["last_price"] - df["intrinsieke_waarde"]

# Dynamisch bereik helper
def get_dynamic_scale(series):
    return [series.min() * 0.98, series.max() * 1.02]

# ✅ Eén gecombineerde grafiek met dynamisch geschaalde tweede y-as (S&P)
with st.expander(":chart_with_upwards_trend: Prijsontwikkeling van de Optieserie", expanded=True):
    base = alt.Chart(df).encode(
        x=alt.X("formatted_date:T", title="Peildatum (datum)", timeUnit="yearmonthdate")
    )

    price_lines = base.transform_fold(
        ["bid", "ask", "last_price"],
        as_=["Type", "Prijs"]
    ).mark_line(point=alt.OverlayMarkDef(filled=True, size=100)).encode(
        y=alt.Y("Prijs:Q", title="Optieprijs (linkeras)", scale=alt.Scale(domain=get_dynamic_scale(df[["bid", "ask", "last_price"]].values.flatten()))),
        color=alt.Color("Type:N", title="Prijssoort", scale=alt.Scale(scheme="category10")),
        tooltip=["formatted_date:T", "Type:N", "Prijs:Q"]
    )

    sp_line = base.mark_line(strokeDash=[4, 4]).encode(
        y=alt.Y(
            "underlying_price:Q",
            axis=alt.Axis(title="S&P Koers (rechteras)", orient="right"),
            scale=alt.Scale(domain=get_dynamic_scale(df["underlying_price"]))
        ),
        color=alt.value("gray"),
        tooltip=["formatted_date:T", "underlying_price:Q"]
    )

    combined_chart = alt.layer(price_lines, sp_line).resolve_scale(y='independent').properties(
        height=500,
        title="Bid, Ask, LastPrice en S&P Koers door de tijd"
    )

    st.altair_chart(combined_chart, use_container_width=True)

# ✅ IV & VIX met onafhankelijke assen
with st.expander(":chart_with_upwards_trend: Implied Volatility (IV) en VIX", expanded=True):
    if "implied_volatility" in df.columns and df["implied_volatility"].notna().any():
        df_iv = df[["formatted_date", "implied_volatility", "vix"]].dropna()

        iv_line = alt.Chart(df_iv).mark_line(point=True).encode(
            x="formatted_date:T",
            y=alt.Y("implied_volatility:Q", title="IV (linkeras)", scale=alt.Scale(domain=get_dynamic_scale(df_iv["implied_volatility"]))),
            color=alt.value("red"),
            tooltip=["formatted_date:T", "implied_volatility"]
        )

        vix_line = alt.Chart(df_iv).mark_line(point=True).encode(
            x="formatted_date:T",
            y=alt.Y("vix:Q", axis=alt.Axis(title="VIX (rechteras)", orient="right"), scale=alt.Scale(domain=get_dynamic_scale(df_iv["vix"]))),
            color=alt.value("blue"),
            tooltip=["formatted_date:T", "vix"]
        )

        chart = alt.layer(iv_line, vix_line).resolve_scale(y='independent').properties(
            height=300,
            title="Implied Volatility (IV) en VIX"
        )

        st.altair_chart(chart, use_container_width=True)

# ✅ Analyse met dubbele y-as voor PPD/intrinsiek & tijdswaarde
with st.expander(":chart_with_upwards_trend: Analyse van Optiewaarden", expanded=True):
    analyse_kolommen = ["formatted_date"]
    for kolom in ["intrinsieke_waarde", "tijdswaarde", "ppd"]:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")
            if df[kolom].notna().any():
                analyse_kolommen.append(kolom)

    if len(analyse_kolommen) > 1:
        analysis_df = df[analyse_kolommen].dropna(subset=analyse_kolommen[1:], how="any")

        if not analysis_df.empty:
            melted_df = analysis_df.melt(id_vars="formatted_date", value_vars=analyse_kolommen[1:], var_name="Type", value_name="Waarde")

            base = alt.Chart(melted_df).encode(
                x=alt.X("formatted_date:T", title="Peildatum (datum)")
            )

            left = base.transform_filter("datum.Type != 'tijdswaarde'").mark_line(point=True).encode(
                y=alt.Y("Waarde:Q", scale=alt.Scale(domain=get_dynamic_scale(melted_df[melted_df["Type"] != "tijdswaarde"]["Waarde"]))),
                color=alt.Color("Type:N", scale=alt.Scale(scheme="set1")),
                tooltip=["formatted_date:T", "Type:N", "Waarde:Q"]
            )

            right = base.transform_filter("datum.Type == 'tijdswaarde'").mark_line(point=True).encode(
                y=alt.Y("Waarde:Q", axis=alt.Axis(title="Tijdswaarde", orient="right"), scale=alt.Scale(domain=get_dynamic_scale(melted_df[melted_df["Type"] == "tijdswaarde"]["Waarde"]))),
                color=alt.Color("Type:N", scale=alt.Scale(scheme="set1")),
                tooltip=["formatted_date:T", "Type:N", "Waarde:Q"]
            )

            chart = alt.layer(left, right).resolve_scale(y='independent').properties(
                height=400,
                title="Tijdswaarde en premium per dag (PPD)"
            )

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Geen geldige numerieke data.")
    else:
        st.info("Niet genoeg data beschikbaar voor analysegrafiek.")
