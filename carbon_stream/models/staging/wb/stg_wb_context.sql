with source as (
    select * from 
        {{ source('raw', 'wb_context') }}
),

renamed as (
    select 
        country         as country_name,
        iso3_code       as iso3,
        region          as region_name,
        income_level,
        year            as observation_year,
        gdp_usd,
        population,
        energy_use_pc,
        renewable_pct
    
    from 
        source

    where
        country is not null
        and year is not null
        and iso3_code is not null
)

select * from renamed