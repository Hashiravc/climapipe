"""Unit tests for Open-Meteo extraction client."""

import pytest
import responses
import pandas as pd

from src.config import CITIES
from src.extractor.open_meteo import OpenMeteoExtractor


@pytest.fixture
def mock_open_meteo_response():
    """Payload simulado idéntico al emitido por Open-Meteo ERA5."""
    return {
        "latitude": -18.0,
        "longitude": -70.25,
        "elevation": 560,
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "temperature_2m_max": [26.2, 25.8, 26.5],
            "temperature_2m_min": [15.1, 14.8, 15.3],
            "temperature_2m_mean": [20.6, 20.3, 20.9],
            "precipitation_sum": [0.0, 0.2, 0.0],
            "rain_sum": [0.0, 0.2, 0.0],
            "wind_speed_10m_max": [16.5, 18.2, 14.9],
            "wind_gusts_10m_max": [24.1, 26.3, 21.0],
            "shortwave_radiation_sum": [26.4, 25.1, 27.0],
        },
    }


@responses.activate
def test_fetch_city_weather_success(mock_open_meteo_response):
    """Verifica la extracción exitosa y la correcta normalización a DataFrame."""
    extractor = OpenMeteoExtractor(base_url="https://archive-api.open-meteo.com/v1/archive")
    city = CITIES["TAC"]

    responses.add(
        responses.GET,
        "https://archive-api.open-meteo.com/v1/archive",
        json=mock_open_meteo_response,
        status=200,
    )

    df = extractor.fetch_city_weather(city, "2024-01-01", "2024-01-03")

    assert not df.empty
    assert len(df) == 3
    assert list(df["city_code"].unique()) == ["TAC"]
    assert "date" in df.columns
    assert "temperature_mean" in df.columns
    assert "source" in df.columns
    assert df["source"].iloc[0] == "open-meteo-era5"
    assert df["temperature_max"].iloc[0] == 26.2


@responses.activate
def test_fetch_city_weather_empty_response():
    """Valida el manejo de respuestas sin bloque diario."""
    extractor = OpenMeteoExtractor(base_url="https://archive-api.open-meteo.com/v1/archive")
    city = CITIES["LIM"]

    responses.add(
        responses.GET,
        "https://archive-api.open-meteo.com/v1/archive",
        json={"reason": "No data found"},
        status=200,
    )

    df = extractor.fetch_city_weather(city, "2024-01-01", "2024-01-02")
    assert df.empty
