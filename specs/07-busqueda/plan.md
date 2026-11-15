# Búsqueda: plan técnico

## Diseño

- **Índice derivado, nunca fuente de verdad.** Hoy `verdicts` **no** calcula los veredictos al arrancar: `VERDICTS_WARM_CACHE=1` solo calienta el contraste con OPERA, en un hilo aparte y solo si hay token (`main.py`, comprobado el 2026-11-14 tras la revisión de Balanza). T-BAL-11 añade ese paso: al arrancar, en segundo plano, calcula todos los veredictos de los manifiestos y vuelca una fila por veredicto e idioma en un SQLite en memoria con FTS5 para el texto. Si cambia un manifiesto, se reconstruye entero: con cientos de pares tarda menos de un segundo. Cada resultado se genera desde el veredicto calculado, así que no puede contradecirlo. Mientras el índice no esté listo, `/search/*` responde 503 con `Retry-After`, no una lista incompleta.
- **El contraste con OPERA puede llegar después.** Si una fila se indexa antes de que termine el contraste, o `verdicts` no tiene token, su campo `water` vale `not_available`. La fila no se quita: un filtro `water=disagree` la deja fuera, pero `query` cuenta cuántas filas quedaron sin poder evaluarse y por qué. Cuando el contraste termina, se reconstruye el índice.
- **Filtros como parámetros de consulta**, no un lenguaje propio: `state=change_probable&min_fraction=0.05&max_noise_hh_db=1.0&from=2026-07-01&to=2026-09-30&water=disagree`. Los parámetros repetidos se combinan con O dentro del mismo campo y con Y entre campos. La respuesta devuelve `query` con la interpretación.
- **Paginación por cursor** opaco (base64 del último orden y del `pair_id`), estable aunque cambie el índice entre páginas.
- **Exportación en streaming** (`StreamingResponse`) para no cargar todo en memoria. GeoJSON usa como geometría la caja de la zona en WGS84, con 5 decimales (constitución V.3).

## Forma de la respuesta

```json
{
  "query": {"state": ["change_probable"], "max_noise_hh_db": 1.0},
  "total": 2,
  "next_cursor": null,
  "results": [
    {
      "aoi": "parral", "series_id": "T048A-F015", "pair_id": "20260816_20260828",
      "from": "2026-08-16", "to": "2026-08-28", "interval_days": 12,
      "state": "change_probable", "changed_fraction": 0.0518,
      "noise_hh_db": 1.27, "scene_shift_exceeds": false, "water": "none_in_window",
      "data_kind": "real", "href": "/aois/parral/series/T048A-F015/verdicts/20260816_20260828"
    }
  ]
}
```

Los valores del ejemplo son ilustrativos de la forma; los reales salen de la API.

## Ruido por par (Eco)

`processor` ya calcula la diferencia de cada par. Se añade su dispersión robusta (1,4826 · MAD alrededor de la mediana), en HH y en HV, a `pairs[].stats` como `noise_hh_db` y `noise_hv_db`:

- Sobre los píxeles observables del par (sin `low_looks`, `terrain` ni `no_data`), después de suavizar 5 × 5 y antes del filtro de grupos. Así se midió la tabla por par del PR 39 (de 0,76 a 1,59 dB en HH), que hoy solo vive en esa descripción. El 1,27 dB del ejemplo es el valor real de T048 08-16→08-28.
- Vale lo mismo con `correct_scene_shift` activo o no: restar una constante no cambia la MAD.
- No es ruido puro del instrumento: incluye cambio real repartido y textura. La descripción del campo y la interfaz lo llaman "dispersión de la diferencia".
- `pairs[].stats` tiene `additionalProperties: false` en `contracts/artifact-manifest.schema.json`, así que el cambio de esquema de T-ECO-09 tiene que fusionarse antes que cualquier manifiesto con `noise_*`, o `verdicts` lo rechazará.

Campo opcional del manifiesto: cambio aditivo. Observaciones de Eco y Balanza en el PR 66.

## Fracción de cambio en un rectángulo (P2)

Con las celdas de 1 km de Eco (T-ECO-12), no leyendo el COG `state` en cada consulta. Cada celda trae `changed_fraction`, `observed_fraction` y `state`, y su polígono reproyectado a WGS84 (las celdas son cuadradas en UTM, no en grados). `verdicts` suma las celdas que corta el rectángulo, ponderadas por su superficie observable, y aplica `MIN_OBSERVED_FRACTION` como en un veredicto. Decidido en la revisión del PR 66 (Balanza y Eco).

## Búsqueda de pasadas (Antena)

`catalog` ya arma la línea de tiempo con `published_at`, `latency_hours`, `excluded[]` y `observation_plan`. `/search/passes` filtra esa misma lista; la precisión de órbita sale de la letra del nombre del gránulo (P, M, N o F según la guía de ASF) y se declara que `ORBIT_TYPE` de CMR no coincide (ver MEMORY, 2026-11-12).

## Permisos

Las rutas `/search/*` llaman a `requiere_perfil("student")`; la exportación, los filtros de calidad y ruido y `limit > 50` piden `researcher` (`specs/06-acceso`). Con `AUTH_ENABLED=0` todo `/search/*` responde 403 con el perfil necesario, y la interfaz lo explica.

## Pruebas

- Con artefactos sintéticos: cada filtro solo y combinado, orden, cursor y total.
- `state=change_probable` da los mismos pares que `/series/{serie}/verdicts` en la misma pila, sin lista fija.
- Contraste con OPERA sin token o sin terminar: las filas salen con `water: not_available` y `query` lo explica.
- Exportación: el CSV se vuelve a leer y cada fila tiene `data_kind` y gránulos.
- Permisos: 403 por perfil, como en la matriz.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Presentar 18 veredictos como "motor de búsqueda masivo" | La interfaz muestra el total real y la zona; la especificación lo prohíbe |
| El índice se desfasa del veredicto | Se reconstruye desde la caché de veredictos, nunca se edita a mano |
| Exportaciones grandes saturan `verdicts` | Streaming, solo `researcher` y cuota del gateway |
