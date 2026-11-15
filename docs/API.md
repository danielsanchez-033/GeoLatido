# API

Todo pasa por el gateway en `http://localhost:8080`. Contratos OpenAPI en `contracts/`.

| Prefijo | Servicio | Contrato |
|---|---|---|
| `/api/catalog/` | catalog | `contracts/catalog.openapi.json` |
| `/api/verdicts/` | verdicts | `contracts/verdicts.openapi.json` |
| `/api/auth/` | auth | `contracts/auth.openapi.json` |
| `/api/research/` | research (nuevo, 2026-11-15) | `contracts/research.openapi.json` |
| `/api/online/` | online (nuevo, 2026-11-15) | `GET /zones`, `POST /zones {name, bbox}` (202), `GET /zones/{id}` (al terminar, con `summary`: por par, fechas, días, estado y fracción de cambio sacados del manifiesto con la regla de verdicts, `calibrated: false`), `POST /zones/{id}/cancel`, `GET /limits`, `GET /health` |

## Investigación (`/api/research/`)

GET y POST; cuerpo de 16 KB como máximo; sin cuenta. Los pasos largos responden 202 y siguen en segundo plano.

| Método y ruta | Qué hace |
|---|---|
| `GET /places?q=` | Nomenclátor curado y, si está activo, Nominatim |
| `GET /sources` | Fuentes de acontecimientos y capas: activas o a la espera de credencial |
| `GET /profiles` | Perfiles: minería, inundación, laderas, glaciares |
| `GET /products` | Registro de colecciones con sensor, banda, nivel y polarizaciones |
| `POST /research/parse` | Interpreta una pregunta sin guardar nada |
| `POST /research` | Crea una investigación (`question`, `areas[]`, `period`, `phenomena`, `products`, `profile`, `run`) |
| `GET /research` | Últimas investigaciones |
| `GET /research/{id}` | Documento completo |
| `GET /research/{id}/status` | Estado del trabajo y pasos hechos |
| `POST /research/{id}/discover-data` | Paso 1: catálogo CMR |
| `POST /research/{id}/analyze` | Paso 2: cambio, series, acontecimientos, InSAR, susceptibilidad, comparación |
| `POST /research/{id}/generate-story` | Paso 3: historia |
| `POST /research/{id}/run` | Los tres pasos |
| `POST /research/{id}/cancel` | Cancela entre pasos o entre áreas |
| `GET /research/{id}/acquisitions?product=&area=` | Adquisiciones normalizadas y compatibilidad |
| `GET /research/{id}/timeline` | Series temporales con su análisis |
| `GET /research/{id}/anomalies` | Hallazgos |
| `GET /research/{id}/events` | Acontecimientos y correlaciones |
| `GET /research/{id}/risk` | Inventario de susceptibilidad |
| `GET /research/{id}/insar` | Evaluación InSAR |
| `GET /research/{id}/comparison` | Comparación entre áreas |
| `GET /stories?research_id=` | Historias |
| `GET /stories/{id}` | Historia con capítulos y evidencia |
| `GET /stories/{id}/evidence` | Evidencia y trazabilidad |
| `GET /stories/{id}/export?format=md\|json` | Informe reproducible |

Errores: 422 si la pregunta no nombra un lugar conocido y no hay áreas, si una caja está mal formada o si el periodo
está al revés o en el futuro; 404 si no existe; 409 si se pide una sección cuyo paso aún no se ejecutó; 405 en el
gateway con otro método.

```bash
curl -X POST localhost:8080/api/research/research -H 'Content-Type: application/json' \
  -d '{"areas":[{"id":"parral"},{"id":"helheim"}],"period":{"start":"2026-06-01","end":"2026-10-31"},"phenomena":["flood"],"run":true}'
curl localhost:8080/api/research/research/R-xxxx/status
curl -OJ "localhost:8080/api/research/stories/S-xxxx/export?format=md"
```

Regenerar el contrato: `cd services/research && python -m research.export_openapi ../../contracts/research.openapi.json`.
