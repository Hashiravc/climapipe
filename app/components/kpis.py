"""KPIs render component for Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_kpis(df: pd.DataFrame, city_name: str) -> None:
    """Renderiza tarjetas métricas principales."""
    if df.empty:
        st.warning("No hay datos disponibles para calcular indicadores en el rango seleccionado.")
        return

    avg_temp = df["temperature_mean_c"].mean()
    max_temp = df["temperature_max_c"].max()
    min_temp = df["temperature_min_c"].min()
    total_precip = df["precipitation_sum_mm"].sum()
    rainy_days = df["is_rainy_day"].sum()
    avg_thermal_range = df["temperature_range_c"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="🌡️ Temp. Media",
            value=f"{avg_temp:.1f} °C",
            help="Promedio histórico de la temperatura diaria",
        )
    with col2:
        st.metric(
            label="🔥 Máx. Absoluta",
            value=f"{max_temp:.1f} °C",
            delta=f"+{max_temp - avg_temp:.1f} °C sobre media",
            delta_color="off",
            help="Pico máximo registrado en el periodo",
        )
    with col3:
        st.metric(
            label="❄️ Mín. Absoluta",
            value=f"{min_temp:.1f} °C",
            delta=f"{min_temp - avg_temp:.1f} °C bajo media",
            delta_color="off",
            help="Pico mínimo registrado en el periodo",
        )
    with col4:
        st.metric(
            label="🌧️ Precip. Total",
            value=f"{total_precip:.1f} mm",
            delta=f"{rainy_days} días con lluvia",
            delta_color="off",
            help="Suma total de precipitación y conteo de días con lluvia",
        )
    with col5:
        st.metric(
            label="🔄 Oscilación Térmica",
            value=f"{avg_thermal_range:.1f} °C",
            help="Amplitud térmica diaria promedio (Máx - Mín)",
        )
