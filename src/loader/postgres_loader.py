"""Idempotent PostgreSQL Loader with Audit Logging.

Handles UPSERT operations on PostgreSQL/Neon and tracks execution history
in raw.pipeline_runs. Supports SQLite engine for offline unit and integration tests.
"""

from __future__ import annotations

import datetime
import os
import uuid
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger("loader")


class PostgresLoader:
    """Cargador idempotente a base de datos PostgreSQL/Neon."""

    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or settings.get_connection_url(readonly=False)
        self.is_sqlite = self.connection_url.startswith("sqlite")
        if self.is_sqlite and ":///" in self.connection_url:
            path_part = self.connection_url.split(":///", 1)[1]
            if path_part and not path_part.startswith(":"):
                dir_name = os.path.dirname(os.path.abspath(path_part))
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
        self.engine: Engine = self._create_engine()

    def _create_engine(self) -> Engine:
        """Crea el engine de SQLAlchemy configurado para Neon/PostgreSQL."""
        if self.is_sqlite:
            return create_engine(self.connection_url, future=True)
        return create_engine(
            self.connection_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )

    def init_schema(self) -> None:
        """Crea los esquemas y tablas necesarias si no existen."""
        logger.info("Verificando e inicializando esquemas y tablas...")
        with self.engine.begin() as conn:
            if not self.is_sqlite:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts;"))

                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
                            run_id VARCHAR(64) PRIMARY KEY,
                            started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                            ended_at TIMESTAMP WITH TIME ZONE,
                            status VARCHAR(20) NOT NULL,
                            execution_type VARCHAR(20) NOT NULL,
                            rows_extracted INT DEFAULT 0,
                            rows_upserted INT DEFAULT 0,
                            error_message TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                )

                conn.execute(
                    text(
                        """
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
                        """
                    )
                )
            else:
                # Esquema simplificado para SQLite en modo testing local
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS pipeline_runs (
                            run_id TEXT PRIMARY KEY,
                            started_at TEXT NOT NULL,
                            ended_at TEXT,
                            status TEXT NOT NULL,
                            execution_type TEXT NOT NULL,
                            rows_extracted INTEGER DEFAULT 0,
                            rows_upserted INTEGER DEFAULT 0,
                            error_message TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                )
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS raw_weather_daily (
                            city_code TEXT NOT NULL,
                            city_name TEXT NOT NULL,
                            department TEXT NOT NULL,
                            region TEXT NOT NULL,
                            latitude REAL NOT NULL,
                            longitude REAL NOT NULL,
                            elevation REAL NOT NULL,
                            date TEXT NOT NULL,
                            temperature_max REAL,
                            temperature_min REAL,
                            temperature_mean REAL,
                            precipitation_sum REAL,
                            rain_sum REAL,
                            wind_speed_max REAL,
                            wind_gusts_max REAL,
                            solar_radiation REAL,
                            extracted_at TEXT NOT NULL,
                            source TEXT NOT NULL DEFAULT 'open-meteo-era5',
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (city_code, date)
                        );
                        """
                    )
                )
        logger.info("Esquemas y tablas base inicializados exitosamente.")

    def start_pipeline_run(self, execution_type: str = "incremental") -> str:
        """Registra el inicio de una corrida en la tabla de auditoría."""
        run_id = f"run_{uuid.uuid4().hex[:12]}_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        now = datetime.datetime.now(datetime.timezone.utc)
        table_name = "pipeline_runs" if self.is_sqlite else "raw.pipeline_runs"

        query = text(
            f"""
            INSERT INTO {table_name} (run_id, started_at, status, execution_type)
            VALUES (:run_id, :started_at, 'RUNNING', :execution_type);
            """
        )

        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "run_id": run_id,
                    "started_at": now.isoformat() if self.is_sqlite else now,
                    "execution_type": execution_type,
                },
            )
        logger.info(f"Iniciada auditoría de pipeline con run_id: {run_id}")
        return run_id

    def finish_pipeline_run(
        self,
        run_id: str,
        status: str,
        rows_extracted: int,
        rows_upserted: int,
        error_message: Optional[str] = None,
    ) -> None:
        """Actualiza el estado final y métricas de la corrida en la tabla de auditoría."""
        now = datetime.datetime.now(datetime.timezone.utc)
        table_name = "pipeline_runs" if self.is_sqlite else "raw.pipeline_runs"

        query = text(
            f"""
            UPDATE {table_name}
            SET ended_at = :ended_at,
                status = :status,
                rows_extracted = :rows_extracted,
                rows_upserted = :rows_upserted,
                error_message = :error_message
            WHERE run_id = :run_id;
            """
        )

        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "run_id": run_id,
                    "ended_at": now.isoformat() if self.is_sqlite else now,
                    "status": status,
                    "rows_extracted": rows_extracted,
                    "rows_upserted": rows_upserted,
                    "error_message": error_message,
                },
            )
        logger.info(
            f"Corrida {run_id} finalizada con estado [{status}]. Filas extraídas: {rows_extracted}, upserted: {rows_upserted}"
        )

    def get_latest_date_by_city(self, city_code: str) -> Optional[str]:
        """Obtiene la fecha más reciente disponible en base de datos para una ciudad dada."""
        table_name = "raw_weather_daily" if self.is_sqlite else "raw.weather_daily"
        query = text(
            f"SELECT MAX(date) AS max_date FROM {table_name} WHERE city_code = :city_code;"
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"city_code": city_code}).scalar()

        if result:
            return str(result)[:10]
        return None

    def upsert_weather_daily(self, df: pd.DataFrame) -> int:
        """Inserta o actualiza registros de forma estrictamente idempotente.

        Returns:
            Número total de filas procesadas.
        """
        if df.empty:
            logger.info("DataFrame vacío. Ningún registro cargado.")
            return 0

        # Sanitizar NaNs de Pandas a None para que PostgreSQL reciba NULLs
        clean_df = df.where(pd.notnull(df), None)
        records = clean_df.to_dict(orient="records")
        table_name = "raw_weather_daily" if self.is_sqlite else "raw.weather_daily"

        if self.is_sqlite:
            # SQLite UPSERT sintaxis
            upsert_query = text(
                f"""
                INSERT INTO {table_name} (
                    city_code, city_name, department, region, latitude, longitude, elevation,
                    date, temperature_max, temperature_min, temperature_mean, precipitation_sum,
                    rain_sum, wind_speed_max, wind_gusts_max, solar_radiation, extracted_at, source
                ) VALUES (
                    :city_code, :city_name, :department, :region, :latitude, :longitude, :elevation,
                    :date, :temperature_max, :temperature_min, :temperature_mean, :precipitation_sum,
                    :rain_sum, :wind_speed_max, :wind_gusts_max, :solar_radiation, :extracted_at, :source
                ) ON CONFLICT(city_code, date) DO UPDATE SET
                    city_name = excluded.city_name,
                    department = excluded.department,
                    region = excluded.region,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    elevation = excluded.elevation,
                    temperature_max = excluded.temperature_max,
                    temperature_min = excluded.temperature_min,
                    temperature_mean = excluded.temperature_mean,
                    precipitation_sum = excluded.precipitation_sum,
                    rain_sum = excluded.rain_sum,
                    wind_speed_max = excluded.wind_speed_max,
                    wind_gusts_max = excluded.wind_gusts_max,
                    solar_radiation = excluded.solar_radiation,
                    extracted_at = excluded.extracted_at,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
                """
            )
        else:
            # PostgreSQL UPSERT sintaxis
            upsert_query = text(
                f"""
                INSERT INTO {table_name} (
                    city_code, city_name, department, region, latitude, longitude, elevation,
                    date, temperature_max, temperature_min, temperature_mean, precipitation_sum,
                    rain_sum, wind_speed_max, wind_gusts_max, solar_radiation, extracted_at, source
                ) VALUES (
                    :city_code, :city_name, :department, :region, :latitude, :longitude, :elevation,
                    :date, :temperature_max, :temperature_min, :temperature_mean, :precipitation_sum,
                    :rain_sum, :wind_speed_max, :wind_gusts_max, :solar_radiation, :extracted_at, :source
                ) ON CONFLICT (city_code, date) DO UPDATE SET
                    city_name = EXCLUDED.city_name,
                    department = EXCLUDED.department,
                    region = EXCLUDED.region,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    elevation = EXCLUDED.elevation,
                    temperature_max = EXCLUDED.temperature_max,
                    temperature_min = EXCLUDED.temperature_min,
                    temperature_mean = EXCLUDED.temperature_mean,
                    precipitation_sum = EXCLUDED.precipitation_sum,
                    rain_sum = EXCLUDED.rain_sum,
                    wind_speed_max = EXCLUDED.wind_speed_max,
                    wind_gusts_max = EXCLUDED.wind_gusts_max,
                    solar_radiation = EXCLUDED.solar_radiation,
                    extracted_at = EXCLUDED.extracted_at,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP;
                """
            )

        batch_size = 500
        total_upserted = 0

        with self.engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                conn.execute(upsert_query, batch)
                total_upserted += len(batch)

        logger.info(
            f"Carga idempotente exitosa: {total_upserted} filas insertadas/actualizadas en {table_name}."
        )
        return total_upserted
