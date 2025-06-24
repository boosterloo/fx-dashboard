if not df_filtered_tab2.empty and selected_snapshot_date:
    # Filter for selected snapshot date
    df_maturity = df_filtered_tab2[df_filtered_tab2["snapshot_date"] == pd.to_datetime(selected_snapshot_date, utc=True)].copy()
    
    # Calculate days to maturity for all expirations
    df_maturity["days_to_maturity"] = (df_maturity["expiration"] - df_maturity["snapshot_date"]).dt.days
    # Filter out invalid or negative days
    df_maturity = df_maturity[df_maturity["days_to_maturity"] > 0]
    # Calculate PPD using bid and prevent division by zero
    df_maturity["ppd"] = df_maturity["bid"] / df_maturity["days_to_maturity"].replace(0, 0.01)
    
    # Debug: Show initial row count
    initial_rows = len(df_maturity)
    st.write("Aantal rijen na snapshot-filter:", initial_rows)
    invalid_ppd = df_maturity["ppd"].isna().sum()
    st.write(f"Aantal rijen met ongeldige PPD (NaN): {invalid_ppd}")
    
    # Show table
    st.write("Gefilterde data:", df_maturity)
    
    # Chart (using all valid data)
    chart2 = alt.Chart(df_maturity).mark_line(point=True).encode(
        x=alt.X("days_to_maturity:Q", title="Dagen tot Maturity", sort=None),
        y=alt.Y("ppd:Q", title="Premium per Dag (PPD)", scale=alt.Scale(zero=True, nice=True)),
        tooltip=["expiration", "days_to_maturity", "ppd", "strike"]
    ).interactive().properties(
        title=f"PPD per Dag tot Maturity — {type_optie.upper()} {strike}",
        height=400
    )
    st.altair_chart(chart2, use_container_width=True)
    
    # Suggestie voor gunstige maturity (moved to bottom)
    if not df_maturity["ppd"].empty:
        max_ppd = df_maturity["ppd"].max()
        best_maturity = df_maturity.loc[df_maturity["ppd"].idxmax(), "days_to_maturity"]
        st.write(f"Gunstige maturity om te schrijven/kopen: ~{best_maturity} dagen (max PPD: {max_ppd:.4f})")