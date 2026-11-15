"""Database access layer for Streamlit dashboard.

Connects with read-only privileges to Neon/PostgreSQL with caching,
and falls back gracefully to local sample data if the live database
is not configured or temporarily unreachable.
"""

from __future__ import annotations

import datetime
import os
import pathlib
import sys

# Asegurar que la raíz del repositorio esté en sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st

from src.config import CITIES, settings
from src.utils.logger import setup_logger

logger = setup_logger("dashboard_db")


def get_db_engine():
    """Retorna un engine de base de datos de solo lectura."""
    conn_str = None
    try:
        if hasattr(st, "secrets") and "NEON_DATABASE_URL" in st.secrets:
            conn_str = st.secrets["NEON_DATABASE_URL"]
    except Exception as e:
        logger.debug(f"st.secrets no disponible o no accesible: {e}")

    if not conn_str and settings.DATABASE_URL:
        conn_str = settings.get_connection_url(readonly=True)

    if not conn_str:
        return None

    try:
        engine = create_engine(
            conn_str,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
            future=True,
        )
        return engine
    except Exception as e:
        logger.warning(f"No se pudo crear engine con la URL configurada: {e}")
        return None


@st.cache_data(ttl=900)
def load_pipeline_status() -> Dict[str, Optional[str]]:
    """Obtiene el último estado de ejecución del pipeline."""
    engine = get_db_engine()
    if not engine:
        return {
            "status": "LOCAL_OFFLINE",
            "last_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "execution_type": "sample_mode",
            "rows_upserted": "0",
        }

    try:
        with engine.connect() as conn:
            query = text(
                """
                SELECT run_id, started_at, ended_at, status, execution_type, rows_upserted
                FROM raw.pipeline_runs
                ORDER BY started_at DESC
                LIMIT 1;
                """
            )
            result = conn.execute(query).mappings().first()
            if result:
                return {
                    "status": result["status"],
                    "last_run": str(result["ended_at"] or result["started_at"])[:19] + " UTC",
                    "execution_type": result["execution_type"],
                    "rows_upserted": str(result["rows_upserted"]),
                }
    except Exception as e:
        logger.warning(f"Error consultando raw.pipeline_runs: {e}")

    return {
        "status": "SIN DATOS DE CORRIDA",
        "last_run": "N/A",
        "execution_type": "N/A",
        "rows_upserted": "0",
    }


@st.cache_data(ttl=1800)
def load_dim_cities() -> pd.DataFrame:
    """Carga el catálogo de ciudades desde marts.dim_cities o fallback."""
    engine = get_db_engine()
    if engine:
        try:
            with engine.connect() as conn:
                df = pd.read_sql("SELECT * FROM marts.dim_cities ORDER BY city_name;", conn)
                if not df.empty:
                    return df
        except Exception as e:
            logger.warning(f"Error cargando marts.dim_cities: {e}")

    # Fallback estático desde configuración canónica
    data = [
        {
            "city_code": c.code,
            "city_name": c.name,
            "department": c.department,
            "region": c.region,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "elevation_meters": c.elevation_meters,
            "altitudinal_region_javier_pulgar_vidal": (
                "Chala / Costa (< 500 msnm)" if c.elevation_meters < 500
                else "Yunga (500 - 2300 msnm)" if c.elevation_meters <= 2300
                else "Quechua (2300 - 3500 msnm)"
            ),
        }
        for c in CITIES.values()
    ]
    return pd.DataFrame(data)


@st.cache_data(ttl=1800)
def load_daily_weather(
    city_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Carga observaciones diarias desde marts.fct_weather_daily o genera dataset consistente."""
    engine = get_db_engine()
    if engine:
        try:
            filters = []
            params = {}
            if city_code and city_code != "TODAS":
                filters.append("f.city_code = :city_code")
                params["city_code"] = city_code
            if start_date:
                filters.append("f.observation_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                filters.append("f.observation_date <= :end_date")
                params["end_date"] = end_date

            where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
            query = f"""
                SELECT
                    f.observation_id,
                    f.city_code,
                    c.city_name,
                    c.region,
                    f.observation_date,
                    f.observation_year,
                    f.observation_month,
                    f.year_month,
                    f.temperature_max_c,
                    f.temperature_min_c,
                    f.temperature_mean_c,
                    f.temperature_range_c,
                    f.precipitation_sum_mm,
                    f.wind_speed_max_kmh,
                    f.solar_radiation_mj_m2,
                    f.is_rainy_day,
                    f.is_heat_day,
                    f.is_cold_day
                FROM marts.fct_weather_daily f
                LEFT JOIN marts.dim_cities c ON f.city_code = c.city_code
                {where_clause}
                ORDER BY f.observation_date ASC;
            """
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
                if not df.empty:
                    df["observation_date"] = pd.to_datetime(df["observation_date"])
                    return df
        except Exception as e:
            logger.warning(f"Error consultando marts.fct_weather_daily: {e}")

    # Fallback sintetizado basado en perfiles climáticos reales para asegurar visualización
    return _generate_realistic_sample_daily(city_code, start_date, end_date)


@st.cache_data(ttl=1800)
def load_monthly_aggregates() -> pd.DataFrame:
    """Carga datos de marts.agg_weather_monthly."""
    engine = get_db_engine()
    if engine:
        try:
            query = "SELECT * FROM marts.agg_weather_monthly ORDER BY year_month ASC, city_name ASC;"
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    return df
        except Exception as e:
            logger.warning(f"Error consultando marts.agg_weather_monthly: {e}")

    # Derivar del fallback diario
    daily_df = load_daily_weather()
    daily_df["year_month"] = daily_df["observation_date"].dt.strftime("%Y-%m")
    daily_df["observation_year"] = daily_df["observation_date"].dt.year
    daily_df["observation_month"] = daily_df["observation_date"].dt.month

    monthly = (
        daily_df.groupby(["city_code", "city_name", "region", "observation_year", "observation_month", "year_month"])
        .agg(
            total_recorded_days=("observation_date", "count"),
            avg_temperature_c=("temperature_mean_c", "mean"),
            max_temperature_c=("temperature_max_c", "max"),
            min_temperature_c=("temperature_min_c", "min"),
            avg_daily_thermal_range_c=("temperature_range_c", "mean"),
            total_precipitation_mm=("precipitation_sum_mm", "sum"),
            rainy_days_count=("is_rainy_day", "sum"),
            heat_days_count=("is_heat_day", "sum"),
            cold_days_count=("is_cold_day", "sum"),
            avg_max_wind_speed_kmh=("wind_speed_max_kmh", "mean"),
            avg_daily_solar_radiation_mj_m2=("solar_radiation_mj_m2", "mean"),
        )
        .reset_index()
    )
    return monthly


def _generate_realistic_sample_daily(
    city_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Genera datos sintéticos calibrados con las características climáticas reales de Perú."""
    import numpy as np

    start = pd.to_datetime(start_date or "2023-01-01")
    end = pd.to_datetime(end_date or "2024-12-31")
    dates = pd.date_range(start, end, freq="D")

    records = []
    codes = [city_code] if (city_code and city_code != "TODAS") else list(CITIES.keys())

    np.random.seed(42)

    for code in codes:
        city = CITIES[code]
        n_days = len(dates)
        day_of_year = dates.dayofyear.values

        # Perfiles bioclimáticos específicos
        if code == "TAC":  # Desierto costero árido, templado, lluvias mínimas
            base_temp = 18.5 + 4.5 * np.cos(2 * np.pi * (day_of_year - 30) / 365)
            temp_range = 9.0 + np.random.normal(0, 0.8, n_days)
            precip_prob = 0.03
            precip_vals = np.where(np.random.rand(n_days) < precip_prob, np.random.exponential(1.2, n_days), 0.0)
        elif code == "AQP":  # Sierra volcánica (2328 msnm), alta amplitud térmica, lluvias en verano
            base_temp = 14.5 + 2.0 * np.cos(2 * np.pi * (day_of_year - 30) / 365)
            temp_range = 14.0 + np.random.normal(0, 1.2, n_days)
            is_summer = (dates.month >= 1) & (dates.month <= 3)
            precip_prob = np.where(is_summer, 0.25, 0.02)
            precip_vals = np.where(np.random.rand(n_days) < precip_prob, np.random.exponential(4.5, n_days), 0.0)
        else:  # LIM: Costa húmeda, nubosidad invernal (garúa), verano cálido
            base_temp = 19.8 + 5.0 * np.cos(2 * np.pi * (day_of_year - 45) / 365)
            temp_range = 6.5 + np.random.normal(0, 0.7, n_days)
            is_winter = (dates.month >= 6) & (dates.month <= 9)
            precip_prob = np.where(is_winter, 0.20, 0.02)
            precip_vals = np.where(np.random.rand(n_days) < precip_prob, np.random.uniform(0.1, 0.8, n_days), 0.0)

        temp_mean = np.round(base_temp + np.random.normal(0, 1.0, n_days), 1)
        temp_max = np.round(temp_mean + (temp_range / 2), 1)
        temp_min = np.round(temp_mean - (temp_range / 2), 1)
        precip = np.round(precip_vals, 2)
        wind = np.round(np.random.uniform(10.0, 25.0, n_days), 1)
        solar = np.round(np.random.uniform(15.0, 28.0, n_days), 1)

        for i, dt in enumerate(dates):
            records.append({
                "observation_id": f"{code}_{dt.strftime('%Y%m%d')}",
                "city_code": code,
                "city_name": city.name,
                "region": city.region,
                "observation_date": dt,
                "observation_year": dt.year,
                "observation_month": dt.month,
                "year_month": dt.strftime("%Y-%m"),
                "temperature_max_c": temp_max[i],
                "temperature_min_c": temp_min[i],
                "temperature_mean_c": temp_mean[i],
                "temperature_range_c": np.round(temp_max[i] - temp_min[i], 1),
                "precipitation_sum_mm": precip[i],
                "wind_speed_max_kmh": wind[i],
                "solar_radiation_mj_m2": solar[i],
                "is_rainy_day": precip[i] >= 0.1,
                "is_heat_day": temp_max[i] >= 28.0,
                "is_cold_day": temp_min[i] <= 6.0,
            })

    return pd.DataFrame(records)
