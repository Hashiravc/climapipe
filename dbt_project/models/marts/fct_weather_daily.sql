{{ config(materialized='table') }}

WITH stg AS (
    SELECT * FROM {{ ref('stg_weather_daily') }}
)

SELECT
    observation_id,
    city_code,
    observation_date,
    observation_year,
    observation_month,
    year_month,
    temperature_max_c,
    temperature_min_c,
    temperature_mean_c,
    temperature_range_c,
    precipitation_sum_mm,
    rain_sum_mm,
    wind_speed_max_kmh,
    wind_gusts_max_kmh,
    solar_radiation_mj_m2,
    is_rainy_day,
    is_heat_day,
    is_cold_day,
    extracted_at
FROM stg
