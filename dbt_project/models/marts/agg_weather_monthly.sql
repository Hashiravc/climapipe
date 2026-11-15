{{ config(materialized='table') }}

WITH daily AS (
    SELECT
        f.*,
        c.city_name,
        c.region
    FROM {{ ref('fct_weather_daily') }} f
    INNER JOIN {{ ref('dim_cities') }} c ON f.city_code = c.city_code
)

SELECT
    MD5(CONCAT(city_code, '_', year_month)) AS monthly_id,
    city_code,
    city_name,
    region,
    observation_year,
    observation_month,
    year_month,
    COUNT(*) AS total_recorded_days,
    ROUND(AVG(temperature_mean_c), 2) AS avg_temperature_c,
    ROUND(MAX(temperature_max_c), 2) AS max_temperature_c,
    ROUND(MIN(temperature_min_c), 2) AS min_temperature_c,
    ROUND(AVG(temperature_range_c), 2) AS avg_daily_thermal_range_c,
    ROUND(SUM(precipitation_sum_mm), 2) AS total_precipitation_mm,
    SUM(CASE WHEN is_rainy_day THEN 1 ELSE 0 END) AS rainy_days_count,
    SUM(CASE WHEN is_heat_day THEN 1 ELSE 0 END) AS heat_days_count,
    SUM(CASE WHEN is_cold_day THEN 1 ELSE 0 END) AS cold_days_count,
    ROUND(AVG(wind_speed_max_kmh), 2) AS avg_max_wind_speed_kmh,
    ROUND(AVG(solar_radiation_mj_m2), 2) AS avg_daily_solar_radiation_mj_m2
FROM daily
GROUP BY
    city_code,
    city_name,
    region,
    observation_year,
    observation_month,
    year_month
ORDER BY
    city_code,
    year_month
