import wbdata
import json
# source = wbdata.get_sources()

# indicators = wbdata.get_indicators(source=2)
# with open("indicators.json", "w") as f:
#     json.dump(indicators, f, indent=2)

countries = wbdata.get_countries()
with open("countries.json", "w") as f:
    json.dump(countries, f, indent=2)

indicators = {    
    'EN.ATM.CO2E.KT': 'co2_emissions_kt',      # Total emissions
    'EN.ATM.CO2E.PC': 'co2_per_capita',        # Rate per person (most useful for "rate")
    'EN.ATM.CO2E.PP.GD': 'co2_per_gdp'}
data = wbdata.get_data(indicators, country="USA")