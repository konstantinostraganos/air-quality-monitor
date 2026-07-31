with source as (
    select * from {{ source('raw', 'measurements') }}
)

select
    sensor_id,
    location_id,
    location_name,
    country_code,
    city,
    parameter,
    parameter_display as parameter_label,
    units,
    cast(date_from as timestamp) as measured_at,
    avg_value,
    min_value,
    max_value
from source
where avg_value is not null
  and avg_value >= 0