# Balanza — interpretación y veracidad: especificación

- **Responsable:** @lospapulindos2-netizen
- **Estado:** aprobada para el hackathon

## Misión

Convertir mediciones en respuestas que una persona entienda **y pueda comprobar**. Balanza decide el veredicto, redacta los textos, contrasta con fuentes independientes y vigila que nada de lo que se muestra exceda lo que el dato sostiene. Además integra la pila: gateway, teselas y compose.

## Alcance

- `services/verdicts`, `gateway/`, `docker-compose.yml` y `scripts/`.
- Contrato `contracts/verdicts.openapi.json`, y la aprobación del manifiesto junto a Eco.

## Historias de usuario

- Como persona usuaria, quiero saber cuántos días separan las imágenes y qué edad tienen los datos.
- Como persona usuaria, quiero ver una imagen óptica de antes y de después para entender el cambio.
- Como periodista, quiero saber si un evento concreto pudo verse y por qué.
- Como jurado, quiero que ningún texto afirme más de lo que el dato prueba.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-BAL-01 | Veredicto en tres estados con recibo, evidencia y textos ES/EN | Hecho |
| RF-BAL-02 | Cada veredicto informa `interval_days` y la frescura del dato (edad y latencia), y los textos lo mencionan | Hecho |
| RF-BAL-03 | Prueba automática de lenguaje: ninguna plantilla afirma causas, daños ni confirmaciones | Hecho |
| RF-BAL-04 | Contraste óptico: escena Sentinel-2 anterior y posterior más cercana, con URL de tesela y licencia | Hecho |
| RF-BAL-05 | La prueba de humo cubre todas las rutas nuevas, incluidas las de Antena | Hecho |
| RF-BAL-06 | Eventos con las horas UTC de la línea de tiempo y persistencias por tipo de evento declaradas como supuestos | Hecho |
| RF-BAL-07 | Contraste con OPERA DSWx-S1: acuerdo o desacuerdo sobre agua, presentado como desacuerdo y no como error | Hecho (T-BAL-08); probado con radar real de T048 y T171 y token de Earthdata |
| RF-BAL-08 | Calibrar reglas con datos reales junto a Eco | Hecho (T-BAL-09): `MIN_CHANGED_FRACTION` del 5 %, fijado con el ruido de 16 pares reales corregidos por Eco (T-ECO-07); sin verdad de campo, así que `calibrated` sigue en false y los demás umbrales quedan como supuestos declarados |
| RF-BAL-09 | Las fechas con bandera de calidad de Eco se reflejan en el texto y en el recibo | Hecho (T-BAL-07), con aviso de desplazamiento de la escena |

## Criterios de aceptación

- [x] Un par que cruza el hueco de agosto dice "24 días" y lo explica.
- [x] La prueba de lenguaje falla si una plantilla contiene "confirmado", "causado por" o "daño".
- [x] El gateway solo deja pasar a TiTiler artefactos propios y el host público de COG de Sentinel-2.
- [x] Ningún veredicto se emite sin `data_kind`: es obligatorio en `Receipt`, sin valor por defecto, y FastAPI valida cada respuesta con su `response_model`.
- [x] Cada tesela de `evidence.optical.*.scene.tiles` trae `bbox` [oeste, sur, este, norte] en WGS84, la caja de los datos de la escena que da catalog (T-ANT-19), o `null` si catalog no la da o no es válida (T-BAL-19).
- [x] Cada veredicto trae `evidence.water` con el producto DSWx-S1 más cercano a cada fecha, o por qué no lo hay.
- [x] Con radar sintético el producto se lista y nunca se compara.
- [x] Una fecha con `radiometric_outlier` aparece en `summary.missing` y en `receipt.quality`.
- [x] Si toda la escena cambia de nivel más de 1,5 dB entre las dos fechas, `summary.does_not_prove` avisa de que el porcentaje puede reflejar ese desplazamiento y no un cambio local, sin cambiar el estado.
- [x] Una pasada que catalog excluye (`excluded[]`) aparece en `receipt.excluded_passes` y en `summary.missing` del par que la abarca, y no cuenta como pasada para un evento.
- [x] Un desacuerdo con DSWx-S1 se redacta como desacuerdo entre dos métodos; la prueba de lenguaje falla si un texto de agua habla de error o fallo.
- [x] Los textos de `/events` (`summary`, `cause_label` y `assumption.text`) no nombran parámetros de la API: dicen qué dato hay que indicar, no cómo se llama en la consulta.
- [x] Los textos de `/events` hablan de la «duración supuesta» del evento y nunca la dan por hecha («mientras duraba»), porque la duración es un supuesto sin calibrar.

## Interfaces

- **Consume:** manifiesto de Eco, API de catálogo de Antena (línea de tiempo y referencias) y, con token de Earthdata, la capa B01_WTR de OPERA DSWx-S1 en PO.DAAC.
- **Produce:** API de veredictos, teselas y entrada única en el puerto 8080.

## Fuera de alcance

- Diseño visual, que es trabajo de Atlas y Faro.
- Calcular el cambio, que es trabajo de Eco.

## Preguntas abiertas

- ~~¿Qué persistencia suponemos para una tormenta urbana frente a una crecida de río?~~ Resuelta en T-BAL-06: tormenta urbana 6 h, crecida de río 72 h e incendio 240 h, valores iniciales sin calibrar; cada respuesta de eventos los declara en `assumption` y en `summary.does_not_prove`.
- ~~¿Qué hacemos si el óptico más cercano está a más de 10 días o muy nublado?~~ Resuelta en T-BAL-04: a más de 10 días no se muestra y se dice (`none_in_window`); muy nublado se muestra la menos nublada con su nubosidad (`cloudy`).
