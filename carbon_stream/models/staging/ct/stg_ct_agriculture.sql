with country as (
    select * from 
        {{ source('raw', 'ct_agriculture_country') }}
),

ownership as (
    select * from
        {{ source('raw', 'ct_agriculture_ownership') }}
)

-- "iso3_country"	"sector"	"subsector"	"start_time"	"end_time"	"gas"	"emissions_quantity"	"emissions_quantity_units"	"temporal_granularity"	"created_date"	"modified_date"	"_source_file"

select
    iso3_country,
    sector,
    subsector,
    start_time,
    end_time,
    gas,
    emissions_quantity,
    emissions_quantity_units,
    temporal_granularity,
    created_date,
    modified_date,
    _source_file



-- "parent_name"	"parent_entity_id"	"parent_entity_type"	"parent_lei"	"parent_permid"	"parent_registration_country"	"parent_headquarter_country"	"overall_share_percent"	"ownership_path"	"ownership_path_datasource_ids"	"immediate_source_owner"	"immediate_source_owner_entity_id"	"source_operator"	"source_operator_id"	"percentage_of_operation"	"source_id"	"source_name"	"source_sector"	"source_subsector"	"iso3_country"	"_source_file"


