import wbdata
import psycopg2
from psycopg2.extras import execute_values

# Database connection
DB_CONFIG = {
    "host": "myimage", 
    "database": "carbon_stream", 
    "user": "root", 
    "password": "root"
}

# Define countries with their alpha-3 codes
countries = {
    'USA': 'United States',
    'CAN': 'Canada',
    'MEX': 'Mexico',
    'BRA': 'Brazil',
    'DEU': 'Germany'
}

# Connect to database
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Drop existing table if it exists (to ensure clean slate)
cursor.execute("DROP TABLE IF EXISTS ghg_emissions CASCADE")
print("✓ Dropped existing table (if any)")

# Create table with correct schema including country_code
cursor.execute("""
    CREATE TABLE ghg_emissions (
        id SERIAL PRIMARY KEY,
        country_code VARCHAR(3),
        year INTEGER,
        value DECIMAL,
        UNIQUE(country_code, year)
    )
""")
conn.commit()
print("✓ Created new table with country_code column")

# Process each country
for country_code, country_name in countries.items():
    try:
        print(f"\n📊 Fetching data for {country_name} ({country_code})...")
        
        # Get data using the country alpha-3 code
        all_data = wbdata.get_data("EN.GHG.ALL.LU.MT.CE.AR5", country=country_code)
        
        if not all_data:
            print(f"  ⚠ No data found for {country_code}")
            continue
        
        # Convert to list for processing
        data_list = list(all_data)
        
        # Filter out None values and prepare records
        records = []
        for item in data_list:
            if item.get('value') is not None:
                records.append((
                    country_code,
                    int(item['date']), 
                    float(item['value'])
                ))
        
        if not records:
            print(f"  ⚠ No valid data records for {country_code}")
            continue
        
        # Chunk limiter pattern
        chunk_size = 10
        total_chunks = (len(records) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            
            # Insert chunk using execute_values
            execute_values(
                cursor, 
                """
                INSERT INTO ghg_emissions (country_code, year, value) 
                VALUES %s
                ON CONFLICT (country_code, year) 
                DO UPDATE SET value = EXCLUDED.value
                """, 
                chunk
            )
            conn.commit()
            
            chunk_num = i // chunk_size + 1
            print(f"  ✅ Inserted chunk {chunk_num}/{total_chunks}: {len(chunk)} records")
        
        print(f"  ✓ Successfully loaded {len(records)} total records for {country_name}")
        
    except Exception as e:
        print(f"  ❌ Error loading data for {country_code}: {e}")
        conn.rollback()

# Show summary
cursor.execute("SELECT country_code, COUNT(*) as record_count FROM ghg_emissions GROUP BY country_code ORDER BY country_code")
summary = cursor.fetchall()

print("\n" + "="*50)
print("📈 FINAL SUMMARY:")
for country_code, count in summary:
    print(f"  {country_code}: {count} records")
print("="*50)

# Cleanup
cursor.close()
conn.close()
print("\n✅ Done! All countries processed successfully.")