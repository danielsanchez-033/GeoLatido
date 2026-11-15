import type { EventVerdict } from '../api/client'

/** Datos fijos de la consulta de ejemplo y del modo historia (specs/05-faro/spec.md). */

export type EventType = NonNullable<EventVerdict['event_type']>
export const EVENT_TYPES: EventType[] = ['urban_storm', 'river_flood', 'wildfire']

export interface Query {
  date: string
  eventType: EventType | ''
  time: string
}

/** Tormenta del 1 de julio de 2026 en Parral: primer incidente a las 15:37 hora local (MEMORY.md). */
export const EXAMPLE: Query = { date: '2026-07-01', eventType: 'urban_storm', time: '21:37' }

/** Datos fijos de cada escena (specs/05-faro/spec.md, T-FAR-06). El resultado llega siempre de la API. */
export const STORY = {
  storm: { ...EXAMPLE },
  monsoon: { series: 'T048A-F015', pair: '20260816_20260828' },
  /** Mina la Prieta en OpenStreetMap (Nominatim, consultado el 2026-11-13). No marca los jales. */
  mine: { series: 'T048A-F015', lon: -105.66631, lat: 26.93807 },
} as const

