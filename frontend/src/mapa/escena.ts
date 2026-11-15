// Aviso de cambio de nivel de toda la escena (evidence.scene_shift, PR 37 y PR 42).

/**
 * - `ninguno`: el par no cambió de nivel por encima del umbral, o no hay datos.
 * - `sin_corregir`: cambió y el porcentaje de cambio no lo descuenta: puede no ser local.
 * - `corregido`: cambió, pero Eco ya lo restó antes de medir el cambio (PR 42).
 */
export type AvisoEscena = "ninguno" | "sin_corregir" | "corregido";

/** Lo que el mapa usa de `verdict.evidence.scene_shift`. `corrected` llega con el PR 42. */
export interface DesplazamientoEscenaApi {
  exceeds_threshold: boolean;
  corrected?: boolean;
}

/** Convierte `verdict.evidence.scene_shift` en el aviso de la leyenda. */
export function avisoEscena(shift: DesplazamientoEscenaApi | null | undefined): AvisoEscena {
  if (!shift?.exceeds_threshold) return "ninguno";
  return shift.corrected ? "corregido" : "sin_corregir";
}

/**
 * Normaliza la opción `desplazamientoEscena`. `true` se mantiene por compatibilidad con
 * el PR 32 y equivale a `sin_corregir`: es lo que significaba antes de existir `corrected`.
 */
export function normalizarAvisoEscena(v: boolean | AvisoEscena | undefined): AvisoEscena {
  if (v === true) return "sin_corregir";
  if (v === false || v === undefined) return "ninguno";
  return v;
}
