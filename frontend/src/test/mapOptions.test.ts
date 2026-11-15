import { API_BASE } from '../api/client'
import { hasOpticalScene, mapOptionsFor } from '../api/mapOptions'
import { makeVerdict } from './fixtures'

const series = {
  id: 'T048A-F015',
  bbox: [-105.95, 26.7, -105.4, 27.15],
  data_kind: 'real' as const,
  dates: [],
  maturity: 'PROVISIONAL',
}

function opticalSide(withScene: boolean) {
  return {
    status: withScene ? ('clear' as const) : ('none_in_window' as const),
    radar_date: '2026-06-17',
    radar_acquired_at: null,
    scene: withScene
      ? {
          id: 'S2C_13RDK_20260618_0_L2A',
          platform: 'sentinel-2c',
          acquired_at: '2026-06-18T17:46:00Z',
          days_from_radar: 1,
          max_cloud_cover: 3.4,
          covers_aoi: true,
          attribution: 'Copernicus Sentinel data 2026',
          tiles: [{ tile: '13RDK', cloud_cover: 3.4, tile_url: '/tiles/cog/x.png?url=a' }],
        }
      : null,
  }
}

function withOptical(before: boolean, after: boolean) {
  const v = makeVerdict()
  v.evidence.optical = { ...v.evidence.optical, before: opticalSide(before), after: opticalSide(after) } as never
  return v
}

test('pone el origen del gateway delante de las capas y arma la ruta del píxel', () => {
  const o = mapOptionsFor('parral', series, withOptical(true, false), 'es')!
  expect(o.aoi).toEqual([-105.95, 26.7, -105.4, 27.15])
  expect(o.nombreZona).toBe('Hidalgo del Parral')
  expect(o.layers.state).toBe(`${API_BASE}/tiles/state`)
  expect(o.layers.change_hv).toBe(`${API_BASE}/tiles/hv`)
  expect(o.pixelUrl).toBe(`${API_BASE}/api/verdicts/aois/parral/series/T048A-F015/pixel`)
  expect(o.dataKind).toBe('real')
  expect(o.idioma).toBe('es')
})

test('dataKind sale del recibo del veredicto, no de la serie', () => {
  const v = makeVerdict({ receipt: { data_kind: 'synthetic' } })
  v.evidence.optical = withOptical(false, false).evidence.optical
  expect(mapOptionsFor('parral', series, v, 'en')!.dataKind).toBe('synthetic')
})

test('convierte el óptico a VistaOptica, con y sin escena', () => {
  const o = mapOptionsFor('parral', series, withOptical(true, false), 'es')!
  expect(o.optical.before).toEqual({
    status: 'clear',
    tiles: [`${API_BASE}/tiles/cog/x.png?url=a`],
    attribution: 'Copernicus Sentinel data 2026',
    cloudCover: 3.4,
    acquiredAt: '2026-06-18T17:46:00Z',
    daysFromRadar: 1,
    coversAoi: true,
  })
  expect(o.optical.after).toEqual({ status: 'none_in_window', tiles: [] })
})

test('solo ofrece comparar si algún lado trae escena', () => {
  expect(hasOpticalScene(withOptical(false, false))).toBe(false)
  expect(hasOpticalScene(withOptical(false, true))).toBe(true)
})

test('pasa la causa solo si el veredicto es no observable', () => {
  const base = withOptical(false, false)
  const no = { ...base, state: 'not_observable' as const, cause_label: 'relieve' }
  expect(mapOptionsFor('parral', series, no, 'es')!.causaNoObservable).toBe('relieve')
  expect(mapOptionsFor('parral', series, { ...no, state: 'change_probable' }, 'es')!.causaNoObservable).toBeUndefined()
})

test('pasa el aviso de desplazamiento de escena de Atlas: sin corregir, corregido o ninguno', () => {
  const base = withOptical(false, false)
  const shift = { basis: 'qa', hh_db: 1.8, hv_db: 1.6, same_direction: true, threshold_db: 1.5 }
  const con = (s: object | null) =>
    mapOptionsFor('parral', series, { ...base, evidence: { ...base.evidence, scene_shift: s } } as never, 'es')!
      .desplazamientoEscena
  expect(con(null)).toBe('ninguno')
  expect(con({ ...shift, exceeds_threshold: false, corrected: false })).toBe('ninguno')
  expect(con({ ...shift, exceeds_threshold: true, corrected: false })).toBe('sin_corregir')
  expect(con({ ...shift, exceeds_threshold: true, corrected: true })).toBe('corregido')
})

test('sin una caja de cuatro números no hay mapa', () => {
  expect(mapOptionsFor('parral', { ...series, bbox: [1, 2] }, withOptical(false, false), 'es')).toBeNull()
})
