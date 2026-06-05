with country as (
    select * from 
        {{ source('raw', 'ct_power_country') }}
), 

ownership as (
    select * from
        {{ source('raw', 'ct_power_ownership') }}
),

sources as (
    select * from
        {{ source('raw', 'ct_power_sources') }}
),

sources_with_ownership as (
    select
        s.source_id,
        s.source_name,
        s.iso3_country,
        s.subsector,
        s.gas,
        date_part('year', s.start_time)     as emission_year,
        s.emissions_quantity                as emission_tonnes,
        s.capacity,
        s.capacity_units,
        o.parent_name,
        o.parent_entity_type,               -- state, private, etc.
        o.overall_share_percent,
        o.source_operator

    from sources s
    left join ownership o on s.source_id = o.source_id
),

sources_agg as (
    select
        iso3_country,
        subsector,
        emission_year,
        gas,
        count(distinct source_id)           as facility_count,
        count(distinct parent_name)         as owner_count,
        count(distinct parent_entity_type)  as entity_types,
        sum(emission_tonnes)                as sources_emission_tonnes

    from sources_with_ownership
    group by iso3_country, subsector, emission_year, gas
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
        s.owner_count,
        s.entity_types,
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

    