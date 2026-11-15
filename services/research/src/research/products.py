"""Registro de productos científicos que el motor sabe descubrir.

Cada `short_name` se comprobó en CMR el 2026-11-15 (`/search/collections.json?short_name=...` devuelve una
colección). Las polarizaciones son las que el producto puede traer; las de cada adquisición se leen de su nombre
cuando el nombre las declara, y si no, quedan como `declared` (del producto) y no como leídas.

`phase: True` solo en productos con fase interferométrica (GUNW) o desplazamiento ya derivado (DISP-S1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["sar", "insar", "water", "disturbance", "optical", "vegetation", "precipitation", "dem", "altimetry", "gravity"]


@dataclass(frozen=True)
class Product:
    id: str
    short_name: str
    provider: str
    sensor: str
    band: str | None
    level: str
    kind: Kind
    resolution_m: float | None
    polarizations: tuple[str, ...] = ()
    phase: bool = False
    static: bool = False
    access: Literal["public", "earthdata_login", "eodms_login"] = "earthdata_login"
    analyzed_here: bool = False
    phenomena: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    # Catálogo donde se busca: CMR de NASA o el STAC público de EODMS (Recursos Naturales de Canadá).
    catalog: Literal["cmr", "eodms"] = "cmr"


PRODUCTS: tuple[Product, ...] = (
    Product(
        "nisar_gcov", "NISAR_L2_GCOV_PROVISIONAL_V1", "ASF", "NISAR L-SAR", "L", "L2 GCOV (RTC, geocodificado)", "sar", 10,
        ("HH", "HV", "VV", "VH"), analyzed_here=True,
        phenomena=("surface_change", "mining", "flood", "landslide", "glacier"),
        notes="Covarianza geocodificada con corrección radiométrica de relieve. Sin fase: no sirve para InSAR. "
        "Los artefactos de este proyecto usan HH y HV del modo DHDH.",
    ),
    Product(
        "nisar_gunw", "NISAR_L2_GUNW_PROVISIONAL_V1", "ASF", "NISAR L-SAR", "L", "L2 GUNW (interferograma desenvuelto)", "insar", 80,
        ("HH", "VV"), phase=True, phenomena=("deformation", "landslide", "mining", "glacier"),
        notes="Fase desenvuelta y coherencia ya calculadas por JPL. Se descubre; este proyecto no la lee todavía.",
    ),
    Product(
        "opera_rtc_s1", "OPERA_L2_RTC-S1_V1", "ASF", "Sentinel-1 C-SAR", "C", "L2 RTC", "sar", 30, ("VV", "VH", "HH", "HV"),
        phenomena=("surface_change", "flood", "mining", "glacier"),
        notes="Retrodispersión gamma0 con corrección de relieve, por ráfaga. Banda C: no es comparable en valor con NISAR banda L.",
    ),
    Product(
        "opera_disp_s1", "OPERA_L3_DISP-S1_V1", "ASF", "Sentinel-1 C-SAR", "C", "L3 DISP (desplazamiento LOS)", "insar", 30,
        ("VV",), phase=True, phenomena=("deformation", "landslide", "mining"),
        notes="Desplazamiento en la línea de vista (LOS), no vertical. Cobertura limitada a Norteamérica.",
    ),
    Product(
        "opera_dswx_s1", "OPERA_L3_DSWX-S1_V1", "PO.DAAC", "Sentinel-1 C-SAR", "C", "L3 DSWx (agua superficial)", "water", 30,
        ("VV", "VH"), phenomena=("flood",),
        notes="Agua abierta de más de 3 ha. No ve calles inundadas.",
    ),
    Product(
        "opera_dswx_hls", "OPERA_L3_DSWX-HLS_V1", "PO.DAAC", "Landsat 8/9 + Sentinel-2", None, "L3 DSWx (agua superficial)", "water", 30,
        phenomena=("flood",), notes="Óptico: depende de las nubes.",
    ),
    Product(
        "opera_dist_s1", "OPERA_L3_DIST-ALERT-S1_V1", "ASF", "Sentinel-1 C-SAR", "C", "L3 DIST-ALERT (perturbación)", "disturbance", 30,
        ("VV", "VH"), phenomena=("surface_change", "mining", "landslide"),
    ),
    Product(
        "s1a_grd", "SENTINEL-1A_DP_GRD_HIGH", "ASF", "Sentinel-1A C-SAR", "C", "L1 GRD", "sar", 10, ("VV", "VH", "HH", "HV"),
        phenomena=("surface_change", "flood", "glacier"),
        notes="Sin corrección de relieve: hay que calibrar y corregir antes de comparar. Desde 2014.",
    ),
    Product(
        "s1c_grd", "SENTINEL-1C_DP_GRD_HIGH", "ASF", "Sentinel-1C C-SAR", "C", "L1 GRD", "sar", 10, ("VV", "VH", "HH", "HV"),
        phenomena=("surface_change", "flood", "glacier"),
    ),
    Product(
        "s1a_slc", "SENTINEL-1A_SLC", "ASF", "Sentinel-1A C-SAR", "C", "L1 SLC", "insar", 5, ("VV", "VH", "HH", "HV"), phase=True,
        phenomena=("deformation", "landslide", "mining", "glacier"),
        notes="Con fase: materia prima para InSAR (ISCE2/ISCE3, HyP3, MintPy). No se procesa en esta pila.",
    ),
    Product("hls_l30", "HLSL30", "LP DAAC", "Landsat 8/9 OLI", None, "L2 HLS", "optical", 30, phenomena=("surface_change", "mining", "glacier")),
    Product("hls_s30", "HLSS30", "LP DAAC", "Sentinel-2 MSI", None, "L2 HLS", "optical", 30, phenomena=("surface_change", "mining")),
    Product("modis_ndvi", "MOD13Q1", "LP DAAC", "Terra MODIS", None, "L3 NDVI 16 días", "vegetation", 250, phenomena=("landslide", "surface_change")),
    Product(
        "gpm_imerg_late", "GPM_3IMERGDL", "GES DISC", "GPM IMERG", None, "L3 precipitación diaria (Late)", "precipitation", 11000,
        phenomena=("flood", "landslide"),
        notes="Rejilla global de 0,1°. Los gránulos son globales: cubren cualquier zona.",
    ),
    Product(
        "nasadem", "NASADEM_HGT", "LP DAAC", "SRTM reprocesado", None, "DEM", "dem", 30, static=True,
        phenomena=("flood", "landslide", "mining"), notes="Elevación del año 2000.",
    ),
    Product(
        "icesat2_atl06", "ATL06", "NSIDC", "ICESat-2 ATLAS", None, "L3A altura de hielo", "altimetry", 40,
        phenomena=("glacier",), notes="Elevación de la superficie del hielo a lo largo de la traza; no es pérdida de masa.",
    ),
    Product(
        "gracefo_mascon", "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4", "PO.DAAC", "GRACE/GRACE-FO", None, "L3 mascons", "gravity", 300000,
        static=True, phenomena=("glacier",),
        notes="Masa equivalente de agua mensual a ~300 km: válida para Groenlandia entera, no para un glaciar.",
    ),
)

# Socios del reto (recursos oficiales de Space Apps): RADARSAT-1 y RCM de la Agencia Espacial Canadiense, buscados
# en el STAC público de EODMS (https://eodms-sgdot.nrcan-rncan.gc.ca/search), comprobado el 2026-11-15.
PRODUCTS = PRODUCTS + (
    Product(
        "radarsat1", "Radarsat-1-L1-COG", "CSA / NRCan (EODMS, AWS)", "RADARSAT-1 SAR", "C", "L1 SGF (COG calibrado)", "sar", 12.5,
        ("HH",), access="public", catalog="eodms", phenomena=("surface_change", "mining", "flood", "glacier"),
        notes="Archivo histórico de 1996 a 2013, licencia abierta de Canadá; COG públicos en AWS (radarsat-r1-l1-cog). "
        "Sirve de línea base antigua; banda C y otra geometría: no se compara en valor con NISAR.",
    ),
    Product(
        "rcm", "RCMImageProducts", "CSA (EODMS)", "RADARSAT Constellation Mission", "C", "L1 (SLC, GRD y otros)", "sar", 16,
        ("HH", "HV", "VV", "VH"), access="eodms_login", catalog="eodms", phenomena=("surface_change", "flood", "glacier"),
        notes="Desde 2019. La búsqueda es pública; descargar pide una cuenta de EODMS. El archivo abierto cubre sobre todo Canadá.",
    ),
)

BY_ID = {p.id: p for p in PRODUCTS}

# Productos que se piden por fenómeno (además de los de la zona procesada).
PHENOMENON_PRODUCTS: dict[str, tuple[str, ...]] = {
    "surface_change": ("nisar_gcov", "opera_rtc_s1", "opera_dist_s1", "s1a_grd", "hls_l30", "radarsat1", "rcm"),
    "mining": ("nisar_gcov", "nisar_gunw", "opera_disp_s1", "opera_dist_s1", "opera_rtc_s1", "s1a_slc", "hls_s30", "nasadem", "radarsat1"),
    "flood": ("nisar_gcov", "opera_dswx_s1", "opera_dswx_hls", "opera_rtc_s1", "gpm_imerg_late", "nasadem", "radarsat1"),
    "landslide": ("nisar_gcov", "nisar_gunw", "opera_disp_s1", "opera_dist_s1", "gpm_imerg_late", "modis_ndvi", "nasadem"),
    "deformation": ("nisar_gunw", "opera_disp_s1", "s1a_slc"),
    "glacier": ("nisar_gcov", "nisar_gunw", "opera_rtc_s1", "s1c_grd", "icesat2_atl06", "gracefo_mascon", "hls_l30", "radarsat1", "rcm"),
}


def products_for(phenomena: list[str]) -> list[Product]:
    ids: list[str] = []
    for ph in phenomena or ["surface_change"]:
        for pid in PHENOMENON_PRODUCTS.get(ph, PHENOMENON_PRODUCTS["surface_change"]):
            if pid not in ids:
                ids.append(pid)
    return [BY_ID[i] for i in ids]
