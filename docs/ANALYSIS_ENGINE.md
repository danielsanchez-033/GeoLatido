# Motor de análisis

## Detección de cambios

Para cada área, `research` busca en `verdicts` las series cuya caja toca el área y toma los veredictos del periodo.
Comparaciones disponibles: pares consecutivos, ventana completa (primera contra última fecha) y, en la serie, cada
par consecutivo contra la mediana de todos (anomalías). La comparación entre dos polígonos se hace en `comparison`.

Un **hallazgo** (`DetectedAnomaly`) nace de un par `change_probable` o de una anomalía robusta en la serie. Guarda: id,
geometría (celdas de 1 km con cambio si el manifiesto las trae; si no, la caja de la serie), fechas, sensor, producto,
variables (HH, HV en dB), método, magnitud (fracción con cambio, cambio medio HH/HV), confianza, motivos de reserva,
hipótesis y límites del veredicto, gránulos y la ruta del veredicto en la API.

La **confianza** es descriptiva y nunca `high`: `low` si se cumple alguno de estos motivos, `medium` si ninguno.

- menos del 90 % de la zona observable;
- desplazamiento de toda la escena por encima del umbral;
- dispersión de la diferencia HH ≥ 1,2 dB;
- el par cruza un hueco de adquisición;
- alguna fecha con bandera de calidad;
- fracción a menos de un punto del umbral de decisión.

Humedad, vegetación, geometría y ruido no se separan con estos datos: se citan como hipótesis y límites.

## Series temporales (`temporal.py`)

| Pregunta | Método | Mínimo |
|---|---|---|
| ¿Tendencia? | Theil-Sen, por 30 días | 4 puntos |
| ¿Anomalías? | \|x − mediana\| / (1,4826·MAD) ≥ 3,5 | 5 puntos |
| ¿Cuándo empezó? ¿abrupto? | Una partición por mínima suma de cuadrados, tramos ≥ 3, \|Δmedia\| ≥ 2·MAD de residuos | 6 puntos |
| ¿Huecos? | Intervalo > 1,5 × mediana o cruce del hueco declarado por ASF | 2 puntos |
| ¿Estacional? ¿interanual? | No se calcula con menos de 2 años | — |

Un hueco se lista como falta de datos: nunca como estabilidad. Con los datos de 2026-11-15 (junio-octubre de 2026),
la estacionalidad sale siempre `insufficient_span`.

## Correlación con acontecimientos (`events.py`)

1. `temporal`: el acontecimiento cae dentro del par. `temporal_near`: a ±12 días de sus extremos.
2. `spatial`: además, la caja del acontecimiento toca la geometría de un hallazgo de ese par.
3. Asociación estadística: `not_computed`.
4. Causalidad: siempre `not_demonstrated`.

Para los acontecimientos del registro con `verdicts_event_type`, se pide además a `verdicts /events` si alguna pasada
de NISAR pudo verlo.

## Susceptibilidad (`assess.py`)

Inventario de factores por fenómeno (inundación, deslizamiento) con su fuente y estado (`found`, `missing`,
`not_in_artifacts`…). `score` es siempre `null`. Se definen susceptibilidad, amenaza, exposición, vulnerabilidad y
riesgo para que la interfaz no los confunda. No hay alertas.

## Comparación de lugares

Indicadores comunes: adquisiciones NISAR, revisita mediana, pares observados, pares con cambio, hallazgos y notas de
calidad. La magnitud física solo se compara entre áreas medidas con el mismo método y sensor.
