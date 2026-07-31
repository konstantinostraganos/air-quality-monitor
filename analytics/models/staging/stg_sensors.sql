with source as (
    select * from {{ source('raw', 'sensors') }}
)

select
    sensor_id,
    location_id,
    location_name,
    country_code,
    city,
    parameter_name as parameter,
    parameter_units as units,
    parameter_display as parameter_label
from source
where parameter_name in ('pm25', 'pm10', 'no2', 'co', 'o3', 'so2')