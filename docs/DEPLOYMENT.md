# Despliegue

```bash
docker compose up --build
```

App en `http://localhost:3000` y API en `http://localhost:8080`. El servicio `research` arranca con la pila; guarda sus
investigaciones en `./data/research` (fuera de git) y lee `./data/artifacts` y `./config/events` en solo lectura.
Tope de memoria: 256 MB (no lee rásteres).

## Variables de `research`

| Variable | Por omisión (compose) | Qué hace |
|---|---|---|
| `VERDICTS_URL` | `http://verdicts:8000` | API de veredictos |
| `ARTIFACT_ROOT` | `/data/artifacts` | Manifiestos para las celdas de 1 km |
| `EVENTS_DIR` | `/config/events` | Registro de acontecimientos verificados |
| `RESEARCH_DATA_DIR` | `/data/research` | Base SQLite |
| `RESEARCH_MAX_JOBS` | `2` | Investigaciones en paralelo |
| `RESEARCH_GEOCODER` | `nominatim` | Geocodificador de OSM; vacío lo apaga |
| `RESEARCH_EONET` | `1` | NASA EONET; `0` lo apaga |
| `RESEARCH_DISCOVERY_LIMIT` | `100` | Adquisiciones listadas por producto y área (el total de CMR se da aparte) |
| `RESEARCH_EVENT_PROVIDERS` | vacío (todos) | Lista separada por comas: `usgs,gdacs,copernicus_ems,nasa_glc,ibtracs,reliefweb,firms` |
| `RELIEFWEB_APPNAME` | vacío | Nombre de aplicación aprobado por ReliefWeb; sin él, esa fuente no se consulta |
| `FIRMS_MAP_KEY` | vacío | Clave gratuita de NASA FIRMS; sin ella, esa fuente no se consulta |

Variables de `online` (procesado en línea):

| Variable | Por omisión | Qué hace |
|---|---|---|
| `EARTHDATA_TOKEN` | del `.env` | Obligatoria para procesar: sin ella `POST /zones` responde 503 |
| `ONLINE_MAX_SPAN_DEG` | `0.3` | Lado máximo de la zona, en grados |
| `ONLINE_MAX_DATES` | `4` | Fechas más recientes que se traen y procesan |

Nada se guarda en disco salvo el resultado (`data/artifacts/<zona>` y el estado en `data/aois-online`). Medido el
2026-11-15 con Delicias (Chihuahua, 0,1° × 0,1°, T048A-F016): las cuatro capas de una fecha suman 17,8 MB de trozos
comprimidos y se leen en unos 35 s. Con la caja que da Nominatim para Delicias, recortada al máximo de 0,3° × 0,3°
(nueve veces el área), las 4 fechas tardaron 890 s (casi 4 min por fecha) y dejaron 689 MB de artefactos; ningún
recorte en disco. La primera versión copiaba recortes con ingest y llegó a 8,7 GB de red sin
terminar dos fechas; se descartó.

Solo `RELIEFWEB_APPNAME` y `FIRMS_MAP_KEY` son credenciales: van en el `.env` local, nunca en git. Los catálogos
descargados (NASA GLC, IBTrACS) se guardan en `data/research/cache`. El resto de variables (`EARTHDATA_TOKEN`, `AUTH_*`) no cambia; ver `.env.example`.

## Solo `research`, fuera de Docker

```bash
cd services/research
pip install -e ".[dev]"
pytest -q
VERDICTS_URL=http://localhost:8080/api/verdicts EVENTS_DIR=../../config/events ARTIFACT_ROOT=../../data/artifacts \
  uvicorn --factory research.main:create_app --port 8010
```

## Demostración

1. `docker compose up --build` y abrir `http://localhost:3000`.
2. Pestaña **Investigar** (icono de pluma en la barra derecha).
3. Elegir «Compara Parral y Jakobshavn durante 2026» y pulsar **Investigar** (unos 15 s con CMR real).
4. Recorrer los capítulos: «Hallazgos» abre en el mapa el primer par con cambio (T048, 2026-08-16 → 2026-08-28, con datos reales); cada afirmación
   despliega su evidencia y el enlace al veredicto JSON.
5. Descargar el informe en Markdown o JSON.
