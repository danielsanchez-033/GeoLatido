# Eco — tareas

| ID | Tarea | Prioridad | Depende de | Estado |
|---|---|---|---|---|
| T-ECO-01 | Detección de cambio, estados y COGs | — | — | hecha |
| T-ECO-02 | [P] Procesar por pares, sin todas las fechas en memoria, y medir la RAM | P0 | — | hecha (PR 12) |
| T-ECO-03 | [P] Control de calidad por fecha en el manifiesto (`dates[].qa`) | P0 | Visto bueno de Balanza al contrato | hecha (PR 8) |
| T-ECO-04 | [P] Modo y polarización desde los metadatos del producto | P0 | — | hecha (PR 13) |
| T-ECO-05 | Layover y sombra con DEM GLO-30 (estado 15) | P1 | `radarGrid` en el recorte (PR 23 y 25) | hecha (PR 24) |
| T-ECO-06 | Verificar la georreferencia con La Boquilla frente a Sentinel-2 | P1 | Datos reales, T-ANT-05 | hecha (PR 21) |
| T-ECO-07 | Calibrar umbrales con datos reales | P1 | T-ANT-03, acuerdo con Balanza | hecha |
| T-ECO-08 | Filtro multitemporal opcional | P2 | T-ECO-02 | hecha |

## Ola 2: acceso, búsqueda e interfaz

Aprobada el 2026-11-14 por las cinco personas (PR 66). Especificaciones en [06-acceso](../06-acceso/spec.md), [07-busqueda](../07-busqueda/spec.md) y [08-interfaz](../08-interfaz/spec.md). Prioridades de esta ola en [specs/README.md](../README.md#prioridades-de-la-ola-2).

| ID | Tarea | Prioridad | Depende de | Estado |
|---|---|---|---|---|
| T-ECO-09 | [P] Dispersión de la diferencia por par en el manifiesto: `stats.noise_hh_db` y `stats.noise_hv_db`, opcionales, con su cambio de esquema (1,4826 · MAD alrededor de la mediana, sobre los píxeles observables, tras suavizar 5 × 5 y antes del filtro de grupos; definición en RF-BUS-08) | P1 | — | hecha (PR 89) |
| T-ECO-10 | [P] Publicar el DEM GLO-30 de la zona como COG en `artifacts/<aoi>/dem.tif`, en su malla nativa (1″, EPSG:4326) recortada con margen y sin remuestrear a 10 m, y declararlo en el manifiesto con un campo opcional que diga la fuente, que las alturas son ortométricas (EGM2008) y el texto de atribución de Copernicus (RF-INT-12) | P1 | — | hecha (PR 92) |
| T-ECO-11 | Revisar la exactitud física de las explicaciones de la vista Estudiante (dB, HH y HV, ruido, looks, layover) | P1 | T-FAR-14 | pendiente |
| T-ECO-12 | Celdas de 1 km como GeoJSON en `artifacts`, para buscar por rectángulo sin leer el COG en cada consulta: por celda, `changed_fraction`, `observed_fraction` y `state` (con `MIN_OBSERVED_FRACTION` de Balanza, para no dar 0 % donde no se observó) y su polígono reproyectado a WGS84, no una caja (RF-BUS-10) | P2 | — | hecha (PR 94) |
| T-ECO-13 | DEM sintético en `seed-synthetic`, marcado como sintético en el GeoTIFF y en el manifiesto (`dem.data_kind`), para probar el relieve (prueba de humo, T-BAL-15, T-ATL-12) sin bajar GLO-30. Nunca se usa con gránulos reales | P1 | T-ECO-10 | hecha (PR 106) |
