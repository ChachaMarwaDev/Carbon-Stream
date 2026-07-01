-- models/marts/fct_emissions_by_country.sql
{{ config(materialized='table') }}
with gcp as (
    select * from {{ ref('stg_gcp_emissions') }}
),

wb_emissions as (
    select * from {{ ref('stg_wb_emissions') }}
),

wb_context as (
    select * from {{ ref('stg_wb_context') }}
),

agriculture as (
    select * from {{ ref('stg_ct_agriculture') }}
),

power as (
    select * from {{ ref('stg_ct_power') }}
),

transportation as (
    select * from {{ ref('stg_ct_transportation') }}
),

waste as (
    select * from {{ ref('stg_ct_waste') }}
),

buildings as (
    select * from {{ ref('stg_ct_buildings') }}
),

final as (
    select
        -- identifiers
        gcp.country_name,
        wb_context.iso3,
        gcp.emission_year,

        -- country context
        wb_context.region_name,
        wb_context.income_level,
        wb_context.population,
        wb_context.gdp_usd,
        wb_context.renewable_pct,

        -- total emissions
        gcp.emissions_mtco2                             as total_emissions_mtco2,
        wb_emissions.co2_kt                             as wb_co2_kt,
        wb_emissions.co2_per_capita                     as co2_per_capita,

        -- agriculture
        agriculture.emission_tonnes                     as agriculture_emission_tonnes,
        agriculture.facility_count                      as agriculture_facility_count,

        -- power
        power.country_emission_tonnes                   as power_emission_tonnes,
        power.facility_count                            as power_facility_count,
        power.owner_count                               as power_owner_count,

        -- transportation
        transportation.country_emission_tonnes          as transportation_emission_tonnes,
        transportation.facility_count                   as transportation_facility_count,
        transportation.operator_count                   as transportation_operator_count,

        -- waste
        waste.country_emission_tonnes                   as waste_emission_tonnes,
        waste.facility_count                            as waste_facility_count,

        -- buildings
        buildings.emission_tonnes                       as buildings_emission_tonnes
        -- buildings.facility_count                        as buildings_facility_count

    from gcp
    left join wb_context
        on  gcp.country_name    = wb_context.country_name
        and gcp.emission_year   = wb_context.observation_year
    left join wb_emissions
        on  wb_context.iso3     = wb_emissions.iso3
        and gcp.emission_year   = wb_emissions.observation_year
    left join agriculture
        on  wb_context.iso3     = agriculture.iso3
        and gcp.emission_year   = agriculture.emission_year
    left join power
        on  wb_context.iso3     = power.iso3_country
        and gcp.emission_year   = power.emission_year
    left join transportation
        on  wb_context.iso3     = transportation.iso3_country
        and gcp.emission_year   = transportation.emission_year
    left join waste
        on  wb_context.iso3     = waste.iso3_country
        and gcp.emission_year   = waste.emission_year
    left join buildings
        on  wb_context.iso3     = buildings.iso3
        and gcp.emission_year   = buildings.emission_year
)

select * from final
