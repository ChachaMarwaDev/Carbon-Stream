with source as (
    select * from
        {{ source('raw', 'wb_emissions') }}
),

renamed as (
    select
        country             as country_name,
        iso2_code           as iso2,
        iso3_code           as iso3,
        region              as region_name,
        income_level        as income_level,
        year                as observation_year,
        co2_kt              as co2_kt,
        co2_per_capita      as co2_per_capita,
        methane_kt          as methane_kt,
        nitrous_oxide_kt    as nitrous_oxide_kt

    from
        source

    where
        country is not null
        and year is not null
        and iso3_code is not null
)

select * from renamed
