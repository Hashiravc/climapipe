"""City comparisons module for ClimaData Perú."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_city_comparisons(daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> None:
    """Renderiza vistas comparativas directas entre Tacna, Arequipa y Lima."""
    st.header("⚖️ Análisis Comparativo Multiciudad")
    st.markdown(
        """
        Comparación de perfiles climáticos contrastantes del Perú:
        * **Tacna (Costa Árida)**: Clima desértico subtropical con oscilación térmica moderada y casi nula precipitación.
        * **Arequipa (Sierra / Quechua - 2,328 msnm)**: Clima templado seco de gran altitud, alta radiación, fuerte oscilación térmica y lluvias de verano (enero a marzo).
        * **Lima (Costa Central Húmeda - 154 msnm)**: Clima marítimo con alta humedad, persistente cobertura nubosa (estratos) en invierno y baja amplitud térmica.
        """
    )

    tab1, tab2, tab3 = st.tabs(["🌡️ Temperaturas Comparadas", "🌧️ Régimen de Lluvias", "⛰️ Perfil Geográfico"])

    with tab1:
        st.subheader("Temperaturas Medias Mensuales Comparadas")
        fig_temp = px.line(
            monthly_df,
            x="year_month",
            y="avg_temperature_c",
            color="city_name",
            markers=True,
            labels={"year_month": "Mes", "avg_temperature_c": "Temp. Media (°C)", "city_name": "Ciudad"},
            color_discrete_map={"Tacna": "#F59E0B", "Arequipa": "#EF4444", "Lima": "#3B82F6"},
            template="plotly_dark",
        )
        fig_temp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            hovermode="x unified",
            xaxis=dict(tickangle=-45),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with tab2:
        st.subheader("Precipitación Acumulada Anual/Mensual")
        annual_precip = (
            monthly_df.groupby(["observation_year", "city_name"])["total_precipitation_mm"]
            .sum()
            .reset_index()
        )
        fig_precip = px.bar(
            annual_precip,
            x="observation_year",
            y="total_precipitation_mm",
            color="city_name",
            barmode="group",
            labels={
                "observation_year": "Año",
                "total_precipitation_mm": "Precipitación Acumulada (mm)",
                "city_name": "Ciudad",
            },
            color_discrete_map={"Tacna": "#F59E0B", "Arequipa": "#EF4444", "Lima": "#3B82F6"},
            template="plotly_dark",
        )
        fig_precip.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_precip, use_container_width=True)

    with tab3:
        st.subheader("Pisos Ecológicos y Factores Geográficos")
        geo_summary = [
            {
                "Ciudad": "Lima",
                "Región": "Costa Central",
                "Piso Ecológico": "Chala / Costa",
                "Altitud (msnm)": 154,
                "Latitud": "-12.0464°",
                "Longitud": "-77.0428°",
                "Patrón Dominante": "Alta humedad relativa, garúas de invierno, baja oscilación",
            },
            {
                "Ciudad": "Tacna",
                "Región": "Costa Sur",
                "Piso Ecológico": "Yunga Marítima baja",
                "Altitud (msnm)": 562,
                "Latitud": "-18.0146°",
                "Longitud": "-70.2536°",
                "Patrón Dominante": "Hiperárido, soleado, escasas precipitaciones todo el año",
            },
            {
                "Ciudad": "Arequipa",
                "Región": "Sierra Sur",
                "Piso Ecológico": "Quechua",
                "Altitud (msnm)": 2328,
                "Latitud": "-16.4090°",
                "Longitud": "-71.5375°",
                "Patrón Dominante": "Clima seco, alta radiación UV, lluvias convectivas de verano",
            },
        ]
        st.dataframe(pd.DataFrame(geo_summary), use_container_width=True, hide_index=True)
