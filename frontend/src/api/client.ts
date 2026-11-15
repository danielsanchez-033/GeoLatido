import createClient from 'openapi-fetch'
import type { components, paths } from './verdicts'
import type { LineaTiempoApi } from '../mapa/lineaTiempo'

/** Origen del gateway: todo (API y teselas) se sirve desde aquí. */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8080').replace(/\/$/, '')

/** Cliente tipado de la API de veredictos. Los tipos salen de `contracts/verdicts.openapi.json`. */
export const verdictsApi = createClient<paths>({
  baseUrl: `${API_BASE}/api/verdicts`,
  // Se resuelve en cada petición: así las pruebas pueden sustituir fetch.
  fetch: (request) => globalThis.fetch(request),
})

/** La API da plantillas de tesela relativas al gateway; el mapa las necesita absolutas. */
export function absoluteTileUrl(template: string): string {
  return `${API_BASE}${template}`
}

type Schemas = components['schemas']
export type Verdict = Schemas['Verdict']
export type EventVerdict = Schemas['EventVerdict']
export type SeriesInfo = Schemas['SeriesInfo']
export type PixelSeries = Schemas['PixelSeries']
export type Receipt = Schemas['Receipt']
export type DataKind = SeriesInfo['data_kind']
export type Lang = 'es' | 'en'

/** URL de un veredicto en la API, para seguir con él en código (RF-INT-05, vista Investigador). */
export function verdictJsonUrl(verdict: Verdict, lang: Lang): string {
  const c = encodeURIComponent
  return `${API_BASE}/api/verdicts/aois/${c(verdict.aoi)}/series/${c(verdict.series)}/verdicts/${c(verdict.id)}?lang=${lang}`
}

/**
 * Línea de tiempo del catálogo (GET /api/catalog/aois/{aoi}/timeline) para la línea de Atlas.
 * null si falla o si lo que llega no tiene la forma esperada: la consulta de evento sigue sin ella.
 */
export async function fetchTimeline(aoi: string): Promise<LineaTiempoApi | null> {
  try {
    const r = await globalThis.fetch(`${API_BASE}/api/catalog/aois/${encodeURIComponent(aoi)}/timeline`)
    if (!r.ok) return null
    const data = (await r.json()) as LineaTiempoApi
    return Array.isArray(data?.passes) ? data : null
  } catch {
    return null
  }
}
