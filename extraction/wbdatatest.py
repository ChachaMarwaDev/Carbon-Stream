import wbdata
import psycopg2
from psycopg2.extras import execute_values

# Database connection
DB_CONFIG = {
    "host": "myimage", 
    "database": "carbon_stream", 
    "user": "root", 
    "password": "root" }

# Fetch data
all_data = wbdata.get_data("EN.GHG.ALL.LU.MT.CE.AR5", country="USA")

# Connect and create table
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS ghg_emissions (
        id SERIAL PRIMARY KEY,
        year INTEGER,
        value DECIMAL
    )
""")

# Process in chunks
chunk_size = 10
for i in range(0, len(all_data), chunk_size):
    chunk = all_data[i:i + chunk_size]
    
    # Prepare records
    records = [(int(r['date']), float(r['value'])) for r in chunk if r['value']]
    
    # Insert chunk
    execute_values(cursor, "INSERT INTO ghg_emissions (year, value) VALUES %s", records)
    conn.commit()
    print(f"Uploaded chunk {i//chunk_size + 1}")

# Cleanup
cursor.close()
conn.close()
print("Done!")