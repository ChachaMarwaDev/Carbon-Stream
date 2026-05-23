import cdsapi

client = cdsapi.Client()

dataset = "reanalysis-era5-single-levels-monthly-means"
request = {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": ["2m_temperature", "total_precipitation"],
    "year": ["2020", "2021", "2022", "2023"],
    "month": ["01","02","03","04","05","06",
               "07","08","09","10","11","12"],
    "time": ["00:00"],
    "data_format": "netcdf",
    "area": [55, 6, 47, 15],
}
target = "de_era5_monthly.nc"

client.retrieve(dataset, request, target)
