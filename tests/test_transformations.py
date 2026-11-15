"""Unit tests for climate metrics and transformation logic."""

import pandas as pd
import numpy as np


def test_thermal_range_and_flags_logic():
    """Valida la lógica de cálculo de amplitud térmica y banderas climáticas."""
    data = {
        "city_code": ["TAC", "AQP", "LIM"],
        "temperature_max": [26.0, 22.0, 19.0],
        "temperature_min": [14.0, 5.0, 15.0],
        "precipitation_sum": [0.0, 8.5, 0.4],
    }
    df = pd.DataFrame(data)

    # Transformaciones equivalentes a las de stg_weather_daily.sql
    df["temperature_range"] = df["temperature_max"] - df["temperature_min"]
    df["is_rainy_day"] = df["precipitation_sum"] >= 0.1
    df["is_cold_day"] = df["temperature_min"] <= 6.0

    assert df.loc[df["city_code"] == "TAC", "temperature_range"].iloc[0] == 12.0
    assert df.loc[df["city_code"] == "AQP", "temperature_range"].iloc[0] == 17.0
    assert df.loc[df["city_code"] == "LIM", "temperature_range"].iloc[0] == 4.0

    assert bool(df.loc[df["city_code"] == "TAC", "is_rainy_day"].iloc[0]) is False
    assert bool(df.loc[df["city_code"] == "AQP", "is_rainy_day"].iloc[0]) is True
    assert bool(df.loc[df["city_code"] == "LIM", "is_rainy_day"].iloc[0]) is True

    # Solo Arequipa (5.0 °C <= 6.0 °C) califica como día frío / riesgo de helada en este dataset
    assert bool(df.loc[df["city_code"] == "AQP", "is_cold_day"].iloc[0]) is True
    assert bool(df.loc[df["city_code"] == "TAC", "is_cold_day"].iloc[0]) is False
