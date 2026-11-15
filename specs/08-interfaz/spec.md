# Interfaz por perfiles y mapa en 3D: especificación

- **Responsables:** @danielsanchez-033 (sistema de diseño, vistas por perfil, inicio de sesión y búsqueda) y @Fransomware (globo 3D, relieve y herramientas del mapa)
- **Aportan:** @TakoKami-dev (relieve como artefacto), @KinzzoCS (huella de cada serie) y @lospapulindos2-netizen (gateway para el relieve)
- **Estado:** aprobada el 2026-11-14 por las cinco personas (PR 66)
- **Depende de:** `specs/06-acceso` y `specs/07-busqueda`

## Misión

Una interfaz de primer nivel que cualquiera entiende a la primera (80/20: el 80 % del valor con el 20 % de la interfaz) y que crece, sin cambiar de aplicación, hasta la potencia que necesita un investigador. El mapa abre en un globo 3D y puede pasar a 2D.

## Vista y perfil: dos cosas distintas

- La **vista** decide cuánto se enseña: `Público`, `Estudiante` o `Investigador`. Es solo presentación, porque todos los datos de la API pública ya son visibles para cualquiera.
- El **perfil** (`specs/06-acceso`) decide qué rutas de la API puede usar: búsqueda, exportación y cuotas.
- **Desde el 2026-11-14, la vista sale del perfil de la sesión** y no hay selector: sin sesión es `Público`; con sesión, la del perfil declarado (`student` o `researcher`). Decisión del usuario tras ver el diseño en blanco y negro: la cabecera solo lleva el idioma y el icono de la cuenta. Sustituye a la vista elegible por cualquiera.
- Lo que no cambia: la tarjeta del veredicto (estado, los tres textos, el distintivo de datos sintéticos y el recibo con los gránulos) es idéntica en las tres vistas, y el JSON de cada veredicto sigue siendo público en la API. La sesión solo añade explicaciones y herramientas (constitución X: los perfiles cambian la profundidad, nunca la verdad).
- **Desde el 2026-11-14 (rediseño de vidrio, RF-INT-23), la interfaz es solo oscura** y no hay botón de tema. Sustituye al tema del sistema con botón luna o sol. Decisión del usuario sobre el diseño de referencia de vidrio esmerilado.

## Qué ve cada vista

Las tres vistas muestran siempre, juntos, el estado, "qué detectamos", "qué no prueba" y "qué falta", el distintivo de datos sintéticos y el recibo plegado (criterios ya aprobados de Faro). Lo que cambia es lo que se añade:

| | Público (80/20) | Estudiante | Investigador |
|---|---|---|---|
| Primera pantalla | La historia de Parral y una pregunta: "¿Qué pasó aquí?" | Igual, con un acceso a "Cómo funciona" | El panel de trabajo: mapa, selector de par y evidencia |
| Veredicto | Estado en una frase y los tres textos; recibo plegado | Lo anterior, con cada número de la evidencia explicado en una línea (qué es un dB, por qué HV, qué es el ruido) | Todos los números de `evidence` y `receipt` abiertos y en tabla, con unidades |
| Mapa | Globo que vuela a Parral, capa de estado y leyenda; sin selector de capas | Selector HH/HV con explicación y serie por píxel con anotaciones | Selector de capas, opacidad, comparador óptico, coordenadas, dibujar un rectángulo para buscar |
| Búsqueda | No aparece | Búsqueda básica con la explicación de cada filtro (requiere cuenta) | Búsqueda completa y exportación (requiere cuenta) |
| Lenguaje | Llano, sin siglas | Siglas explicadas en el primer uso | Términos técnicos con enlace al glosario |

## Historias de usuario

- Como persona del público, quiero entender en menos de un minuto qué pasó en Parral sin crear cuenta ni tocar un menú.
- Como estudiante, quiero tocar cualquier número y que se me explique qué significa y de dónde sale.
- Como investigadora, quiero ver toda la evidencia de un par a la vez, buscar y exportar sin salir de la aplicación.
- Como persona usuaria, quiero ver la Tierra en 3D, llegar a Parral y ver el relieve, y pasar a un mapa plano cuando quiera medir.
- Como persona que usa teclado o lector de pantalla, quiero que el 3D no me impida nada de lo que permite el 2D.

## Requisitos

### Experiencia (Faro)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-INT-01 | Sistema de diseño con variables (color, tipografía, espaciado, radios, elevación) en tema claro y oscuro; contraste AA comprobado en cada par de colores | P0 |
| RF-INT-02 | La vista sale del perfil de la sesión (`Público` sin sesión) y se anuncia junto al icono de la cuenta; sin selector de vista. Tema solo oscuro, sin botón (cambio del 2026-11-14, RF-INT-23) | P0 |
| RF-INT-03 | Vista Público 80/20: una pregunta, una respuesta y un mapa; ninguna sigla sin explicar; acciones avanzadas fuera de la primera pantalla | P0 |
| RF-INT-04 | Vista Estudiante: explicación de cada campo de la evidencia, con textos en `src/i18n/` que pasan la prueba de lenguaje | P1 |
| RF-INT-05 | Vista Investigador: panel denso con toda la evidencia, atajos de teclado documentados y enlace al JSON de cada veredicto | P1 |
| RF-INT-06 | Inicio de sesión y registro (correo, contraseña y perfil declarado), token en memoria, renovación silenciosa y cierre de sesión; la interfaz dice que el perfil es declarado | P1 |
| RF-INT-07 | Pantalla de búsqueda sobre `specs/07-busqueda`: filtros, resultados en tabla con `data_kind` por fila, exportación para `researcher` y, ante un 403, qué perfil hace falta | P1 |
| RF-INT-08 | Presupuesto de rendimiento: la primera respuesta legible en menos de 2,5 s en un móvil medio con 4G simulado; el mapa se carga de forma diferida | P1 |
| RF-INT-09 | Movimiento reducido: con `prefers-reduced-motion`, sin vuelos ni animaciones; mismo contenido | P0 |
| RF-INT-21 | Botones solo con icono de línea, con nombre accesible (`aria-label`) y descripción emergente (`title`); texto solo donde hace falta (idioma con su código, escenas de la historia, el ejemplo de la consulta de evento, cambiar entre entrar y crear cuenta) | P1 |
| RF-INT-22 | Esqueletos en las cargas (la forma de lo que llega, con un brillo que se detiene con movimiento reducido), con el aviso de carga para el lector de pantalla | P1 |

### Mapa (Atlas)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-INT-10 | Globo 3D con la proyección de globo de MapLibre a zoom bajo, que pasa a plano al acercarse; sin biblioteca nueva | P0 |
| RF-INT-11 | Botón 2D/3D con `aria-pressed`. 2D: plano, norte arriba, sin inclinación. 3D: globo, relieve e inclinación | P0 |
| RF-INT-12 | Relieve con el DEM Copernicus GLO-30 de la zona, servido por TiTiler como `terrainrgb`; exageración 1× por omisión y, si se cambia, el factor visible en pantalla | P1 |
| RF-INT-13 | Mientras haya inclinación o la proyección efectiva no sea Mercator (el globo a zoom bajo), la barra de escala se oculta y un aviso dice que las distancias varían con la perspectiva; al volver a 2D reaparece (RF-ATL-05) | P0 |
| RF-INT-14 | La selección de punto funciona igual en 3D: seleccionar el mismo lugar da las mismas coordenadas que en 2D, con 5 decimales | P0 |
| RF-INT-15 | Teclado en 3D: girar, inclinar y volver al norte con teclas documentadas en la leyenda | P1 |
| RF-INT-16 | Contexto en el globo: caja de la zona y huella de cada serie (pista y marco) con su nombre | P1 |
| RF-INT-17 | Si el navegador no admite el globo o WebGL falla, el mapa abre en 2D y lo dice | P0 |
| RF-INT-18 | Herramienta de rectángulo (vista Investigador) que emite `onBboxDrawn` en WGS84 con 5 decimales para la búsqueda | P1 |
| RF-INT-19 | La interfaz `crearMapa` sigue siendo compatible: las opciones nuevas (`modo3d`, `relieve`, `huellas`) son opcionales | P0 |
| RF-INT-20 | El comparador radar frente a óptico (RF-ATL-07) no mezcla geometrías: en 3D, copia al mapa óptico la proyección y el relieve además del centro, el zoom, la orientación y la inclinación, o fuerza 2D mientras está activo y lo dice | P0 |

### Rediseño de vidrio (Faro, con cambios en el mapa de Atlas; 2026-11-14)

Pedido por el usuario a partir de un diseño de referencia: el mapa ocupa toda la pantalla de fondo y la interfaz flota encima en paneles de vidrio esmerilado (glassmorfismo) que se recogen en su borde. Todo lo que hoy se muestra se conserva; solo cambia dónde y cómo. Sigue sin color: grises, blanco y transparencias.

| ID | Requisito | Prioridad |
|---|---|---|
| RF-INT-23 | Tema solo oscuro. Superficies de vidrio: fondo negro translúcido con `backdrop-filter: blur()` y borde claro fino; sin `backdrop-filter`, fondo casi opaco. El texto sobre vidrio cumple AA medido contra el fondo opaco equivalente. Los botones son píldoras translúcidas; el activo, más claro y con texto en negrita | P0 |
| RF-INT-24 | El mapa siempre de fondo, a pantalla completa y abierto en el globo 3D, con un fondo de espacio con estrellas alrededor del globo. Ningún panel lo sustituye | P0 |
| RF-INT-25 | Cuatro barras recogibles, cada una en su borde: superior (marca, buscador de ubicación, estado de la API, idioma y cuenta), izquierda (Filtros: la búsqueda de veredictos con la línea de tiempo, los resultados y el pie de licencia), derecha (pestañas) e inferior (herramientas del mapa). Recogida, cada barra deja solo una pestaña pequeña en su borde. Botón con `aria-expanded` y `aria-controls`; recogida, su contenido sale del orden de tabulación y del árbol de accesibilidad | P0 |
| RF-INT-26 | Al cargar en escritorio: mapa, Filtros y la barra derecha en Hallazgos, abiertos; barras superior e inferior recogidas. Por debajo de 40rem, todas recogidas y cada panel abierto ocupa el ancho de la pantalla | P0 |
| RF-INT-27 | Barra derecha de unos 25 % del ancho (entre 20 y 30 rem) con cuatro pestañas verticales pegadas al borde derecho y centradas en vertical: Hallazgos (la tarjeta del veredicto elegido, su evidencia y el JSON en Investigador), Historia de Parral, Consulta de eventos y Comunidad. Pulsar la pestaña activa con el panel abierto lo recoge | P0 |
| RF-INT-28 | Barra inferior: 3D y 2D (`aria-pressed`, usa `modo3d` de `crearMapa`), volver a encuadrar la zona, capas (radar de estado, cambio HH o HV, y opacidad; no aparece en vista Público) y pantalla completa | P1 |
| RF-INT-29 | Buscador de ubicación en la barra superior: se ve, pero está desactivado y dice «Próximamente», porque la API no tiene geocodificador. No busca ni inventa resultados | P2 |
| RF-INT-30 | Comunidad: al abrir una historia aparece un botón de reproducir. La reproducción recorre sus pares en orden de fechas, elige cada uno en el mapa y en Hallazgos (unos 4 s por par) y muestra una línea de tiempo de la historia con el par actual marcado, con pausa, anterior y siguiente. El borrador del intérprete y las historias publicadas siguen en Comunidad. Con movimiento reducido, sin transiciones; el avance automático sigue y se puede pausar | P1 |
| RF-INT-31 | Mapa base de imagen de satélite en grises: Sentinel-2 cloudless 2016 de EOX (CC BY 4.0), con su atribución y el año visibles: es una imagen de fondo de 2016, no de las fechas del veredicto. Las otras ediciones son CC BY-NC-SA y no se usan | P1 |
| RF-INT-32 | El distintivo de datos sintéticos queda siempre visible, fuera de las barras recogibles (constitución II.2) | P0 |

Cambios sobre lo anterior: el tema (RF-INT-02) y, para la vista Público, la primera pantalla (RF-INT-03) pasa a ser el mapa con Hallazgos; la historia de Parral queda a un clic en la pestaña Historia. La barra de paneles para móvil (Buscar, Ver y Guardar) se sustituye por las barras recogibles.

## Criterios de aceptación

- [ ] Rediseño de vidrio: el mapa se ve detrás de las cuatro barras; cada barra se recoge a su pestaña y se vuelve a abrir con teclado y ratón; al cargar en escritorio están abiertos Filtros y Hallazgos; axe sin errores con las barras abiertas y recogidas; sin desbordamiento horizontal a 375 px.
- [ ] Reproducir una historia de la comunidad pasa por todos sus pares en orden, el mapa y Hallazgos cambian con cada uno y la pausa los detiene.

- [ ] Una persona sin cuenta, en vista Público, llega a la respuesta de la tormenta del 1 de julio sin abrir ningún menú.
- [ ] En las tres vistas, el estado, los tres textos, el distintivo de datos sintéticos y el recibo están presentes (prueba de componentes con las tres vistas).
- [ ] Cambiar de vista no vuelve a pedir el veredicto ni cambia ningún dato mostrado: el estado, las cifras, `data_kind` y el recibo son idénticos en las tres vistas. Una vista puede pedir datos **adicionales** que solo ella enseña (la serie por píxel en Estudiante, el comparador óptico en Investigador).
- [ ] La auditoría automática de accesibilidad (axe) no da errores en las tres vistas, en claro y oscuro, en 2D y en 3D.
- [ ] Seleccionar el mismo lugar en 2D y en 3D devuelve las mismas coordenadas con 5 decimales. Se prueba con `project`/`unproject` de un lon/lat fijo, no con el mismo píxel de pantalla, que en el globo no es el mismo lugar.
- [ ] Con inclinación, o con el globo a zoom bajo, no hay barra de escala y sí el aviso de perspectiva.
- [ ] La atribución de OpenStreetMap, Copernicus DEM, Sentinel-2 y NISAR está visible en 2D y en 3D.
- [ ] La trama de lo no observable y el distintivo de datos sintéticos se ven en 2D y en 3D, y la trama sigue distinguiéndose de "sin cambio" con inclinación y relieve (constitución II.2 y IX.2).
- [ ] Con el comparador activo en 3D, el radar y el óptico casan bajo el deslizador: los dos mapas tienen la misma proyección y el mismo relieve, o el mapa está en 2D y lo dice.
- [ ] Con `prefers-reduced-motion`, el globo no vuela: aparece ya centrado en Parral.
- [ ] Ningún texto nuevo pasa de la prueba de lenguaje de Balanza.

## Interfaces

- **Consume:** API de veredictos y de catálogo, `auth` (`specs/06-acceso`), búsqueda (`specs/07-busqueda`) y un COG de relieve de Eco en `artifacts`.
- **Produce:** la aplicación web y la interfaz `crearMapa` ampliada (`specs/04-atlas/plan.md`).

## Fuera de alcance

- Cambiar de biblioteca de mapas (CesiumJS u otras). El informe de investigación señala que los proyectos rivales visibles son globos 3D multirriesgo con datos de demostración: el 3D aquí es un medio para situarse, no el producto.
- Edificios en 3D o nubes de puntos.
- Relieve fuera de la zona: el resto del globo queda plano, y se dice en la leyenda.

## Preguntas abiertas

- ¿La demo del 15 de noviembre usa ya la vista 3D? Recomendación: solo si T-ATL-09 y T-ATL-10 están fusionadas y probadas con teclado antes de la demo.
- ¿Tipografía? Decisión de Faro; debe tener licencia OFL o compatible y servirse desde el propio frontend.
