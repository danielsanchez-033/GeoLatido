# Búsqueda para estudiantes e investigadores: especificación

- **Responsables:** @lospapulindos2-netizen (búsqueda de veredictos y exportación), @KinzzoCS (búsqueda de pasadas) y @TakoKami-dev (ruido por par en el manifiesto)
- **Consumen:** @danielsanchez-033 (pantalla de búsqueda) y @Fransomware (resultados sobre el mapa y búsqueda por área)
- **Estado:** aprobada el 2026-11-14 por las cinco personas (PR 66)
- **Depende de:** `specs/06-acceso` (perfiles `student` y `researcher`)

## Misión

Que una persona investigadora encuentre en segundos **todos** los veredictos y pasadas que cumplen una condición (estado, fechas, calidad, ruido, contraste con OPERA, texto) y se los lleve con su recibo, sin perder nunca la trazabilidad hasta los gránulos.

## Escala honesta

Hoy hay una zona, dos series y 18 veredictos reales. La búsqueda se diseña para varias zonas y cientos de pares, pero su valor hoy es **filtrar por evidencia** (ruido, desplazamiento de escena, acuerdo con OPERA), no el volumen. Ningún texto de la interfaz la presenta como un buscador de todo NISAR.

## Historias de usuario

- Como investigadora, quiero listar los pares `change_probable` cuyo ruido en HH sea menor de 1 dB, para separar cambio de ruido.
- Como investigador, quiero los pares donde el radar y OPERA DSWx-S1 no coinciden sobre agua, con el porcentaje comparado.
- Como investigadora, quiero exportar el resultado a CSV o GeoJSON con el `granule_id` de cada fecha, para citarlo en un artículo.
- Como estudiante, quiero buscar por fecha y estado y que la interfaz me explique cada filtro.
- Como investigador, quiero buscar pasadas por latencia de publicación, precisión de órbita o exclusión, para auditar el catálogo.
- Como investigadora, quiero dibujar un rectángulo en el mapa y ver qué series y pares lo cubren.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-BUS-01 | `GET /search/verdicts` en `verdicts` con filtros estructurados: zona, serie, dirección, rango de fechas, rango de `interval_days`, estado, causa de no observable, rango de fracción de cambio, desplazamiento de escena sobre el umbral, banderas de calidad, estado del contraste con OPERA, nubosidad del óptico y `data_kind` | P0 |
| RF-BUS-02 | Texto libre sobre los resúmenes ES/EN, hipótesis, causas y `granule_id`, con el idioma de `lang` | P1 |
| RF-BUS-03 | Orden por fecha, intervalo, fracción de cambio o ruido; paginación por cursor; total de resultados | P0 |
| RF-BUS-04 | Cada resultado trae `aoi`, `series_id`, `pair_id`, estado, fechas, `data_kind`, los números del filtro y el enlace al veredicto completo. Nunca un resultado sin `data_kind` | P0 |
| RF-BUS-05 | `student`: filtros de RF-BUS-01 salvo los de calidad y ruido, y 50 resultados por página. `researcher`: todo, hasta 500 por página | P0 |
| RF-BUS-06 | `GET /search/verdicts/export?format=csv\|geojson\|json` (`researcher`): mismas consultas, con recibo, gránulos, umbrales y la consulta usada en la cabecera o en `metadata` | P1 |
| RF-BUS-07 | `GET /search/passes` en `catalog`: zona, serie, rango de fechas, dirección, latencia, precisión de órbita (letra del nombre del gránulo), excluida o no, con plan de observación o no | P1 |
| RF-BUS-08 | **Dispersión de la diferencia** de cada par en el manifiesto, en HH y HV, como campos opcionales `stats.noise_hh_db` y `stats.noise_hv_db`: desviación robusta (1,4826 · MAD alrededor de la mediana) sobre los píxeles observables del par (sin `low_looks`, `terrain` ni `no_data`), después de suavizar 5 × 5 y **antes** del filtro de grupos. No depende de la corrección del desplazamiento de escena, porque restar una constante no cambia la MAD. No es ruido del instrumento: incluye también cambio real repartido (humedad, vegetación) y textura, y la descripción del campo lo dice | P1 |
| RF-BUS-09 | El veredicto expone esa dispersión en `evidence.noise` (campo nuevo y opcional, con la misma advertencia) y la búsqueda filtra y ordena por ella | P1 |
| RF-BUS-10 | Filtro espacial por `bbox` (WGS84): series cuya huella corta el rectángulo y, en P2, la fracción de cambio dentro de él calculada con las celdas de 1 km de Eco (T-ECO-12), ponderada por la fracción observable de cada celda. Si lo observable dentro del rectángulo no llega a `MIN_OBSERVED_FRACTION`, el resultado es `not_observable`, igual que un veredicto | P1 (huella), P2 (fracción) |
| RF-BUS-11 | Búsquedas guardadas por cuenta | P2 |

## Criterios de aceptación

- [ ] `state=change_probable` devuelve exactamente los pares cuyo veredicto en `/aois/{aoi}/series/{serie}/verdicts` tiene ese estado, comparados en la misma pila y con los mismos artefactos (prueba automática). No se compara con una lista fija: depende de los artefactos del momento, y T048 08-16→08-28 está solo 0,18 puntos sobre el umbral. Con los artefactos reales corregidos por T-ECO-07 (hay que reprocesar con `processor` si la copia local es anterior) hoy son T048 08-16→08-28 y 08-28→09-09.
- [ ] Un filtro sin resultados devuelve una lista vacía con el total 0 y la consulta interpretada, nunca un 404.
- [ ] Un resultado de datos sintéticos lleva `data_kind: synthetic` y la interfaz lo marca en la fila.
- [x] La exportación CSV incluye, por fila, `data_kind`, los dos `granule_id`, `interval_days`, `decision_rule` con el umbral y `calibrated`, y la lista de supuestos declarados del veredicto. Columnas `data_kind`, `granule_from`, `granule_to`, `interval_days`, `min_observed_fraction`, `min_changed_fraction`, `decision_calibrated` y `assumptions` (T-BAL-13, prueba de `verdicts`, 2026-11-14).
- [ ] Mientras el contraste con OPERA no está calculado, o si `verdicts` no tiene token, cada fila lleva `water: not_available`. Sin filtro `water`, la fila no desaparece del resultado; con un filtro `water` (por ejemplo, `water=disagree`), queda fuera porque no se puede evaluar, y `query` dice cuántas filas quedaron sin evaluar y por qué.
- [ ] `student` recibe 403 con `required_role: researcher` al pedir la exportación o un filtro de ruido; `public` recibe 403 en `/search/*`.
- [ ] Ningún resultado afirma más que el veredicto completo: los textos son los mismos campos de la API (prueba de lenguaje incluida).
- [x] Los manifiestos sin `stats.noise_*` siguen siendo válidos y el veredicto sale sin `evidence.noise`. Sale con `evidence.noise: null`, y en la búsqueda esas filas quedan fuera de un filtro de ruido y se cuentan en `query.not_evaluated` con `no_noise_stats` (T-BAL-14, prueba de `verdicts`, 2026-11-14).
- [ ] La prueba de humo cubre las rutas nuevas (lo exige ya T-BAL-05).

## Interfaces

- **Produce:** rutas nuevas en `contracts/verdicts.openapi.json` y `contracts/catalog.openapi.json`, y campos opcionales en `contracts/artifact-manifest.schema.json`. Todos son cambios **aditivos**.
- **Consume:** los veredictos que ya calcula `verdicts`, la línea de tiempo de `catalog` y el manifiesto de Eco.

## Fuera de alcance

- Buscar en todo CMR o en zonas que no estén en `config/aois`. Para eso existen Vertex y Earthdata Search.
- Procesar en el momento un par que no esté precalculado (decisión del 2026-11-09: la demo no procesa en vivo).
- Clasificar la causa de un cambio.

## Preguntas abiertas

- ¿El estudiante ve el filtro de ruido con una explicación en lugar de no verlo? Propuesta de Faro a decidir con Balanza; no cambia la matriz de acceso si solo se muestra deshabilitado con su explicación.
