"""Plotly charts module for ClimaData Perú dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_temperature_timeseries(df: pd.DataFrame, city_name: str) -> None:
    """Gráfico interactivo de series de tiempo de temperaturas diarias."""
    st.subheader(f"📈 Evolución de Temperaturas en {city_name}")

    fig = go.Figure()

    # Área de rango térmico (Min a Max)
    fig.add_trace(
        go.Scatter(
            x=df["observation_date"],
            y=df["temperature_max_c"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            name="Máxima",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["observation_date"],
            y=df["temperature_min_c"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(2, 132, 199, 0.15)",
            showlegend=True,
            name="Rango Térmico (Mín - Máx)",
        )
    )

    # Curva de Temperatura Media
    fig.add_trace(
        go.Scatter(
            x=df["observation_date"],
            y=df["temperature_mean_c"],
            mode="lines",
            line=dict(color="#38BDF8", width=2),
            name="Temp. Media",
        )
    )

    # Media móvil de 30 días para suavizar tendencias
    if len(df) > 30:
        df_sorted = df.sort_values("observation_date").copy()
        df_sorted["rolling_mean"] = df_sorted["temperature_mean_c"].rolling(window=30, min_periods=7).mean()
        fig.add_trace(
            go.Scatter(
                x=df_sorted["observation_date"],
                y=df_sorted["rolling_mean"],
                mode="lines",
                line=dict(color="#F59E0B", width=2.5, dash="dash"),
                name="Tendencia (Media Móvil 30d)",
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(title="Temperatura (°C)", gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(title="Fecha", gridcolor="rgba(255,255,255,0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_monthly_precipitation_chart(monthly_df: pd.DataFrame, city_name: str) -> None:
    """Gráfico de barras de precipitación acumulada mensual y días lluviosos."""
    st.subheader(f"🌧️ Precipitación Mensual y Días de Lluvia en {city_name}")

    if monthly_df.empty:
        st.info("Sin registros mensuales para graficar.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly_df["year_month"],
            y=monthly_df["total_precipitation_mm"],
            name="Precipitación Total (mm)",
            marker_color="#0EA5E9",
            opacity=0.85,
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly_df["year_month"],
            y=monthly_df["rainy_days_count"],
            name="Días con Lluvia",
            mode="lines+markers",
            line=dict(color="#10B981", width=2),
            marker=dict(size=6),
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Mes", tickangle=-45, gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(title="Precipitación (mm)", gridcolor="rgba(255,255,255,0.08)"),
        yaxis2=dict(
            title="N° Días con Lluvia",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_thermal_distribution(df: pd.DataFrame) -> None:
    """Histograma y distribución del rango térmico diario."""
    st.subheader("📊 Distribución de la Amplitud Térmica Diaria")

    fig = px.histogram(
        df,
        x="temperature_range_c",
        color="city_name",
        nbins=30,
        barmode="overlay",
        marginal="box",
        labels={"temperature_range_c": "Oscilación Térmica (°C)", "city_name": "Ciudad"},
        color_discrete_map={
            "Tacna": "#F59E0B",
            "Arequipa": "#EF4444",
            "Lima": "#3B82F6",
        },
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
