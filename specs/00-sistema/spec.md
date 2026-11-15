# Especificación del sistema

## Visión

Una persona sin formación en radar abre la aplicación, elige una zona y una fecha, y recibe una respuesta honesta: qué cambió, qué no se detectó y qué no se puede saber, con los datos exactos que lo respaldan.

## Personas usuarias

| Persona | Necesita | Ejemplo en Parral |
|---|---|---|
| Habitante o periodista local | Saber si un evento se ve desde el espacio | La tormenta del 1 de julio de 2026 |
| Gestor de agua o protección civil | Cambios en agua y suelo durante la temporada | Presa y campo durante el monzón |
| Jurado y comunidad científica | Comprobar de dónde sale cada afirmación | Recibo con gránulos, CRID y avisos |

Desde la ola 2 (`specs/06-acceso` y `specs/08-interfaz`), estas personas se agrupan en tres perfiles: **público general** (las dos primeras, sin cuenta), **estudiante** e **investigador** (la comunidad científica). El jurado usa la vista que quiera. Los perfiles cambian la profundidad, nunca la verdad (constitución X).

## Flujo de datos

```
NASA CMR ──────────────> Antena: catalog ──(series, pasadas, referencias)──┐
NASA (HTTPS, token) ───> Antena: ingest ──(recortes GCOV)──┐               │
Sentinel-2 / OPERA ────> Antena: catalog                   │               │
                                                           v               │
                                Eco: processor ──(COG + manifiesto)──┐     │
                                                                     v     v
                                          Balanza: verdicts + gateway + tiles
                                                           │
                                                         (API)
                                                           │
                                    ┌──────────────────────┴───────────────┐
                                    v                                      v
                              Atlas: mapa                         Faro: relato y UI
```

## Contratos

| Contrato | Produce | Consume | Archivo |
|---|---|---|---|
| API de catálogo | Antena | Antena (ingest), Balanza, Atlas | `contracts/catalog.openapi.json` |
| Recorte GCOV | Antena | Eco | `contracts/gcov-subset.md` |
| Manifiesto de artefactos | Eco | Balanza | `contracts/artifact-manifest.schema.json` |
| API de veredictos | Balanza | Atlas, Faro | `contracts/verdicts.openapi.json` |
| Interfaz del mapa | Atlas | Faro | `specs/04-atlas/plan.md` |
| API de acceso (ola 2) | Antena | Balanza (gateway), Faro | `contracts/auth.openapi.json` |

## Calendario

La fecha del evento sale de una fuente secundaria y falta confirmarla.

| Fecha | Hito |
|---|---|
| 10 nov | Especificaciones aprobadas. Cada rol arranca sus tareas `[P]` |
| 11 nov | P0 en curso. El frontend consume la API sintética |
| 12 nov | P0 terminados e integrados. Datos reales si ya hay cuenta de Earthdata |
| 13 nov | Calibración y ensayo completo de la demo |
| 14 nov | Evento. El sistema sigue creciendo: ola 2 aprobada (PR 66) y cualquier cambio, aunque sea radical, con el proceso de la constitución VI.2 |
| 15 nov | Evento: demo. Sin congelamiento de contratos: lo que está listo se fusiona |

## Demo mínima aceptable

1. La tormenta del 1 de julio aparece como `not_observable`, con la causa y las pasadas anterior y siguiente.
2. Un par del monzón muestra `change_probable` con hipótesis redactadas como tales.
3. Un punto del mapa muestra su serie temporal.
4. Cada pantalla deja claro si el dato es real o sintético y permite ver los gránulos usados.

## Riesgos

| Riesgo | Mitigación | Dueño |
|---|---|---|
| Sin cuenta de Earthdata antes del evento | La demo funciona con sintéticos marcados y `ingest` queda listo | Antena |
| Lectura remota lenta | Probar `--limit 2` lo antes posible y medir | Antena |
| RAM insuficiente con 10 fechas a 10 m | Procesar por pares | Eco |
| Umbrales sin calibrar | Declararlo en cada veredicto y calibrar con datos reales | Eco y Balanza |
| Cambios de contrato durante el evento | Sin congelamiento (decisión del 2026-11-14). Los cambios que rompen necesitan la aprobación de quien consume el contrato y se prueban con `scripts/smoke.sh` antes de fusionar | Todos |
