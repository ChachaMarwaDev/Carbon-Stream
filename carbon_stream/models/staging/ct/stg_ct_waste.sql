with country as (
    select * from {{ source('raw', 'ct_waste_country') }}
), 

sources as (
    select * from {{ source('raw', 'ct_waste_sources') }}
),

sources_agg as (
    select
        iso3_country,
        subsector,
        gas,
        date_part('year', start_time)       as emission_year,
        count(distinct source_id)           as facility_count,
        sum(emissions_quantity)             as sources_emission_tonnes

    from sources
    where iso3_country is not null
    group by iso3_country, subsector, gas, date_part('year', start_time)
),

final as (
    select
        c.iso3_country,
        c.sector,
        c.subsector,
        date_part('year', c.start_time)     as emission_year,
        c.gas,
        c.emissions_quantity                as country_emission_tonnes,
        s.facility_count,
        s.sources_emission_tonnes

    from country c
    left join sources_agg s
        on  c.iso3_country  = s.iso3_country
        and c.subsector     = s.subsector
        and c.gas           = s.gas
        and date_part('year', c.start_time) = s.emission_year

    where c.iso3_country is not null
      and c.emissions_quantity is not null
)

select * from final
