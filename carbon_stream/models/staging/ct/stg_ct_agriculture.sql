with country as (
    select * from 
        {{ source('raw', 'ct_agriculture_country') }}
),

ownership as (
    select * from
        {{ source('raw', 'ct_agriculture_ownership') }}
),

ownership_agg as (
    select
        iso3_country,
        source_subsector,
        count(distinct source_name)         as facility_count,
        count(distinct parent_name)         as owner_count,
        avg(overall_share_percent)          as avg_ownership_share

    from ownership
    where iso3_country is not null
    group by iso3_country, source_subsector
),


final as (
    select
        c.iso3_country                          as iso3,
        c.sector,
        c.subsector,
        date_part('year', c.start_time)         as emission_year,
        c.gas,
        c.emissions_quantity                    as emission_tonnes,

        -- ownership context at country level
        o.facility_count,
        o.owner_count,
        o.avg_ownership_share

    from country c
    left join ownership_agg o
        on c.iso3_country = o.iso3_country
        and c.subsector = o.source_subsector

    where c.iso3_country is not null
      and c.emissions_quantity is not null
)

select * from final



