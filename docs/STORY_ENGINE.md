# Motor de historias

`services/research/src/research/story.py` convierte una investigación analizada en una historia con estas 17
secciones, en este orden: título, pregunta, contexto geográfico, importancia, periodo, fuentes, metodología, estado
inicial, transformaciones, acontecimientos, evolución temporal, hallazgos, interpretación, incertidumbre,
implicaciones, conclusiones y referencias.

## Reglas

- Cada afirmación es `{text, evidence[], kind}`; `kind` es `statement`, `caveat`, `hypothesis`, `decision`,
  `context` o `warning`.
- Cada evidencia es `{id, kind, label, …}` con `kind` en `product`, `acquisition`, `calculation`,
  `external_source` o `method`, y lleva los valores de los que sale la cifra (por ejemplo `changed_fraction` y la
  ruta del veredicto).
- `check_traceability` comprueba que toda afirmación con dígitos cite evidencia (salvo la pregunta y la importancia)
  y que toda evidencia citada exista. El resultado va en `story.traceability`; las pruebas exigen `ok: true`.
- Sin datos, la historia lo dice («no hay estado inicial medido», «la disponibilidad no es una medición»).
- Las hipótesis salen de `verdicts` y se rotulan como hipótesis; ninguna frase afirma causa.
- Si alguna serie es sintética, el título lo avisa y `data_kind` vale `synthetic`.

## Mapa

Cada capítulo lleva `map`: un par (`aoi`, `series`, `pair_id`) o una caja (`bbox`). La pestaña Investigar, al abrir un
capítulo, elige ese par en el mapa (tarjeta y capa) o vuela a la caja.

## Exportación

`GET /stories/{id}/export?format=md` (Markdown con los ids de evidencia entre corchetes y el registro de evidencia al
final) o `format=json` (historia más la investigación completa: plan, respuestas de proveedores y cálculos, para
reproducirla).

## Modelo de lenguaje

No hay ninguno en la pila. Si se añade, solo debería reescribir el estilo de `claims[].text` conservando los mismos
ids de evidencia y sin añadir cifras; `check_traceability` serviría como barrera. El texto generado está en español.
