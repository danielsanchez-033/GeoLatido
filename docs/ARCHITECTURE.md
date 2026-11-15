# Arquitectura

```
                       ┌────────────── NASA CMR (metadatos públicos) ──────────────┐
                       │                                                            │
config/aois ──> catalog ──> ingest ──> processor ──> data/artifacts ──> verdicts ──┤
                                                                         │          │
config/events ─────────────────────────────────────────> research <──────┘  <── NASA EONET
                                                            │                      OSM Nominatim (opcional)
                                                       data/research (SQLite)
                                                            │
                    gateway :8080 (/api/catalog, /api/verdicts, /api/research, /api/auth, /tiles)
                                                            │
                                                  frontend :3000 (pestaña Investigar)
```

## Servicio `research` (2026-11-15)

Servicio nuevo y aditivo: no cambia ninguna ruta existente. No importa código de otros servicios: llama a `verdicts`
por HTTP y lee el manifiesto de Eco (contrato `artifact-manifest.schema.json`) en solo lectura para las celdas de 1 km.

| Módulo | Fase del encargo | Qué hace |
|---|---|---|
| `products.py` | 2 | Registro de 17 colecciones CMR con sensor, banda, nivel, polarizaciones y fase |
| `discovery.py` | 2, 3 | Consulta CMR por área y periodo; normaliza adquisiciones; avisa de incompatibilidades |
| `analysis.py` | 5 | Veredictos por serie, hallazgos con geometría, confianza descriptiva |
| `temporal.py` | 5 | Theil-Sen, media móvil, anomalías MAD, punto de cambio, huecos |
| `events.py` | 6 | Registro verificado + EONET; correlación en cuatro niveles sin causalidad |
| `assess.py` | 4, 7, 10 | Evaluación InSAR, inventario de susceptibilidad, comparación entre áreas |
| `places.py`, `nlq.py` | 8 | Nomenclátor con procedencia, Nominatim opcional, parser de preguntas |
| `story.py` | 9 | Historia de 17 secciones, evidencia por afirmación, comprobación de trazabilidad |
| `pipeline.py`, `store.py` | 14, 16 | Trabajos asíncronos cancelables (máx. 2), persistencia SQLite |

## Servicio `online` (2026-11-15): veredictos de la zona buscada

Al elegir en la barra superior un lugar sin veredictos, la interfaz pide `POST /api/online/zones` con su nombre y su
caja. El servicio, uno a uno y con estado en `data/aois-online/<zona>.job.json`:

1. Crea la zona (`data/aois-online/<zona>.yaml`, como las de `config/aois`), centrada en el lugar y de 0,3° como
   mucho por lado, con ventana de 150 días. catalog lee esa carpeta además de `config/aois` (`AOI_DIR` con `:`).
2. Elige con `catalog /aois/<zona>/series` la serie con HH y HV (processor no procesa otras) que contiene la zona y
   tiene más fechas. Sin ninguna, termina en `no_processable_series` y lista las que hay.
3. `python -m processor run-remote --last 4`: abre las 4 fechas más recientes en NASA por HTTPS (con el
   `EARTHDATA_TOKEN` del `.env`) y lee **en memoria** solo la ventana de la zona. No escribe recortes en disco: solo
   los artefactos del veredicto en `data/artifacts/<zona>`. Sin `radarGrid` ni DEM, no marca layover ni sombra (el
   manifiesto lo avisa).
4. Al terminar, el trabajo trae `summary`: por par, fechas, días, estado y fracción de cambio, calculados del manifiesto
   con la regla de verdicts (umbrales copiados, `calibrated: false`). La pestaña Hallazgos lo enseña en cuanto llega.
5. verdicts y tiles ven `data/artifacts/<zona>` sin reiniciarse; la interfaz recarga las zonas y pasa a sus veredictos,
   que son los que mandan.

En la interfaz, el procesado vive en la pestaña Hallazgos: una ciudad buscada se procesa sola y abre Hallazgos; un
punto elegido con un clic en el mapa (caja de ±0,05°, «Punto lat, lon», sin mover el mapa) espera al botón «Procesar
veredictos de este punto». La historia y la investigación usan ese punto.

processor se instala en la imagen de `online` y se llama como programa: no se importa. ingest no interviene.

## Historia de la zona

La pestaña Historia ya no es la historia fija de Parral: para la zona activa (la buscada, o la de veredictos en
pantalla) pide a `research` una investigación del último año y muestra su historia de 17 capítulos con reproducción
(`VisorHistoria`): cada 7 s avanza un capítulo y el mapa vuela a su zona o abre su par. Los acontecimientos (USGS, GDACS,
Copernicus EMS, IBTrACS, EONET, NASA GLC y el registro verificado) salen con su enlace de origen en la evidencia.

## Modelo de datos

Las entidades del encargo se guardan como documentos JSON en SQLite (`data/research/research.db`):

| Entidad | Dónde vive |
|---|---|
| ResearchProject, ResearchQuery | tabla `research` (`plan` con la pregunta interpretada) |
| GeographicArea | `plan.areas[]` (caja, fuente, aproximada o no) |
| SatelliteAcquisition, DataProduct | `discovery[].acquisitions[]`, `discovery[].products[]` |
| ProcessingJob | `job` (estado, paso, error, horas) |
| AnalysisResult, TemporalObservation | `analysis[].series[]` (puntos y análisis temporal) |
| DetectedAnomaly | `analysis[].findings[]` |
| HistoricalEvent | `events[].events[]` y `correlations[]` |
| RiskAssessment | `risk[]` (inventario de factores) e `insar[]` |
| ScientificStory, StoryChapter, Evidence, StorySource | tabla `stories` (`chapters[]`, `evidence[]`) |

Una investigación guarda las respuestas normalizadas de cada proveedor y su procedencia: se puede volver a leer
aunque cambie el catálogo, y repetir un paso sin repetir los anteriores.

## Decisiones

- **Servicio nuevo, no ampliar `verdicts`.** `verdicts` responde por un par; la investigación cruza áreas, fuentes y
  tiempo. Separarlo mantiene los contratos existentes sin cambios.
- **Sin modelo de lenguaje.** La pila no tiene uno y el encargo prohíbe inventar cifras. La historia se arma con
  plantillas sobre los resultados; `check_traceability` falla si una afirmación con cifras no cita evidencia.
- **Sin InSAR propio.** GCOV no tiene fase. Se descubren GUNW, DISP-S1 y SLC y se dice qué haría falta.
- **Sin puntuación de riesgo.** Faltan geología, red hidrográfica, uso de suelo e inventarios. Se inventarían factores.
- **Datos sintéticos solo en pruebas**, con ids `SYNTH-` y `data_kind: synthetic`; la historia lo avisa en el título.
