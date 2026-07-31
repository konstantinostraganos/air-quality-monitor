with source as (
    select * from {{ source('raw', 'locations') }}
)

select
    id as location_id,
    name as location_name,
    locality as city,
    country_code,
    country_name,
    latitude,
    longitude,
    is_mobile,
    is_monitor,
    provider_name,
    cast(first_datetime_utc as timestamp) as first_reading_at,
    cast(last_datetime_utc as timestamp) as last_reading_at
from source
where latitude is not null
  and longitude is not null