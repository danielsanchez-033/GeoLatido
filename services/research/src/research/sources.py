"""Proveedores de acontecimientos con datos abiertos (2026-11-15).

Cada proveedor devuelve acontecimientos normalizados con el mismo esquema que `config/events` y NASA EONET:
`id, title, type, phenomena, date, end_date, bbox, geometry_precision, description, confidence, sources[], origin`.
Todos se comprobaron en vivo el 2026-11-15 antes de escribirse (ver docs/DATA_SOURCES.md). Un proveedor que falla no
tumba los demás: `gather` lo anota con su estado.

Sin cuenta: USGS, GDACS, Copernicus EMS Rapid Mapping, NASA Global Landslide Catalog e IBTrACS.
Con credencial (se activan con una variable de entorno; sin ella, el estado es `needs_credentials`):
ReliefWeb (`RELIEFWEB_APPNAME`, nombre de aplicación aprobado por OCHA) y NASA FIRMS (`FIRMS_MAP_KEY`).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
import re
import threading
import time
from pathlib import Path

import httpx

UA = {"User-Agent": "dancing-with-the-sar-research/0.1"}


def _intersects(a: list[float], b: list[float]) -> bool:
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def _grow(b: list[float], deg: float) -> list[float]:
    return [max(-180, b[0] - deg), max(-90, b[1] - deg), min(180, b[2] + deg), min(90, b[3] + deg)]


class Provider:
    id = "base"
    name = "base"
    url = ""
    credential_env: str | None = None
    coverage = "global"

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=45, headers=UA, follow_redirects=True)

    @property
    def enabled(self) -> bool:
        return not self.credential_env or bool(os.environ.get(self.credential_env))

    def events(self, bbox: list[float], start: str, end: str) -> list[dict]:  # pragma: no cover - interfaz
        raise NotImplementedError

    def describe(self) -> dict:
        return {"id": self.id, "name": self.name, "url": self.url, "coverage": self.coverage,
                "credential_env": self.credential_env, "enabled": self.enabled}


class DiskCache:
    """Descargas grandes (catálogos CSV) guardadas en disco con caducidad, y su versión ya leída en memoria."""

    def __init__(self, directory: Path | None = None):
        self.dir = directory or Path(os.environ.get("RESEARCH_DATA_DIR", "./data/research")) / "cache"
        self._mem: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def text(self, key: str, url: str, max_age_s: float, client: httpx.Client) -> str:
        path = self.dir / key
        with self._lock:
            if path.exists() and time.time() - path.stat().st_mtime < max_age_s:
                return path.read_text(encoding="utf-8")
            r = client.get(url, timeout=120)
            r.raise_for_status()
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            tmp.write_text(r.text, encoding="utf-8")
            tmp.replace(path)
            return r.text

    def parsed(self, key: str, max_age_s: float, build):
        hit = self._mem.get(key)
        if hit and time.time() - hit[0] < max_age_s:
            return hit[1]
        value = build()
        self._mem[key] = (time.time(), value)
        return value


# --- USGS ---------------------------------------------------------------------------------------------------------

class Usgs(Provider):
    id = "usgs"
    name = "USGS Earthquake Catalog (ComCat)"
    url = "https://earthquake.usgs.gov/fdsnws/event/1/"
    MIN_MAG = 2.5

    def events(self, bbox, start, end):
        w, s, e, n = bbox
        r = self.client.get(self.url + "query", params={
            "format": "geojson", "starttime": start, "endtime": end, "minlatitude": s, "maxlatitude": n,
            "minlongitude": w, "maxlongitude": e, "minmagnitude": self.MIN_MAG, "orderby": "time", "limit": 500})
        r.raise_for_status()
        out = []
        for f in r.json().get("features", []):
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"][:2]
            depth = f["geometry"]["coordinates"][2] if len(f["geometry"]["coordinates"]) > 2 else None
            when = dt.datetime.fromtimestamp(p["time"] / 1000, dt.timezone.utc)
            out.append({
                "id": f"usgs-{f['id']}",
                "title": p.get("title") or f"M {p.get('mag')} sismo",
                "type": "earthquake",
                "phenomena": ["deformation", "landslide"],
                "date": when.date().isoformat(),
                "time_utc": when.strftime("%H:%M"),
                "bbox": [lon, lat, lon, lat],
                "geometry_precision": "epicenter",
                "description": f"Magnitud {p.get('mag')} ({p.get('magType')}), profundidad {depth} km. {p.get('place') or ''}".strip(),
                "magnitude": p.get("mag"),
                "confidence": "official_catalog",
                "sources": [{"name": "USGS", "url": p.get("url")}],
                "origin": self.id,
            })
        return out


# --- GDACS --------------------------------------------------------------------------------------------------------

GDACS_TYPES = {"EQ": ("earthquake", ["deformation", "landslide"]), "TC": ("tropical_cyclone", ["flood", "landslide"]),
               "FL": ("flood", ["flood"]), "VO": ("volcano", ["deformation", "surface_change"]),
               "DR": ("drought", ["flood"]), "WF": ("wildfire", ["surface_change"])}


def country_of(bbox: list[float], client: httpx.Client) -> str | None:
    """País (nombre en inglés) del centro de la caja, con la geocodificación inversa de OpenStreetMap (Nominatim)."""
    if os.environ.get("RESEARCH_GEOCODER", "nominatim") != "nominatim":
        return None
    lat, lon = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
    try:
        r = client.get("https://nominatim.openstreetmap.org/reverse",
                       params={"lat": lat, "lon": lon, "zoom": 3, "format": "jsonv2", "accept-language": "en"})
        r.raise_for_status()
        d = r.json()
        return (d.get("address") or {}).get("country") or d.get("name")
    except (httpx.HTTPError, ValueError):
        return None


class Gdacs(Provider):
    """GDACS pagina de 100 en 100 y por todo el mundo. Con el país del área (Nominatim) la consulta se filtra en el
    servidor (`country=`, comprobado el 2026-11-15: unos 3 s); sin él, se recorren como mucho GLOBAL_PAGES páginas,
    las más recientes, y se avisa en `truncated`."""

    id = "gdacs"
    name = "GDACS (Comisión Europea y ONU)"
    url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    MAX_PAGES = 15
    GLOBAL_PAGES = 4

    def __init__(self, client=None, country_resolver=None):
        super().__init__(client)
        self.country_resolver = country_resolver or (lambda b: country_of(b, self.client))
        self.truncated = False

    def events(self, bbox, start, end):
        out, seen = [], set()
        country = self.country_resolver(bbox) if bbox[2] - bbox[0] < 40 else None
        pages = self.MAX_PAGES if country else self.GLOBAL_PAGES
        self.truncated = False
        # Los incendios (WF) son la mayoría y llenarían las páginas: van en su propia consulta.
        for kinds in ("EQ;TC;FL;VO;DR", "WF"):
            for page in range(1, pages + 1):
                params = {"fromdate": start, "todate": end, "alertlevel": "green;orange;red", "eventlist": kinds, "pagenumber": page}
                if country:
                    params["country"] = country
                r = self.client.get(self.url, params=params)
                if r.status_code in (204, 404):  # sin más páginas GDACS responde 204 vacío (comprobado el 2026-11-15)
                    break
                r.raise_for_status()
                feats = (r.json() or {}).get("features", [])
                for f in feats:
                    p = f["properties"]
                    box = f.get("bbox") or _point_box(f.get("geometry"))
                    key = (p["eventtype"], p["eventid"])
                    if not box or key in seen or not _intersects(_grow(bbox, 0.5 if p["eventtype"] != "TC" else 2), box):
                        continue
                    seen.add(key)
                    kind, phen = GDACS_TYPES.get(p["eventtype"], ("other", []))
                    sev = p.get("severitydata")
                    sev_text = sev.get("severitytext") if isinstance(sev, dict) else None
                    links = p.get("url") if isinstance(p.get("url"), dict) else {}
                    out.append({
                        "id": f"gdacs-{p['eventtype']}-{p['eventid']}",
                        "title": p.get("name") or p.get("description"),
                        "type": kind,
                        "phenomena": phen,
                        "date": p["fromdate"][:10],
                        "end_date": (p.get("todate") or p["fromdate"])[:10],
                        "bbox": box,
                        "geometry_precision": "gdacs_" + (p.get("Class") or "geometry").lower(),
                        "description": f"Alerta {p.get('alertlevel')}. {sev_text or ''} País: {p.get('country') or '—'}.".strip(),
                        "alert_level": p.get("alertlevel"),
                        "confidence": "curated_index",
                        "sources": [{"name": "GDACS", "url": links.get("report")}, {"name": f"GDACS fuente: {p.get('source')}", "url": None}],
                        "origin": self.id,
                    })
                if len(feats) < 100:
                    break
            else:
                self.truncated = True
        return out


def _point_box(g: dict | None) -> list[float] | None:
    if not g or not g.get("coordinates"):
        return None
    if g["type"] == "Point":
        x, y = g["coordinates"][:2]
        return [x, y, x, y]
    return None


# --- Copernicus EMS -------------------------------------------------------------------------------------------------

POINT_RE = re.compile(r"POINT \(([-\d.]+) ([-\d.]+)\)")
NUM_PAIR = re.compile(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")


class CopernicusEms(Provider):
    id = "copernicus_ems"
    name = "Copernicus Emergency Management Service — Rapid Mapping"
    url = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/"

    def __init__(self, client=None, cache: DiskCache | None = None):
        super().__init__(client)
        self.cache = cache or DiskCache()

    def _activations(self) -> list[dict]:
        def build():
            items, nxt = [], self.url + "public-activations-info/?limit=100"
            while nxt and len(items) < 3000:
                r = self.client.get(nxt)
                r.raise_for_status()
                d = r.json()
                items += d.get("results", [])
                nxt = d.get("next")
            return items
        return self.cache.parsed("cems", 3600, build)

    def events(self, bbox, start, end):
        out = []
        for a in self._activations():
            when = (a.get("eventTime") or a.get("activationTime") or "")[:10]
            m = POINT_RE.search(a.get("centroid") or "")
            if not when or not m or not (start <= when <= end):
                continue
            x, y = float(m.group(1)), float(m.group(2))
            if not _intersects(_grow(bbox, 1.0), [x, y, x, y]):
                continue
            box, aois = self._aoi_box(a["code"])
            if box and not _intersects(bbox, box):
                continue
            out.append({
                "id": f"cems-{a['code']}",
                "title": a.get("name"),
                "type": (a.get("category") or "other").lower(),
                "phenomena": ["flood"] if "flood" in (a.get("category") or "").lower() else ["surface_change"],
                "date": when,
                "end_date": (a.get("lastUpdate") or when)[:10] if a.get("closed") else None,
                "bbox": box or [x, y, x, y],
                "geometry_precision": "cems_aoi_extent" if box else "cems_centroid",
                "description": f"Activación {a['code']} de Copernicus EMS ({a.get('category')}), {a.get('n_products')} productos cartográficos. Áreas: {', '.join(aois[:5]) or '—'}.",
                "confidence": "official_mapping",
                "mapping_products": a.get("n_products"),
                "sources": [{"name": "Copernicus EMS Rapid Mapping", "url": f"https://rapidmapping.emergency.copernicus.eu/{a['code']}/"}],
                "origin": self.id,
            })
        return out

    def _aoi_box(self, code: str) -> tuple[list[float] | None, list[str]]:
        try:
            r = self.client.get(self.url + "public-activations/", params={"code": code})
            r.raise_for_status()
            res = (r.json().get("results") or [{}])[0]
        except (httpx.HTTPError, ValueError):
            return None, []
        xs, ys, names = [], [], []
        for aoi in res.get("aois", []):
            names.append(aoi.get("name", ""))
            for x, y in NUM_PAIR.findall(aoi.get("extent") or ""):
                xs.append(float(x))
                ys.append(float(y))
        return ([min(xs), min(ys), max(xs), max(ys)] if xs else None), names


# --- NASA Global Landslide Catalog -----------------------------------------------------------------------------------

class NasaLandslides(Provider):
    id = "nasa_glc"
    name = "NASA Global Landslide Catalog"
    url = "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv"
    coverage = "global, 1988-2016 (catálogo histórico, sin actualizar)"

    def __init__(self, client=None, cache: DiskCache | None = None):
        super().__init__(client)
        self.cache = cache or DiskCache()

    def _rows(self) -> list[dict]:
        def build():
            text = self.cache.text("nasa_glc.csv", self.url, 30 * 86400, self.client)
            rows = []
            for r in csv.DictReader(io.StringIO(text)):
                try:
                    d = dt.datetime.strptime(r["event_date"][:10], "%m/%d/%Y").date()
                    lon, lat = float(r["longitude"]), float(r["latitude"])
                except (ValueError, KeyError):
                    continue
                rows.append((d, lon, lat, r))
            return rows
        return self.cache.parsed("nasa_glc", 30 * 86400, build)

    def events(self, bbox, start, end):
        s0, e0 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        out = []
        for d, lon, lat, r in self._rows():
            if not (s0 <= d <= e0) or not _intersects(bbox, [lon, lat, lon, lat]):
                continue
            out.append({
                "id": f"glc-{r['event_id']}",
                "title": r.get("event_title") or "Deslizamiento",
                "type": "landslide",
                "phenomena": ["landslide"],
                "date": d.isoformat(),
                "bbox": [lon, lat, lon, lat],
                "geometry_precision": f"glc_{(r.get('location_accuracy') or 'unknown').replace(' ', '_')}",
                "description": f"{r.get('landslide_category') or 'deslizamiento'}, detonante {r.get('landslide_trigger') or 'desconocido'}, tamaño {r.get('landslide_size') or '—'}; víctimas mortales: {r.get('fatality_count') or '0'}. {r.get('location_description') or ''}".strip(),
                "confidence": "curated_catalog",
                "sources": [{"name": "NASA GLC", "url": self.url}] + ([{"name": r.get("source_name"), "url": r["source_link"]}] if r.get("source_link") else []),
                "origin": self.id,
            })
        return out


# --- IBTrACS ------------------------------------------------------------------------------------------------------

class Ibtracs(Provider):
    id = "ibtracs"
    name = "NOAA IBTrACS (trayectorias de ciclones, últimos 3 años)"
    url = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.last3years.list.v04r01.csv"
    coverage = "global, últimos 3 años (el archivo completo desde 1842 pesa cientos de MB)"
    BUFFER_DEG = 2.0  # radio aproximado en que un ciclón afecta: se declara en geometry_precision

    def __init__(self, client=None, cache: DiskCache | None = None):
        super().__init__(client)
        self.cache = cache or DiskCache()

    def _tracks(self) -> dict[str, dict]:
        def build():
            text = self.cache.text("ibtracs_last3years.csv", self.url, 86400, self.client)
            tracks: dict[str, dict] = {}
            reader = csv.DictReader(io.StringIO(text))
            next(reader, None)  # segunda fila: unidades
            for r in reader:
                try:
                    lat, lon = float(r["LAT"]), float(r["LON"])
                    t = dt.datetime.fromisoformat(r["ISO_TIME"])
                except (ValueError, KeyError):
                    continue
                tr = tracks.setdefault(r["SID"], {"name": r["NAME"], "points": [], "wind": None})
                tr["points"].append((t, lon, lat))
                w = (r.get("USA_WIND") or r.get("WMO_WIND") or "").strip()
                if w.isdigit():
                    tr["wind"] = max(tr["wind"] or 0, int(w))
            return tracks
        return self.cache.parsed("ibtracs", 86400, build)

    def events(self, bbox, start, end):
        s0, e0 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        zone = _grow(bbox, self.BUFFER_DEG)
        out = []
        for sid, tr in self._tracks().items():
            near = [(t, x, y) for t, x, y in tr["points"] if s0 <= t.date() <= e0 and _intersects(zone, [x, y, x, y])]
            if not near:
                continue
            xs, ys = [p[1] for p in near], [p[2] for p in near]
            out.append({
                "id": f"ibtracs-{sid}",
                "title": f"Ciclón tropical {tr['name'].title()}",
                "type": "tropical_cyclone",
                "phenomena": ["flood", "landslide"],
                "date": near[0][0].date().isoformat(),
                "end_date": near[-1][0].date().isoformat(),
                "time_utc": near[0][0].strftime("%H:%M"),
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "geometry_precision": f"track_within_{self.BUFFER_DEG:g}deg",
                "description": f"Trayectoria a menos de {self.BUFFER_DEG:g}° del área; viento máximo registrado {tr['wind'] or '—'} kt.",
                "confidence": "official_catalog",
                "sources": [{"name": "NOAA NCEI IBTrACS v04r01", "url": "https://www.ncei.noaa.gov/products/international-best-track-archive"}],
                "origin": self.id,
            })
        return out


# --- Con credencial -------------------------------------------------------------------------------------------------

class ReliefWeb(Provider):
    """Desastres de OCHA. La API v2 exige un `appname` aprobado (403 sin él, comprobado el 2026-11-15). Sin
    geometría propia: se usa la ubicación del país principal, y se declara."""

    id = "reliefweb"
    name = "ReliefWeb (OCHA, ONU)"
    url = "https://api.reliefweb.int/v2/disasters"
    credential_env = "RELIEFWEB_APPNAME"

    def events(self, bbox, start, end):
        body = {
            "limit": 500,
            "fields": {"include": ["name", "date.event", "type.name", "primary_country.name", "primary_country.location", "url", "glide"]},
            "filter": {"field": "date.event", "value": {"from": f"{start}T00:00:00+00:00", "to": f"{end}T23:59:59+00:00"}},
        }
        r = self.client.post(self.url, params={"appname": os.environ[self.credential_env]}, json=body)
        r.raise_for_status()
        out = []
        for d in r.json().get("data", []):
            f = d.get("fields", {})
            loc = (f.get("primary_country") or {}).get("location") or {}
            if "lon" not in loc or not _intersects(_grow(bbox, 3), [loc["lon"], loc["lat"], loc["lon"], loc["lat"]]):
                continue
            types = [t["name"] for t in f.get("type", [])]
            out.append({
                "id": f"reliefweb-{d['id']}",
                "title": f.get("name"),
                "type": (types[0] if types else "other").lower().replace(" ", "_"),
                "phenomena": ["flood"] if any("Flood" in t or "Storm" in t or "Cyclone" in t for t in types) else ["surface_change"],
                "date": (f.get("date") or {}).get("event", "")[:10],
                "bbox": [loc["lon"], loc["lat"], loc["lon"], loc["lat"]],
                "geometry_precision": "country_centroid",
                "description": f"{', '.join(types)} en {(f.get('primary_country') or {}).get('name')}. GLIDE {f.get('glide') or '—'}.",
                "confidence": "humanitarian_report",
                "sources": [{"name": "ReliefWeb", "url": f.get("url")}],
                "origin": self.id,
            })
        return out


class Firms(Provider):
    """Detecciones de fuego activo de VIIRS. La API de área pide una MAP_KEY gratuita y como mucho 10 días por
    petición; se agrupan por día y se piden como mucho los últimos 120 días del periodo (se declara)."""

    id = "firms"
    name = "NASA FIRMS (fuego activo VIIRS)"
    url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    credential_env = "FIRMS_MAP_KEY"
    MAX_DAYS = 120

    def events(self, bbox, start, end):
        key = os.environ[self.credential_env]
        e0 = dt.date.fromisoformat(end)
        s0 = max(dt.date.fromisoformat(start), e0 - dt.timedelta(days=self.MAX_DAYS - 1))
        recent = (dt.date.today() - s0).days < 60
        source = "VIIRS_SNPP_NRT" if recent else "VIIRS_SNPP_SP"
        area = ",".join(f"{v:.4f}" for v in bbox)
        by_day: dict[str, list[tuple[float, float]]] = {}
        day = s0
        while day <= e0:
            n = min(10, (e0 - day).days + 1)
            r = self.client.get(f"{self.url}{key}/{source}/{area}/{n}/{day.isoformat()}")
            r.raise_for_status()
            for row in csv.DictReader(io.StringIO(r.text)):
                try:
                    by_day.setdefault(row["acq_date"], []).append((float(row["longitude"]), float(row["latitude"])))
                except (KeyError, ValueError):
                    continue
            day += dt.timedelta(days=n)
        out = []
        for d, pts in sorted(by_day.items()):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append({
                "id": f"firms-{d}-{area}",
                "title": f"{len(pts)} detecciones de fuego activo (VIIRS)",
                "type": "active_fire",
                "phenomena": ["surface_change"],
                "date": d,
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "geometry_precision": "viirs_375m_detections",
                "description": f"{len(pts)} píxeles de 375 m con fuego activo ese día ({source}). Periodo consultado: {s0} a {e0}.",
                "confidence": "satellite_detection",
                "sources": [{"name": "NASA FIRMS", "url": "https://firms.modaps.eosdis.nasa.gov/"}],
                "origin": self.id,
            })
        return out


def default_providers(client: httpx.Client | None = None, cache: DiskCache | None = None) -> list[Provider]:
    cache = cache or DiskCache()
    return [Usgs(client), Gdacs(client), CopernicusEms(client, cache), NasaLandslides(client, cache), Ibtracs(client, cache),
            ReliefWeb(client), Firms(client)]


# --- Capas de México para la susceptibilidad -----------------------------------------------------------------------

MEXICO_BBOX = [-118.5, 14.5, -86.7, 32.8]
INEGI_WMS = "https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61"
# Capas del WMS de INEGI comprobadas el 2026-11-15 (GetCapabilities y GetMap sobre Parral con 200 e imagen PNG).
INEGI_LAYERS = {
    "c402": ("Cuencas hidrológicas", "flood"),
    "c310": ("Corrientes de agua (red hidrográfica)", "flood"),
    "c783": ("Uso de suelo y vegetación, serie VII", "both"),
    "c416": ("Suelos (edafología)", "landslide"),
    "c407": ("Humedad del suelo", "landslide"),
    "c102": ("Localidades urbanas (exposición)", "both"),
}


def inegi_layers(bbox: list[float]) -> list[dict]:
    if not _intersects(bbox, MEXICO_BBOX):
        return []
    w, s, e, n = bbox
    out = []
    for code, (title, phen) in INEGI_LAYERS.items():
        out.append({
            "code": code,
            "title": title,
            "phenomenon": phen,
            "wms": INEGI_WMS,
            "getmap": f"{INEGI_WMS}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS={code}&STYLES=&SRS=EPSG:4326"
            f"&BBOX={w},{s},{e},{n}&WIDTH=512&HEIGHT=512&FORMAT=image/png&TRANSPARENT=true",
        })
    return out
