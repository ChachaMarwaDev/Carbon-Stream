import xarray as xr
import psycopg2
from psycopg2 import sql
import pandas as pd
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

create_table_query = """
CREATE TABLE IF NOT EXISTS era5_monthly_data(
    id SERIAL PRIMARY KEY,
    country VARCHAR(10) NOT NULL,
    time DATE NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    temperature_2m FLOAT,
    total_precipitation FLOAT
);
"""

cursor.execute(create_table_query)
conn.commit()

# countries to be used
countries = ["us_era5_monthly.nc", "au_era5_monthly.nc", 
             "br_era5_monthly.nc", "cn_era5_monthly.nc", 
             "de_era5_monthly.nc", "fr_era5_monthly.nc",
             "gb_era5_monthly.nc", "in_era5_monthly.nc"]

# Function to extract country name from filename
def get_country_name(filename):
    return filename.split('_')[0]

# Insert data for each country
for country_file in countries:
    country_name = get_country_name(country_file)
    print(f"Processing {country_name}...")

    try:
        # Open the netCDF file
        ds = xr.open_dataset(country_file)

        # Extract variables (adjust variable names as per your ERA5 file)
        time = ds['time'].values
        latitudes = ds['latitude'].values
        longitudes = ds['longitude'].values
        
        # Get data variables (adjust these based on your actual file)
        temperature_2m = ds['t2m'].values if 't2m' in ds.variables else None
        precipitation = ds['tp'].values if 'tp' in ds.variables else None

        # Convert to DataFrame for easier handling
        data_list = []
        
        for t_idx, t in enumerate(time):
            for lat_idx, lat in enumerate(latitudes):
                for lon_idx, lon in enumerate(longitudes):
                    row = {
                        'country': country_name,
                        'time': pd.Timestamp(t),
                        'latitude': float(lat),
                        'longitude': float(lon),
                        'temperature_2m': float(temperature_2m[t_idx, lat_idx, lon_idx]) if temperature_2m is not None else None,
                        'total_precipitation': float(precipitation[t_idx, lat_idx, lon_idx]) if precipitation is not None else None
                    }
                    data_list.append(row)  # <-- FIXED: This was outside the loop

        # Insert in batches for better performance
        if data_list:
            insert_query = """
            INSERT INTO era5_monthly_data 
            (country, time, temperature_2m, total_precipitation, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            batch_size = 1000
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i+batch_size]
                batch_values = [(
                    row['country'], 
                    row['time'], 
                    row['temperature_2m'], 
                    row['total_precipitation'],  # <-- FIXED: Changed from 'precipitation' to 'total_precipitation'
                    row['latitude'], 
                    row['longitude']
                ) for row in batch]
                cursor.executemany(insert_query, batch_values)
                conn.commit()
                print(f"  Inserted {len(batch)} records for {country_name}")
            
            ds.close()
            print(f"Completed {country_name}\n")

    except Exception as e:
        print(f"Error processing {country_file}: {e}")
        conn.rollback()

# Close connection
cursor.close()
conn.close()
print("All data processed successfully!")