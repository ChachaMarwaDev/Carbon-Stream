with source as(
    select * from
        {{ source('raw', 'ct_buildings_country') }}
), 


renamed as (
    select
    iso3_country            as iso3,
    sector,
    subsector, 
    date_part('year', start_time)         as emission_year,
    gas,
    emissions_quantity      as emission_tonnes

from 
    source

where iso3_country is not null
    and emissions_quantity is not null
)

select * from renamed