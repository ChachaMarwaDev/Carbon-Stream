with country as (
    select * from 
        {{ source('raw', 'ct_transportation_country') }}
),

ownership as (
    select * from 
        {{ source('raw', 'ct_transportation_ownership') }}
),

sources as (
    select * from 
        {{ source('raw', 'ct_transportation_sources') }}
),

sources_with_ownership as (
    select
        s.source_id,
        s.source_name,
        s.source_type,
        s.iso3_country,
        s.subsector,
        s.gas,
        date_part('year', s.start_time)     as emission_year,
        s.emissions_quantity                as emission_tonnes,
        s.activity,
        s.activity_units,
        s.capacity                          as flight_capacity,

        -- ownership (mostly NaN for transportation but still useful)
        o.source_operator,
        o.parent_name,
        o.parent_entity_type,
        o.overall_share_percent,
        o.percentage_of_operation

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
        count(distinct source_operator)     as operator_count,
        sum(emission_tonnes)                as sources_emission_tonnes

    from sources_with_ownership
    where iso3_country is not null
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
        s.operator_count,
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
