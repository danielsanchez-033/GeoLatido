# Fuentes de datos

Todas las colecciones se comprobaron en CMR el 2026-11-15 (`/search/collections.json?short_name=…`). El motor solo lee
**metadatos** (públicos, sin cuenta); casi todos los archivos piden una cuenta de Earthdata.

| Id | Colección CMR | Proveedor | Sensor / banda | Nivel | Uso | Analizado aquí |
|---|---|---|---|---|---|---|
| `nisar_gcov` | NISAR_L2_GCOV_PROVISIONAL_V1 | ASF | NISAR, L | L2 GCOV (RTC) | Cambio de superficie | Sí, en zonas procesadas |
| `nisar_gunw` | NISAR_L2_GUNW_PROVISIONAL_V1 | ASF | NISAR, L | L2 interferograma | Deformación | No |
| `opera_rtc_s1` | OPERA_L2_RTC-S1_V1 | ASF | Sentinel-1, C | L2 RTC | Cambio, agua | No |
| `opera_disp_s1` | OPERA_L3_DISP-S1_V1 | ASF | Sentinel-1, C | L3 desplazamiento LOS | Deformación | No |
| `opera_dswx_s1` | OPERA_L3_DSWX-S1_V1 | PO.DAAC | Sentinel-1, C | L3 agua | Inundación | En `verdicts` con token |
| `opera_dswx_hls` | OPERA_L3_DSWX-HLS_V1 | PO.DAAC | HLS | L3 agua | Inundación | No |
| `opera_dist_s1` | OPERA_L3_DIST-ALERT-S1_V1 | ASF | Sentinel-1, C | L3 perturbación | Cambio | No |
| `s1a_grd`, `s1c_grd` | SENTINEL-1A/1C_DP_GRD_HIGH | ASF | Sentinel-1, C | L1 GRD | Cambio | No |
| `s1a_slc` | SENTINEL-1A_SLC | ASF | Sentinel-1A, C | L1 SLC | InSAR | No |
| `hls_l30`, `hls_s30` | HLSL30, HLSS30 | LP DAAC | Landsat / Sentinel-2 | L2 | Óptico | No |
| `modis_ndvi` | MOD13Q1 | LP DAAC | Terra MODIS | L3 NDVI | Vegetación | No |
| `gpm_imerg_late` | GPM_3IMERGDL | GES DISC | GPM IMERG | L3 diario | Precipitación | No |
| `nasadem` | NASADEM_HGT | LP DAAC | SRTM | DEM | Relieve | No (se usa GLO-30) |
| `icesat2_atl06` | ATL06 | NSIDC | ICESat-2 | L3A altura | Glaciares | No |
| `gracefo_mascon` | TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 | PO.DAAC | GRACE/GRACE-FO | L3 masa | Glaciares | No |

Socios del reto, en el STAC público de EODMS (`https://eodms-sgdot.nrcan-rncan.gc.ca/search`), comprobado el 2026-11-15:

| Id | Colección EODMS | Proveedor | Sensor / banda | Nivel | Acceso a los datos |
|---|---|---|---|---|---|
| `radarsat1` | Radarsat-1-L1-COG | CSA / NRCan | RADARSAT-1, C (HH) | L1 SGF/SCN COG | **Público**: COG en AWS (`radarsat-r1-l1-cog`), 1996-2013 |
| `rcm` | RCMImageProducts | CSA | RCM, C | L1 (SLC, GRD…) | Buscar es público; **descargar pide cuenta de EODMS**. Archivo abierto casi solo sobre Canadá (0 escenas en Parral y Helheim) |

RADARSAT-1 sobre Parral: 2 escenas (2002-01-05 y 2002-01-12, descendentes, W2); sobre Helheim, más de 100 de 1998 a
2008. Se descubren, no se analizan: son banda C con otra geometría y no se comparan en valor con NISAR.

SAOCOM (CONAE, banda L): sin registro solo se buscan productos y miniaturas; descargar pide registro en CONAE y, según su
página, un convenio y la licencia de uso. Sin API comprobada: no está conectado.

Notas comprobadas:

- `COP30` no está en CMR. Copernicus GLO-30 se lee de AWS en `processor fetch-dem`.
- `GPM_3IMERGDF` (final) no tenía gránulos del último año el 2026-11-15 por su latencia; se usa la versión Late.
  Sus gránulos son globales (caja −90…90, −180…180).
- `OPERA_L3_DISP-S1_V1` cubre Parral (762 productos 2016-2026 sobre La Prieta) y no Groenlandia (0).
- Productos estáticos (`nasadem`, `gracefo_mascon`) se consultan sin filtro de fechas.

## Acontecimientos

| Fuente | Acceso | Estado |
|---|---|---|
| `config/events/*.yaml` | Archivo del repositorio | Solo hechos leídos en su fuente, con URL y fecha de consulta |
| NASA EONET v3 | `https://eonet.gsfc.nasa.gov/api/v3/events`, público | Integrado (`RESEARCH_EONET=1`) |
| USGS ComCat | `earthquake.usgs.gov/fdsnws/event/1/query`, público | Integrado: sismos M ≥ 2,5 en la caja, hasta 500 por consulta |
| GDACS (CE y ONU) | `gdacs.org/gdacsapi/.../geteventlist/SEARCH`, público | Integrado: sismos, ciclones, inundaciones, volcanes, sequías e incendios. Filtra por país (Nominatim inverso, ~3 s); sin país, solo las 4 páginas más recientes y `truncated` |
| Copernicus EMS Rapid Mapping | `rapidmapping.emergency.copernicus.eu/backend/dashboard-api/`, público | Integrado: activaciones con la caja de sus zonas cartografiadas (268 el 2026-11-15) |
| NASA Global Landslide Catalog | CSV de `data.nasa.gov` (8,5 MB, caché de 30 días) | Integrado: 11 033 deslizamientos de 1988 a 2016; no se actualiza |
| NOAA IBTrACS v04r01 | CSV `last3years` (12 MB, caché diaria) | Integrado: ciclones cuya trayectoria pasa a menos de 2° del área |
| ReliefWeb (OCHA) | API v2, **pide un `appname` aprobado** (403 sin él) | Código listo; se activa con `RELIEFWEB_APPNAME`. Sin probar en vivo |
| NASA FIRMS | API de área, **pide `MAP_KEY` gratuita** | Código listo; se activa con `FIRMS_MAP_KEY`. Sin probar en vivo |
| SSN (UNAM), CENAPRED, SGM | Solo formularios o visores web; ningún servicio de datos comprobado | Pendiente |
| CONAGUA (Monitor de Sequía), EM-DAT | Descargas manuales / cuenta | Pendiente |

`GET /api/research/sources` dice qué fuentes están activas. Cada investigación guarda, por área, el estado de cada
fuente (`ok`, `error`, `needs_credentials`) y su número de acontecimientos.

## Capas de susceptibilidad (México)

WMS de INEGI `https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61`, público. Capas comprobadas el 2026-11-15 con
GetCapabilities y GetMap sobre Parral: `c402` cuencas, `c310` corrientes de agua, `c783` uso de suelo y vegetación
serie VII, `c416` suelos, `c407` humedad del suelo y `c102` localidades urbanas. El inventario de susceptibilidad
las cita con su URL de GetMap cuando el área está en México; no se calcula ningún índice con ellas.

## Lugares

Nomenclátor curado en `services/research/src/research/places.py` (cada caja con su procedencia; las delimitaciones
propias van marcadas como aproximadas) y, opcional, Nominatim de OpenStreetMap (`RESEARCH_GEOCODER=nominatim`), con
una petición por búsqueda explícita, caché y como mucho una por segundo, según su política de uso.
