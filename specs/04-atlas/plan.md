# Atlas — plan técnico

## Biblioteca

Recomendada: **MapLibre GL JS** (BSD-3, compatible con Apache-2.0), que admite teselas raster `{z}/{x}/{y}` como las de la API. La decisión final es de Atlas y se registra en MEMORY.

## Mapa base: opciones a verificar

| Opción | Licencia a comprobar | Nota |
|---|---|---|
| Teselas de OpenStreetMap | Datos ODbL; el servidor público tiene una política de uso | Válido para la demo con atribución; no para tráfico alto |
| Sentinel-2 de la propia API (Balanza) | Copernicus, libre con atribución | El óptico del mismo periodo; puede salir nublado |
| Sentinel-2 cloudless de EOX | Depende de la edición; algunas no permiten uso comercial | Revisar antes de usar |

## Interfaz del mapa para Faro

Contrato interno del frontend, independiente del framework:

| Entrada | Tipo | Descripción |
|---|---|---|
| `aoi` | `[oeste, sur, este, norte]` | Encuadre inicial y contorno |
| `layers` | `{ state, change_hh, change_hv }` | Plantillas de tesela tal como vienen de la API, con el host del gateway delante |
| `activeLayer` | `"state" \| "change_hh" \| "change_hv"` | Capa visible |
| `optical` | `{ before?: VistaOptica, after?: VistaOptica }` | Escenas Sentinel-2 de antes y después del veredicto (`verdict.evidence.optical`). Ver la tabla de abajo |
| `compare` | `"off" \| "swipe"` | Modo de comparación |
| `dataKind` | `"real" \| "synthetic"` | El mapa muestra un distintivo si es sintético |

`VistaOptica` sale de `evidence.optical.before` o `.after` de la API de veredictos (PR 19):

| Campo | Tipo | Desde la API | Descripción |
|---|---|---|---|
| `status` | `"clear" \| "cloudy" \| "partial_coverage" \| "none_in_window" \| "catalog_unavailable"` | `status` | Siempre presente. Con `none_in_window` o `catalog_unavailable` no hay escena y el mapa lo dice en lugar de dejar el lado vacío. Con `cloudy` o `partial_coverage` avisa junto a la imagen |
| `tiles` | `string[]` | `scene.tiles[].tile_url` | Una plantilla XYZ por tesela MGRS (4 en Parral), con el host del gateway delante. Se pinta una capa por tesela. Fuera de la huella de su tesela, TiTiler responde 404: el mapa lo trata como tesela vacía, no como error. Vacío si no hay escena |
| `attribution` | `string?` | `scene.attribution` | Se muestra junto a la imagen (licencia Copernicus) |
| `cloudCover` | `number?` | `scene.max_cloud_cover` | Nubosidad en %, de la tesela MGRS completa y no de la zona; el texto lo dice así |
| `acquiredAt` | `string?` | `scene.acquired_at` | Hora UTC de la escena |
| `daysFromRadar` | `number?` | `scene.days_from_radar` | Días respecto a la pasada de radar; negativo si es anterior |
| `coversAoi` | `boolean?` | `scene.covers_aoi` | Si las teselas juntas cubren toda la zona |

Los campos con `?` faltan cuando `scene` es `null`. Faro hace la conversión desde la respuesta de la API; el mapa no llama a la API óptica.

| Evento | Carga | Cuándo |
|---|---|---|
| `onPointSelected` | `{ lon, lat }` con 5 decimales | Clic o tecla Enter sobre el mapa |
| `onViewChanged` | `{ bbox, zoom }` | Al terminar un desplazamiento o zoom |

## Interfaz ampliada (ola 2, T-ATL-11)

Todas las opciones nuevas son **opcionales** (RF-INT-19): un `crearMapa` que solo pase las entradas de arriba funciona igual que en la ola 1, en 2D y sin botones nuevos salvo el de 3D. Las ya disponibles están en [`src/mapa/tipos.ts`](../../frontend/src/mapa/tipos.ts); las que llegan con otra tarea se publican aquí para que Faro programe contra ellas, y entran en `tipos.ts` con su tarea, no antes, para que ningún tipo prometa algo que el mapa aún no hace.

### Entradas

| Opción | Tipo | Por omisión | Estado | Descripción |
|---|---|---|---|---|
| `nombreZona` | `string` | «la zona de estudio» | Disponible | Etiqueta de la extensión y nombre accesible del mapa |
| `causaNoObservable` | `string` | — | Disponible | `verdict.cause_label` si el veredicto es no observable; sale en la leyenda |
| `desplazamientoEscena` | `"ninguno" \| "sin_corregir" \| "corregido"` | `"ninguno"` | Disponible | `avisoEscena(verdict.evidence.scene_shift)` de `escena.ts` (PR 49). `true` equivale a `"sin_corregir"` |
| `idioma` | `"es" \| "en"` | `"es"` | Disponible | Textos, leyenda y atribución |
| `pixelUrl` | `string` | — | Disponible | Ruta de la serie por píxel de la serie activa, con el host delante |
| `controlCapas` | `boolean` | `true` | Disponible | Selector de capa y opacidad dentro del mapa |
| `modo3d` | `boolean` | `false` | Disponible (T-ATL-09) | Globo de MapLibre, que pasa a plano desde el zoom 12. Queda en 2D, y lo dice, sin aceleración gráfica, si el globo falla o con el comparador activo |
| `control3d` | `boolean` | `true` | Disponible (T-ATL-10) | Botón 3D con `aria-pressed` bajo el zoom. `false` si Faro pone el suyo y cambia con `actualizar({ modo3d })` |
| `relieve` | `{ plantilla: string; exageracion?: number; atribucion: string }` | — | Llega con T-ATL-12 (necesita T-BAL-15) | Plantilla `terrainrgb` del DEM GLO-30 tal como la da la API, con el host delante. `exageracion` por omisión 1; si es otra, el factor se ve en pantalla (RF-INT-12). Solo se aplica en 3D. `atribucion` va al control de atribución |
| `huellas` | `Huellas` de `huellas.ts`: `{ type: "FeatureCollection"; features: SeriesFootprint[] }`, con el tipo del contrato de `catalog` | — | Disponible (T-ATL-13); también en `actualizar` | Una Feature por serie, la de `footprint` de `GET /api/catalog/aois/{aoi}/series` sin tocar; las `null` se dejan fuera. El mapa las pinta con su nombre corto (`T048A-F015`) y las lista con pista, sentido y marco para lectores de pantalla. Las que no se pueden dibujar se ignoran. Sin huellas, solo la caja de la zona, con un punto en su centro hasta el zoom 7 |
| `herramientaRectangulo` | `boolean` | `false` | Llega con T-ATL-14 | Herramienta para dibujar un rectángulo de búsqueda (vista Investigador, RF-INT-18) |

### Eventos

| Evento | Carga | Estado | Cuándo |
|---|---|---|---|
| `onLayerChanged` | `"state" \| "change_hh" \| "change_hv"` | Disponible | La persona cambia de capa con el selector del mapa |
| `onModo3dChanged` | `boolean` | Disponible (T-ATL-10) | La persona pulsa el botón 3D del mapa. No salta con `actualizar({ modo3d })` |
| `onBboxDrawn` | `[oeste, sur, este, norte]` en WGS84 con 5 decimales | Llega con T-ATL-14 | Al terminar de dibujar el rectángulo. Si cruza el antimeridiano, oeste > este, igual que `aoi` |

### Decisiones

- **El mapa abre en 2D por omisión.** Así lo que ya monta Faro no cambia (RF-INT-19). Cada vista decide pasando `modo3d`; 08-interfaz pide que la vista pública abra en globo, y eso lo hace Faro en su vista (T-FAR-18), no el mapa.
- **Comparador en 3D: fuerza 2D mientras está activo y lo dice** (RF-INT-20, T-ATL-10). Es la opción más simple que no mezcla geometrías. Copiar al mapa óptico la proyección y el relieve queda para cuando haya relieve (T-ATL-12).
- **Huellas y relieve se pasan tal como los da la API.** Faro solo pone el host del gateway delante de la plantilla de relieve, igual que hace hoy con `layers` (`absoluteTileUrl`); las huellas van sin tocar.
- **Caja de cada tesela óptica.** Desde el PR 88 de Balanza, `OpticalTileOut` traerá `bbox`. Para usarla como `bounds` de cada fuente en el comparador, `VistaOptica` (`src/types/map.ts`, de Faro) necesita un campo opcional `tileBboxes?: Bbox[]`, en el mismo orden que `tiles`. Lo propongo a Faro; sin él, el comparador sigue acotado a la caja de la zona (T-ATL-08).

## Leyenda de estados

| Código | Estado | Representación |
|---|---|---|
| 0 | Sin cambio | Transparente |
| 1 | Cambio probable | Color de acento opaco |
| 10-15 | No observable | Gris con trama diagonal y etiqueta de causa |

## Pruebas

- Prueba visual de la leyenda y de la trama de lo no observable.
- Prueba de que `onPointSelected` redondea a 5 decimales.

## Riesgos

- Las teselas de 10 m a zoom bajo pueden verse vacías. Se limita el zoom y se explica.
- Límites de zoom (T-ATL-08, 2026-11-14): el mapa llega como mucho al zoom 16, dos niveles sobre el dato, donde un píxel de 10 m ocupa unos 5 px de pantalla. Las fuentes de radar y ópticas piden teselas hasta el zoom 14 (unos 8,5 m por píxel a 27° de latitud) y MapLibre las amplía por encima, porque más teselas no traerían más detalle. La trama de lo no observable no se amplía: se dibuja por píxel de tesela y saldría más gruesa. Todas las fuentes de datos llevan `bounds` con la caja de la zona, salvo si cruza el antimeridiano.
