import wbdata

# Test each code separately
test_indicators = {
    "EN.GHG.CO2.MT.CE.AR5":    "co2_kt",           # Total CO₂ in Mt CO2e
    "EN.GHG.CO2.PC.CE.AR5":    "co2_per_capita",   # CO₂ per capita (t CO2e)
    "EN.GHG.CH4.MT.CE.AR5":    "methane_kt",       # Methane emissions (Mt CO2e) 
    "EN.GHG.N2O.MT.CE.AR5":    "nitrous_oxide_kt", # Nitrous oxide emissions (Mt CO2e)
    "NY.GDP.MKTP.CD":          "gdp_usd",          # GDP (current US$)
    "SP.POP.TOTL":             "population",        # Population, total
    "EG.USE.PCAP.KG.OE":       "energy_use_pc",    # Energy use per capita
    "EG.ELC.RNEW.ZS":          "renewable_pct",    # Renewable electricity output (%)
}

for code, name in test_indicators.items():
    print(f"Testing {code}...")
    try:
        df = wbdata.get_dataframe({code: name}, date=("2020", "2020"), source=2)
        print(f"  ✓ {code} works! Got {len(df)} rows")
    except Exception as e:
        print(f"  ✗ {code} FAILED: {e}")