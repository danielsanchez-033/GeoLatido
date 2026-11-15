# InSAR

**Estado (2026-11-15): no se procesa InSAR en esta plataforma y no se simula ningún desplazamiento.**

Los artefactos del proyecto son NISAR GCOV: potencia (covarianza) sin fase. `GET /api/research/research/{id}/insar`
devuelve, por área, qué productos con fase existen (comprobado en CMR) y qué haría falta:

| Camino | Producto | Qué aporta | Requisito |
|---|---|---|---|
| Desplazamiento ya calculado | OPERA DISP-S1 (Sentinel-1, C) | Serie LOS lista para leer | Cuenta de Earthdata; solo Norteamérica |
| Interferogramas NISAR | NISAR GUNW (L) | Fase desenvuelta y coherencia | Cuenta de Earthdata; MintPy para series |
| Procesado propio | Sentinel-1 SLC | Pares a medida | HyP3 (en la nube de ASF) o ISCE2/ISCE3 |

Herramientas evaluadas: HyP3 (pares Sentinel-1 bajo demanda), ISCE2/ISCE3 (procesadores de JPL; ISCE3 es el de NISAR,
pesado para una pila de 16 GB), MintPy (series temporales desde GUNW, HyP3 o ISCE), ESA SNAP (útil con Sentinel-1, no
contenedorizado aquí).

Límites que la API repite siempre:

- El desplazamiento interferométrico es en la **línea de vista (LOS)**; vertical y este-oeste exigen combinar órbitas.
- La decorrelación (vegetación, cambios, nieve) deja zonas sin medida.
- Layover y sombra impiden medir en laderas empinadas.
- La atmósfera puede imitar deformación.

Siguiente paso recomendado: leer OPERA DISP-S1 sobre Parral (762 productos) con un token de Earthdata y añadir sus
puntos como una serie más en `analysis.py`, con `variable: los_displacement_m`.
