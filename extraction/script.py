import json

# Load the authoritative country list with codes
with open('countries.json', 'r', encoding='utf-8') as f:
    countries_data = json.load(f)

# Load your extracted data with regions
with open('extracted_data.json', 'r', encoding='utf-8') as f:
    region_data = json.load(f)

# Create a mapping from country name to region
name_to_region = {}
for item in region_data:
    name_to_region[item['name'].lower()] = item['region']

# Add region information to countries_data
filtered_countries = []
matched = 0
unmatched = []

for country in countries_data:
    country_name = country['name']
    country_name_lower = country_name.lower()
    
    # Try to find matching region
    region = name_to_region.get(country_name_lower)
    
    if region:
        filtered_countries.append({
            'id': country['id'],
            'alpha2': country['alpha2'].upper(),  # Uppercase for World Bank format
            'alpha3': country['alpha3'].upper(),
            'name': country['name'],
            'region': region
        })
        matched += 1
    else:
        # Try matching without "Republic of", etc.
        cleaned_name = country_name.replace("Republic of", "").replace("United Republic of", "").replace(",", "").strip()
        if cleaned_name.lower() in name_to_region:
            region = name_to_region[cleaned_name.lower()]
            filtered_countries.append({
                'id': country['id'],
                'alpha2': country['alpha2'].upper(),
                'alpha3': country['alpha3'].upper(),
                'name': country['name'],
                'region': region
            })
            matched += 1
        else:
            unmatched.append(country_name)

# Save the enriched data
with open('enriched_countries.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_countries, f, indent=2, ensure_ascii=False)

# Print summary
print(f"Total countries in countries.json: {len(countries_data)}")
print(f"Successfully matched with regions: {matched}")
print(f"Unmatched countries: {len(unmatched)}")
print(f"\nEnriched data saved to 'enriched_countries.json'")

# Show unmatched countries
if unmatched:
    print(f"\nUnmatched countries (no region found in extracted_data.json):")
    for name in sorted(unmatched):
        print(f"  - {name}")

# Also create a CSV version
import csv
with open('enriched_countries.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['alpha2', 'name', 'region', 'alpha3', 'id'])
    writer.writeheader()
    for country in filtered_countries:
        writer.writerow({
            'alpha2': country['alpha2'],
            'name': country['name'],
            'region': country['region'],
            'alpha3': country['alpha3'],
            'id': country['id']
        })

print(f"\nCSV version saved to 'enriched_countries.csv'")

# Display first 10 as sample
print("\n" + "="*60)
print("SAMPLE OF ENRICHED DATA (first 10 countries):")
print("="*60)
for country in filtered_countries[:10]:
    print(f"{country['alpha2']}: {country['name']} -> {country['region']}")