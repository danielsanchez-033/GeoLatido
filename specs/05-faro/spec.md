# Faro — relato y experiencia: especificación

- **Responsable:** @danielsanchez-033
- **Estado:** aprobada para el hackathon

## Misión

Que cualquier persona entienda en menos de un minuto qué pasó, qué no sabemos y por qué confiar en la respuesta. Faro diseña la experiencia completa, la historia de Parral y la presentación ante el jurado.

## Alcance

- Toda la aplicación de `frontend/` salvo el módulo de mapa de Atlas: estructura, navegación, tarjetas, formularios, textos de interfaz, idiomas y accesibilidad.
- Guion y materiales de la demo.

## Historias de usuario

- Como persona sin formación técnica, quiero una respuesta en una frase y poder ampliar los detalles si los necesito.
- Como habitante de Parral, quiero preguntar por la tormenta del 1 de julio y entender por qué el satélite no la vio.
- Como jurado, quiero ver en tres pasos el valor del producto y abrir el recibo de cualquier afirmación.
- Como persona que usa lector de pantalla o teclado, quiero usar la aplicación completa.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-FAR-01 | Tarjeta de veredicto: estado, "qué detectamos", "qué no prueba", "qué falta", hipótesis y recibo desplegable | Hecho (T-FAR-02, PR 50) |
| RF-FAR-02 | Consulta de evento: fecha y tipo de evento, con la respuesta y sus supuestos | Hecho (T-FAR-03, PR 56) |
| RF-FAR-03 | Distintivo permanente cuando los datos son sintéticos | Hecho (T-FAR-04, PR 50) |
| RF-FAR-04 | Modo historia de Parral en tres escenas: tormenta no observable, cambio en el monzón y estabilidad de los jales | Hecho (T-FAR-06, PR 57) |
| RF-FAR-05 | Español e inglés en toda la interfaz | Hecho (T-FAR-07, PR 69) |
| RF-FAR-06 | WCAG 2.1 AA: contraste, teclado, foco visible y estados no solo por color | Hecho (T-FAR-07, PR 69) |
| RF-FAR-07 | Glosario y explicación breve de cómo ve el radar | Hecho (T-FAR-08) |
| RF-FAR-08 | Guion de demo de 3 minutos y material para el jurado ([demo.md](demo.md)) | Hecho (T-FAR-09, PR 78) |
| RF-FAR-09 | Prueba rápida con 3 a 5 personas y ajustes resultantes ([prueba.md](prueba.md)) | Fuera del hackathon: pasa a la ola 2 como T-FAR-20 (decisión de Faro, 2026-11-14) |

## Criterios de aceptación

- [x] La tarjeta muestra siempre los tres textos juntos, nunca solo "qué detectamos" (T-FAR-02).
- [x] `not_observable` tiene su propio estilo y texto, distinto de "sin cambio" (T-FAR-02).
- [x] Ningún texto de interfaz afirma más que la API: los textos del veredicto llegan tal cual y una prueba pasa la de lenguaje de Balanza por `src/i18n/` (T-FAR-02).
- [x] La demo completa funciona solo con teclado (T-FAR-07).

### Tarjeta de veredicto (T-FAR-02) y distintivo de datos sintéticos (T-FAR-04)

Consume `GET /aois/{aoi}/series` y `GET /aois/{aoi}/series/{series_id}/verdicts?lang=`. Los textos del veredicto se muestran tal como llegan de la API: Faro solo pone rótulos.

- [x] La persona elige la serie y el par de fechas con controles nativos (`select`) que tienen rótulo y se usan con teclado. Al abrir, se elige el primer par consecutivo de la primera serie.
- [x] El encabezado de la tarjeta dice el estado en una frase, con un icono distinto por estado y el texto escrito, nunca solo con color: "Cambio probable", "Sin cambio detectable" y "No observable".
- [x] `not_observable` tiene un estilo propio (borde discontinuo y trama), distinto de `no_detectable_change`, y muestra `cause_label` junto al estado como motivo de que no se pudiera medir ("Motivo de que no se pudiera medir: …"), nunca como causa de un cambio.
- [x] Bajo el estado se ven las fechas y `interval_days` ("del 2026-06-17 al 2026-06-29 · 12 días").
- [x] "Qué detectamos", "Qué no prueba" y "Qué falta" (`summary.detected`, `summary.does_not_prove` y `summary.missing`) salen siempre juntos y visibles, sin plegar.
- [x] Las hipótesis salen en una lista con el rótulo "Posibles explicaciones, sin comprobar" solo si `hypotheses` no está vacío.
- [x] El recibo va plegado en un `details` nativo y muestra: tipo de datos, madurez, serie (pista, dirección y marco), modo y polarización, CRID, gránulos, si cruza un hueco sin adquisiciones, avisos (`notices`), la frescura de cada pasada (antigüedad en días y latencia de publicación o su motivo) y los textos del contraste óptico (`evidence.optical.text`) y del contraste de agua con OPERA DSWx-S1 (`evidence.water.text`).
- [x] Al cambiar de idioma se vuelven a pedir los veredictos con el `lang` nuevo.
- [x] Si la API falla, se avisa con `role="alert"` sin mostrar un veredicto viejo como si fuera actual.
- [x] **Distintivo de datos sintéticos:** si la serie elegida o el recibo tiene `data_kind: synthetic`, se muestra en la cabecera de la página un aviso fijo, que no se puede cerrar, y otro dentro de la tarjeta. El texto dice que los datos son sintéticos y que no describen Parral. Con datos reales no aparece.
- [x] Ningún texto de interfaz en `src/i18n/` usa las palabras que prohíbe la prueba de lenguaje de Balanza (`services/verdicts/tests/test_language.py`): una prueba del frontend lo comprueba.

Fuera de esta entrega: el mapa (T-FAR-05), la consulta de evento (T-FAR-03), la serie por píxel, el comparador óptico (Atlas) y la auditoría WCAG completa (T-FAR-07). Se cuidan desde ya el teclado, el foco visible y los estados no solo por color.

### Integrar el mapa de Atlas (T-FAR-05)

Consume `crearMapa` de `frontend/src/mapa/` (interfaz en `specs/04-atlas/plan.md` y `src/mapa/tipos.ts`). Faro no toca esa carpeta.

- [x] El mapa va junto a la tarjeta del veredicto elegido, en un contenedor con altura explícita (60vh, mínimo 320 px) y un rótulo accesible.
- [x] Muestra las capas del veredicto (`verdict.layers` con el origen del gateway delante), y `dataKind` sale de `verdict.receipt.data_kind`.
- [x] Si el veredicto es `not_observable`, la leyenda recibe `cause_label`.
- [x] Si el veredicto trae `scene_shift`, solo se avisa de un cambio posiblemente no local cuando `exceeds_threshold` es verdadero y `corrected` no lo es. Si Eco ya descontó el desplazamiento, no se muestra ese aviso. Cuando entre el PR 49 se pasará `avisoEscena(scene_shift)`, que además añade la nota de "corregido".
- [x] Al seleccionar un punto, el mapa enseña su serie por píxel (`pixelUrl` de la serie activa).
- [x] Un botón con `aria-pressed` activa o quita el comparador radar/óptico. Solo aparece si `evidence.optical` trae escena en algún lado.
- [x] El mapa se crea una sola vez y se destruye al desmontar (`crearMapa` y `destruir` en el mismo efecto, para que StrictMode no deje dos mapas). Al cambiar de par, de serie o de idioma se usa `actualizar()`, sin recrearlo.
- [x] El idioma del mapa sigue al de la interfaz.
- [x] Mientras carga un veredicto nuevo, el mapa sigue montado, pero queda tapado con "Cargando…" y `aria-busy`, para que no se lean las capas anteriores como si fueran del par nuevo.

Fuera de esta entrega: un selector de capa propio de Faro (se usa el del mapa) y la escena de la historia (T-FAR-06).

### Consulta de evento (T-FAR-03)

Consume `GET /aois/{aoi}/events?date=&event_type=&time=&lang=`. Responde otra pregunta que la tarjeta: si el satélite pasó dentro de la duración supuesta del evento, no si algo cambió. La duración es un supuesto sin calibrar y la fecha y la hora se interpretan en UTC (`rules.event_status`).

- [x] Un formulario con rótulos visibles pide la fecha en UTC (obligatoria, con la ayuda de que a partir de las 18:00 en Parral en UTC ya es el día siguiente), el tipo de evento (sin especificar, tormenta urbana, crecida de río o incendio; "tormenta urbana" es el nombre que usa la API) y la hora de inicio en UTC (opcional, con la ayuda de que en Parral es UTC−6). Se envía con Enter o con el botón.
- [x] Un botón de ejemplo rellena la tormenta del 1 de julio de 2026 en Parral y hace la consulta.
- [x] La respuesta dice el estado con icono y texto: "Observable: hubo una pasada dentro de la duración supuesta del evento" o "No observable", nunca solo con color. Con `not_observable` muestra `cause_label` como motivo.
- [x] Siempre muestra juntos "Qué encontramos", "Qué no prueba" y "Qué falta" (`summary`) y la pasada anterior y la siguiente (o "ninguna" si no hay). El supuesto de duración no se repite aparte: la API ya lo incluye en `summary.does_not_prove` (T-BAL-06).
- [x] Si la respuesta es `observable`, se dice que eso no afirma ningún cambio y que hay que mirar el veredicto del par.
- [x] Si `data_kind` es `synthetic`, la respuesta lleva el aviso de datos sintéticos. Si hay `excluded_passes`, se listan con su motivo.
- [x] Al cambiar de idioma se repite la última consulta con el `lang` nuevo.
- [x] Mientras se consulta, la respuesta anterior no se muestra como actual. Si la API falla o rechaza la consulta, se avisa con `role="alert"`.
- [x] La respuesta recibe el foco, o un lector de pantalla la anuncia, al llegar.

Fuera de esta entrega: elegir la duración en horas a mano (`persistence_hours`); el tipo de evento ya fija una duración supuesta y declarada. Tampoco se enlaza la respuesta con el par de fechas del mapa.

### Modo historia de Parral (T-FAR-06)

Tres escenas al principio de la página, una visible cada vez. Cada escena trae su respuesta en vivo de la API: los textos de Faro presentan la escena, pero **no afirman el resultado**, porque los artefactos pueden reprocesarse.

| Escena | Datos | Qué presenta Faro |
|---|---|---|
| 1. La tormenta | `GET /aois/parral/events?date=2026-07-01&event_type=urban_storm&time=21:37` | La tormenta del 1 de julio, citada con el boletín de Protección Civil de Chihuahua (22,8 mm en una hora, enlace a la fuente), y la pregunta de si el satélite pudo verla |
| 2. Agosto | `GET /aois/parral/series/T048A-F015/verdicts/20260816_20260828` | Un par de fechas de agosto, sin desplazamiento de toda la escena. Qué dice el veredicto y qué no prueba. No menciona la lluvia: sería sugerir una causa que es solo hipótesis. Con la corrección de T-ECO-07 queda en 5,18 %, justo sobre el umbral del 5 %, así que su estado puede cambiar si se recalibra; la escena lo muestra en vivo |
| 3. La mina | `GET /aois/parral/series/T048A-F015/pixel?lon=-105.66631&lat=26.93807` | Un punto junto a la Mina La Prieta (según OpenStreetMap, consultado el 2026-11-13), con el recuento en vivo de pares sin cambio detectable |

- [x] Una navegación con los tres pasos (botones con `aria-current` en el paso activo) y botones "Anterior" y "Siguiente". Todo se usa con teclado.
- [x] Cada escena muestra su respuesta con los componentes de la app: la respuesta de la consulta de evento en la 1 y la tarjeta de veredicto en la 2. La 3 muestra el recuento de pares por estado y la lista por par.
- [x] La escena 2 tiene un botón "Ver este par en el mapa" que elige esa serie y ese par en el selector y lleva el foco allí.
- [x] La escena 1 enlaza la fuente de la tormenta. La 3 no llama "jales" al punto: OpenStreetMap solo marca la mina.
- [x] Con datos sintéticos, cada escena lo dice. Si una llamada falla, la escena lo avisa con `role="alert"`, y las demás siguen funcionando.
- [x] Al cambiar de idioma, cada escena vuelve a pedir sus textos.
- [x] Ningún texto de la historia afirma una causa ni un resultado que la API no dé (lo comprueba la prueba de lenguaje sobre `src/i18n/`), ni sugiere una causa por contexto (por ejemplo, la lluvia en la escena 2), ni presenta los datos como procesados en directo.

Fuera de esta entrega: animaciones, centrar el mapa en el punto de la escena 3 (el mapa de Atlas no ofrece seleccionar un punto desde fuera) y coordenadas verificadas de los jales.

### Español e inglés, y WCAG 2.1 AA (T-FAR-07)

Cierra RF-FAR-05 y RF-FAR-06 sobre lo que ya hay. Los textos del veredicto llegan de la API con `lang`; Faro se ocupa de los suyos.

- [x] Todos los textos de interfaz viven en `src/i18n/es.json` y `src/i18n/en.json`, con las mismas claves. Ningún componente de Faro escribe a mano un texto visible ni un atributo accesible (`aria-label`, `title`, `alt`).
- [x] El `lang` del documento y su título (`document.title`) siguen al idioma elegido.
- [x] Un enlace "Saltar al contenido principal" es lo primero que recibe el foco con el tabulador y lleva a `main`.
- [x] Una prueba automática pasa axe-core por la app en español y en inglés, con datos reales y sintéticos, y falla con cualquier infracción de WCAG 2.0/2.1 A o AA. jsdom no calcula colores, así que esa prueba no mide el contraste.
- [x] El contraste se mide con axe en el navegador sobre la pila, en las dos lenguas, sin infracciones de AA en la parte de Faro. Comprobado el 2026-11-14 con la pila local y el par y la consulta de ejemplo abiertos; dentro de las cajas con trama de "No observable", el peor contraste es 14,3:1. Los bordes de botones y campos pasan a `#6e7781` (4,3:1 sobre el gris de la historia, WCAG 1.4.11).
- [x] La demo completa (historia, selector de par, tarjeta, recibo, botones del mapa y consulta de evento) se recorre solo con teclado, con el foco siempre visible.

Fuera de esta entrega: el módulo de mapa (`src/mapa/`, de Atlas), que tiene sus propios textos ES/EN; lo que salga de la auditoría ahí se avisa a Atlas. Tampoco se prueba con un lector de pantalla real (NVDA o VoiceOver).

### Guion de demo y material para el jurado (T-FAR-09)

Cierra RF-FAR-08 en [demo.md](demo.md). El guion sigue la historia de Parral (T-FAR-06) y termina en el recibo, para que el jurado vea en tres pasos el valor del producto y pueda abrir la procedencia de cualquier afirmación.

- [x] Un guion hablado de 3 minutos como máximo, con lo que se dice y lo que se hace en pantalla en cada tramo, cronometrado al ensayarlo en la app. El equipo lo ensayó en persona el 2026-11-14 y cupo en los 3 minutos.
- [x] El guion no fija ninguna cifra ni ningún estado de un par: se leen en pantalla, porque los artefactos pueden reprocesarse (constitución II.6). Solo cita cifras externas con su fuente, como los 22,8 mm del boletín de Protección Civil.
- [x] Cada afirmación del guion y de la ficha sale de la API, de una especificación o de `MEMORY.md`. Nada presenta una hipótesis como causa ni lo sintético como real.
- [x] Los textos pasan la misma prueba de lenguaje que `src/i18n/` (palabras que prohíbe `services/verdicts/tests/test_language.py`).
- [x] Una ficha de una página para el jurado: qué hace, con qué datos, qué no hace, cómo comprobar una respuesta y fuentes.
- [x] Respuestas cortas a las preguntas probables del jurado, cada una con su fuente en el repositorio.
- [x] Una lista de comprobación antes de salir a escena y un plan por si algo falla.
- [x] El equipo revisa el guion antes de la demo (decisión del 2026-11-14 en `MEMORY.md`: T-FAR-09 se cierra con todo el equipo). Las cinco personas confirmaron a Faro el 2026-11-14 que lo leyeron y les parece bien.

Fuera de esta entrega: diapositivas, vídeo grabado y la versión en inglés del guion.

## Interfaces

- **Consume:** API de veredictos y la interfaz del mapa de Atlas.
- **Produce:** aplicación web y materiales de la demo.

## Fuera de alcance

- Renderizar capas o calcular coordenadas, que es trabajo de Atlas.
- Redactar los textos del veredicto, que vienen de la API (Balanza). Faro puede proponer cambios a Balanza.

## Preguntas abiertas

- ¿Qué framework usamos? Se decide con Atlas en T-FAR-01.
- ¿La demo se presenta en vivo o grabada?
