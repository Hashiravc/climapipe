"""Unit tests for PostgreSQL/SQLite loader and idempotent UPSERT."""

import pytest
import pandas as pd
from sqlalchemy import text

from src.loader.postgres_loader import PostgresLoader


@pytest.fixture
def test_loader(tmp_path):
    """Instancia de PostgresLoader apuntando a una base SQLite en memoria/temporal."""
    db_file = tmp_path / "test_clima.db"
    conn_url = f"sqlite:///{db_file}"
    loader = PostgresLoader(connection_url=conn_url)
    loader.init_schema()
    return loader


def test_init_schema(test_loader):
    """Verifica que las tablas de pipeline y datos se creen correctamente."""
    with test_loader.engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).scalars().all()
    assert "pipeline_runs" in tables
    assert "raw_weather_daily" in tables


def test_pipeline_run_lifecycle(test_loader):
    """Prueba el ciclo de vida de auditoría (inicio, actualización y finalización)."""
    run_id = test_loader.start_pipeline_run(execution_type="initial")
    assert run_id.startswith("run_")

    # Finalizar con éxito
    test_loader.finish_pipeline_run(
        run_id=run_id,
        status="SUCCESS",
        rows_extracted=100,
        rows_upserted=100,
        error_message=None,
    )

    with test_loader.engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, rows_extracted, rows_upserted FROM pipeline_runs WHERE run_id = :r;"),
            {"r": run_id},
        ).mappings().first()

    assert row["status"] == "SUCCESS"
    assert row["rows_extracted"] == 100
    assert row["rows_upserted"] == 100


def test_idempotent_upsert(test_loader):
    """Prueba fundamental: re-ejecutar la inserción con los mismos datos NO debe duplicar registros."""
    data = [
        {
            "city_code": "TAC",
            "city_name": "Tacna",
            "department": "Tacna",
            "region": "Costa",
            "latitude": -18.0146,
            "longitude": -70.2536,
            "elevation": 562.0,
            "date": "2024-01-01",
            "temperature_max": 25.5,
            "temperature_min": 14.2,
            "temperature_mean": 19.8,
            "precipitation_sum": 0.0,
            "rain_sum": 0.0,
            "wind_speed_max": 15.0,
            "wind_gusts_max": 22.0,
            "solar_radiation": 25.0,
            "extracted_at": "2024-01-02T00:00:00Z",
            "source": "open-meteo-era5",
        },
        {
            "city_code": "AQP",
            "city_name": "Arequipa",
            "department": "Arequipa",
            "region": "Sierra",
            "latitude": -16.4090,
            "longitude": -71.5375,
            "elevation": 2328.0,
            "date": "2024-01-01",
            "temperature_max": 21.0,
            "temperature_min": 9.5,
            "temperature_mean": 15.2,
            "precipitation_sum": 3.4,
            "rain_sum": 3.4,
            "wind_speed_max": 12.0,
            "wind_gusts_max": 18.0,
            "solar_radiation": 24.0,
            "extracted_at": "2024-01-02T00:00:00Z",
            "source": "open-meteo-era5",
        },
    ]
    df = pd.DataFrame(data)

    # 1era Inserción
    upserted_1 = test_loader.upsert_weather_daily(df)
    assert upserted_1 == 2

    with test_loader.engine.connect() as conn:
        count_1 = conn.execute(text("SELECT COUNT(*) FROM raw_weather_daily;")).scalar()
    assert count_1 == 2

    # 2da Inserción (idéntica)
    upserted_2 = test_loader.upsert_weather_daily(df)
    assert upserted_2 == 2

    with test_loader.engine.connect() as conn:
        count_2 = conn.execute(text("SELECT COUNT(*) FROM raw_weather_daily;")).scalar()
    assert count_2 == 2, "La re-ejecución no debe duplicar registros"

    # 3era Inserción con valor actualizado
    df_updated = df.copy()
    df_updated.loc[df_updated["city_code"] == "TAC", "temperature_max"] = 28.0
    test_loader.upsert_weather_daily(df_updated)

    with test_loader.engine.connect() as conn:
        tac_temp = conn.execute(
            text("SELECT temperature_max FROM raw_weather_daily WHERE city_code = 'TAC' AND date = '2024-01-01';")
        ).scalar()
        total_count = conn.execute(text("SELECT COUNT(*) FROM raw_weather_daily;")).scalar()

    assert total_count == 2
    assert tac_temp == 28.0, "El registro existente debió ser actualizado mediante UPSERT"
