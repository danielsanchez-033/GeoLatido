# Eco — señal y georreferencia: especificación

- **Responsable:** @TakoKami-dev
- **Estado:** aprobada para el hackathon

## Misión

Convertir recortes GCOV en mediciones fiables y bien ubicadas: control de calidad de cada fecha, detección de cambio y capas georreferenciadas que el resto del equipo pueda creer sin revisar el HDF5.

## Alcance

- `services/processor`.
- Contrato `contracts/artifact-manifest.schema.json`, compartido con Balanza.

## Historias de usuario

- Como Balanza, quiero saber qué fechas son sospechosas antes de interpretar un cambio.
- Como Atlas, quiero capas COG con su CRS correcto para que se alineen con el mapa y con el óptico.
- Como jurado, quiero saber por qué un píxel no es observable, incluido el relieve.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-ECO-01 | Detectar cambio entre pares comparables y clasificar cada píxel con su estado | Hecho |
| RF-ECO-02 | Procesar una serie real completa de la zona sin cargar todas las fechas en memoria | Hecho (T-ECO-02) |
| RF-ECO-03 | Control de calidad por fecha en el manifiesto: fracción válida, mediana en dB de HH y HV, desviación respecto a la serie y banderas | Hecho (T-ECO-03) |
| RF-ECO-04 | Leer modo y polarización de los metadatos del producto, no del nombre del archivo | Hecho (T-ECO-04) |
| RF-ECO-05 | Marcar layover y sombra con el DEM Copernicus GLO-30 (estado 15) | Hecho (T-ECO-05) |
| RF-ECO-06 | Verificar la georreferencia contra un rasgo conocido y documentar el desplazamiento | Hecho (T-ECO-06) |
| RF-ECO-07 | Calibrar umbrales con datos reales junto a Balanza | Hecho (T-ECO-07, PR 39) |
| RF-ECO-08 | Filtro multitemporal opcional para reducir el speckle | Hecho (T-ECO-08, PR 36) |

## Criterios de aceptación

- [x] Procesar 10 fechas reales de Parral con menos de 2 GB de RAM. Comprobado el 2026-11-12 con las 10 fechas reales de T048 en Docker: 1611 MB de pico del contenedor (`memory.peak`, incluye caché de archivos) y 389 s.
- [x] Una fecha con su mediana desplazada más de 1,5 dB respecto a la serie aparece marcada en el control de calidad. Comprobado con datos sintéticos (+3 dB), no con datos reales.
- [x] Toda capa COG declara su CRS, y su extensión en WGS84 coincide con la del manifiesto. Prueba `test_every_cog_declares_the_crs_and_covers_the_manifest_bbox`: cada COG cubre el `bbox` y lo excede menos de 0,01°. En las 36 capas reales de Parral (T048 y T171, 2026-11-12) el exceso máximo es 0,004°, por recortar en UTM.
- [x] Ningún píxel no observable cambia de estado por el procesamiento. Prueba `test_unobservable_pixels_keep_their_cause_in_the_written_state`: en cada `state.tif` escrito, los píxeles no observables conservan su causa y nunca valen `no_change` ni `change_probable`.
- [x] Las pruebas sintéticas siguen pasando (28 en `processor`, 2026-11-12).

## Interfaces

- **Consume:** recortes GCOV (`contracts/gcov-subset.md`) y el DEM Copernicus GLO-30.
- **Datos sintéticos:** `seed-synthetic` genera también un DEM sintético de la zona y lo publica como `dem.tif` con `dem.data_kind: "synthetic"`, sin fuente ni atribución de Copernicus (T-ECO-13). Un DEM sintético nunca se usa con gránulos reales: si llega junto a ellos, se ignora para el relieve y para el layover.
- **Produce:** COGs, estados y manifiesto (`contracts/artifact-manifest.schema.json`); el DEM de cada zona como COG en `<zona>/dem.tif` para el relieve de la interfaz (campo `dem` del manifiesto, T-ECO-10), y por cada par un GeoJSON de celdas de 1 km para buscar por rectángulo (campo `cells` del par, T-ECO-12).

## Fuera de alcance

- Redactar textos o decidir el veredicto final, que es trabajo de Balanza.
- Descargar datos, que es trabajo de Antena.

## Resultados

- RF-ECO-06 (2026-11-12): frente a Sentinel-2 en La Boquilla no hay un desplazamiento detectable mayor que un píxel (10 m). Método y cifras en `MEMORY.md`; se repite con `bench/georref.py`.
- RF-ECO-07 (2026-11-12, acordado con Balanza): `low_looks` se decide con la suma de looks en la ventana de 5 × 5 (mínimo 50), no por píxel. El cambio de cada par se mide respecto al desplazamiento de toda la escena (mediana de la diferencia), que se resta antes del umbral y se publica en `stats.scene_shift_hh_db` y `scene_shift_hv_db`. El umbral de fracción del veredicto lo calibra Balanza (T-BAL-07).
- RF-ECO-08 (2026-11-12): filtro de Quegan y Yu, opcional con `processor run --multitemporal` y apagado por omisión. Con T048 real reduce el speckle (ENL de 2,1 a 3,4 en HH) y entre un 10 % y un 50 % el cambio por par, pero no corrige el desplazamiento de toda la escena (T-ECO-07). Si se usa, el manifiesto lo declara.

- T-ECO-10 (2026-11-14): el DEM GLO-30 se publica en su malla nativa (1″, EPSG:4326), recortado a la zona con 0,01° de margen y sin remuestrear a 10 m. El manifiesto lo declara en `dem` con la fuente, `vertical_datum: EGM2008` (alturas ortométricas, no elipsoidales) y el texto de atribución de Copernicus, que la interfaz debe mostrar. Se publica aunque el recorte no traiga `radarGrid`, porque el relieve de la interfaz no depende de marcar layover. En Parral: 2052 × 1692 píxeles, 14,8 MB, de 1521 a 3041 m.
- T-ECO-12 (2026-11-14): cada par trae en `cells` un GeoJSON de celdas de 1 km alineadas a múltiplos de 1 km de la proyección de la escena (dos series en la misma zona UTM comparten celdas) y recortadas a la escena. Por celda: `observed_fraction`, `changed_fraction` sobre lo observado, `pixels` y `state` con la misma regla que el veredicto (`MIN_OBSERVED_FRACTION` 0,5 y `MIN_CHANGED_FRACTION` 0,05, copiados de Balanza y publicados en el GeoJSON). Una celda con menos de la mitad observable sale `not_observable` con su causa, no 0 % de cambio. El polígono se reproyecta a WGS84 desde sus esquinas. Con T048 real 08-16→08-28: 2856 celdas, 986 KB, 0,15 s; la suma de las celdas da el cambio del par salvo el redondeo.

## Preguntas abiertas

- ¿Coinciden píxel a píxel las mallas de un mismo marco entre fechas? Hoy se rechazan si difieren.
- ¿Trae el producto `NISAR_L2_STATIC` capas de geometría útiles para layover y sombra? En los gránulos reales, `identification/staticLayersDataAccess` apunta a él (comprobado el 2026-11-11), pero aún no se ha abierto ninguno.
- El recorte no copia el ancho de banda de la fuente, y `listOfObservationModes` llega como `(NOT SPECIFIED)`. Hoy el código de ancho de banda (`4005`) sale del nombre tras comprobarlo con `listOfFrequencies`. ¿Lo copia Antena en el recorte?
