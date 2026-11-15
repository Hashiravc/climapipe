-- Test singular dbt: La temperatura máxima jamás debe ser inferior a la temperatura mínima
-- Devuelve los registros infractores; si la consulta arroja 0 filas, el test PASA exitosamente.

SELECT
    observation_id,
    city_code,
    observation_date,
    temperature_max_c,
    temperature_min_c
FROM {{ ref('fct_weather_daily') }}
WHERE temperature_max_c < temperature_min_c
