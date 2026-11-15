# Requisitos del reto NISAR: dónde se cumple cada uno

Revisado el 2026-11-15 contra la app de Docker (`http://localhost:3000`) y el código. «App» indica dónde verlo en la
interfaz.

## A. Obligatorios

| Id | Requisito | Estado | Dónde |
|---|---|---|---|
| R1 | Aplicación interactiva | Cumple | App web (React + MapLibre): mapa, filtros, pestañas, buscador, historias reproducibles |
| R2 | Seguir y visualizar cambios en el tiempo | Cumple | Veredicto por par de fechas, línea de tiempo de pasadas, gráfica de evolución (Filtros), capas de estado y de diferencia HH/HV |
| R3 | Al menos un tipo de cambio | Cumple | Humedad del suelo, agua e inundación (contraste con OPERA DSWx-S1), crecimiento y pérdida de vegetación y bosque (firmas de HV), suelo removido, y **hundimiento** con interferogramas NISAR GUNW (tarjeta «¿Se hunde el suelo?» y capa «Hundimiento») |
| R4 | Ubicaciones del mundo, una zona bien desarrollada | Cumple | Parral con 2 series y 18 fechas; cualquier ciudad buscada se procesa en línea (`services/online`, ~2,5 min por zona de 0,3°) |
| R5 | NISAR como fuente principal | Cumple | NISAR L2 GCOV (HH y HV) en todos los veredictos |
| R6 | Datos de recursos oficiales (ASF / Earthdata) | Cumple | CMR de NASA y gránulos de ASF DAAC con token de Earthdata; vistas previas de ASF Vertex |
| R7 | Varias fechas | Cumple | 10 fechas en T048, 8 en T171; 4 últimas en zonas en línea |
| R8 | Zona justificada | Cumple | App: Acerca de GeoLatido → Radar y ciencia → «Por qué Hidalgo del Parral»; [HALLAZGOS.md §1](HALLAZGOS.md#1-la-zona-y-por-qué) |
| R9 | Visualizaciones intuitivas | Cumple | Mapa de cambio con trama para lo no observable, globo 3D, comparador antes/después, gráfica de evolución, historia animada |
| R10 | Accesible a públicos amplios | Cumple | Español e inglés; WCAG 2 AA con axe-core; misma información con o sin cuenta; explicación del radar para público general |
| R11 | Qué cambió, cuánto, dónde y qué implica | Cumple | Tarjeta del veredicto (qué detectamos, qué no prueba, qué falta), fracción de cambio y dB, celdas de 1 km, bloque «Implicaciones» |
| R12 | Patrones en distintas escalas de tiempo | Cumple | Pares de 12 días, ventana completa de 4 meses, análisis temporal multianual en Investigar (Theil-Sen, anomalías) |
| R13 | Fácil de usar | Cumple con reserva | Buscador de lugares, procesado automático, ayudas en cada panel. **No se probó con usuarios reales** (T-FAR-20) |
| R14 | Open source con licencia y README | Parcial | Licencia Apache 2.0 (con `NOTICE` de créditos) y README con instrucciones. **El repositorio sigue privado**: hay que hacerlo público antes de entregar |
| R15 | Presentación interactiva de hallazgos | Cumple | Pestaña Historia (story map reproducible sobre el mapa) e informe [HALLAZGOS.md](HALLAZGOS.md). Falta el video o las diapositivas si el equipo los quiere |
| R16 | Hipótesis de lo que se ve y de lo que no | Cumple | Radar y ciencia → «Lo que se ve» y «Lo que no se ve»; hipótesis en cada veredicto |
| R17 | Por qué cambia la superficie: causas naturales y humanas | Cumple | Radar y ciencia → «Causas naturales» y «Causas humanas»; [HALLAZGOS.md §7](HALLAZGOS.md#7-por-qué-cambia-la-superficie) |
| R18 | Qué polarizaciones resaltan mejor los cambios | Cumple | Tabla HH/HV/VV/VH y lo medido en Parral (16 de 16 pares, 1,18 dB HH frente a 0,74 dB HV) |
| R19 | Aplicaciones futuras | Cumple | Radar y ciencia → «Aplicaciones futuras»; [HALLAZGOS.md §9](HALLAZGOS.md#9-aplicaciones-futuras-de-nisar) |
| R20 | Qué mide el SAR, en simple | Cumple | Radar y ciencia: día y noche, nubes, rugosidad, constante dieléctrica, InSAR centimétrico, pasada cada 12 días |

## B. Recomendados

| Id | Requisito | Estado | Dónde |
|---|---|---|---|
| O1 | Varias polarizaciones y otro sensor | Cumple | HH y HV en cada veredicto; banda C de Sentinel-1 vía OPERA DSWx-S1 (desacuerdo medido); RADARSAT-1 descubierto en Investigar |
| O2 | Serie de tiempo | Cumple | Línea de tiempo, gráfica de evolución y serie por píxel |
| O3 | Datos auxiliares | Cumple | Sentinel-2 (antes/después), DEM GLO-30, capas WMS de INEGI (uso de suelo, cuencas, localidades), acontecimientos de 7 fuentes |
| O4 | Impacto humano | Cumple | «Causas humanas» e «Implicaciones»: minería, agricultura, riego, urbanización |
| O5 | Storytelling | Cumple | Historia de la zona reproducible con acontecimientos citados; historias de la comunidad |
| O6 | Contexto local | Cumple | Zona del equipo; tormenta del 1 de julio verificada con Protección Civil y prensa local |
| O7 | Resumen interactivo | Cumple | Comparador antes/después, mapa web, filtros por periodo y órbita |
| O8 | Implicaciones para ecosistemas, agua, agricultura, infraestructura y comunidades | Cumple | Bloque «Implicaciones» y [HALLAZGOS.md §8](HALLAZGOS.md#8-implicaciones) |

## C. Entregables

| Entregable | Estado | Qué falta |
|---|---|---|
| App web desplegada y accesible por URL | **Falta** | Hoy corre en local con `docker compose up --build`. Hace falta un servidor (y el token de Earthdata en su `.env`) para publicarla |
| Repositorio público con licencia, README, fuentes y pasos | Parcial | Licencia Apache 2.0 desde el 2026-11-15 (aprobada en persona por el equipo), `NOTICE` con créditos, README, fuentes y pasos para reproducir. Falta hacer público el repositorio |
| Pieza de presentación | Cumple | Historia interactiva en la app y [HALLAZGOS.md](HALLAZGOS.md) (hallazgos, hipótesis, polarizaciones y aplicaciones futuras). Opcional: video o diapositivas |
| Créditos y atribución | Cumple | [NOTICE](../NOTICE), [README → Fuentes de datos y créditos](../README.md#fuentes-de-datos-y-créditos), ventana «Datos y créditos» (tabla de créditos y qué datos recabamos, enlazada desde el pie del panel de Filtros), atribución en el mapa y en el comparador, y [PRIVACIDAD.md](PRIVACIDAD.md) |
