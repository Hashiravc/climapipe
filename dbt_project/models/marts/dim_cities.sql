{{ config(materialized='table') }}

WITH city_data AS (
    SELECT DISTINCT
        city_code,
        city_name,
        department,
        region,
        latitude,
        longitude,
        elevation_meters
    FROM {{ ref('stg_weather_daily') }}
)

SELECT
    city_code,
    city_name,
    department,
    region,
    latitude,
    longitude,
    elevation_meters,
    CASE
        WHEN elevation_meters < 500 THEN 'Chala / Costa (< 500 msnm)'
        WHEN elevation_meters BETWEEN 500 AND 2300 THEN 'Yunga (500 - 2300 msnm)'
        WHEN elevation_meters BETWEEN 2300 AND 3500 THEN 'Quechua (2300 - 3500 msnm)'
        ELSE 'Suni / Puna (> 3500 msnm)'
    END AS altitudinal_region_javier_pulgar_vidal,
    'America/Lima' AS timezone
FROM city_data
