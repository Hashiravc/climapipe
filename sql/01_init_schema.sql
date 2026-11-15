-- ==============================================================================
-- ClimaData Perú: Esquemas DDL para PostgreSQL / Neon
-- ==============================================================================

-- 1. Crear esquemas de aislamiento
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS marts;

-- 2. Tabla de auditoría de ejecuciones del pipeline
CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL, -- 'RUNNING', 'SUCCESS', 'FAILED'
    execution_type VARCHAR(20) NOT NULL, -- 'initial', 'incremental'
    rows_extracted INT DEFAULT 0,
    rows_upserted INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON raw.pipeline_runs (started_at DESC);

-- 3. Tabla Raw de observaciones diarias meteorológicas (Landing Zone Idempotente)
CREATE TABLE IF NOT EXISTS raw.weather_daily (
    city_code VARCHAR(10) NOT NULL,
    city_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    elevation NUMERIC(7, 2) NOT NULL,
    date DATE NOT NULL,
    temperature_max NUMERIC(5, 2),
    temperature_min NUMERIC(5, 2),
    temperature_mean NUMERIC(5, 2),
    precipitation_sum NUMERIC(6, 2),
    rain_sum NUMERIC(6, 2),
    wind_speed_max NUMERIC(5, 2),
    wind_gusts_max NUMERIC(5, 2),
    solar_radiation NUMERIC(7, 2),
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'open-meteo-era5',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_raw_weather_daily PRIMARY KEY (city_code, date)
);

-- Índices de consulta frecuente
CREATE INDEX IF NOT EXISTS idx_raw_weather_date ON raw.weather_daily (date);
CREATE INDEX IF NOT EXISTS idx_raw_weather_city_date ON raw.weather_daily (city_code, date DESC);
