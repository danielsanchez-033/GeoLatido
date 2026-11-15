# Mapa (Atlas)

Módulo de mapa de Atlas. Especificación: [`specs/04-atlas`](../../../specs/04-atlas/spec.md).

## Uso

```ts
import { avisoEscena } from "./mapa/escena";
import { crearMapa } from "./mapa/mapa";

const GATEWAY = "http://localhost:8080";
const conHost = (l) => Object.fromEntries(Object.entries(l).map(([k, t]) => [k, GATEWAY + t]));

const mapa = crearMapa(document.getElementById("mapa")!, {
  aoi: serie.bbox,                      // [oeste, sur, este, norte] de GET /aois/{aoi}/series
  nombreZona: "Hidalgo del Parral",
  dataKind: veredicto.receipt.data_kind, // "synthetic" muestra el distintivo
  layers: conHost(veredicto.layers),     // plantillas de la API con el host delante
  causaNoObservable: veredicto.cause_label ?? undefined,
  // Cambio de nivel de toda la escena (PR 37 y 42), con avisoEscena de "./mapa/escena":
  // sin corregir, la leyenda avisa de que puede no ser local; corregido, anota que se descontó.
  desplazamientoEscena: avisoEscena(veredicto.evidence.scene_shift),
  idioma: "es",                         // o "en"
  // Serie por píxel de la serie activa: al seleccionar un punto, el mapa la pide y la enseña.
  pixelUrl: `${GATEWAY}/api/verdicts/aois/parral/series/${serie.id}/pixel`,
  onPointSelected: ({ lon, lat }) => {}, // ya redondeados a 5 decimales
  onLayerChanged: (capa) => {},
  onViewChanged: ({ bbox, zoom }) => {},
});

// Al elegir otro veredicto, sin recrear el mapa:
mapa.actualizar({ layers: conHost(otro.layers), dataKind: otro.receipt.data_kind });

mapa.destruir(); // al desmontar
```

El contenedor necesita una altura (mínimo 320 px). La interfaz completa está en [`tipos.ts`](tipos.ts); la de la ola 2, con lo que ya está y lo que llega con cada tarea (relieve, huellas y rectángulo), en [`specs/04-atlas/plan.md`](../../../specs/04-atlas/plan.md#interfaz-ampliada-ola-2-t-atl-11). Si Faro quiere su propio selector de capa, pasa `controlCapas: false` y cambia la capa con `actualizar({ activeLayer })`.

## Cómo se pinta cada capa

| Capa | Qué se ve |
|---|---|
| `state` | Cambio probable en naranja sólido. Sin cambio, transparente |
| `change_hh`, `change_hv` | Diferencia en dB con la paleta `rdbu` de la API. El rango de la leyenda sale del parámetro `rescale` de la plantilla |
| Trama (siempre encima) | Lo no observable (códigos 10-15) con rayas diagonales gris oscuro y gris claro. Opacidad mínima del 70 % |

Para la trama, el mapa sustituye el `colormap` de la plantilla `state` por uno que guarda el código en el canal rojo ([`estado.ts`](estado.ts)) y pinta cada tesela en el navegador ([`protocolo.ts`](protocolo.ts)).

## Selección de punto

- Clic sobre el mapa, o Enter con el mapa enfocado, que selecciona el punto bajo la cruz central. La cruz y la ayuda solo aparecen con foco de teclado.
- El mapa pone un marcador, anuncia las coordenadas a los lectores de pantalla y llama a `onPointSelected` con `{ lon, lat }` redondeados a 5 decimales.
- Con `pixelUrl`, abre una ventana con la historia del punto: gráfica de HH (línea continua) y HV (discontinua), el resultado de cada par consecutivo y la tabla de valores. Si la API responde 404, dice que el punto queda fuera de la zona con datos.
- Escape cierra la ventana y quita el marcador.

## Comparador óptico

Con `compare: "swipe"` y `optical` con al menos un lado (`VistaOptica`, ver [`src/types/map.ts`](../types/map.ts)), el mapa monta un deslizador: a la izquierda el radar y a la derecha la escena Sentinel-2.

- La escena se pinta en un segundo mapa MapLibre, sin interacción propia, que sigue la cámara del principal ([`comparador.ts`](comparador.ts)).
- Una capa por tesela MGRS. Fuera de su huella TiTiler responde 404, que se pinta como tesela vacía.
- Un panel elige antes o después y muestra la fecha UTC, los días respecto a la pasada de radar, la nubosidad (de la tesela, no de la zona) y la atribución. Con `cloudy`, `partial_coverage`, `none_in_window` o `catalog_unavailable` dice por qué ([`optico.ts`](optico.ts)).
- El deslizador se arrastra o se mueve con el teclado: flechas, Re Pág, Av Pág, Inicio y Fin.

```ts
mapa.actualizar({ optical: { before, after }, compare: "swipe" }); // "off" lo quita
```

## Línea de tiempo

Pasadas de radar, huecos sin adquisiciones, pasadas excluidas, próximas pasadas estimadas y el evento consultado, en un componente aparte del mapa ([`lineaTiempo.ts`](lineaTiempo.ts)). Faro hace las peticiones y le pasa las respuestas tal cual, como con el óptico:

```ts
import { crearLineaTiempo } from "./mapa/lineaTiempo";

const linea = crearLineaTiempo(document.getElementById("linea")!, {
  timeline,          // GET /api/catalog/aois/parral/timeline; null mientras carga
  evento,            // opcional: GET /api/verdicts/aois/parral/events?date=…
  serie: serie.id,   // opcional: solo esa fila
  idioma: "es",
  onPassSelected: ({ series, granule_id, acquired_at }) => {}, // opcional: cada pasada es un botón
});
linea.actualizar({ evento: otro, idioma: "en" });
linea.destruir();
```

- Cada marca tiene su forma: pasada (círculo lleno; hueco si la serie no cubre toda la zona), excluida (aspa), estimada (círculo discontinuo), hueco (trama) y evento (banda; borde discontinuo si no tiene hora).
- A la vista, no solo en el título emergente: el supuesto del evento (`assumption.text`), cada estimación con «no es un plan de observación» y la fecha de consulta del plan (`checked_at`), cada pasada excluida con su motivo y su evidencia, los huecos y que la publicación es la fecha de actualización de CMR.
- Debajo, la lista de todas las pasadas en texto. En pantallas estrechas la gráfica se desplaza en horizontal.
- Los tipos del catálogo están en [`catalogo.d.ts`](catalogo.d.ts), generados de `contracts/catalog.openapi.json`; [`catalogo.test.ts`](catalogo.test.ts) falla si el contrato cambia.

## Globo 3D

Con `modo3d: true` el mapa usa el globo de MapLibre 6.16.0 (`projection: globe`), que pasa a plano por dentro al acercarse: globo hasta el zoom 11 y Mercator desde el 12. Por omisión es `false` y el mapa queda en 2D, como hasta ahora ([`globo.ts`](globo.ts)).

```ts
mapa.actualizar({ modo3d: true }); // false vuelve al plano
```

Se queda en 2D, y lo dice en pantalla, si:

- el navegador no tiene aceleración gráfica (WebGL 2 por software);
- `setProjection` falla;
- el comparador óptico está activo, para que el radar y el óptico casen (RF-INT-20). Al quitarlo, vuelve el globo.

MapLibre 6 solo funciona con WebGL 2, así que sin él no hay mapa ni en 2D: `crearMapa` no rompe la página, muestra la extensión de la zona en texto, el distintivo de sintético y un aviso.

Controles en 3D (T-ATL-10):

- **Botón 3D** bajo el zoom, con `aria-pressed`. Cambia `modo3d` y llama a `onModo3dChanged(modo3d)`. Se quita con `control3d: false` si Faro pone el suyo.
- **Girar e inclinar solo con el globo:** arrastre con el botón derecho o Ctrl, gestos táctiles y teclado (Mayús + ← → gira, Mayús + ↑ ↓ inclina, N vuelve al norte). Aparece la brújula, que devuelve el norte. Al volver a 2D, norte arriba, sin inclinación y sin giro.
- **Escala:** se oculta con inclinación o mientras el globo no se ve plano (hasta el zoom 12, con la vista normal de Parral incluida) y la sustituye un aviso de que las distancias cambian con la perspectiva (RF-INT-13).
- **Ayuda:** las teclas de 3D salen en la leyenda y en la ayuda que aparece con el foco del teclado.
- **Selección de punto:** igual que en 2D, con 5 decimales. `unproject(project(lugar))` da el mismo lon/lat en globo y en plano (MEMORY, 2026-11-14).

Pendiente: el espacio alrededor del globo sale oscuro.

## Huellas de las series

`huellas` recibe una `FeatureCollection` con el `footprint` de cada serie de `GET /api/catalog/aois/{aoi}/series` (T-ANT-17), sin tocar; las series con `footprint: null` se dejan fuera ([`huellas.ts`](huellas.ts)).

```ts
const series = await (await fetch(`${gateway}/api/catalog/aois/parral/series`)).json();
const huellas = { type: "FeatureCollection", features: series.flatMap((s) => (s.footprint ? [s.footprint] : [])) };
mapa.actualizar({ huellas });
```

- **En el mapa:** contorno azul y relleno tenue bajo el radar, con el nombre corto (`T048A-F015`) en el vértice más al norte, hacia fuera de la huella, para que dos series cruzadas no se tapen. El nombre se oculta desde el zoom 9, donde la huella ya llena la pantalla.
- **Zona:** además de la caja, un punto en su centro hasta el zoom 7, porque en el globo la caja no se ve.
- **Lectores de pantalla:** las etiquetas del mapa no se leen; la caja de extensión lleva la lista con pista, sentido y marco en palabras. Sin WebGL 2, la lista se ve en texto.
- **Antimeridiano:** las longitudes se hacen seguidas, para no dar la vuelta al mundo.

## Límites de zoom

- El mapa llega como mucho al zoom 16 (`ZOOM_MAXIMO_MAPA`): un píxel de 10 m ocupa unos 5 px de pantalla, suficiente para elegir un punto sin aparentar más detalle.
- Las capas de radar y las ópticas piden teselas hasta el zoom 14 (`ZOOM_NATIVO_DATOS`); por encima, MapLibre amplía las que ya tiene. La trama no, porque se dibuja por píxel de tesela.
- Cada fuente de datos lleva `bounds` con la caja de la zona (`fuenteDatos` en [`mapaBase.ts`](mapaBase.ts)), así que no se piden teselas fuera de ella. Si la zona cruza el antimeridiano no se acota.

## Estado

| Parte | Tarea | Estado |
|---|---|---|
| Mapa base OSM con atribución, escala y contorno de la zona | T-ATL-02 | Hecho |
| Capas, opacidad, leyenda y trama de lo no observable | T-ATL-03 | Hecho; falta probarlo con teselas reales |
| Selección de punto y serie por píxel | T-ATL-04 | Hecho; falta probarlo con la API real |
| Distintivo de sintético y atribución de NISAR solo con datos reales | — | Hecho |
| Teclado: mapa (flechas, + y −, Enter, Escape), selector de capa y opacidad | — | Hecho |
| Línea de tiempo de pasadas, huecos y eventos | T-ATL-06 | Hecho; probado con la API real de Parral. Faro la monta bajo la consulta de evento (PR 76) |
| Globo 3D (`modo3d`) con caída a 2D y aviso | T-ATL-09 | Hecho; probado en el navegador con la API local |
| Botón 2D/3D, giro e inclinación, escala oculta y teclas en 3D | T-ATL-10 | Hecho; probado en el navegador con la API local |
| Comparador óptico (`optical` y `compare`) | T-ATL-07 | Hecho; probado con la API real y artefactos reales de T048 (PR 77) |
| Huellas de las series y punto de la zona en el globo (`huellas`) | T-ATL-13 | Hecho; probado en el navegador con el catálogo local (T048A y T171D de Parral) |
| Límites de zoom y fuentes acotadas a la zona | T-ATL-08 | Hecho; probado con la API real. Quedan 404 ópticos dentro de la zona hasta tener la caja de cada tesela |

## Desarrollo

Desde `frontend/`:

```bash
npm install
npm run dev:mapa   # banco de pruebas en /src/mapa/demo.html (?3d abre el globo; ?sin-comparador lo quita)
                   # y el de la línea de tiempo en /src/mapa/lineaTiempo.html?fecha=2026-07-01&tipo=urban_storm
npm test
npx tsc -b         # tipos, igual que npm run build
```

El banco de pruebas lee la serie y el primer veredicto de `http://localhost:8080` (`docker compose up --build`). Sin la pila levantada, usa la extensión de `config/aois/parral.yaml`, **teselas de prueba** con formas geométricas generadas en el navegador y una serie por píxel de prueba, y lo avisa en pantalla.
