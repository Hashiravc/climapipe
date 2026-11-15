"""Unit tests for project configuration and constants."""

from src.config import CITIES, METEO_DAILY_VARIABLES, Settings


def test_cities_definition():
    """Verifica que las tres ciudades canónicas estén correctamente configuradas."""
    expected_codes = {"TAC", "AQP", "LIM"}
    assert set(CITIES.keys()) == expected_codes

    tacna = CITIES["TAC"]
    assert tacna.name == "Tacna"
    assert tacna.region == "Costa"
    assert -19.0 <= tacna.latitude <= -17.0
    assert -72.0 <= tacna.longitude <= -69.0
    assert tacna.elevation_meters > 0

    arequipa = CITIES["AQP"]
    assert arequipa.name == "Arequipa"
    assert arequipa.region == "Sierra"
    assert arequipa.elevation_meters > 2000

    lima = CITIES["LIM"]
    assert lima.name == "Lima"
    assert lima.region == "Costa"
    assert lima.elevation_meters < 300


def test_meteorological_variables():
    """Valida la presencia de las variables meteorológicas esenciales."""
    assert "temperature_2m_max" in METEO_DAILY_VARIABLES
    assert "temperature_2m_min" in METEO_DAILY_VARIABLES
    assert "temperature_2m_mean" in METEO_DAILY_VARIABLES
    assert "precipitation_sum" in METEO_DAILY_VARIABLES
    assert "shortwave_radiation_sum" in METEO_DAILY_VARIABLES


def test_settings_connection_url():
    """Verifica la generación de la URL de conexión."""
    url = Settings.get_connection_url(readonly=False)
    assert url.startswith("postgresql://")
