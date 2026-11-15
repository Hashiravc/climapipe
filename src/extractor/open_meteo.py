"""Open-Meteo ERA5 Historical Weather Extractor.

Handles robust extraction with HTTP retries, exponential backoff, rate limit handling,
and data normalization for Tacna, Arequipa, and Lima.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

from src.config import CityConfig, CITIES, METEO_DAILY_VARIABLES, settings
from src.utils.logger import setup_logger

logger = setup_logger("extractor")


class OpenMeteoExtractor:
    """Cliente para la API histórica de Open-Meteo (reanálisis ERA5)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.base_url = base_url or settings.OPEN_METEO_BASE_URL
        self.timeout = timeout or settings.OPEN_METEO_TIMEOUT
        self.max_retries = max_retries or settings.OPEN_METEO_MAX_RETRIES
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Configura una sesión HTTP con política de reintentos y backoff exponencial."""
        session = requests.Session()
        retries = Retry(
            total=self.max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {"User-Agent": "ClimaDataPeru-ELT/1.0 (academic-research-pipeline)"}
        )
        return session

    def fetch_city_weather(
        self,
        city: CityConfig,
        start_date: str,
        end_date: str,
        variables: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Extrae el clima histórico diario para una ciudad específica en un rango de fechas.

        Args:
            city: Configuración de la ciudad.
            start_date: Fecha inicio en formato 'YYYY-MM-DD'.
            end_date: Fecha fin en formato 'YYYY-MM-DD'.
            variables: Lista de variables meteorológicas diarias.

        Returns:
            pd.DataFrame con registros normalizados y metadatos de auditoría.
        """
        daily_vars = variables or METEO_DAILY_VARIABLES
        params = {
            "latitude": round(city.latitude, 4),
            "longitude": round(city.longitude, 4),
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(daily_vars),
            "timezone": city.timezone,
        }

        logger.info(
            f"Extrayendo datos de {city.name} ({city.code}) entre {start_date} y {end_date}..."
        )

        try:
            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.HTTPError as err:
            logger.error(f"Error HTTP al consultar Open-Meteo para {city.code}: {err}")
            raise
        except requests.exceptions.RequestException as err:
            logger.error(f"Falla de red o timeout al consultar Open-Meteo: {err}")
            raise

        return self._normalize_response(city, payload)

    def _normalize_response(
        self, city: CityConfig, payload: Dict[str, Any]
    ) -> pd.DataFrame:
        """Transforma la estructura tabular de Open-Meteo en un DataFrame plano con metadatos."""
        if "daily" not in payload or "time" not in payload["daily"]:
            logger.warning(
                f"Respuesta vacía o incompleta para {city.code}: {payload.get('reason', 'Sin datos')}"
            )
            return pd.DataFrame()

        daily = payload["daily"]
        dates = daily["time"]
        num_records = len(dates)

        if num_records == 0:
            return pd.DataFrame()

        extraction_timestamp = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

        # Mapeo y saneamiento de columnas
        records: List[Dict[str, Any]] = []
        for i in range(num_records):
            records.append(
                {
                    "city_code": city.code,
                    "city_name": city.name,
                    "department": city.department,
                    "region": city.region,
                    "latitude": city.latitude,
                    "longitude": city.longitude,
                    "elevation": city.elevation_meters,
                    "date": dates[i],
                    "temperature_max": daily.get("temperature_2m_max", [None] * num_records)[i],
                    "temperature_min": daily.get("temperature_2m_min", [None] * num_records)[i],
                    "temperature_mean": daily.get("temperature_2m_mean", [None] * num_records)[i],
                    "precipitation_sum": daily.get("precipitation_sum", [None] * num_records)[i],
                    "rain_sum": daily.get("rain_sum", [None] * num_records)[i],
                    "wind_speed_max": daily.get("wind_speed_10m_max", [None] * num_records)[i],
                    "wind_gusts_max": daily.get("wind_gusts_10m_max", [None] * num_records)[i],
                    "solar_radiation": daily.get("shortwave_radiation_sum", [None] * num_records)[i],
                    "extracted_at": extraction_timestamp,
                    "source": "open-meteo-era5",
                }
            )

        df = pd.DataFrame(records)
        logger.info(f"Normalizados {len(df)} registros para {city.name}.")
        return df

    def extract_all_cities(
        self,
        start_date: str,
        end_date: str,
        cities: Optional[Dict[str, CityConfig]] = None,
    ) -> pd.DataFrame:
        """Extrae el clima para todas las ciudades configuradas y consolida el resultado."""
        target_cities = cities or CITIES
        dfs: List[pd.DataFrame] = []

        for code, city in target_cities.items():
            df_city = self.fetch_city_weather(city, start_date, end_date)
            if not df_city.empty:
                dfs.append(df_city)

        if not dfs:
            return pd.DataFrame()

        consolidated = pd.concat(dfs, ignore_index=True)
        logger.info(
            f"Extracción total completada: {len(consolidated)} registros consolidados para {len(dfs)} ciudades."
        )
        return consolidated
