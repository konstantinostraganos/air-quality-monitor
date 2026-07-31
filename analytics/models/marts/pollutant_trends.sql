with daily as (
    select * from {{ ref('city_daily_avg') }}
)

select
    country_code,
    city,
    parameter,
    parameter_label,
    units,
    measurement_date,
    daily_avg,
    avg(daily_avg) over (
        partition by city, parameter
        order by measurement_date
        rows between 2 preceding and current row
    ) as moving_avg_3d
from daily