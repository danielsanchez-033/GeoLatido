// Lógica del comparador óptico (T-ATL-07, RF-ATL-07), sin MapLibre ni DOM.
import type { MapProps, VistaOptica } from "../types/map";
import type { Idioma } from "./textos";
import { TEXTOS } from "./textos";

export type LadoOptico = "before" | "after";

/** Posición inicial del deslizador, en % del ancho desde la izquierda. */
export const POSICION_INICIAL = 50;
const PASO = 5;
const PASO_LARGO = 25;

/**
 * Lado que se enseña: el preferido si existe y, si no, el otro.
 * `null` si no hay ninguno: entonces no se monta el comparador.
 */
export function ladoDisponible(
  optical: MapProps["optical"],
  preferido: LadoOptico,
): LadoOptico | null {
  if (optical?.[preferido]) return preferido;
  const otro: LadoOptico = preferido === "after" ? "before" : "after";
  return optical?.[otro] ? otro : null;
}

export function limitarPosicion(p: number): number {
  if (!Number.isFinite(p)) return POSICION_INICIAL;
  return Math.min(100, Math.max(0, p));
}

/** Nueva posición del deslizador para una tecla, o `null` si la tecla no lo mueve. */
export function moverConTecla(p: number, tecla: string): number | null {
  switch (tecla) {
    case "ArrowLeft":
    case "ArrowDown":
      return limitarPosicion(p - PASO);
    case "ArrowRight":
    case "ArrowUp":
      return limitarPosicion(p + PASO);
    case "PageDown":
      return limitarPosicion(p - PASO_LARGO);
    case "PageUp":
      return limitarPosicion(p + PASO_LARGO);
    case "Home":
      return 0;
    case "End":
      return 100;
    default:
      return null;
  }
}

/** "2026-07-03T17:46:21Z" → "2026-07-03 17:46", siempre en UTC. Si no es una fecha, se devuelve tal cual. */
export function formatoFechaUtc(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  return new Date(t).toISOString().slice(0, 16).replace("T", " ");
}

export function formatoPorcentaje(x: number, idioma: Idioma): string {
  const s = x.toFixed(1);
  return idioma === "es" ? s.replace(".", ",") : s;
}

export interface DescripcionLado {
  /** Hay teselas que pintar. */
  conImagen: boolean;
  /** Fecha, distancia a la pasada de radar y nubosidad, en este orden. */
  lineas: string[];
  /** Por qué no hay imagen o por qué hay que leerla con cuidado. */
  aviso: string | null;
  /** Texto de atribución de la escena; debe verse junto a la imagen. */
  atribucion: string | null;
}

export function describirLado(v: VistaOptica, idioma: Idioma): DescripcionLado {
  const t = TEXTOS[idioma];
  const lineas: string[] = [];
  if (v.acquiredAt) lineas.push(t.escenaDel(formatoFechaUtc(v.acquiredAt)));
  if (v.daysFromRadar !== undefined) lineas.push(t.diasRadar(v.daysFromRadar));
  if (v.cloudCover !== undefined) lineas.push(t.nubes(formatoPorcentaje(v.cloudCover, idioma)));

  let aviso: string | null = v.status === "clear" ? null : t.estadosOpticos[v.status];
  // Una escena "clear" que no cubre la zona también se avisa.
  if (!aviso && v.coversAoi === false) aviso = t.estadosOpticos.partial_coverage;

  return {
    conImagen: v.tiles.length > 0,
    lineas,
    aviso,
    atribucion: v.attribution ?? null,
  };
}
