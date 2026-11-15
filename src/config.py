"""Configuration management for ClimaData Perú ELT pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()


@dataclass(frozen=True)
class CityConfig:
    code: str
    name: str
    department: str
    region: str  # Costa, Sierra, Selva
    latitude: float
    longitude: float
    elevation_meters: float
    timezone: str = "America/Lima"


# Definición canónica de las ciudades objetivo del proyecto
CITIES: Dict[str, CityConfig] = {
    "TAC": CityConfig(
        code="TAC",
        name="Tacna",
        department="Tacna",
        region="Costa",
        latitude=-18.0146,
        longitude=-70.2536,
        elevation_meters=562.0,
    ),
    "AQP": CityConfig(
        code="AQP",
        name="Arequipa",
        department="Arequipa",
        region="Sierra",
        latitude=-16.4090,
        longitude=-71.5375,
        elevation_meters=2328.0,
    ),
    "LIM": CityConfig(
        code="LIM",
        name="Lima",
        department="Lima",
        region="Costa",
        latitude=-12.0464,
        longitude=-77.0428,
        elevation_meters=154.0,
    ),
}

# Variables meteorológicas diarias solicitadas a Open-Meteo ERA5
METEO_DAILY_VARIABLES: List[str] = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "shortwave_radiation_sum",
]


class Settings:
    """Configuraciones globales del entorno."""

    # Open-Meteo
    OPEN_METEO_BASE_URL: str = os.getenv(
        "OPEN_METEO_BASE_URL", "https://archive-api.open-meteo.com/v1/archive"
    )
    OPEN_METEO_TIMEOUT: int = int(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "30"))
    OPEN_METEO_MAX_RETRIES: int = int(os.getenv("OPEN_METEO_MAX_RETRIES", "4"))

    # Database
    DATABASE_URL: Optional[str] = os.getenv("NEON_DATABASE_URL")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "neondb")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_SSLMODE: str = os.getenv("DB_SSLMODE", "prefer")

    # Read-Only Database (para Streamlit)
    DB_READONLY_USER: str = os.getenv("DB_READONLY_USER", DB_USER)
    DB_READONLY_PASSWORD: str = os.getenv("DB_READONLY_PASSWORD", DB_PASSWORD)

    # Pipeline
    PIPELINE_MODE: str = os.getenv("PIPELINE_MODE", "incremental").lower()
    BACKFILL_START_DATE: str = os.getenv("BACKFILL_START_DATE", "2022-01-01")
    BACKFILL_END_DATE: str = os.getenv("BACKFILL_END_DATE", "2024-12-31")
    INCREMENTAL_DAYS_LOOKBACK: int = int(os.getenv("INCREMENTAL_DAYS_LOOKBACK", "15"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_connection_url(cls, readonly: bool = False) -> str:
        """Retorna la URL de conexión SQLAlchemy / psycopg2."""
        if cls.DATABASE_URL and not readonly:
            return cls.DATABASE_URL
        user = cls.DB_READONLY_USER if readonly else cls.DB_USER
        password = cls.DB_READONLY_PASSWORD if readonly else cls.DB_PASSWORD
        auth = f"{user}:{password}@" if password else f"{user}@"
        ssl = f"?sslmode={cls.DB_SSLMODE}" if cls.DB_SSLMODE else ""
        return f"postgresql://{auth}{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}{ssl}"


settings = Settings()
