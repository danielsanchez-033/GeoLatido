import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { beforeEach, vi } from 'vitest'
import type { VerdictMapOptions } from '../api/mapOptions'
import { AtlasMap } from '../components/AtlasMap'
import i18n from '../i18n'

// MapLibre necesita WebGL, que jsdom no tiene: se sustituye crearMapa por un doble.
const mapa = vi.hoisted(() => {
  type Doble = Record<'actualizar' | 'destruir' | 'fijarOpacidad' | 'encuadrar', ReturnType<typeof vi.fn>>
  const instancias: Doble[] = []
  const crearMapa = vi.fn(() => {
    const m = { actualizar: vi.fn(), destruir: vi.fn(), fijarOpacidad: vi.fn(), encuadrar: vi.fn(), mostrarMundo: vi.fn(), volarA: vi.fn(), rotularPunto: vi.fn() }
    instancias.push(m)
    return m
  })
  return { crearMapa, instancias }
})
vi.mock('../mapa/mapa', () => ({ crearMapa: mapa.crearMapa }))

function options(over: Partial<VerdictMapOptions> = {}): VerdictMapOptions {
  return {
    aoi: [-105.95, 26.7, -105.4, 27.15],
    nombreZona: 'Hidalgo del Parral',
    layers: { state: 'http://g/s', change_hh: 'http://g/h', change_hv: 'http://g/v' },
    dataKind: 'real',
    causaNoObservable: undefined,
    desplazamientoEscena: 'ninguno',
    idioma: 'es',
    pixelUrl: 'http://g/pixel',
    optical: { before: { status: 'clear', tiles: ['http://g/t'] }, after: { status: 'none_in_window', tiles: [] } },
    ...over,
  }
}

beforeEach(async () => {
  await i18n.changeLanguage('es')
  mapa.crearMapa.mockClear()
  mapa.instancias.length = 0
})

/** Props por omisión del mapa a pantalla completa (T-FAR-21): las herramientas viven en la barra inferior. */
const base = { compare: false, canCompare: false, busy: false, modo3d: true, layer: 'state' as const, opacity: 0.85, reframe: 0 }

test('con StrictMode deja un solo mapa vivo y lo destruye al desmontar', () => {
  const { unmount } = render(
    <StrictMode>
      <AtlasMap options={options()} {...base} />
    </StrictMode>,
  )
  const vivos = () => mapa.instancias.filter((m) => m.destruir.mock.calls.length === 0)
  expect(vivos()).toHaveLength(1)
  // Sin botón 3D ni selector de capas dentro del mapa: los da la barra de herramientas.
  expect(mapa.crearMapa).toHaveBeenLastCalledWith(
    expect.any(HTMLElement),
    expect.objectContaining({ compare: 'off', modo3d: true, activeLayer: 'state', control3d: false, controlCapas: false }),
  )
  expect(vivos()[0].actualizar).not.toHaveBeenCalled()
  unmount()
  expect(vivos()).toHaveLength(0)
})

test('al cambiar de veredicto o de idioma usa actualizar() sin recrear el mapa', () => {
  const { rerender } = render(<AtlasMap options={options()} {...base} />)
  const next = options({ layers: { state: 'http://g/s2', change_hh: 'x', change_hv: 'y' }, idioma: 'en' })
  rerender(<AtlasMap options={next} {...base} />)
  expect(mapa.crearMapa).toHaveBeenCalledTimes(1)
  expect(mapa.instancias[0].actualizar).toHaveBeenCalledWith({ ...next, compare: 'off', activeLayer: 'state' })
})

test('las herramientas cambian solo lo suyo: comparador, 3D, capa, opacidad y encuadre', () => {
  const o = options()
  const { rerender } = render(<AtlasMap options={o} {...base} canCompare />)
  const m = mapa.instancias[0]
  // Solo el modo: reenviar las capas haría que el mapa las volviera a cargar.
  rerender(<AtlasMap options={o} {...base} canCompare compare />)
  expect(m.actualizar).toHaveBeenLastCalledWith({ antesDespues: true })
  rerender(<AtlasMap options={o} {...base} canCompare compare modo3d={false} />)
  expect(m.actualizar).toHaveBeenLastCalledWith({ modo3d: false })
  rerender(<AtlasMap options={o} {...base} canCompare compare modo3d={false} layer="change_hv" />)
  expect(m.actualizar).toHaveBeenLastCalledWith({ activeLayer: 'change_hv' })
  rerender(<AtlasMap options={o} {...base} canCompare compare modo3d={false} layer="change_hv" opacity={0.4} />)
  expect(m.fijarOpacidad).toHaveBeenLastCalledWith(0.4)
  expect(m.encuadrar).not.toHaveBeenCalled()
  rerender(<AtlasMap options={o} {...base} canCompare compare modo3d={false} layer="change_hv" opacity={0.4} reframe={1} />)
  expect(m.encuadrar).toHaveBeenCalledTimes(1)
  expect(mapa.crearMapa).toHaveBeenCalledTimes(1)
})

test('sin escena óptica el comparador no se activa aunque se pida', () => {
  render(<AtlasMap options={options()} {...base} compare />)
  expect(mapa.crearMapa).toHaveBeenLastCalledWith(expect.any(HTMLElement), expect.objectContaining({ compare: 'off', antesDespues: false }))
})

test('mientras carga, tapa el mapa y lo marca ocupado', () => {
  const { container, rerender } = render(<AtlasMap options={options()} {...base} busy />)
  expect(screen.getByRole('status')).toHaveTextContent('Cargando veredictos…')
  expect(container.querySelector('.atlas-map-frame')).toHaveAttribute('aria-busy', 'true')
  rerender(<AtlasMap options={options()} {...base} />)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})
