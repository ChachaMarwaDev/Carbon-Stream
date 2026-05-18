import wbdata
import psycopg2
from psycopg2 import sql
import pandas as pd
from datetime import datetime

# 1. Fetch data from World Bank API
indicator_code = "EN.ATM.CO2E.KT"  # CO2 emissions (kt)
country_code = "USA"

# Get the data
data = wbdata.get_data(indicator_code, country=country_code)

# Convert to DataFrame
df = pd.DataFrame([
    {
        'country': d['country']['value'],
        'year': int(d['date']),
        'co2_emissions_kt': d['value']
    }
    for d in data if d['value'] is not None
])

print(f"Fetched {len(df)} years of CO2 data for USA")

# 2. Database connection parameters
conn_params = {
    'host': 'myimage',      # or 'db' if running in Docker network
    'port': 5432,
    'database': 'carbon_stream',
    'user': 'root',
    'password': 'root'
}

try:
    # 3. Connect to PostgreSQL
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    
    # 4. Create table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS world_bank_co2 (
        id SERIAL PRIMARY KEY,
        country VARCHAR(100),
        year INTEGER,
        co2_emissions_kt NUMERIC,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(country, year)
    )
    """
    cur.execute(create_table_query)
    
    # 5. Insert or update data
    insert_query = """
    INSERT INTO world_bank_co2 (country, year, co2_emissions_kt)
    VALUES (%s, %s, %s)
    ON CONFLICT (country, year) 
    DO UPDATE SET co2_emissions_kt = EXCLUDED.co2_emissions_kt
    """
    
    for _, row in df.iterrows():
        cur.execute(insert_query, (row['country'], row['year'], row['co2_emissions_kt']))
    
    conn.commit()
    print(f"Successfully inserted/updated {len(df)} records")
    
    # 6. Verify the data
    cur.execute("SELECT country, year, co2_emissions_kt FROM world_bank_co2 ORDER BY year DESC LIMIT 5")
    print("\nLast 5 years of data:")
    for row in cur.fetchall():
        print(f"  {row[0]}, {row[1]}: {row[2]:,.0f} kt")
        
except psycopg2.Error as e:
    print(f"Database error: {e}")
    if conn:
        conn.rollback()
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()