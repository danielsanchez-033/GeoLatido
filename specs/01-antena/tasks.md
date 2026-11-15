# Antena — tareas

| ID | Tarea | Prioridad | Depende de | Estado |
|---|---|---|---|---|
| T-ANT-01 | Series comparables desde CMR | — | — | hecha |
| T-ANT-02 | Servicio `ingest` con lectura por recorte | P0 | — | hecha (PR 2) |
| T-ANT-03 | Prueba real con `--limit 2`: medir MB, segundos y RAM, y anotarlo en MEMORY | P0 | Cuenta de Earthdata, T-ANT-02 | hecha |
| T-ANT-04 | [P] `GET /aois/{id}/timeline` con pasadas UTC, intervalos, huecos y latencia | P0 | — | hecha (PR 5) |
| T-ANT-05 | [P] `GET /aois/{id}/references/optical` con Sentinel-2 L2A de Earth Search | P1 | — | hecha (PR 7) |
| T-ANT-06 | [P] `GET /aois/{id}/references/opera` con DSWx-S1 a ±N días, agrupado por pasada y sin versiones repetidas (diseño en `plan.md`) | P1 | — | hecha |
| T-ANT-07 | Registro de ingesta por serie (`ingest.json`) | P1 | T-ANT-02 | hecha |
| T-ANT-08 | Ingesta de la serie T171 descendente | P1 | T-ANT-03 | hecha |
| T-ANT-09 | Siguiente pasada con el plan de observación de NISAR (`NISAR_COP`): `ingest plan` y `observation_plan` en la línea de tiempo (diseño en `plan.md`) | P2 | — | hecha |
| T-ANT-10 | Excluir gránulos defectuosos declarados en la zona (T171 del 2026-08-13) | P0 | — | hecha |
| T-ANT-11 | Copiar `radarGrid` al recorte para que Eco marque layover y sombra (T-ECO-05) | P0 | — | hecha |
| T-ANT-12 | Cerrar los criterios de horas UTC en ISO 8601 y de 502 ante fallos externos | P1 | — | hecha |
| T-ANT-13 | Sacar la caja de cada tesela OPERA (`bbox`) en `/references/opera`, para que Atlas sitúe `browse_url` en el mapa | P1 | T-ANT-06 | hecha |
| T-ANT-19 | Sacar la caja de los datos de cada tesela Sentinel-2 (`bbox`) en `/references/optical`, para que Atlas la use como `bounds` y no pida teselas fuera de su huella (T-ATL-08); Balanza la pasa a `OpticalTileOut` | P2 | T-ANT-05 | hecha |
| T-ANT-20 | Historias de la comunidad en `auth`: crear, listar, leer, borrar las propias, estrellas de 1 a 5 con desglose por perfil y descarga con sesión (RF-ACC-13 a 17) | P2 | T-ANT-14 | hecha (2026-11-14): `services/auth/src/auth/stories.py` con rutas en `/stories` (sin `PUT`), tablas `stories` y `story_ratings`, 14 pruebas nuevas (65 en total, una comprueba que la historia más grande cabe en 4 KB) y contrato regenerado. Probado con la pila de Docker en `AUTH_ENABLED=1`: crear, listar sin cuenta, valorar con desglose por perfil y guardar desde la interfaz |

## Ola 2: acceso, búsqueda e interfaz

Aprobada el 2026-11-14 por las cinco personas (PR 66). Especificaciones en [06-acceso](../06-acceso/spec.md), [07-busqueda](../07-busqueda/spec.md) y [08-interfaz](../08-interfaz/spec.md). Prioridades de esta ola en [specs/README.md](../README.md#prioridades-de-la-ola-2).

| ID | Tarea | Prioridad | Depende de | Estado |
|---|---|---|---|---|
| T-ANT-14 | [P] Servicio `services/auth`: registro, inicio de sesión, renovación rotativa, cierre, `/me`, `/verify` y JWKS; Argon2id, EdDSA y SQLite en volumen; contrato `contracts/auth.openapi.json` (RF-ACC-01 a 04 y 12) | P0 | — | hecha (2026-11-14): `services/auth` con `uvicorn --factory`, 21 pruebas, contrato `contracts/auth.openapi.json` y probado en Docker. Montado en el compose y en el gateway por Balanza (T-BAL-10, PR 97) |
| T-ANT-15 | Orden para crear cuentas de prueba con contraseñas del `.env`, documentada en el README del servicio | P1 | T-ANT-14 | hecha (2026-11-14): `python -m auth seed-accounts [--env-file]`, solo lee `AUTH_TEST_*`, idempotente, no cambia perfiles ni imprime contraseñas; 8 pruebas y probada con la pila de Docker |
| T-ANT-16 | [P] `GET /search/passes` en catalog: fechas, dirección, latencia, precisión de órbita, exclusión y plan (RF-BUS-07) | P1 | — | hecha (2026-11-14): pasadas adquiridas, excluidas y estimadas, con filtros, orden, cursor y perfil `student` (más de 50 por página, `researcher`); probado con CMR real. Añade una comprobación a `scripts/smoke.sh`, que tiene que aprobar Balanza |
| T-ANT-17 | [P] Huella de cada serie (`footprint`, GeoJSON opcional) en `/aois/{id}/series` para el globo (RF-INT-16) | P1 | — | hecha (2026-11-14): `footprint` como Feature GeoJSON con la huella del gránulo más reciente con polígono, anillo cerrado y 5 decimales; probado con CMR real |
| T-ANT-18 | Tokens personales para scripts de `researcher` (RF-ACC-11) | P2 | T-ANT-14 | hecha (2026-11-14): `POST`, `GET` y `DELETE /tokens` con la sesión de un `researcher`, token opaco `nvp_…` de hasta 90 días que se muestra una vez, guardado como SHA-256 y revocable al instante; `/verify` y `/me` lo aceptan. Contrato aditivo, 16 pruebas y probado con la pila en `AUTH_ENABLED=1` y `0` |
