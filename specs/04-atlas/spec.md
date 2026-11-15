# Atlas — mapa y representación web: especificación

- **Responsable:** @Fransomware
- **Estado:** aprobada para el hackathon

## Misión

Mostrar dónde ocurre cada cosa con precisión y sin engañar a la vista: capas radar, contexto óptico, estados no observables y georreferencia que se pueda comprobar.

## Alcance

- Módulo de mapa dentro de `frontend/`. Se propone `frontend/src/mapa/`, y la carpeta final se acuerda con Faro en T-ATL-01.
- La interfaz del mapa que consume Faro, documentada en `plan.md`.

## Historias de usuario

- Como persona usuaria, quiero ver sobre un mapa reconocible dónde hubo cambio y dónde no se pudo observar.
- Como persona usuaria, quiero comparar el radar con una imagen óptica deslizando entre ambas.
- Como persona usuaria, quiero tocar un punto y ver cómo evolucionó su señal.
- Como jurado, quiero ver las coordenadas y la extensión exactas de la zona.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-ATL-01 | Mapa base con licencia compatible con Apache-2.0 y atribución visible | Hecho (T-ATL-01 y 02, PR 32; atribución en el idioma de la interfaz, PR 70) |
| RF-ATL-02 | Capas `state`, `change_hh` y `change_hv` desde las plantillas de la API, con opacidad ajustable | Hecho (T-ATL-03, PR 32) |
| RF-ATL-03 | Leyenda fija de estados. Lo no observable se ve distinto de "sin cambio", con trama o gris, nunca transparente | Hecho (T-ATL-03, PR 32, 49 y 62) |
| RF-ATL-04 | Al seleccionar un punto: coordenadas con 5 decimales y llamada a la serie por píxel | Hecho (T-ATL-04, PR 32) |
| RF-ATL-05 | Extensión de la zona y escala visibles | Hecho (T-ATL-02, PR 32) |
| RF-ATL-06 | Línea de tiempo con pasadas, hueco de datos y eventos | Hecho (T-ATL-06, PR 72; Faro la monta en el PR 76) |
| RF-ATL-07 | Comparador deslizante radar frente a óptico Sentinel-2 | Hecho (T-ATL-07, PR 32 y 54; probado con la API real en el PR 77) |
| RF-ATL-08 | Límites de zoom acordes con la resolución del dato | P2 |

## Criterios de aceptación

- [x] El estado no observable se distingue sin depender del color: trama diagonal en todo el rango 10-63, en su propia capa y con opacidad mínima del 70 % (T-ATL-03).
- [x] La atribución de cada fuente está visible en el mapa: OpenStreetMap siempre, NASA/ISRO NISAR con datos reales y Copernicus Sentinel-2 en el comparador, en el idioma de la interfaz (PR 70).
- [x] Una capa radar y la óptica coinciden en el mapa, sin desplazamiento mayor de un píxel, sobre una zona de la app con artefactos de radar. Si no, se reporta a Eco. Comprobado por Antena el 2026-11-14 en Parral con la API real y la serie T048 (PR 77); T171 sin probar, y respecto a T048 está desplazada de 0,5 a 1,1 px en filas (T-ECO-06), así que su comparador podría descuadrarse de 5 a 11 m. La presa La Boquilla queda fuera de la zona de Parral y la app no tiene artefactos suyos: la coincidencia allí se comprobó con los datos en T-ECO-06 (2026-11-12).
- [x] El mapa funciona con teclado: desplazamiento, zoom y selección de punto (flechas, + y −, Enter y Escape), además del selector de capa, la opacidad y el deslizador del comparador (T-ATL-04 y 07).

## Interfaces

- **Consume:** API de veredictos (plantillas de tesela y serie por píxel) y API de catálogo (línea de tiempo y referencias ópticas).
- **Produce:** componente de mapa con la interfaz de `plan.md`.

## Fuera de alcance

- Textos de veredicto, tarjetas y navegación general, que son trabajo de Faro.

## Preguntas abiertas

- ¿Qué mapa base usamos? Ver las opciones y sus licencias en `plan.md`.
