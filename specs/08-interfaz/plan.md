# Interfaz por perfiles y mapa en 3D: plan técnico

## Vistas (Faro)

- Un contexto de React `VistaContexto` con `vista: "public" | "student" | "researcher"` y `perfil` (de `auth`, o `public` sin cuenta). La vista inicial es el perfil; el selector la cambia y se guarda en `localStorage` dentro de un `try/catch`.
- Los componentes no se duplican por vista: cada uno recibe la vista y añade bloques (`<ExplicacionCampo>` en Estudiante, `<TablaEvidencia>` en Investigador). Lo obligatorio de las tres vistas vive fuera de esas ramas, así que no se puede ocultar por error.
- Sesión: el token de acceso en memoria (un módulo, no `localStorage`); `client.ts` añade `Authorization` si hay token y, ante 401, llama una vez a `/api/auth/refresh` y repite. Si vuelve a fallar, cierra la sesión y lo dice.
- Rutas de la aplicación: `/` (historia y respuesta), `/explorar` (mapa y veredicto), `/buscar` y `/cuenta`.

## Sistema de diseño (Faro)

- Variables CSS en `:root` y redefinidas para el tema oscuro, con una prueba que calcula el contraste de cada par texto-fondo declarado y falla por debajo de 4,5:1 (3:1 en texto grande e iconos).
- Colores de estado coordinados con la leyenda de Atlas: cambio probable en color sólido; no observable con trama y borde discontinuo; sin cambio, neutro. Nunca solo color (constitución IX.2).
- Tipografía y escala tipográfica fijas en pocas medidas; la decisión de fuente se anota en MEMORY con su licencia.

### Decisiones de T-FAR-12 (Faro, 2026-11-14)

- **Una sola fuente de verdad:** `frontend/src/tema/tokens.css`. Cada color se declara una vez con `light-dark(claro, oscuro)`, así que el tema oscuro no es una copia que se pueda desincronizar.
- **Qué tema se usa:** el del sistema (`prefers-color-scheme`), con `color-scheme: light dark` en `:root`. `<html data-tema="claro">` u `"oscuro"` lo fuerza; el botón para elegirlo llega con el selector de vista (T-FAR-13) y la auditoría axe en los dos temas con T-FAR-18.
- **Islas claras para el mapa:** el mapa y la línea de tiempo de Atlas (`src/mapa/`) tienen colores propios pensados para fondo claro. Hasta que Atlas los pase a variables, su contenedor fija `color-scheme: light` y fondo claro, para que en tema oscuro no quede texto oscuro sobre fondo oscuro. Faro no toca `src/mapa/`.
- **Colores de estado:** cambio probable `--color-cambio` (naranja quemado), sin cambio `--color-sin-cambio` (verde), no observable `--color-no-observable` (gris) con trama y borde discontinuo, observable (consulta de evento) `--color-acento`. El estado siempre lleva icono y texto.
- **Tipografía:** Atkinson Hyperlegible Next (Braille Institute, SIL OFL 1.1), diseñada para legibilidad con baja visión, servida desde el propio frontend con `@fontsource/atkinson-hyperlegible-next` (subconjunto latino, pesos 400 y 700). Código en la monoespaciada del sistema. Escala de cinco medidas: `--texto-s` 0,875 rem, `--texto-m` 1 rem, `--texto-l` 1,25 rem, `--texto-xl` 1,5 rem y `--texto-xxl` 1,75 rem.
- **Espaciado, radios y elevación:** escala de espaciado `--espacio-1` a `--espacio-6` (0,25 a 2,5 rem), radios `--radio-s` y `--radio-m`, y dos sombras `--elevacion-1` y `--elevacion-2`.
- **Prueba de contraste** (`src/tema/contraste.test.ts`): lee `tokens.css`, resuelve cada variable en claro y en oscuro y comprueba una lista declarada de pares: 4,5:1 en texto, 3:1 en bordes de control, foco e iconos (WCAG 1.4.3 y 1.4.11). Una variable nueva sin par declarado no falla, pero un par que usa una variable inexistente sí.

### Decisiones de T-FAR-13 (Faro, 2026-11-14)

- **Vista:** `frontend/src/vista/`: `VistaProvider` y `useVista()`. Sin sesión todavía (llega con T-FAR-16), la vista inicial es la guardada en `localStorage` (`vista`) o `public`. Leer y guardar van en `try/catch`: sin almacenamiento, la vista funciona igual y no se recuerda.
- **Selector:** grupo de botones con `aria-pressed` en la cabecera, junto al idioma (mismo patrón que `LanguageSwitch`), así que se usa con Tab y Enter o Espacio. Al lado, el tema: Sistema, Claro y Oscuro, que pone o quita `data-tema` en `<html>` y también se recuerda (`tema`).
- **Cambiar de vista no desmonta nada que pida datos.** Lo avanzado no se quita del DOM: va dentro de `<details>` que en Público empiezan cerrados y en Estudiante e Investigador abiertos. Así no se repite ninguna petición (prueba con `fetch` contado).
- **Público 80/20:** arriba, la pregunta "¿Qué pasó en Parral?" con una línea que explica qué es NISAR sin siglas; debajo, la historia (la escena 1 ya trae la respuesta de la tormenta, sin abrir menús); luego la tarjeta del par elegido y el mapa. Plegado: el cambio de serie o par ("Elegir otro par de fechas") y la consulta de evento ("Consultar otra fecha"). El botón "Ver este par en el mapa" de la escena 2 abre el pliegue antes de llevar el foco al selector.
- **Mapa en Público:** sin selector de capas ni opacidad (`controlCapas: false`) y sin comparador óptico, que queda para Investigador (tabla de la spec). Estudiante mantiene el selector de capas. Como `controlCapas` no está en `CambiosMapa`, el mapa se vuelve a crear solo al pasar de Público a otra vista o al revés; eso no pide veredictos a la API. Pedido a Atlas: aceptar `controlCapas` en `actualizar()`.
- **Movimiento reducido (RF-INT-09):** el mapa ya lo respeta (`sinAnimacion()` en `mapa.ts`). En la app, `@media (prefers-reduced-motion: reduce)` quita transiciones, animaciones y desplazamiento suave, y `scrollIntoView` no usa `smooth`. Mismo contenido con y sin movimiento.
- **Fuera de esta tarea:** lo que añaden Estudiante (T-FAR-14) e Investigador (T-FAR-15); por ahora las dos ven lo de hoy con todo desplegado, salvo el comparador, que solo está en Investigador. El globo y el vuelo a Parral (`modo3d`) se encienden cuando T-ATL-09 y T-ATL-10 estén probadas.

### Decisiones de T-FAR-21: rediseño de vidrio (Faro, 2026-11-14)

- **Armazón:** `App.tsx` pinta el mapa en una capa fija a pantalla completa (`.fondo-mapa`) y encima cuatro `BarraRecogible` (`components/Barra.tsx`): un `<section>` con su botón-pestaña (`aria-expanded`, `aria-controls`) y el contenido con `hidden` cuando está recogida, así que sale del orden de tabulación. Los componentes de contenido (Buscador, VerdictCard, Evidencia, Story, EventQuery, Interprete, Comunidad) no cambian; solo se mueven.
- **Vidrio:** variables nuevas en `tokens.css` (`--vidrio-fondo`, `--vidrio-borde`, `--vidrio-desenfoque`, `--vidrio-sombra`) y una clase `.vidrio`. `color-scheme: dark` fijo; sin `@supports (backdrop-filter)`, fondo casi opaco. El contraste se prueba contra el fondo opaco equivalente (peor caso: imagen clara debajo, compensado con la opacidad mínima del vidrio).
- **Mapa (cambio en `src/mapa/`, de Atlas; el PR pide la aprobación de @Fransomware):** mapa base Sentinel-2 cloudless 2016 de EOX (`s2cloudless_3857`, CC BY 4.0, comprobado en el `WMTSCapabilities.xml` de EOX el 2026-11-14; las ediciones de 2017 a 2025 salvo 2017 son CC BY-NC-SA) en grises, con la atribución en el control de MapLibre; controles del mapa con el mismo vidrio oscuro; el espacio alrededor del globo, transparente, para que se vea el fondo de estrellas de la app.
- **Barra inferior:** usa la interfaz pública de `crearMapa`: `control3d: false` y `actualizar({ modo3d })`, `encuadrar()`, `actualizar({ activeLayer })` y `fijarOpacidad()`. Con `controlCapas: false` siempre: el selector de capas pasa a la barra (oculto en Público).
- **Reproducción de historias:** estado en `App.tsx` (índice y en marcha o en pausa); un temporizador elige cada par con `setSeleccion` sin cambiar de pestaña. La línea de la historia (`components/Reproductor.tsx`) se dibuja sobre la barra inferior.

## Globo y relieve (Atlas)

- **Proyección.** MapLibre GL JS 6.16.0 admite la proyección de globo sin biblioteca nueva. Comprobado el 2026-11-14 en los tipos de `frontend/node_modules` (observación de Faro en el PR 66): `map.setProjection(projection: ProjectionSpecification)`, cuyo `type` acepta el texto `'globe'` (también `'mercator'` y `'vertical-perspective'`), un estado de transición o una expresión; la librería trae además `GlobeControl`. Se usa `map.setProjection({ type: "globe" })`: `globe` ya pasa a Mercator por dentro al acercarse, así que no hay que escribir la transición (`vertical-perspective` es el globo que no cambia). Corregido el 2026-11-14 por Atlas en el PR 66; los tipos lo dicen («globe projection to fall back to mercator projection in an animated way»). Visto en el navegador por Atlas el 2026-11-14: globo hasta el zoom 11, transición en 11,5 y Mercator desde 12 (detalle en MEMORY).
- **Relieve.** Eco publica un COG del DEM GLO-30 recortado a la zona en `artifacts/<aoi>/dem.tif` (EPSG:4326 o su CRS declarado). El mapa añade una fuente `raster-dem` con la plantilla `/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=file:///data/artifacts/<aoi>/dem.tif&algorithm=terrainrgb` y `encoding: "mapbox"`. El gateway ya deja pasar `file:///data/artifacts/`; Balanza solo comprueba que el parámetro `algorithm` llega a TiTiler. La ruta exacta de la plantilla la publica la API, no se construye en el frontend.
- **Modo 2D.** `setProjection` a Mercator, `setTerrain(null)`, `pitch` 0, `bearing` 0 y `maxPitch` 0, y se vuelven a desactivar girar e inclinar (`dragRotate`, `touchPitch` y el giro con teclado), como hoy, para que el norte quede arriba.
- **Modo 3D.** Se activan girar e inclinar al entrar y se desactivan al volver a 2D, después de poner la orientación a 0. Observación de Atlas en el PR 66.
- **Escala.** El control de escala se quita mientras haya inclinación (`pitch > 0`) o la proyección efectiva no sea Mercator (el globo a zoom bajo, donde la escala no vale en toda la vista), y vuelve cuando se cumplen las dos cosas. La proyección efectiva se lee del zoom o de `transitionState`, no del evento `projectiontransition`, que no avisa del paso a Mercator (prueba de Atlas, 2026-11-14). En 3D, el encuadre de Parral (zoom 9-10) queda en globo y sin escala. El aviso de perspectiva usa los textos de `textos.ts` en los dos idiomas.
- **Comparador en 3D.** Hoy `src/mapa/comparador.ts` copia al mapa óptico el centro, el zoom, la orientación y la inclinación, pero no la proyección ni el relieve: en 3D, el radar iría sobre un globo con relieve y el óptico sobre un plano, y el deslizador no casaría. En 3D, el comparador copia también la proyección y el relieve, o fuerza 2D mientras está activo y lo dice; Atlas elige en T-ATL-10 y lo anota en `specs/04-atlas/plan.md`.
- **Trama y distintivo en 3D.** La trama de lo no observable se dibuja en píxeles de tesela, así que con inclinación y relieve se deforma; se comprueba que sigue distinguiéndose de "sin cambio" y que el distintivo de datos sintéticos sigue visible.
- **Huellas.** Las huellas de las series vienen de catalog (`/aois/{id}/series`, campo nuevo y opcional `footprint` en GeoJSON, tarea de Antena). Si faltan, el globo muestra solo la caja de la zona.
- **Interfaz.** Opciones nuevas de `crearMapa`, todas opcionales: `modo3d: boolean`, `relieve?: { plantilla: string; exageracion?: number; atribucion: string }`, `huellas?: GeoJSON.FeatureCollection` y el evento `onBboxDrawn`. Se documentan en `specs/04-atlas/plan.md`.

## Pruebas

- Faro: pruebas de componentes con las tres vistas; prueba de contraste de variables; prueba de que cambiar de vista no llama a `fetch`; axe en las rutas principales.
- Atlas: pruebas de `estado` y `seleccion` también con `modo3d`, con `project`/`unproject` de un lon/lat fijo en 2D y en 3D; prueba de que con `pitch > 0` o con el globo a zoom bajo no hay control de escala; prueba de que el comparador en 3D tiene la misma proyección en los dos mapas o está en 2D; prueba de que, sin soporte de globo, `crearMapa` abre en 2D y emite el aviso.
- Manual: el recorrido de la demo con teclado en 2D y en 3D, anotado en el PR.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| El 3D añade peso y teselas y empeora móviles | Relieve solo en la zona, mapa diferido, presupuesto de RF-INT-08 medido en el PR |
| El 3D distrae del producto (veredictos honestos) | En vista Público el globo vuela a Parral y se queda en la respuesta; el 3D no tiene estados propios ni cifras |
| La inclinación hace engañosas las áreas | Sin escala con inclinación y aviso de perspectiva; el análisis se hace en 2D |
| Un rediseño grande rompe criterios ya aprobados de Faro | Las pruebas actuales de la tarjeta, la consulta de evento y la historia siguen en verde en cada PR |
