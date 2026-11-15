# Antena — ingesta y tiempo: especificación

- **Responsable:** @KinzzoCS
- **Estado:** aprobada para el hackathon

## Misión

Alimentar el sistema con los datos correctos y decir con exactitud **cuándo** existen: qué pasadas hay, cada cuánto, con qué huecos y con qué retraso se publican. Antena es la única puerta de entrada de datos externos.

## Alcance

- `services/catalog`, `services/ingest` y `config/aois/`.
- Contratos `contracts/catalog.openapi.json` y `contracts/gcov-subset.md`.

## Historias de usuario

- Como Eco, quiero recortes GCOV de una serie comparable para procesarlos sin descargar gránulos completos.
- Como Balanza, quiero las pasadas con hora UTC para decidir si un evento pudo observarse.
- Como Balanza y Atlas, quiero escenas ópticas y referencias OPERA cercanas a cada fecha para contrastar el radar.
- Como jurado, quiero saber la edad y la latencia de cada dato para juzgar su vigencia.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-ANT-01 | Listar series comparables por zona sin mezclar pista, dirección, marco, modo, polarización ni CRID | Hecho |
| RF-ANT-02 | Traer por HTTPS solo el recorte de la zona, de forma reanudable y sin exponer el token | Hecho (T-ANT-02, T-ANT-03) |
| RF-ANT-03 | Publicar una línea de tiempo por zona: pasadas con hora UTC, intervalo en días, huecos y latencia de publicación | Hecho (T-ANT-04) |
| RF-ANT-04 | Estimar la siguiente pasada con el ciclo de 12 días, marcarla como estimación y decir si el plan de observación de NISAR (`NISAR_COP`) la incluye, como plan y nunca como adquisición segura. Si no se sabe, lo dice | Hecho (T-ANT-04, T-ANT-09) |
| RF-ANT-05 | Listar escenas Sentinel-2 L2A por fecha, dentro de ±N días y con nubosidad máxima configurable | Hecho (T-ANT-05) |
| RF-ANT-06 | Listar productos OPERA DSWx-S1 a ±N días de una fecha (7 por defecto), agrupados por pasada de Sentinel-1, sin versiones reprocesadas repetidas, con su cobertura de la zona y enlaces que dicen si requieren cuenta. Si no hay ninguno, lo dice | Hecho (T-ANT-06) |
| RF-ANT-07 | Dejar junto a los recortes de cada serie un registro de ingesta (`ingest.json`) con, por gránulo, los bytes pedidos a NASA y los escritos en disco, los segundos de lectura, la hora UTC de la lectura y la fecha de publicación según `catalog`. Lo que no se midió queda en `null`, nunca estimado | Hecho (T-ANT-07) |
| RF-ANT-08 | Excluir los gránulos defectuosos declarados en `config/aois`, con motivo, evidencia y fecha de comprobación. `catalog` los quita de las series y de la línea de tiempo y los lista aparte en `excluded`; `ingest` no los trae | Hecho (T-ANT-10) |
| RF-ANT-09 | Copiar al recorte `metadata/radarGrid`, si el gránulo lo trae, recortado a los nodos que cubren la ventana más 2 por lado, con todas las alturas y sin cambiar valores (`contracts/gcov-subset.md`) | Hecho (T-ANT-11) |

## Criterios de aceptación

- [x] `ingest fetch --limit 2` con un token real deja dos recortes que `processor run` procesa sin errores.
- [x] La línea de tiempo de Parral muestra el hueco del 27 de julio al 10 de agosto y un intervalo de 24 días a su través.
- [x] Todas las horas de la API están en UTC con formato ISO 8601.
- [x] Un fallo del catálogo externo devuelve un 502 claro, nunca datos parciales sin aviso.
- [x] Las fuentes ópticas no requieren cuenta y su licencia queda citada.
- [x] Cada tesela Sentinel-2 de `/references/optical` trae su caja `bbox` en WGS84, `[oeste, sur, este, norte]`: la del item STAC de Earth Search, que es la de su huella de datos y no la del cuadrado MGRS; si falta o no es válida, la de la huella, y si tampoco hay huella, `null`. Como en STAC, una caja que cruza el antimeridiano trae oeste > este y se conserva así. Para `S2A_13RDK_20260812_1_L2A`, escena de borde de franja, es `[-106.00934, 26.12852, -105.70229, 27.12071]` (T-ANT-19, 2026-11-14).
- [x] Cada serie de `/aois/{id}/series` trae `footprint`: una Feature GeoJSON con la huella del gránulo más reciente que tenga polígono en CMR (`properties.basis: \"latest_granule\"` y su `granule_id`), anillo cerrado y 5 decimales, o `null` si ninguna fecha tiene polígono. En Parral, las dos series traen una huella de 5 puntos que contiene la zona (CMR real, 2026-11-14, T-ANT-17).
- [x] `GET /search/passes` (RF-BUS-07) lista las pasadas adquiridas, excluidas y estimadas de las zonas, filtradas por zona, serie, fechas, dirección, latencia, precisión de órbita (letra del nombre del gránulo), tipo y plan de observación, con orden, total y cursor. Pide el perfil `student` y, con más de 50 por página, `researcher`; sin cuenta, 403 con `required_role`. Es la única ruta de catalog que declara `security` en el contrato. En Parral, con CMR real: 18 adquiridas, la excluida del 08-13, las F del 09-18 y 10-12 de T171 y las siguientes del 11-17 y 11-20, planificadas (2026-11-14, T-ANT-16).
- [x] Un gránulo excluido no aparece en `granules` ni en `passes`, sí en `excluded` con su motivo, y `ingest` no lo descarga.
- [x] `python -m auth seed-accounts` crea una cuenta `student` y otra `researcher` con las contraseñas `AUTH_TEST_*` del `.env` (specs/06-acceso), con las que se puede iniciar sesión. Repetirla no duplica nada y sigue los cambios de contraseña; nunca cambia el perfil de una cuenta existente, ni lee otras variables del `.env`, ni imprime contraseñas (T-ANT-15).
- [x] Un `researcher` con sesión crea, lista y revoca tokens personales en `/api/auth/tokens` (RF-ACC-11): el token sale en claro una sola vez, caduca como mucho a los 90 días, el gateway lo acepta como `researcher` y, revocado o caducado, da 401 desde la petición siguiente, nunca `public`. `student`, `public` y los propios tokens personales reciben 403 con `required_role` al gestionarlos. Probado con la pila de Docker en `AUTH_ENABLED=1` (T-ANT-18).

### Plan de observación (RF-ANT-04, T-ANT-09)

Se comprueban con dobles de CMR y de los XML de `NISAR_COP` que reproducen los planes reales de Parral (ver `MEMORY.md`):

- [x] `ingest plan --aoi parral` escribe `data/plan/parral.json` con cada pasada prevista por serie, desde la última adquirida más 12 días hasta el horizonte pedido, con su estado y el plan que la respalda.
- [x] Una pasada cubierta por una observación L-SAR desde 10 s antes hasta 40 s después de la hora prevista queda `planned`, con el plan y su `config_id`. Si la observación la cubre solo en parte, `partial`. Si hay plan ese día y ninguna observación la toca, `not_planned`. Si no hay plan publicado, `no_plan`.
- [x] Si un día tiene varias versiones del plan, se usa la más reciente y se cita.
- [x] Cada serie declara la `config_id` del plan en su última pasada adquirida, y cada pasada dice si coincide con ella.
- [x] `GET /aois/{id}/timeline` añade `observation_plan` a cada elemento de `next_pass_estimates` sin cambiar `expected_at` ni `basis`. Sin archivo de plan, o sin una pasada prevista que coincida en menos de 60 s, el estado es `unknown`.
- [x] La descripción del campo dice que un plan no garantiza la adquisición.
- [x] El token solo lo usa `ingest`. No aparece en el archivo ni en los errores, y `catalog` no lo lee.
- [x] `contracts/catalog.openapi.json` se regenera, el cambio es aditivo y su prueba de contrato pasa.

### Horas UTC y fallos externos (T-ANT-12)

Detalle de los dos primeros criterios sin marcar hasta el 2026-11-12:

- [x] Cada hora de la API sale como `AAAA-MM-DDTHH:MM:SS[.ffffff]Z`. Lo comprueba una prueba que recorre todas las rutas GET con datos en todas sus listas; si se añade una ruta sin incluirla, falla.
- [x] Una hora con otra zona horaria, de CMR o de Earth Search, sale convertida a UTC. Una hora sin zona que llegue de fuera se toma como UTC, que es la referencia de CMR y de STAC.
- [x] Una hora sin zona creada por el propio `catalog` es un fallo del código: el modelo de respuesta la rechaza, nunca adivina la zona.
- [x] CMR, Earth Search u OPERA caídos, con error HTTP, con una respuesta que no es JSON o sin los campos esperados devuelven 502 con el servicio en `detail`. Nunca un 500 ni una lista vacía.
- [x] Si falla una página posterior a la primera, la respuesta es 502 y no la lista de las páginas ya leídas.

### Registro de ingesta (RF-ANT-07)

Se comprueban con el servidor HTTP local que ya imita a NASA en las pruebas de `ingest`:

- [x] Tras `ingest fetch`, `data/raw/real/<zona>/<serie>/ingest.json` tiene una entrada por cada recorte `.h5` de la carpeta, y ninguna más.
- [x] Cada entrada leída en esa ejecución tiene `bytes_requested` igual a los bytes que pidió `fsspec` al servidor, `subset_bytes` igual al tamaño del archivo y `seconds` mayor que cero.
- [x] `published_at` y `acquired_at` coinciden con los de la pasada en `GET /aois/{id}/timeline`. Si `catalog` no la tiene o no responde, quedan en `null` y la ingesta sigue.
- [x] Una segunda ejecución que salta un recorte conserva su entrada sin cambios.
- [x] Un recorte que ya estaba en disco sin entrada se registra con `origin: "found_on_disk"`, su tamaño, y `null` en `bytes_requested`, `seconds` y `fetched_at`.
- [x] Los gránulos excluidos aparecen en `excluded` y no en `granules`. Si su archivo sigue en disco, también en `stale`.
- [x] Si la ingesta falla a mitad, el registro conserva los recortes que sí se escribieron y nunca queda a medio escribir.
- [x] El registro no contiene el token, y declara `data_kind: "real"` y `published_at_basis: "cmr_updated"`.

### OPERA DSWx-S1 (RF-ANT-06)

Se comprueban con dobles de CMR que reproducen los títulos reales de Parral (ver `MEMORY.md`):

- [x] Parral con `date=2026-06-29` devuelve tres pasadas: la del 06-22 (`days_from_date: -7`) y las dos del 06-27, a las 00:58 y a las 13:04 UTC (`-2`).
- [x] Parral con `date=2026-07-08` devuelve 200 con `acquisitions: []`. Nunca un 404 ni una pasada fuera de la ventana.
- [x] Una tesela con dos versiones de producción aparece una sola vez, con la producción más reciente. El caso real es T13RDL del 2026-06-22 a las 12:56 UTC.
- [x] `covers_aoi` es `true` en Parral, y la respuesta declara `coverage_basis: "tile_bbox"`.
- [x] Los enlaces a GeoTIFF están marcados como que requieren cuenta de Earthdata, y `browse_url` solo apunta al bucket público de PO.DAAC.
- [x] Cada tesela trae su caja `bbox` en WGS84, `[oeste, sur, este, norte]`, o `null` si CMR no la publica. Para T13RDK es `[-106.0587906, 26.1714959, -104.9505393, 27.1667001]`.
- [x] La respuesta cita el DOI `10.5067/OPDSWS1-L3V1` y el tamaño mínimo de masa de agua que el producto detecta.
- [x] Si CMR falla, la ruta responde 502 y no devuelve una lista parcial.
- [x] `catalog` no lee ni necesita el token de Earthdata para esta ruta.
- [x] `contracts/catalog.openapi.json` se regenera y su prueba de contrato pasa.

## Interfaces

- **Consume:** NASA CMR (público, también para OPERA DSWx-S1 de PO.DAAC), NASA Earthdata (token, para los recortes y el plan diario `NISAR_COP`), Earth Search STAC para Sentinel-2 (público).
- **Produce:** API de catálogo, recortes GCOV en `data/raw/real/`, un registro `ingest.json` por serie junto a ellos y el resumen del plan de observación en `data/plan/<zona>.json`. El registro es interno de Antena: no es un contrato, y ningún servicio lo lee todavía. El resumen del plan solo lo lee `catalog`.

## Fuera de alcance

- Procesar o modificar valores radar, que es trabajo de Eco.
- Decidir veredictos, que es trabajo de Balanza.
- Leer o recortar los GeoTIFF de DSWx-S1 y comparar su agua con el radar, que es trabajo de Balanza (RF-BAL-07).
- Georreferenciar la vista previa PNG de DSWx-S1 sobre el mapa, que es trabajo de Atlas.

## Preguntas abiertas

- ¿Ofrece ASF el plan de observación en un formato legible por máquina, para RF-ANT-04? **Respondida el 2026-11-12:** sí, la colección `NISAR_COP` de CMR, con un XML diario. No trae pista ni marco, así que se cruza con la hora prevista por el ciclo. Detalle en `plan.md`.
- ¿Qué `LSAR_CONFIG_ID` corresponde a cada modo? En Parral todas las pasadas de 40 MHz DHDH tienen 156, pero falta la tabla de modos (`ModeTable_v54`) para confirmarlo.
- ¿Qué nubosidad máxima es útil en el monzón de Chihuahua?
- ¿El hueco de DSWx-S1 en Parral entre el 2026-06-28 y el 2026-09-13 es definitivo o se rellenará? Hay que volver a consultar CMR antes de la demo.
