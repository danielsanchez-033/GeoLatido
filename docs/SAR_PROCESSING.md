# Procesamiento SAR

## Lo que hace la cadena del proyecto (sin cambios el 2026-11-15)

| Paso | Dónde | Detalle |
|---|---|---|
| Lectura del recorte | `ingest` | HTTPS por bloques, solo la ventana de la zona, sin bajar el gránulo (~7 GB) |
| Calibración y geocodificación | NASA (GCOV) | GCOV ya es gamma0 geocodificado con corrección radiométrica de relieve (RTC); el proyecto no recalibra |
| Polarizaciones | `processor/gcov.py` | HH y HV del modo DHDH. Rechaza modo mixto y productos sin HH+HV. No inventa VV ni VH |
| Conversión a dB y suavizado | `processor/change.py` | 10·log10, ventana 5 × 5 en float32 |
| Co-registro | NASA | Las 18 fechas reales comparten malla (comprobado con h5py); entre órbitas, 0,5-1,1 px |
| Cambio por par | `processor/change.py` | Diferencia, desplazamiento de toda la escena restado, umbral por par (Otsu con mínimo 3 dB) |
| Layover y sombra | `processor/terrain.py` | Con `radarGrid` y GLO-30 |
| Ruido del par | `processor` | 1,4826 · MAD de la diferencia |
| Filtro multitemporal | `processor/multitemporal.py` | Quegan-Yu, opcional |
| Estadística por celdas | `processor/cells.py` | Celdas de 1 km por par |

## Tipos de producto (para no mezclarlos)

| Tipo | Contenido | ¿Se compara directamente? |
|---|---|---|
| SLC | Amplitud y fase, geometría de radar | Solo tras co-registro; base de InSAR |
| GRD | Amplitud multilook, sin corrección de relieve | No con RTC sin calibrar y corregir antes |
| RTC (OPERA RTC-S1, NISAR GCOV) | gamma0 con relieve corregido, geocodificado | Sí dentro del mismo sensor, banda y geometría |
| Derivados (DSWx, DIST, DISP) | Clases o desplazamientos | Según su especificación |

`research` avisa en cada investigación (`discovery[].compatibility`) cuando aparecen bandas distintas (L y C),
órbitas ascendente y descendente, varias pistas, o GRD junto a RTC.

## Ampliaciones no hechas

Procesar Sentinel-1 GRD (calibración, RTC con SNAP o HyP3) o series NISAR de otras zonas exige cuenta de Earthdata y
reutilizar `ingest`/`processor` con un `config/aois/<zona>.yaml` nuevo. No se ha hecho para ninguna zona fuera de Parral.
