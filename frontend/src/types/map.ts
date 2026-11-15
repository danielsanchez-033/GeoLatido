import type { DataKind } from '../api/client'

/**
 * Interfaz del mapa que publica Atlas (specs/04-atlas/plan.md).
 * Faro solo la consume; el componente real vive en `src/mapa/`, que es de Atlas.
 */
export type MapLayerName = 'state' | 'change_hh' | 'change_hv' | 'subsidence'

/**
 * Por qué hay o no hay escena óptica en un lado (`evidence.optical.<lado>.status`, PR 19).
 * `none_in_window` y `catalog_unavailable` llegan sin escena.
 */
export type EstadoOptico =
  | 'clear'
  | 'cloudy'
  | 'partial_coverage'
  | 'none_in_window'
  | 'catalog_unavailable'

/**
 * Un lado (antes o después) del comparador óptico. Tabla completa en
 * specs/04-atlas/plan.md. Se define aquí, sin depender de `api/verdicts.d.ts`,
 * hasta que el PR 19 esté en main. Los campos opcionales faltan si `scene` es null.
 */
export interface VistaOptica {
  status: EstadoOptico
  /** `scene.tiles[].tile_url` con el origen del gateway delante; una por tesela MGRS. Vacío sin escena. */
  tiles: string[]
  /** `scene.attribution`: se muestra junto a la imagen (licencia Copernicus). */
  attribution?: string
  /** `scene.max_cloud_cover`, en %: de la tesela MGRS completa, no de la zona. */
  cloudCover?: number
  /** `scene.acquired_at`, hora UTC de la escena. */
  acquiredAt?: string
  /** `scene.days_from_radar`: días respecto a la pasada de radar; negativo si es anterior. */
  daysFromRadar?: number
  /** `scene.covers_aoi`: si las teselas juntas cubren toda la zona. */
  coversAoi?: boolean
}

export interface MapProps {
  /** [oeste, sur, este, norte] en WGS84. */
  aoi: [number, number, number, number]
  /** Plantillas de tesela absolutas (con el origen del gateway delante). */
  /** `subsidence` solo existe si la zona tiene cálculo de hundimiento (`/aois/{aoi}/subsidence`). */
  layers: Record<Exclude<MapLayerName, 'subsidence'>, string> & { subsidence?: string }
  activeLayer: MapLayerName
  /** Escenas Sentinel-2 de antes y después del veredicto (`verdict.evidence.optical`). */
  optical?: { before?: VistaOptica; after?: VistaOptica }
  compare: 'off' | 'swipe'
  dataKind: DataKind
  /** Clic o Enter sobre el mapa; coordenadas con 5 decimales. */
  onPointSelected?: (point: { lon: number; lat: number }) => void
  /** Clic dentro de una huella del buscador mundial: su id (2026-11-15). Sustituye a onPointSelected en ese clic. */
  onFootprintSelected?: (id: string) => void
  onViewChanged?: (view: { bbox: [number, number, number, number]; zoom: number }) => void
}
