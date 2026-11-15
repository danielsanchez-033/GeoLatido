// Posición del Sol en tiempo real para el globo (corrección de diseño del 2026-11-14).
// - `puntoSubsolar`: dónde está el Sol en el cénit, con el algoritmo aproximado del Almanaque
//   Náutico (error de unas centésimas de grado, de sobra para iluminar un globo).
// - `luzDelSol`: la `light` de MapLibre con la que su atmósfera se ilumina desde ese punto.
// - `nocheGeojson`: polígonos de la noche y de los crepúsculos civil, náutico y astronómico,
//   para oscurecer el lado nocturno del globo.
import type { Feature, FeatureCollection, Polygon } from "geojson";
import type { LightSpecification } from "maplibre-gl";

const RAD = Math.PI / 180;

export interface PuntoSubsolar {
  /** Longitud en grados, de −180 a 180. */
  lon: number;
  /** Latitud en grados: la declinación del Sol. */
  lat: number;
}

function normalizar180(x: number): number {
  return ((((x + 180) % 360) + 360) % 360) - 180;
}

export function puntoSubsolar(fecha: Date): PuntoSubsolar {
  const d = fecha.getTime() / 86_400_000 + 2440587.5 - 2451545.0;
  const g = (357.529 + 0.98560028 * d) * RAD;
  const q = 280.459 + 0.98564736 * d;
  const l = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * RAD;
  const e = (23.439 - 0.00000036 * d) * RAD;
  const ar = Math.atan2(Math.cos(e) * Math.sin(l), Math.cos(l)) / RAD;
  const dec = Math.asin(Math.sin(e) * Math.sin(l)) / RAD;
  // Ecuación del tiempo en horas: hora solar media menos ascensión recta.
  const ecuacion = normalizar180(q - ar) / 15;
  const horasUtc = (fecha.getTime() / 3_600_000) % 24;
  return { lon: normalizar180(-15 * (horasUtc - 12 + ecuacion)), lat: dec };
}

/**
 * `light` de MapLibre con el Sol en el punto subsolar. MapLibre (src/webgl/draw/draw_sky.ts) toma
 * −`position` en coordenadas esféricas como la dirección del Sol en el marco fijo del globo, con
 * x = sen(lon)·cos(lat), y = sen(lat), z = cos(lon)·cos(lat), y luego la gira con la cámara.
 */
export function luzDelSol(fecha: Date): LightSpecification {
  const { lon, lat } = puntoSubsolar(fecha);
  const sol = [Math.sin(lon * RAD) * Math.cos(lat * RAD), Math.sin(lat * RAD), Math.cos(lon * RAD) * Math.cos(lat * RAD)];
  const [x, y, z] = sol.map((v) => -v);
  const polar = Math.acos(Math.max(-1, Math.min(1, z))) / RAD;
  const azimut = ((Math.atan2(y, x) / RAD - 90) % 360 + 360) % 360;
  return { anchor: "map", position: [1.5, azimut, polar], intensity: 0.6 };
}

/** Altura del Sol (grados) de cada banda: bajo el horizonte, crepúsculos civil, náutico y astronómico. */
export const BANDAS_NOCHE = [0, -6, -12, -18] as const;

/**
 * Para cada longitud, la latitud donde el Sol está a `altura` grados. Con
 * sen(h) = sen(φ)·sen(δ) + cos(φ)·cos(δ)·cos(H): a·sen(φ) + b·cos(φ) = sen(h), que da
 * φ = asen(sen(h)/R) − atan2(b, a), con R = √(a² + b²).
 */
function lineaAltura(sol: PuntoSubsolar, altura: number, paso = 2): [number, number][] {
  const dec = (Math.abs(sol.lat) < 0.01 ? 0.01 : sol.lat) * RAD;
  const puntos: [number, number][] = [];
  for (let lon = -180; lon <= 180; lon += paso) {
    const h = (lon - sol.lon) * RAD;
    const a = Math.sin(dec);
    const b = Math.cos(dec) * Math.cos(h);
    const r = Math.hypot(a, b);
    const s = Math.max(-1, Math.min(1, Math.sin(altura * RAD) / r));
    // Dos raíces: la que limita la noche del lado del polo en sombra es la primera si el Sol está al
    // norte del ecuador y la segunda si está al sur.
    const beta = Math.atan2(b, a);
    const raiz = sol.lat >= 0 ? Math.asin(s) - beta : Math.PI - Math.asin(s) - beta;
    const lat = normalizar180(raiz / RAD);
    puntos.push([lon, Math.max(-85, Math.min(85, lat))]);
  }
  return puntos;
}

/**
 * Lado nocturno: un polígono por banda, cerrado por el polo en sombra (el sur si el Sol está al
 * norte del ecuador). Se apilan, así que la oscuridad crece hacia el centro de la noche.
 */
export function nocheGeojson(fecha: Date): FeatureCollection<Polygon> {
  const sol = puntoSubsolar(fecha);
  const polo = sol.lat >= 0 ? -85 : 85;
  const features: Feature<Polygon>[] = BANDAS_NOCHE.map((altura) => {
    const linea = lineaAltura(sol, altura);
    // Entre la línea y el polo en sombra el Sol está más bajo que `altura`.
    const anillo: [number, number][] = [...linea, [180, polo], [-180, polo], linea[0]];
    return { type: "Feature", properties: { altura }, geometry: { type: "Polygon", coordinates: [anillo] } };
  });
  return { type: "FeatureCollection", features };
}
