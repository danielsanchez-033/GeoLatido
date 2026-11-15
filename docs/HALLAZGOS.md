# Hallazgos: Hidalgo del Parral con NISAR

Informe final del equipo para el reto NASA Space Apps 2026 sobre NISAR. Todas las cifras salen de los veredictos
reales que sirve la API (`/api/verdicts/aois/parral/...`), consultados el 2026-11-15. Las causas son **hipótesis**:
ninguna se comprobó en campo.

La versión interactiva de este informe está en la app: la pestaña **Historia** reproduce la historia de la zona
capítulo a capítulo sobre el mapa, y la ventana **Radar y ciencia** resume polarizaciones, hipótesis y aplicaciones.

## 1. La zona y por qué

Hidalgo del Parral, sur de Chihuahua (México). Ciudad minera desde el siglo XVII, semiárida, con lluvias de monzón de
julio a septiembre. Es la zona del equipo.

- Mezcla de causas de cambio: minería (jales y tajos), agricultura de temporal, crecimiento urbano y arroyos urbanos.
- Un evento verificado: tormenta del 1 de julio de 2026, 22,8 mm en una hora según la Coordinación Estatal de
  Protección Civil (boletín del 01/07/2026 en chihuahua.gob.mx).
- La app no se limita a Parral: busca cualquier ciudad del mundo y procesa en línea sus 4 últimas fechas de NISAR con
  HH y HV (unos 2,5 minutos por zona de 0,3°; Guadalajara, 148 s).

## 2. Datos

| Serie | Órbita | Fechas útiles | Periodo |
|---|---|---|---|
| T048A-F015 | Ascendente, 12:24 UTC | 10 | 2026-06-17 a 2026-10-15 |
| T171D-F075 | Descendente, 01:44 UTC | 8 (una excluida por defecto del producto) | 2026-06-26 a 2026-10-12 |

Producto NISAR L2 GCOV (retrodispersión geocodificada, malla de 10 m, HH y HV), colección provisional de ASF DAAC. Se
lee por HTTPS solo el recorte de la zona. Contexto: Copernicus Sentinel-2 (óptico), OPERA DSWx-S1 (agua de
Sentinel-1), Copernicus DEM GLO-30 (relieve) y acontecimientos de USGS, GDACS, Copernicus EMS, NASA EONET, NASA Global
Landslide Catalog y NOAA IBTrACS.

## 3. Método en una línea

Por cada par de fechas: diferencia de HH y HV en dB, suavizado 5 × 5, se resta el desplazamiento de toda la escena,
umbral por par (mínimo 3 dB), y se marca lo que el radar no puede ver (pocos looks, layover y sombra, fuera de escena).
El veredicto es `change_probable` si cambia al menos el 5 % de lo observado, `no_detectable_change` si no, y
`not_observable` con su causa si se ve menos de lo necesario.

## 4. Qué cambió, cuánto y dónde

16 pares consecutivos y 2 ventanas completas.

| Par (T048) | Estado | Cambio | Desplazamiento de escena HH / HV |
|---|---|---|---|
| 06-17 → 06-29 | Sin cambio detectable | 2,11 % | −0,86 / −0,42 dB |
| 06-29 → 07-11 | Sin cambio detectable | 4,18 % | −0,50 / −0,35 dB |
| 07-11 → 07-23 | Sin cambio detectable | 0,86 % | +0,96 / +0,69 dB |
| 07-23 → 08-16 | Sin cambio detectable | 1,48 % | +0,46 / +0,30 dB |
| **08-16 → 08-28** | **Cambio probable** | **5,18 %** | −1,03 / −0,59 dB |
| **08-28 → 09-09** | **Cambio probable** | **9,56 %** | +1,61 / +0,99 dB |
| 09-09 → 09-21 | Sin cambio detectable | 4,64 % | −1,49 / −1,04 dB |
| 09-21 → 10-03 | Sin cambio detectable | 1,08 % | +0,60 / +0,58 dB |
| 10-03 → 10-15 | Sin cambio detectable | 1,64 % | +1,44 / +1,24 dB |
| Ventana 06-17 → 10-15 | Sin cambio detectable | 2,71 % | +1,22 / +1,43 dB |

T171 (descendente): los 7 pares y la ventana completa salen `no_detectable_change` (de 0,58 % a 3,32 %).

**Dónde:** cada par trae celdas de 1 km con su propio estado (pestaña Hallazgos y capa del mapa). **Cuánto:** la
fracción de lo observado con cambio, el cambio medio en dB y la dispersión del par.

**Qué no se pudo ver:** la tormenta del 1 de julio cae entre la pasada del 29 de junio (12:24 UTC) y la del 8 de julio
(01:44 UTC), unas 148 h después del primer incidente: la consulta de evento responde `not_observable` con la causa
`no_acquisition_during_event`.

## 5. Polarizaciones

| Polarización | Qué resalta | Disponibilidad |
|---|---|---|
| HH | Suelo, humedad, agua abierta, inundación bajo árboles | NISAR L (usada) |
| HV | Vegetación y biomasa (dispersión de volumen) | NISAR L (usada) |
| VV | Rugosidad del agua, suelo desnudo, hielo marino | Sentinel-1 C; NISAR solo en modo QP |
| VH | Vegetación en banda C | Sentinel-1 C; NISAR solo en modo QP |

Lo que midieron HH y HV en Parral:

- En **16 de 16** pares, toda la escena se aclaró u oscureció en el mismo sentido en HH y en HV, y siempre más en HH:
  media de **1,18 dB en HH frente a 0,74 dB en HV**.
- La dispersión de la diferencia es mayor en HH (1,19 dB frente a 0,90 dB en el par 06-17 → 06-29; en HH va de 0,76 a
  1,59 dB según el par). En ese par, con 3 dB de umbral, la diferencia supera el umbral en cerca del 2 % de los píxeles
  en HH y en menos del 0,7 % en HV.
- Lectura: en una zona semiárida, **HH resalta mejor los cambios de humedad y superficie de toda la escena**, y **HV es
  más estable**, lo que ayuda a separar un cambio local. Por eso el veredicto usa las dos y resta el desplazamiento.
- Banda L frente a banda C: comparada con OPERA DSWx-S1 (Sentinel-1, VV y VH), NISAR vio más agua en T171 (0,38 a
  1,98 % de la zona frente a ~0,08 %; IoU 0,016 a 0,073). Es un desacuerdo entre métodos, no un error de uno de ellos:
  DSWx-S1 solo detecta masas de agua de más de 3 ha y los umbrales de agua del radar no están calibrados.

## 6. Hipótesis

Lo que se ve:

1. Los desplazamientos de toda la escena siguen a las lluvias del monzón: **humedad del suelo** (constante dieléctrica).
   Antes de corregirlos, el porcentaje de cambio seguía al desplazamiento con correlación 0,9.
2. Los dos pares con cambio probable (finales de agosto y principios de septiembre) caen en plena temporada de lluvias:
   **crecimiento de vegetación y cultivos de temporal**, o suelo removido. El par 08-28 → 09-09 sigue alto tras restar
   el desplazamiento: o hay cambio local, o el desplazamiento no es uniforme en la escena.
3. Junto a la Mina La Prieta, ningún cambio detectable en 9 pares: compatible con jales estables en el periodo.

Lo que no se ve:

1. La tormenta del 1 de julio: no hubo pasada durante el evento y el agua en las calles dura horas.
2. Calles inundadas y deslaves pequeños: por debajo del píxel de 10 m y del 5 % de la zona.
3. Laderas en layover o sombra (0,05 % de la zona) y la fecha 2026-08-13 de T171, excluida por un defecto del producto
   (visible en la vista previa pública de ASF).

## 7. Por qué cambia la superficie

- **Naturales:** monzón, sequía, crecimiento y secado de pastizal y matorral, erosión de laderas, crecidas de arroyos.
- **Humanas:** minería (jales, tajos, caminos), siembra y cosecha de temporal, riego desde presas como La Boquilla,
  expansión urbana y obras en arroyos.

## 8. Implicaciones

- **Agua:** la humedad y el agua superficial dicen cómo responde el suelo a la lluvia en una región con sequías.
- **Agricultura:** el ritmo de los cultivos de temporal se ve cada 12 días, también con nubes.
- **Infraestructura y comunidades:** arroyos urbanos, laderas y presas de jales son los lugares que conviene revisar
  tras una tormenta.
- **Ecosistemas:** el pastizal y el matorral cambian con el monzón; un cambio fuera de ese ritmo merece atención.

## 9. Aplicaciones futuras de NISAR

- Avisos de inundación de noche o con nubes, combinando NISAR con lluvia de GPM.
- Vigilancia de presas de jales y laderas con InSAR (producto GUNW): movimientos de centímetros.
- Calendario de cultivos y humedad del suelo para planear el riego.
- Subsidencia por extracción de agua subterránea en ciudades y valles agrícolas.
- Glaciares, hielo marino y biomasa forestal en todo el mundo con banda L y S.

## 10. Hundimiento (NISAR GUNW)

GCOV no tiene fase, así que el hundimiento se mide aparte con los interferogramas NISAR GUNW de la misma misión:
fase desenrollada menos la corrección ionosférica del producto, en la ventana de la zona, de 6 a 8 pares
consecutivos de 12 días sumados. El resultado es la velocidad con que cada punto se aleja del satélite **respecto al
resto de la zona**, en mm/año.

- **Signo comprobado** con un caso conocido (2026-11-15): en 7 de 8 interferogramas, Nezahualcóyotl (que se hunde)
  tuvo más fase que Ciudad Universitaria (estable): fase positiva = se aleja = hundimiento.
- **Ciudad de México (oriente)**, 84 días: el 24 % de la zona se hunde al menos 83 mm/año más que el resto, y lo
  más rápido llega a unos 186 mm/año, junto al aeropuerto y Nezahualcóyotl. Entre Nezahualcóyotl y Ciudad
  Universitaria hay unos 212 mm/año en la línea de vista (unos 28 cm/año en vertical), en el rango publicado para
  esa zona.
- **Parral**, 108 días: sin hundimiento por encima del ruido (54 mm/año de incertidumbre típica).
- Límites: es relativo a la zona, en la línea de vista (no separa hundir de moverse de lado), y la atmósfera puede
  sumar centímetros por par. Sin calibrar con GPS ni nivelación.

## 11. Límites

- Ningún umbral está calibrado con verdad de campo. `MIN_CHANGED_FRACTION` (5 %) se fijó con el ruido de 16 pares
  reales; los demás son supuestos declarados en cada respuesta (`calibrated: false`).
- GCOV no tiene fase: no medimos desplazamientos (InSAR).
- En zonas procesadas en línea no se marcan layover ni sombra (no se lee `radarGrid` ni DEM).
- La app no se ha probado con usuarios reales.

## Créditos

NISAR es una misión conjunta de NASA (JPL) e ISRO; los datos los distribuye ASF DAAC. Lista completa de fuentes y
licencias en el [README](../README.md#fuentes-de-datos-y-créditos) y en [DATA_SOURCES.md](DATA_SOURCES.md).
