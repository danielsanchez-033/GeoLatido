// Huellas de las series en el globo (T-ATL-13, RF-INT-16). La forma es la de `footprint` en
// `GET /api/catalog/aois/{aoi}/series` (T-ANT-17), sin tocar.
import type { Feature, FeatureCollection, Point, Polygon } from "geojson";
import type { components } from "./catalogo";
import type { Idioma } from "./textos";

/** Una Feature por serie: `series[i].footprint` tal como lo da la API. */
export type Huella = components["schemas"]["SeriesFootprint"];
export type PropiedadesHuella = Huella["properties"];

/** Lo que recibe `crearMapa({ huellas })`. */
export interface Huellas {
  type: "FeatureCollection";
  features: Huella[];
}

/**
 * Se quedan las huellas que se pueden dibujar: polígono con un anillo cerrado de al menos
 * cuatro puntos con coordenadas finitas. Las demás se ignoran sin romper el mapa.
 */
export function huellasValidas(h: Huellas | null | undefined): Huella[] {
  if (!h || !Array.isArray(h.features)) return [];
  return h.features.filter((f) => {
    const anillo = f?.geometry?.type === "Polygon" ? f.geometry.coordinates?.[0] : undefined;
    if (!Array.isArray(anillo) || anillo.length < 4) return false;
    if (!anillo.every((p) => p.length >= 2 && p.every(Number.isFinite))) return false;
    const [a, z] = [anillo[0], anillo[anillo.length - 1]];
    return a[0] === z[0] && a[1] === z[1];
  });
}

/**
 * Longitudes seguidas para un anillo que cruza el antimeridiano (de 179 a −179 pasa a 181):
 * así MapLibre no dibuja la huella dando la vuelta al mundo.
 */
export function anilloContinuo(anillo: number[][]): number[][] {
  const lons = anillo.map((p) => p[0]);
  const cruza = Math.max(...lons) - Math.min(...lons) > 180;
  return anillo.map(([lon, lat]) => [cruza && lon < 0 ? lon + 360 : lon, lat]);
}

/**
 * Punto donde va el nombre: el vértice más al norte. Las huellas de dos series de la misma zona
 * casi comparten centro (una ascendente y otra descendente se cruzan), pero no ese vértice.
 */
export function puntoEtiqueta(h: Huella): [number, number] {
  const anillo = anilloContinuo(h.geometry.coordinates[0]);
  const [lon, lat] = anillo.reduce((a, p) => (p[1] > a[1] ? p : a));
  return [lon > 180 ? lon - 360 : lon, lat];
}

/**
 * Hacia dónde crece la etiqueta desde su vértice: hacia fuera de la huella. Si el vértice norte
 * queda al oeste del centro, el texto va a la izquierda; si no, a la derecha.
 */
export function anclaEtiqueta(h: Huella): "bottom-left" | "bottom-right" {
  const anillo = anilloContinuo(h.geometry.coordinates[0]);
  const vertices = anillo.slice(0, -1);
  const centro = vertices.reduce((s, p) => s + p[0], 0) / vertices.length;
  const norte = anillo.reduce((a, p) => (p[1] > a[1] ? p : a));
  return norte[0] < centro ? "bottom-right" : "bottom-left";
}

/** Nombre corto en el mapa: pista con sentido y marco, como empieza el id de la serie (T048A-F015). */
export function nombreCorto(p: PropiedadesHuella): string {
  const tres = (n: number) => String(n).padStart(3, "0");
  return `T${tres(p.track)}${p.direction}-F${tres(p.frame)}`;
}

const SENTIDO: Record<Idioma, Record<string, string>> = {
  es: { A: "ascendente", D: "descendente" },
  en: { A: "ascending", D: "descending" },
};

/** Pista, sentido y marco en palabras, para la lista de huellas y los lectores de pantalla. */
export function describirHuella(p: PropiedadesHuella, idioma: Idioma): string {
  const sentido = SENTIDO[idioma][p.direction] ?? p.direction;
  return idioma === "es"
    ? `pista ${p.track}, ${sentido}, marco ${p.frame}`
    : `track ${p.track}, ${sentido}, frame ${p.frame}`;
}

/** Fuente GeoJSON de las huellas, con longitudes seguidas. */
export function geojsonHuellas(huellas: Huella[]): FeatureCollection<Polygon, PropiedadesHuella> {
  return {
    type: "FeatureCollection",
    features: huellas.map((h) => ({
      type: "Feature",
      properties: h.properties,
      geometry: { type: "Polygon", coordinates: [anilloContinuo(h.geometry.coordinates[0])] },
    })),
  };
}

/** Centro de la zona, para verla como un punto en el globo cuando la caja es diminuta. */
export function centroZona(aoi: [number, number, number, number]): Feature<Point> {
  const [o, s, e, n] = aoi;
  const este = e < o ? e + 360 : e;
  let lon = (o + este) / 2;
  if (lon > 180) lon -= 360;
  return { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, (s + n) / 2] } };
}

/** Punto dentro de un anillo lon/lat (regla par-impar). Las huellas de NISAR no cruzan el antimeridiano. */
export function dentroDeAnillo(lon: number, lat: number, anillo: number[][]): boolean {
  let dentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [xi, yi] = anillo[i];
    const [xj, yj] = anillo[j];
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}
