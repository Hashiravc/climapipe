{{ config(materialized='view') }}

WITH source_data AS (
    SELECT
        city_code,
        city_name,
        department,
        region,
        latitude::NUMERIC(8, 4) AS latitude,
        longitude::NUMERIC(8, 4) AS longitude,
        elevation::NUMERIC(7, 2) AS elevation_meters,
        date::DATE AS observation_date,
        temperature_max::NUMERIC(5, 2) AS temperature_max_c,
        temperature_min::NUMERIC(5, 2) AS temperature_min_c,
        temperature_mean::NUMERIC(5, 2) AS temperature_mean_c,
        precipitation_sum::NUMERIC(6, 2) AS precipitation_sum_mm,
        rain_sum::NUMERIC(6, 2) AS rain_sum_mm,
        wind_speed_max::NUMERIC(5, 2) AS wind_speed_max_kmh,
        wind_gusts_max::NUMERIC(5, 2) AS wind_gusts_max_kmh,
        solar_radiation::NUMERIC(7, 2) AS solar_radiation_mj_m2,
        extracted_at,
        source
    FROM {{ source('raw', 'weather_daily') }}
),

transformed AS (
    SELECT
        -- Generación de clave subrogada determinística
        MD5(CONCAT(city_code, '_', observation_date::TEXT)) AS observation_id,
        city_code,
        city_name,
        department,
        region,
        latitude,
        longitude,
        elevation_meters,
        observation_date,
        EXTRACT(YEAR FROM observation_date)::INT AS observation_year,
        EXTRACT(MONTH FROM observation_date)::INT AS observation_month,
        TO_CHAR(observation_date, 'YYYY-MM') AS year_month,
        temperature_max_c,
        temperature_min_c,
        temperature_mean_c,
        ROUND((temperature_max_c - temperature_min_c), 2) AS temperature_range_c,
        COALESCE(precipitation_sum_mm, 0) AS precipitation_sum_mm,
        COALESCE(rain_sum_mm, 0) AS rain_sum_mm,
        wind_speed_max_kmh,
        wind_gusts_max_kmh,
        solar_radiation_mj_m2,
        -- Indicadores climatológicos de calidad
        CASE
            WHEN COALESCE(precipitation_sum_mm, 0) >= 0.1 THEN TRUE
            ELSE FALSE
        END AS is_rainy_day,
        CASE
            WHEN temperature_max_c >= 28.0 THEN TRUE
            ELSE FALSE
        END AS is_heat_day,
        CASE
            WHEN temperature_min_c <= 6.0 THEN TRUE
            ELSE FALSE
        END AS is_cold_day,
        extracted_at,
        source
    FROM source_data
)

SELECT * FROM transformed
