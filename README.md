# 🇵🇪 ClimaData Perú: Pipeline ELT Automatizado de Datos Meteorológicos

[![CI - Integración Continua](https://github.com/Hashiravc/climapipe/actions/workflows/ci.yml/badge.svg)](https://github.com/Hashiravc/climapipe/actions/workflows/ci.yml)
[![Pipeline ELT Automatizado](https://github.com/Hashiravc/climapipe/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Hashiravc/climapipe/actions/workflows/pipeline.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Descripción del Proyecto

**ClimaData Perú** es una solución integral y profesional de **Ingeniería de Datos** orientada a la ingestión, almacenamiento, modelado dimensional y visualización analítica de variables climatológicas históricas de tres ciudades con pisos ecológicos contrastantes del Perú: **Tacna** (costa árida meridional), **Arequipa** (región andina / quechua a 2,328 msnm) y **Lima** (costa central marítima húmeda).

El pipeline adopta el paradigma moderno **ELT (Extract - Load - Transform)**:
1. **Extracción**: Cliente Python resiliente que consume la API histórica ERA5 de **Open-Meteo**.
2. **Carga**: Almacenamiento directo e **idempotente (UPSERT)** en PostgreSQL alojado en la nube serverless de **Neon**.
3. **Transformación**: Modelado dimensional (Staging y Marts), indicadores bioclimáticos y pruebas automáticas de calidad con **dbt Core**.
4. **Visualización**: Dashboard interactivo multipágina construido con **Streamlit** y **Plotly**.
5. **Orquestación**: Automatización de CI y ejecuciones periódicas mediante **GitHub Actions**.

---

## 🎯 Objetivo General

Construir un pipeline ELT automatizado y reproducible en la nube que procese mediciones meteorológicas diarias (temperaturas mínimas, medias y máximas, precipitación acumulada, velocidad del viento y radiación solar), garantizando la no duplicidad de datos mediante mecanismos transaccionales, aplicando pruebas de integridad referencial y exponiendo los hallazgos en un panel de control accesible al público.

---

## 🏗️ Arquitectura del Sistema

```mermaid
flowchart LR
    subgraph Fuentes["📡 Fuentes Externas"]
        OM["Open-Meteo API<br/>(Reanálisis ERA5)"]
    end

    subgraph Ingestion["🔄 Extracción y Carga (Python)"]
        EXT["OpenMeteoExtractor<br/>(Retries & Backoff)"]
        LDR["PostgresLoader<br/>(Idempotent UPSERT)"]
    end

    subgraph DataWarehouse["🗄️ PostgreSQL en Neon"]
        subgraph RawSchema["Esquema raw"]
            RAW_W["raw.weather_daily<br/>(PK: city_code, date)"]
            RAW_P["raw.pipeline_runs<br/>(Auditoría y Métricas)"]
        end
        subgraph MartsSchema["Esquema marts (dbt)"]
            DIM_C["marts.dim_cities<br/>(Pisos Ecológicos)"]
            FCT_W["marts.fct_weather_daily<br/>(Hechos Diarios)"]
            AGG_M["marts.agg_weather_monthly<br/>(Métricas Mensuales)"]
            AGG_Y["marts.agg_weather_yearly<br/>(Resumen Anual)"]
        end
    end

    subgraph Orquestacion["⚙️ Orquestación & CI/CD"]
        GHA_CI["GitHub Actions: CI<br/>(pytest + dbt parse)"]
        GHA_CRON["GitHub Actions: Pipeline<br/>(Cron Diario + Dispatch)"]
    end

    subgraph Presentacion["📊 Capa de Consumo"]
        ST["Streamlit Community Cloud<br/>(Rol: streamlit_reader)"]
    end

    OM -->|JSON HTTP| EXT
    EXT -->|DataFrames Normalizados| LDR
    LDR -->|Transacciones ACID / UPSERT| RAW_W
    LDR -->|Logs de Auditoría| RAW_P

    RAW_W -->|dbt run| STG["stg_weather_daily (View)"]
    STG --> DIM_C
    STG --> FCT_W
    FCT_W --> AGG_M
    FCT_W --> AGG_Y

    GHA_CI -.->|Valida código| EXT
    GHA_CRON -->|Dispara corrida| EXT
    GHA_CRON -->|Dispara| MartsSchema

    MartsSchema -->|Consultas Read-Only| ST
```

---

## 🚀 Tecnologías Utilizadas

| Componente | Tecnología | Justificación Técnica |
| :--- | :--- | :--- |
| **Lenguaje Base** | Python 3.12+ | Ecosistema estándar en Data Engineering para procesamiento y APIs. |
| **Extracción** | `requests` + `urllib3` | Implementación de reintentos exponenciales con gestión de límites (HTTP 429). |
| **Almacenamiento** | PostgreSQL 16 (Neon) | RDBMS relacional serverless, compatible con transacciones ACID y UPSERT nativo. |
| **Transformación** | dbt Core (`dbt-postgres`) | Control de versiones de SQL, modularidad, linaje automatizado y suite de pruebas. |
| **Visualización** | Streamlit + Plotly | Dashboard reactivo con renderizado de gráficos vectoriales interactivos. |
| **CI / Orquestación** | GitHub Actions | Automatización sin servidores de pruebas unitarias y sincronización diaria programada. |
| **Control de Calidad** | `pytest` + dbt data tests | Validación rigurosa de unicidad, no nulidad, rangos físicos y lógica de negocio. |

---

## 📁 Estructura del Repositorio

```text
peru-weather-elt-pipeline/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Integración continua (pytest, dbt parse, validación de archivos)
│       └── pipeline.yml           # Flujo ELT programado (Cron 06:00 PET) y manual (workflow_dispatch)
├── .streamlit/
│   └── config.toml                # Paleta de colores e interfaz del dashboard
├── app/
│   ├── main.py                    # Punto de entrada de la aplicación Streamlit
│   ├── components/                # Componentes modulares de interfaz
│   │   ├── charts.py              # Gráficos interactivos Plotly (series temporales, histogramas)
│   │   ├── comparisons.py         # Tableros comparativos multiciudad y pisos ecológicos
│   │   └── kpis.py                # Tarjetas métricas (temperaturas extremas, precipitación acumulada)
│   └── utils/
│       └── db.py                  # Capa de acceso a datos de solo lectura con caché inteligente
├── dbt_project/                   # Proyecto de ingeniería de transformaciones con dbt Core
│   ├── dbt_project.yml            # Configuración de modelos y rutas
│   ├── profiles.yml               # Conexión parametrizada mediante variables de entorno
│   ├── models/
│   │   ├── staging/
│   │   │   ├── schema.yml         # Contratos, fuentes y tests de staging
│   │   │   └── stg_weather_daily.sql
│   │   └── marts/
│   │       ├── schema.yml         # Documentación de mart, claves foráneas y data tests
│   │       ├── dim_cities.sql     # Dimensión geográfica y pisos de Javier Pulgar Vidal
│   │       ├── fct_weather_daily.sql # Hechos a grano diario
│   │       ├── agg_weather_monthly.sql # Agregaciones mensuales
│   │       └── agg_weather_yearly.sql  # Resumen anual
│   └── tests/
│       └── assert_temperature_consistency.sql # Test singular (temperatura máxima >= mínima)
├── docs/
│   ├── articulo-devto.md          # Artículo técnico completo para DEV.to
│   ├── video-script.md            # Guion estructurado y storyboard para video académico de 5 min
│   └── images/                    # Evidencias visuales y diagramas
├── scripts/
│   └── run_pipeline.py            # CLI orquestador local y cloud del pipeline
├── sql/
│   ├── 01_init_schema.sql         # DDL de esquemas raw, marts y tablas base
│   └── 02_create_roles.sql        # Principio de menor privilegio (escritura vs lectura)
├── src/                           # Módulos Python del pipeline
│   ├── config.py                  # Parámetros, ciudades (Tacna, Arequipa, Lima) y settings
│   ├── extractor/
│   │   └── open_meteo.py          # Cliente HTTP de Open-Meteo ERA5 con reintentos
│   ├── loader/
│   │   └── postgres_loader.py     # Cargador idempotente PostgreSQL con auditoría
│   └── utils/
│       └── logger.py              # Logging estructurado con marcas de tiempo
├── tests/                         # Suite de pruebas unitarias con pytest
│   ├── test_config.py
│   ├── test_extractor.py
│   ├── test_loader.py
│   └── test_transformations.py
├── .env.example                   # Plantilla de variables de entorno
├── .gitignore                     # Exclusiones de Git (credenciales, cachés, virtualenv)
├── README.md                      # Documentación maestra del repositorio
├── requirements.txt               # Dependencias de producción
└── requirements-dev.txt           # Dependencias de desarrollo y testing
```

---

## ⚙️ Instalación y Configuración Local

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Hashiravc/climapipe.git
cd climapipe
```

### 2. Configurar Entorno Virtual
```bash
python -m venv .venv

# En Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# En Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements-dev.txt
```

### 4. Configurar Variables de Entorno
Copia el archivo `.env.example` a `.env` y define tus credenciales:
```bash
cp .env.example .env
```
Edita `.env` con los datos de tu instancia de Neon:
```ini
NEON_DATABASE_URL=postgresql://neondb_owner:tu_password@ep-sample-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
DB_HOST=ep-sample-123456.us-east-2.aws.neon.tech
DB_PORT=5432
DB_NAME=neondb
DB_USER=neondb_owner
DB_PASSWORD=tu_password
DB_SSLMODE=require
```

---

## 🧪 Ejecución de Pruebas Unitarias

Para ejecutar la suite de 9 pruebas automatizadas:
```bash
pytest -v
```

Para validar la sintaxis y modelos de dbt Core:
```bash
dbt parse --project-dir dbt_project --profiles-dir dbt_project
```

---

## 🏃 Ejecución del Pipeline ELT

### Modo Inicial (Backfill Histórico)
Extrae el catálogo histórico completo y ejecuta las transformaciones dbt:
```bash
python scripts/run_pipeline.py --mode initial
```

### Modo Incremental
Detecta la fecha máxima almacenada en la base de datos por ciudad y consulta únicamente los días faltantes:
```bash
python scripts/run_pipeline.py --mode incremental
```

### Modo Local Offline (SQLite para pruebas aisladas)
Permite verificar la lógica sin conexión a Neon:
```bash
python scripts/run_pipeline.py --mode initial --start-date 2024-01-01 --end-date 2024-01-05 --connection-url sqlite:///data/test.db --no-dbt
```

---

## 📊 Lanzamiento del Dashboard Local

Para iniciar la aplicación visual de Streamlit en tu navegador:
```bash
streamlit run app/main.py
```
El panel estará disponible de forma predeterminada en `http://localhost:8501`.

---

## 🤖 Automatización con GitHub Actions

El repositorio cuenta con dos flujos de trabajo en `.github/workflows/`:

1. **`ci.yml`**:
   - Se activa ante cada `push` o `pull_request` a `main`.
   - Instala dependencias, ejecuta las pruebas de `pytest`, valida el proyecto dbt y verifica la integridad de archivos.

2. **`pipeline.yml`**:
   - Se ejecuta automáticamente todos los días a las **06:00 AM hora de Lima (11:00 UTC)** mediante cron.
   - Admite ejecución manual bajo demanda mediante `workflow_dispatch` con parámetros de selección de modo (`incremental` o `initial`).
   - Lee de forma segura los secretos `NEON_DATABASE_URL` y variables de conexión configuradas en el repositorio.

---

## ☁️ Despliegue en la Nube

### 1. Base de Datos en Neon
1. Crea un proyecto gratuito en [Neon](https://neon.tech/).
2. Copia la cadena de conexión con SSL activado.
3. Ejecuta el script `sql/01_init_schema.sql` en la consola SQL de Neon.
4. (Opcional recomendado) Ejecuta `sql/02_create_roles.sql` para generar el usuario `streamlit_reader` de solo lectura.

### 2. Dashboard en Streamlit Community Cloud
1. Inicia sesión en [share.streamlit.io](https://share.streamlit.io/).
2. Conecta tu repositorio `Hashiravc/climapipe`.
3. Establece la ruta principal: `app/main.py`.
4. En la sección **Advanced Settings > Secrets**, configura:
   ```toml
   NEON_DATABASE_URL = "postgresql://streamlit_reader:tu_password@ep-sample-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
   ```
5. Haz clic en **Deploy**. Cada actualización en la rama `main` de GitHub actualizará automáticamente el dashboard desplegado.

---

## 🔗 Enlaces del Proyecto

* **Repositorio en GitHub**: [https://github.com/Hashiravc/climapipe](https://github.com/Hashiravc/climapipe)
* **Artículo Técnico en DEV.to**: Documento maestro disponible en [docs/articulo-devto.md](docs/articulo-devto.md)
* **Guion del Video Académico (5 min)**: Disponible en [docs/video-script.md](docs/video-script.md)
* **API de Datos Meteorológicos**: [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api)

---

## 📄 Licencia

Este proyecto se distribuye bajo la Licencia MIT. Consulta el archivo `LICENSE` para mayores detalles.
