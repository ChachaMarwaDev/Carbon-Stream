import wbdata
import pandas as pd

# Current, verified emission indicators
emission_indicators = {
    'EN.ATM.CO2E.KT': 'co2_emissions_kt',      # Total emissions
    'EN.ATM.CO2E.PC': 'co2_per_capita',        # Rate per person (most useful for "rate")
    'EN.ATM.CO2E.PP.GD': 'co2_per_gdp',        # Efficiency metric
}

countries = ['US']

try:
    df_raw = wbdata.get_dataframe(
        indicators=emission_indicators,
        country=countries
    )
    
    df_landing = df_raw.reset_index()
    df_landing['year'] = pd.to_datetime(df_landing['date']).dt.year
    
    print(f"Success! Landing: {len(df_landing)} records")
    print(df_landing.head())
    
except Exception as e:
    print(f"Error: {e}")