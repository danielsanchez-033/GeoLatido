# Auditoría del proyecto (2026-11-15)

Auditoría hecha antes de ampliar Dancing with the SAR hacia investigaciones e historias científicas. Todo lo que
sigue se comprobó leyendo el código de `main` (3b604a4) o consultando CMR y EONET en vivo el 2026-11-15. Lo que no se
pudo comprobar está marcado.

## 1. Arquitectura existente

| Pieza | Tecnología | Qué hace | Dónde |
|---|---|---|---|
| `catalog` | FastAPI, httpx, CMR | Zonas (`config/aois`), series GCOV comparables, línea de tiempo con latencia, referencias ópticas (Earth Search) y OPERA DSWx-S1, búsqueda de pasadas y buscador mundial (`/search/world`) | `services/catalog` |
| `ingest` | h5py, fsspec | Lee por HTTPS solo el recorte de cada gránulo GCOV y el plan de observación | `services/ingest` |
| `processor` | numpy, rasterio | HH/HV en dB, cambio por par con desplazamiento de escena restado, QA, layover y sombra con `radarGrid` + GLO-30, celdas de 1 km, filtro multitemporal opcional, COG y manifiesto | `services/processor` |
| `verdicts` | FastAPI, rasterio | Veredicto en tres estados por par, consulta de eventos, serie por píxel, contraste óptico y con OPERA, búsqueda y exportación | `services/verdicts` |
| `auth` | FastAPI, SQLite, JWT Ed25519 | Cuentas, perfiles, tokens personales, historias de la comunidad | `services/auth` |
| `gateway` | nginx | Punto único `:8080`, CORS, cuotas, lista blanca de teselas | `gateway/` |
| `tiles` | TiTiler 2.4.0 | Teselas de los COG propios y de Sentinel-2 | `docker-compose.yml` |
| `frontend` | Vite, React 19, MapLibre 6.16 | Globo 3D/2D, veredictos, historia de Parral, ¿pudo verlo?, comunidad, buscador mundial | `frontend/` |

Base de datos: no hay una base central. `auth` usa SQLite en `data/auth`; el resto son archivos (manifiestos y COG en
`data/artifacts`, caché en `data/cache`). Los servicios no se importan entre sí: hablan por HTTP o por los contratos
de `contracts/`.

## 2. Datos SAR y polarizaciones

- Solo NISAR L2 GCOV (`NISAR_L2_GCOV_PROVISIONAL_V1`), banda L, modo 40 MHz `DHDH`: **HH y HV**. No hay VV ni VH en
  los datos procesados, y el código lo comprueba (`processor/gcov.py`).
- HH/HV se convierten a dB, se suavizan 5 × 5 y se comparan por par; el cambio se mide respecto al desplazamiento de
  toda la escena (T-ECO-07). GCOV ya es un producto geocodificado con corrección radiométrica de relieve: el proyecto
  no calibra ni geocodifica, y lo dice.
- No hay fase: GCOV es potencia (covarianza), así que **no se puede hacer InSAR con los artefactos actuales**.
- Datos locales comprobados: `data/artifacts/parral/T048A-F015` y `T171D-F075`, `data_kind: real`, manifiestos
  anteriores a la ola 2 (sin `cells`, sin `noise_*`, sin `dem.tif`).

## 3. Proveedores existentes

CMR (NISAR GCOV, OPERA DSWx-S1, plan de observación), ASF (gránulos y vistas previas), PO.DAAC (DSWx-S1 con token),
Earth Search (Sentinel-2 L2A), Copernicus GLO-30 en AWS (DEM), OpenStreetMap y EOX cloudless (mapa base).

Comprobado en CMR el 2026-11-15 (gránulos del último año sobre la ciudad de Parral / Sermeq Kujalleq en Groenlandia):

| Colección CMR | Parral | Groenlandia |
|---|---|---|
| NISAR_L2_GCOV_PROVISIONAL_V1 | 19 | 58 |
| NISAR_L2_GUNW_PROVISIONAL_V1 | 18 | 52 |
| OPERA_L2_RTC-S1_V1 | 170 | 1041 |
| OPERA_L3_DISP-S1_V1 | 9 | 0 |
| OPERA_L3_DSWX-S1_V1 / DSWX-HLS_V1 | 141 / 234 | 349 / 367 |
| OPERA_L3_DIST-ALERT-S1_V1 | 25 | 33 |
| SENTINEL-1A / 1C GRD | 52 / 13 | 82 / 166 |
| HLSL30, MOD13Q1, ATL06 | 86, 23, 12 | 92, 43, 23 |
| GPM_3IMERGDL (global) | 531 en el año | igual |
| NASADEM_HGT, GRACE-FO mascons | estáticos / 1 | igual |

`COP30` no existe en CMR (el GLO-30 se lee de AWS, como ya hace `processor`). NASA EONET v3 responde sin cuenta.

## 4. Funcionalidades implementadas

Veredictos auditables por par y ventana completa, consulta de eventos con persistencias declaradas, serie por píxel,
contraste óptico y de agua, búsqueda y exportación por perfil, cuotas, relieve, celdas de 1 km, historias de la
comunidad con estrellas, globo 3D con comparador, línea de tiempo, buscador mundial de pasadas.

## 5. Funcionalidades incompletas o ausentes (frente al encargo)

- No hay investigación guiada por una pregunta, ni geocodificador (el buscador de ubicación dice «Próximamente»).
- No hay catálogo multi-sensor: solo NISAR GCOV y dos referencias.
- No hay InSAR, ni precipitación, ni series largas (los datos NISAR empiezan en 2025; las series procesadas, el 2026-06-17).
- No hay análisis temporal sobre la serie de veredictos (tendencia, anomalías, puntos de cambio).
- No hay registro de acontecimientos ni correlación; la tormenta del 2026-07-01 solo vive en `MEMORY.md` y la historia.
- No hay evaluación de susceptibilidad.
- No hay historias generadas a partir de evidencia; la historia de Parral está escrita a mano.
- `specs/08-interfaz` y `specs/06-acceso` aún describen vistas por perfil (pendiente anotado en `MEMORY.md`).

## 6. Dependencias

Python 3.10+ (FastAPI, httpx, numpy, rasterio, h5py, PyJWT, argon2), Node 22 (React, MapLibre, i18next,
openapi-fetch), Docker Compose. Ninguna dependencia nueva es necesaria para el motor de investigación salvo PyYAML,
que ya usa `catalog`.

## 7. Oportunidades de reutilización

- La API de `verdicts` ya da todo lo necesario para el análisis temporal de las zonas procesadas (fracciones,
  desplazamiento de escena, ruido, agua, banderas).
- El manifiesto de Eco (contrato) da geometría por celda de 1 km cuando existe.
- El patrón de `catalog/world.py` (CMR sin cuenta, normalización de gránulos) sirve para el catálogo multi-sensor.
- El gateway ya sabe aceptar POST en una ruta (`/api/auth/`) y el frontend ya sabe volar a una caja (`volarMundo`).

## 8. Riesgos técnicos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Sin token de Earthdata en la pila | No se leen IMERG, DISP-S1, GUNW ni ATL06 | Se descubren (metadatos públicos) y se declara que no se analizaron |
| Datos NISAR desde 2025 | «Diez años» no es posible con NISAR | El motor lo dice y propone Sentinel-1 (2014-) como fuente de cobertura, sin analizarla |
| Sin LLM en la pila | No hay redacción libre | Generador determinista con plantillas y evidencia; un LLM solo podría reescribir afirmaciones ya trazadas |
| Proveedores externos caídos | Investigación incompleta | Cada proveedor falla por separado y queda registrado en la investigación |
| Memoria de 16 GB | La pila ya está ajustada | El servicio nuevo no lee rásteres grandes y se limita a 256 MB |

## 9. Plan de implementación (ejecutado el 2026-11-15)

Un servicio nuevo, `services/research`, sin tocar el comportamiento de los existentes:

1. Catálogo de productos y descubrimiento normalizado en CMR (fase 2).
2. Capacidad SAR/InSAR declarada por producto: polarizaciones reales, nivel, fase (fases 3-4).
3. Análisis temporal y anomalías sobre los veredictos de `verdicts` y celdas del manifiesto (fase 5).
4. Registro de acontecimientos verificados y EONET, con correlación de cuatro niveles (fase 6).
5. Inventario de factores de susceptibilidad sin puntuar riesgo (fase 7).
6. Parser de preguntas en español e inglés y geocodificador (fase 8).
7. Historias de 17 secciones con evidencia por afirmación y exportación (fase 9).
8. Pestaña Investigación en el frontend y ruta `/api/research/` en el gateway (fase 10).
9. Pruebas y documentación (fase 11).
