with source as(
    select * from 
        {{ source('raw', 'gcp_emissions') }}
),

renamed as (
    select
        year                as emission_year,
        country             as country_name,
        emissions_mtco2     as emissions_mtco2
    
    from source
    where country is not null
        and year is not null
        and emissions_mtco2 is not null
)

select * from renamed