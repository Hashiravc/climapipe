# Guion Técnico y Storyboard: ClimaData Perú (Video de 5 Minutos)

**Proyecto:** ClimaData Perú  
**Repositorio:** `Hashiravc/climapipe`  
**Duración Total:** 5 minutos (00:00 - 05:00)  
**Objetivo Académico:** Demostración integral del pipeline ELT automatizado, desde la ingestión en Open-Meteo hasta el dashboard interactivo en Streamlit y la orquestación en GitHub Actions.

---

## ⏱️ Estructura Temporal y Storyboard

### Bloque 1: Introducción y Objetivo (0:00 – 0:30)
* **Pantalla:** Portada del proyecto con el título "ClimaData Perú", logotipo de GitHub y vista general del repositorio público.
* **Audio / Locución:**
  > "Saludos. Presento ClimaData Perú, una solución completa de ingeniería de datos diseñada bajo el paradigma ELT. Nuestro objetivo central es capturar, modelar y analizar datos meteorológicos diarios de tres ciudades peruanas con realidades geográficas muy distintas: Tacna en la costa árida sur, Arequipa en la sierra volcánica a más de 2,300 metros, y Lima en la costa central húmeda. Todo el proceso está construido con tecnologías modernas y orquestado en la nube."
* **Acción en Pantalla:** Mostrar la página principal del repositorio en GitHub, destacando el `README.md` y los badges de CI y pipeline.

---

### Bloque 2: Arquitectura y Tecnologías (0:30 – 1:15)
* **Pantalla:** Diagrama de arquitectura Mermaid renderizado.
* **Audio / Locución:**
  > "La arquitectura del proyecto sigue una estrategia ELT estricta. Primero, extraemos datos de reanálisis ERA5 desde la API de Open-Meteo mediante un cliente resiliente en Python. Segundo, realizamos una carga directa e idempotente en PostgreSQL alojado en Neon, asegurando que ninguna ejecución repetida genere registros duplicados. Tercero, transformamos y aplicamos pruebas de calidad utilizando dbt Core. Finalmente, publicamos las métricas en un dashboard analítico desarrollado con Streamlit y automatizamos todo el ciclo con GitHub Actions."
* **Acción en Pantalla:** Hacer zoom secuencial a cada bloque del diagrama: Fuentes ➔ Ingesta ➔ Neon PostgreSQL ➔ dbt Core ➔ Streamlit.

---

### Bloque 3: Extracción, PostgreSQL y dbt Core (1:15 – 2:15)
* **Pantalla:** Terminal / Editor mostrando el código de `open_meteo.py`, `postgres_loader.py` y los modelos dbt.
* **Audio / Locución:**
  > "En el extractor implementamos reintentos exponenciales con `urllib3` y `requests` para gestionar límites de tasa HTTP 429 y caídas temporales. Para la carga, diseñamos una sentencia UPSERT sobre la clave compuesta `city_code` y `date`. Si un dato ya existe, se actualiza; si no, se inserta. Adicionalmente, auditamos cada corrida en la tabla `raw.pipeline_runs`."
  > "En la fase de transformación, dbt Core estructura los datos en capas: `stg_weather_daily` estandariza tipos y calcula rangos térmicos; mientras que la capa mart genera la dimensión de ciudades y las tablas de agregación mensual y anual. Se aplican pruebas automáticas de unicidad, no nulidad y coherencia física."
* **Acción en Pantalla:**
  1. Abrir `src/loader/postgres_loader.py` y resaltar la cláusula `ON CONFLICT (city_code, date) DO UPDATE`.
  2. Ejecutar `pytest -v` en la terminal mostrando las 9 pruebas pasando en verde.
  3. Ejecutar `dbt parse` confirmando la compilación limpia del proyecto.

---

### Bloque 4: GitHub Actions y Automatización (2:15 – 3:15)
* **Pantalla:** Pestaña 'Actions' de GitHub.
* **Audio / Locución:**
  > "Para la automatización configuramos dos flujos independientes en GitHub Actions. El primero es nuestro CI, que ante cada push o pull request ejecuta las pruebas unitarias con pytest y valida la sintaxis de dbt. El segundo es el pipeline programado, configurado mediante una expresión cron para ejecutarse diariamente a las seis de la mañana, hora de Lima, además de admitir disparo manual con workflow_dispatch. Las credenciales de Neon se gestionan estrictamente a través de GitHub Secrets, protegiendo la seguridad del sistema."
* **Acción en Pantalla:**
  1. Navegar a `.github/workflows/ci.yml` y `.github/workflows/pipeline.yml`.
  2. Mostrar una ejecución exitosa en GitHub Actions con los pasos de extracción, carga y dbt build desplegados.

---

### Bloque 5: Dashboard Desplegado en Streamlit (3:15 – 4:30)
* **Pantalla:** Dashboard interactivo desplegado en la nube pública: `https://climadata-peru.streamlit.app/`.
* **Audio / Locución:**
  > "Aquí observamos el dashboard interactivo de ClimaData Perú. En la parte superior vemos el badge en tiempo real con el estado de la última ejecución del pipeline y la cantidad de filas sincronizadas. En el menú lateral podemos alternar entre el análisis individual por ciudad y la comparativa multiciudad."
  > "Al seleccionar Tacna, apreciamos su marcada aridez con casi nula precipitación y temperaturas templadas constantes. Al cambiar a Arequipa, resalta su fuerte oscilación térmica diaria de hasta 15 grados y la concentración de lluvias en el verano andino. Finalmente, en Lima observamos el patrón marítimo de alta humedad y baja amplitud térmica. La pestaña de auditoría expone el linaje de datos de dbt y el resultado de los controles de calidad."
* **Acción en Pantalla:**
  1. Interactuar con el selector de ciudad cambiando entre Tacna, Arequipa y Lima.
  2. Mostrar los KPIs dinámicos y la curva de tendencia con media móvil de 30 días.
  3. Cambiar a la vista 'Comparativa Multiciudad' y mostrar los gráficos de barras agrupadas y el histograma térmico.
  4. Abrir la pestaña de 'Auditoría y Calidad ELT'.

---

### Bloque 6: Resultados, Repositorio y Cierre (4:30 – 5:00)
* **Pantalla:** Repositorio GitHub con enlaces a la documentación y artículo de DEV.to.
* **Audio / Locución:**
  > "En conclusión, logramos una solución de ingeniería de datos robusta, reproducible y de costo cero gracias a la integración de Open-Meteo, Neon, dbt Core, Streamlit y GitHub Actions. Todo el código fuente, las guías de configuración, las pruebas y el artículo técnico detallado se encuentran disponibles de manera pública en el repositorio. Muchas gracias por su atención."
* **Acción en Pantalla:** Mostrar la sección de enlaces en el README, resaltar el archivo `docs/articulo-devto.md` y despedida con datos del autor.

---

## 📋 Checklist de Grabación para el Autor
- [ ] Resolución de pantalla recomendada: 1080p (1920x1080) a 60 fps.
- [ ] Navegador en modo pantalla completa sin pestañas personales visibles.
- [ ] Terminal con tamaño de fuente legible (mínimo 16px) y fondo oscuro.
- [ ] Comprobar audio con micrófono adecuado sin eco ambiental.
- [ ] Verificar que ninguna clave o secreto aparezca durante la grabación.
