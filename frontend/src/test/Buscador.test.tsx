import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import i18n from '../i18n'
import type { SeriesInfo, Verdict } from '../api/client'
import { Buscador } from '../components/Buscador'
import { Hundimiento } from '../components/Hundimiento'
import type { DatosHundimiento } from '../api/hundimiento'
import { ESTADOS, claveVeredicto, type Filtro } from '../comunidad/historias'
import { makeVerdict } from './fixtures'

afterEach(async () => {
  await i18n.changeLanguage('es')
})

const SERIES = [{ id: 'T048A-F015', bbox: [0, 0, 1, 1], data_kind: 'real', dates: ['2026-06-17', '2026-08-28', '2026-10-15'], maturity: 'PROVISIONAL' }] as unknown as SeriesInfo[]
const V = (id: string, from: string, to: string, state: Verdict['state']) => makeVerdict({ id, from_date: from, to_date: to, state })
const VS = [V('a', '2026-09-21', '2026-10-03', 'no_detectable_change'), V('b', '2026-10-03', '2026-10-15', 'change_probable'), V('c', '2026-08-16', '2026-08-28', 'change_probable')]
const FILTRO: Filtro = { series: 'all', desde: '', hasta: '', estados: [...ESTADOS], ventanas: false }

function pintar(onFiltro = vi.fn(), seleccion?: string) {
  render(<Buscador series={SERIES} todos={VS} filtro={FILTRO} onFiltro={onFiltro} resultados={VS} seleccion={seleccion} onSeleccionar={() => {}} cargando={false} error={false} />)
  return onFiltro
}

it('las fechas muestran la primera y la última muestra y ajustan lo que se salga del rango', async () => {
  await i18n.changeLanguage('es')
  const onFiltro = pintar()
  const desde = screen.getByLabelText('Desde') as HTMLInputElement
  const hasta = screen.getByLabelText('Hasta') as HTMLInputElement
  expect([desde.value, desde.min, hasta.value, hasta.max]).toEqual(['2026-06-17', '2026-06-17', '2026-10-15', '2026-10-15'])
  fireEvent.change(desde, { target: { value: '2025-01-01' } })
  expect(onFiltro).toHaveBeenLastCalledWith(expect.objectContaining({ desde: '' }))
  fireEvent.change(hasta, { target: { value: '2027-05-01' } })
  expect(onFiltro).toHaveBeenLastCalledWith(expect.objectContaining({ hasta: '' }))
  fireEvent.change(desde, { target: { value: '2026-08-01' } })
  expect(onFiltro).toHaveBeenLastCalledWith(expect.objectContaining({ desde: '2026-08-01' }))
})

it('el historial de hallazgos se pliega por mes y abre solo el del hallazgo elegido', async () => {
  await i18n.changeLanguage('es')
  pintar(vi.fn(), claveVeredicto(VS[2]))
  const grupos = document.querySelectorAll('details.resultados-grupo')
  expect(Array.from(grupos).map((g) => g.querySelector('summary')!.textContent)).toEqual([
    'octubre de 20262 hallazgos · 1 con cambio probable',
    'agosto de 20261 hallazgo · 1 con cambio probable',
  ])
  expect(Array.from(grupos).map((g) => (g as HTMLDetailsElement).open)).toEqual([false, true])
  expect(within(grupos[1] as HTMLElement).getByRole('button', { pressed: true })).toBeInTheDocument()
})

it('la tarjeta de hundimiento dice en llano si se hunde y ofrece verlo en el mapa', async () => {
  await i18n.changeLanguage('es')
  const datos = {
    aoi: 'z', status: 'computed', days: 108, pairs: [{}, {}], sinking_fraction: 0.25, fastest_point: { lon: -99.03, lat: 19.44 },
    tiles: 'http://x/{z}/{x}/{y}.png', calibrated: false,
    summary: { detected: 'En 108 días, parte del suelo se alejó del satélite más que el resto.', does_not_prove: 'Es relativo.', missing: '' },
  } as unknown as DatosHundimiento
  const onVolar = vi.fn()
  const onVerCapa = vi.fn()
  render(<Hundimiento datos={datos} capaActiva={false} onVerCapa={onVerCapa} onVolar={onVolar} />)
  expect(screen.getByRole('heading', { name: '¿Se hunde el suelo?' })).toBeInTheDocument()
  expect(screen.getByText('Sí: parte de la zona se hunde más que el resto.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Ver en el mapa' }))
  fireEvent.click(screen.getByRole('button', { name: 'Ir a donde más se hunde' }))
  expect(onVerCapa).toHaveBeenCalled()
  expect(onVolar).toHaveBeenCalledWith(-99.03, 19.44)
})
