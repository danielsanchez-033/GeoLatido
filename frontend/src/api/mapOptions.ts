import { avisoEscena, type AvisoEscena } from '../mapa/escena'
import type { MapLayerName, VistaOptica } from '../types/map'
import { API_BASE, absoluteTileUrl, type Lang, type SeriesInfo, type Verdict } from './client'

type OpticalSide = Verdict['evidence']['optical']['before']

/** Nombres legibles de las zonas; si falta, se usa el identificador. */
const ZONE_NAMES: Record<string, string> = { parral: 'Hidalgo del Parral' }

/** Lo que Faro pasa a `crearMapa` y `actualizar` para un veredicto (T-FAR-05). */
export interface VerdictMapOptions {
  aoi: [number, number, number, number]
  nombreZona: string
  layers: Record<Exclude<MapLayerName, 'subsidence'>, string> & { subsidence?: string }
  dataKind: Verdict['receipt']['data_kind']
  causaNoObservable: string | undefined
  desplazamientoEscena: AvisoEscena
  idioma: Lang
  pixelUrl: string
  optical: { before: VistaOptica; after: VistaOptica }
}

export function opticalView(side: OpticalSide): VistaOptica {
  const scene = side.scene
  if (!scene) return { status: side.status, tiles: [] }
  return {
    status: side.status,
    tiles: scene.tiles.map((t) => absoluteTileUrl(t.tile_url)),
    attribution: scene.attribution,
    cloudCover: scene.max_cloud_cover,
    acquiredAt: scene.acquired_at,
    daysFromRadar: scene.days_from_radar,
    coversAoi: scene.covers_aoi,
  }
}

/** Hay algo que comparar si algún lado trae escena con teselas. */
export function hasOpticalScene(verdict: Verdict): boolean {
  const o = verdict.evidence.optical
  return Boolean(o && (o.before.scene?.tiles.length || o.after.scene?.tiles.length))
}

function asBbox(bbox: number[]): [number, number, number, number] | null {
  return bbox.length === 4 ? [bbox[0], bbox[1], bbox[2], bbox[3]] : null
}

export function mapOptionsFor(
  aoiId: string,
  series: SeriesInfo,
  verdict: Verdict,
  lang: Lang,
): VerdictMapOptions | null {
  const aoi = asBbox(series.bbox)
  if (!aoi) return null
  const l = verdict.layers
  const o = verdict.evidence.optical
  return {
    aoi,
    nombreZona: ZONE_NAMES[aoiId] ?? aoiId,
    layers: {
      state: absoluteTileUrl(l.state),
      change_hh: absoluteTileUrl(l.change_hh),
      change_hv: absoluteTileUrl(l.change_hv),
    },
    dataKind: verdict.receipt.data_kind,
    causaNoObservable: verdict.state === 'not_observable' ? (verdict.cause_label ?? undefined) : undefined,
    desplazamientoEscena: avisoEscena(verdict.evidence.scene_shift),
    idioma: lang,
    pixelUrl: `${API_BASE}/api/verdicts/aois/${encodeURIComponent(aoiId)}/series/${encodeURIComponent(series.id)}/pixel`,
    optical: { before: opticalView(o.before), after: opticalView(o.after) },
  }
}
