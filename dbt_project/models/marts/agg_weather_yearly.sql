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
    MD5(CONCAT(city_code, '_', observation_year::TEXT)) AS yearly_id,
    city_code,
    city_name,
    region,
    observation_year,
    COUNT(*) AS total_recorded_days,
    ROUND(AVG(temperature_mean_c), 2) AS annual_avg_temperature_c,
    ROUND(MAX(temperature_max_c), 2) AS annual_extreme_max_temp_c,
    ROUND(MIN(temperature_min_c), 2) AS annual_extreme_min_temp_c,
    ROUND(SUM(precipitation_sum_mm), 2) AS annual_total_precipitation_mm,
    SUM(CASE WHEN is_rainy_day THEN 1 ELSE 0 END) AS annual_rainy_days_count,
    SUM(CASE WHEN is_heat_day THEN 1 ELSE 0 END) AS annual_heat_days_count,
    SUM(CASE WHEN is_cold_day THEN 1 ELSE 0 END) AS annual_cold_days_count,
    ROUND(AVG(solar_radiation_mj_m2), 2) AS annual_avg_daily_solar_radiation_mj_m2
FROM daily
GROUP BY
    city_code,
    city_name,
    region,
    observation_year
ORDER BY
    city_code,
    observation_year
