"""End-to-End ELT Pipeline Runner.

Orchestrates:
1. Determination of extraction windows (Initial backfill vs Incremental).
2. Data extraction from Open-Meteo for Tacna, Arequipa, and Lima.
3. Idempotent loading into PostgreSQL/Neon (with audit tracking in raw.pipeline_runs).
4. Automated execution of dbt transformations and data quality tests.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import subprocess
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Optional
import pandas as pd

from src.config import CITIES, CityConfig, settings
from src.extractor.open_meteo import OpenMeteoExtractor
from src.loader.postgres_loader import PostgresLoader
from src.utils.logger import setup_logger

logger = setup_logger("pipeline_runner")


def determine_date_range(
    city: CityConfig,
    mode: str,
    loader: PostgresLoader,
    explicit_start: Optional[str] = None,
    explicit_end: Optional[str] = None,
) -> tuple[str, str]:
    """Calcula las fechas de inicio y fin para la extracción según el modo."""
    # En reanálisis ERA5 existe un retardo aproximado de 5 días
    safe_today = datetime.date.today() - datetime.timedelta(days=5)
    default_end = safe_today.strftime("%Y-%m-%d")

    if explicit_start and explicit_end:
        return explicit_start, explicit_end

    if mode == "initial":
        start = explicit_start or settings.BACKFILL_START_DATE
        end = explicit_end or min(settings.BACKFILL_END_DATE, default_end)
        return start, end

    # Modo incremental
    latest_db_date = loader.get_latest_date_by_city(city.code)
    if latest_db_date:
        latest_dt = datetime.datetime.strptime(latest_db_date, "%Y-%m-%d").date()
        next_dt = latest_dt + datetime.timedelta(days=1)
        if next_dt > safe_today:
            logger.info(
                f"[{city.code}] Datos al día (Última fecha: {latest_db_date}). No se requiere extracción incremental."
            )
            return "", ""
        start = next_dt.strftime("%Y-%m-%d")
        end = default_end
    else:
        # Si la tabla está vacía, aplicar lookback o rango histórico
        lookback_days = settings.INCREMENTAL_DAYS_LOOKBACK
        start = (safe_today - datetime.timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end = default_end

    return start, end


def run_dbt(project_dir: str = "dbt_project", profiles_dir: str = "dbt_project") -> bool:
    """Ejecuta dbt build para aplicar transformaciones y pruebas."""
    logger.info("Iniciando ejecución de dbt build (modelos + tests)...")
    cmd = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "build",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
    ]
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info("dbt build completado exitosamente.")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error durante dbt build: {e.returncode}")
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        return False


def run_pipeline(
    mode: str = "incremental",
    run_dbt_models: bool = True,
    connection_url: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> bool:
    """Ejecuta el ciclo de vida completo del pipeline ELT."""
    logger.info(f"=== INICIANDO PIPELINE CLIMADATA PERÚ [MODO: {mode.upper()}] ===")
    loader = PostgresLoader(connection_url=connection_url)
    loader.init_schema()

    run_id = loader.start_pipeline_run(execution_type=mode)
    extractor = OpenMeteoExtractor()

    total_extracted = 0
    total_upserted = 0
    dfs = []

    try:
        for code, city in CITIES.items():
            c_start, c_end = determine_date_range(
                city=city,
                mode=mode,
                loader=loader,
                explicit_start=start_date,
                explicit_end=end_date,
            )

            if not c_start or not c_end:
                continue

            logger.info(f"Extrayendo [{city.name}]: {c_start} -> {c_end}")
            df_city = extractor.fetch_city_weather(city, c_start, c_end)

            if not df_city.empty:
                dfs.append(df_city)
                total_extracted += len(df_city)

        if dfs:
            consolidated_df = pd.concat(dfs, ignore_index=True)
            total_upserted = loader.upsert_weather_daily(consolidated_df)
        else:
            logger.info("No hubo nuevos registros que procesar en esta corrida.")

        # Ejecutar dbt si está configurado y no estamos en SQLite puro de test
        dbt_success = True
        if run_dbt_models and not loader.is_sqlite:
            dbt_success = run_dbt()

        status = "SUCCESS" if dbt_success else "FAILED"
        err_msg = None if dbt_success else "Falla en ejecución de dbt build"

        loader.finish_pipeline_run(
            run_id=run_id,
            status=status,
            rows_extracted=total_extracted,
            rows_upserted=total_upserted,
            error_message=err_msg,
        )

        logger.info(
            f"=== PIPELINE COMPLETADO CON ESTADO [{status}]. Filas extraídas: {total_extracted}, upserted: {total_upserted} ==="
        )
        return dbt_success

    except Exception as e:
        logger.exception(f"Falla crítica en la ejecución del pipeline: {e}")
        loader.finish_pipeline_run(
            run_id=run_id,
            status="FAILED",
            rows_extracted=total_extracted,
            rows_upserted=total_upserted,
            error_message=str(e),
        )
        return False


def main():
    parser = argparse.ArgumentParser(description="ClimaData Perú ELT Pipeline Runner")
    parser.add_argument(
        "--mode",
        choices=["initial", "incremental"],
        default=settings.PIPELINE_MODE,
        help="Modo de ejecución del pipeline",
    )
    parser.add_argument(
        "--no-dbt",
        action="store_true",
        help="Omitir la fase de transformación dbt",
    )
    parser.add_argument(
        "--connection-url",
        type=str,
        default=None,
        help="URL opcional de conexión a la base de datos (e.g. sqlite:///test.db)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Fecha de inicio forzada YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Fecha de fin forzada YYYY-MM-DD",
    )

    args = parser.parse_args()

    success = run_pipeline(
        mode=args.mode,
        run_dbt_models=not args.no_dbt,
        connection_url=args.connection_url,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
