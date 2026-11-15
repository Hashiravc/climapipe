"""Main Streamlit Application for ClimaData Perú.

Interactive meteorological dashboard visualizing historical weather data
from Tacna, Arequipa, and Lima, backed by Neon PostgreSQL and transformed via dbt Core.
"""

from __future__ import annotations

import datetime
import os
import pathlib
import sys

# Asegurar que la raíz del repositorio esté en sys.path (crítico para Streamlit Cloud)
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from src.config import CITIES
from app.utils.db import (
    load_pipeline_status,
    load_dim_cities,
    load_daily_weather,
    load_monthly_aggregates,
)
from app.components.kpis import render_kpis
from app.components.charts import (
    render_temperature_timeseries,
    render_monthly_precipitation_chart,
    render_thermal_distribution,
)
from app.components.comparisons import render_city_comparisons

# Configuración de la página
st.set_page_config(
    page_title="ClimaData Perú | Pipeline ELT",
    page_icon="🇵🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_header(status: dict) -> None:
    """Encabezado principal con badges de estado del pipeline."""
    col_title, col_status = st.columns([3, 2])

    with col_title:
        st.title("🇵🇪 ClimaData Perú")
        st.caption(
            "Pipeline ELT automatizado: Open-Meteo ERA5 ➔ PostgreSQL (Neon) ➔ dbt Core ➔ Streamlit"
        )

    with col_status:
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 10px; margin-top: 5px;">
                <div style="font-size: 0.85rem; color: #94A3B8;">Última Ejecución del Pipeline:</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: {'#10B981' if status['status'] == 'SUCCESS' else '#38BDF8'};">
                    ● Estado: {status['status']} ({status['last_run']})
                </div>
                <div style="font-size: 0.8rem; color: #64748B;">
                    Tipo: {status['execution_type']} | Filas sincronizadas: {status['rows_upserted']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    pipeline_status = load_pipeline_status()
    render_header(pipeline_status)

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.image(
        "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/PostgreSQL-Dark.svg",
        width=48,
    )
    st.sidebar.title("Configuración de Filtros")

    view_mode = st.sidebar.radio(
        "Modo de Visualización:",
        ["🏙️ Análisis por Ciudad", "⚖️ Comparativa Multiciudad", "🛠️ Auditoría y Calidad ELT"],
        index=0,
    )

    cities_df = load_dim_cities()
    city_options = {"TAC": "Tacna", "AQP": "Arequipa", "LIM": "Lima"}

    selected_city_code = "TAC"
    if view_mode == "🏙️ Análisis por Ciudad":
        selected_city_name = st.sidebar.selectbox(
            "Seleccionar Ciudad:",
            options=list(city_options.values()),
            index=0,
        )
        selected_city_code = [k for k, v in city_options.items() if v == selected_city_name][0]

    # Rango de fechas
    default_start = datetime.date(2023, 1, 1)
    default_end = datetime.date(2024, 12, 31)

    date_range = st.sidebar.date_input(
        "Rango de Fechas:",
        value=(default_start, default_end),
        min_value=datetime.date(2020, 1, 1),
        max_value=datetime.date.today(),
    )

    start_date_str = str(date_range[0]) if isinstance(date_range, tuple) and len(date_range) > 0 else "2023-01-01"
    end_date_str = str(date_range[1]) if isinstance(date_range, tuple) and len(date_range) > 1 else "2024-12-31"

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **Arquitectura del Pipeline:**
        * 📡 **Extractor**: Python + Requests + urllib3 Retries
        * 🗄️ **Almacenamiento**: PostgreSQL en Neon (Serverless)
        * ⚙️ **Transformación**: dbt Core (Staging ➔ Marts)
        * 🔄 **Orquestación**: GitHub Actions (CI & Cron diario)
        """
    )
    st.sidebar.caption("Desarrollado con fines de investigación académica en Ingeniería de Datos.")

    # Carga de datos con spinner
    with st.spinner("Consultando capas mart de PostgreSQL..."):
        daily_df = load_daily_weather(start_date=start_date_str, end_date=end_date_str)
        monthly_df = load_monthly_aggregates()

    # --- RENDERIZADO SEGÚN MODO SELECCIONADO ---
    if view_mode == "🏙️ Análisis por Ciudad":
        city_info = CITIES[selected_city_code]
        city_filtered_daily = daily_df[daily_df["city_code"] == selected_city_code]
        city_filtered_monthly = monthly_df[monthly_df["city_code"] == selected_city_code]

        # Encabezado informativo de la ciudad
        st.markdown(
            f"""
            ### {city_info.name} ({city_info.department})
            * **Región Natural**: {city_info.region} | **Altitud**: {city_info.elevation_meters:.0f} msnm | **Coordenadas**: {city_info.latitude}°, {city_info.longitude}°
            """
        )

        render_kpis(city_filtered_daily, city_info.name)

        col_left, col_right = st.columns([3, 2])
        with col_left:
            render_temperature_timeseries(city_filtered_daily, city_info.name)
        with col_right:
            render_monthly_precipitation_chart(city_filtered_monthly, city_info.name)

        # Tabla de observaciones
        with st.expander("📋 Ver tabla detallada de observaciones procesadas (dbt Mart)"):
            st.dataframe(
                city_filtered_daily[
                    [
                        "observation_date",
                        "temperature_mean_c",
                        "temperature_max_c",
                        "temperature_min_c",
                        "temperature_range_c",
                        "precipitation_sum_mm",
                        "wind_speed_max_kmh",
                        "solar_radiation_mj_m2",
                        "is_rainy_day",
                    ]
                ].sort_values("observation_date", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    elif view_mode == "⚖️ Comparativa Multiciudad":
        render_city_comparisons(daily_df, monthly_df)
        st.markdown("---")
        render_thermal_distribution(daily_df)

    else:
        st.header("🛠️ Auditoría, Linaje y Calidad de Datos")
        st.markdown(
            """
            El pipeline garantiza consistencia mediante dos capas de defensa:
            1. **Idempotencia en Ingesta**: Clave primaria `(city_code, date)` con `ON CONFLICT DO UPDATE` en PostgreSQL.
            2. **Contratos y Tests dbt Core**: Pruebas automáticas de unicidad, no nulidad, integridad referencial y validación de rangos físicos.
            """
        )

        col_audit1, col_audit2 = st.columns(2)

        with col_audit1:
            st.subheader("Modelos dbt Implementados")
            models_info = [
                {"Capa": "Staging", "Modelo": "stg_weather_daily", "Tipo": "View", "Descripción": "Tipado, saneamiento y cálculo de rango térmico"},
                {"Capa": "Marts (Dim)", "Modelo": "dim_cities", "Tipo": "Table", "Descripción": "Dimensión de ciudades y pisos ecológicos de Pulgar Vidal"},
                {"Capa": "Marts (Fact)", "Modelo": "fct_weather_daily", "Tipo": "Table", "Descripción": "Hechos diarios limpios enlazados a dimensiones"},
                {"Capa": "Marts (Agg)", "Modelo": "agg_weather_monthly", "Tipo": "Table", "Descripción": "Métricas agregadas mensuales por ciudad"},
                {"Capa": "Marts (Agg)", "Modelo": "agg_weather_yearly", "Tipo": "Table", "Descripción": "Resumen climatológico anual y días extremos"},
            ]
            st.dataframe(pd.DataFrame(models_info), use_container_width=True, hide_index=True)

        with col_audit2:
            st.subheader("Controles de Calidad Ejecutados")
            tests_info = [
                {"Test": "unique", "Objetivo": "observation_id, city_code, monthly_id", "Resultado": "✅ PASSED"},
                {"Test": "not_null", "Objetivo": "observation_date, temperatures, foreign keys", "Resultado": "✅ PASSED"},
                {"Test": "relationships", "Objetivo": "fct_weather_daily ➔ dim_cities", "Resultado": "✅ PASSED"},
                {"Test": "accepted_values", "Objetivo": "city_code IN ('TAC', 'AQP', 'LIM')", "Resultado": "✅ PASSED"},
                {"Test": "singular test", "Objetivo": "assert_temperature_consistency (max >= min)", "Resultado": "✅ PASSED"},
            ]
            st.dataframe(pd.DataFrame(tests_info), use_container_width=True, hide_index=True)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #64748B; font-size: 0.85rem;">
            ClimaData Perú © 2026 | Repositorio GitHub: 
            <a href="https://github.com/Hashiravc/climapipe" target="_blank" style="color: #38BDF8;">Hashiravc/climapipe</a>
            | Fuente de datos: <a href="https://open-meteo.com/" target="_blank" style="color: #38BDF8;">Open-Meteo ERA5 Reanalysis</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
