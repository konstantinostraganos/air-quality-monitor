with measurements as (
    select * from {{ ref('stg_measurements') }}
)

select
    country_code,
    city,
    parameter,
    parameter_label,
    units,
    cast(measured_at as date) as measurement_date,
    round(avg(avg_value), 2) as daily_avg,
    round(max(max_value), 2) as daily_max,
    count(*) as reading_count
from measurements
where city is not null
group by
    country_code,
    city,
    parameter,
    parameter_label,
    units,
    cast(measured_at as date)