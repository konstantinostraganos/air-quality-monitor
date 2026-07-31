with daily as (
    select * from {{ ref('city_daily_avg') }}
)

select
    country_code,
    city,
    parameter,
    units,
    measurement_date,
    daily_avg,
    daily_max,
    case
        when parameter = 'pm25' and daily_avg > 15 then 'EXCEEDED'
        when parameter = 'pm10' and daily_avg > 45 then 'EXCEEDED'
        when parameter = 'no2' and daily_avg > 25 then 'EXCEEDED'
        when parameter = 'o3' and daily_avg > 100 then 'EXCEEDED'
        when parameter = 'so2' and daily_avg > 40 then 'EXCEEDED'
        when parameter = 'co' and daily_avg > 4 then 'EXCEEDED'
        else 'OK'
    end as who_status
from daily
where parameter in ('pm25', 'pm10', 'no2', 'o3', 'so2', 'co')