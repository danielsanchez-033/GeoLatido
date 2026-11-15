import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, vi } from 'vitest'
import type { EventVerdict } from '../api/client'
import { EventQuery } from '../components/EventQuery'
import i18n from '../i18n'

function makeEvent(over: Partial<EventVerdict> = {}): EventVerdict {
  return {
    aoi: 'parral',
    event_date: '2026-07-01',
    event_time: null,
    event_type: null,
    persistence_hours: 24,
    assumption: {
      persistence_hours: 24,
      source: 'default',
      event_type: null,
      calibrated: false,
      hours_by_event_type: {},
      text: 'Supuesto: el evento dura 24 h, valor por omisión sin calibrar; no se midió.',
    },
    state: 'not_observable',
    cause: 'no_acquisition_during_event',
    cause_label: 'no hubo ninguna pasada mientras duraba el evento',
    previous_pass: '2026-06-29',
    next_pass: '2026-07-08',
    next_pass_acquired_at: '2026-07-08T01:44:35Z',
    data_kind: 'real',
    excluded_passes: [],
    summary: {
      detected: 'El evento del 2026-07-01 no es observable.',
      // Como la API real (T-BAL-06): el supuesto de duración va dentro de does_not_prove.
      does_not_prove: 'Esto no indica que el evento no ocurriera. Supuesto: el evento dura 24 h, valor por omisión sin calibrar; no se midió.',
      missing: 'Haría falta una fuente con mayor frecuencia o reportes locales.',
    },
    ...over,
  } as EventVerdict
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function stub(handler: (url: URL) => Response) {
  const fetch = vi.fn(async (input: Request | string) => handler(new URL(typeof input === 'string' ? input : input.url)))
  vi.stubGlobal('fetch', fetch)
  return fetch
}

beforeEach(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => vi.unstubAllGlobals())

test('consulta con Enter y muestra los tres textos, las pasadas y el supuesto', async () => {
  const user = userEvent.setup()
  const fetch = stub(() => json(makeEvent()))
  render(<EventQuery aoi="parral" lang="es" />)

  await user.type(screen.getByLabelText('Fecha del evento (UTC)'), '2026-07-01')
  await user.keyboard('{Enter}')

  const heading = await screen.findByRole('heading', { name: /No observable/ })
  expect(heading).toHaveFocus()
  expect(screen.getByText('Motivo: no hubo ninguna pasada mientras duraba el evento')).toBeInTheDocument()
  for (const label of ['Qué encontramos', 'Qué no prueba', 'Qué falta', 'Pasada anterior', 'Pasada siguiente']) {
    expect(screen.getByText(label)).toBeVisible()
  }
  expect(screen.getByText('2026-06-29')).toBeInTheDocument()
  // El supuesto llega dentro de «Qué no prueba» (T-BAL-06): se ve ahí y no se repite en una fila aparte.
  expect(screen.getByText('Qué no prueba').nextElementSibling).toHaveTextContent('Supuesto: el evento dura 24 h')
  expect(screen.getAllByText(/Supuesto: el evento dura 24 h/)).toHaveLength(1)
  expect(screen.queryByText('Duración supuesta')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Fecha del evento (UTC)')).toHaveAccessibleDescription(/van en UTC/)

  const url = new URL((fetch.mock.calls[0][0] as Request).url)
  expect(url.pathname).toMatch(/\/aois\/parral\/events$/)
  expect(url.searchParams.get('date')).toBe('2026-07-01')
  expect(url.searchParams.get('lang')).toBe('es')
  expect(url.searchParams.has('event_type')).toBe(false)
  expect(url.searchParams.has('time')).toBe(false)
})

test('el ejemplo pide la tormenta del 1 de julio con tipo y hora UTC', async () => {
  const user = userEvent.setup()
  const fetch = stub(() => json(makeEvent({ event_type: 'urban_storm', persistence_hours: 6 })))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: 'Probar con la tormenta del 1 de julio de 2026' }))
  await screen.findByRole('heading', { name: /No observable/ })

  const url = new URL((fetch.mock.calls[0][0] as Request).url)
  expect(url.searchParams.get('date')).toBe('2026-07-01')
  expect(url.searchParams.get('event_type')).toBe('urban_storm')
  expect(url.searchParams.get('time')).toBe('21:37')
  expect(screen.getByLabelText('Tipo de evento')).toHaveValue('urban_storm')
  // Mismo nombre que el supuesto de la API («tormenta urbana»).
  expect(screen.getByLabelText('Tipo de evento')).toHaveDisplayValue('Tormenta urbana')
})

test('observable no afirma un cambio y remite al veredicto del par', async () => {
  const user = userEvent.setup()
  stub(() => json(makeEvent({ state: 'observable', cause: null, cause_label: null, next_pass: null })))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))
  expect(await screen.findByRole('heading', { name: /Observable: hubo una pasada dentro de la duración supuesta/ })).toBeInTheDocument()
  expect(screen.getByText(/no dice que algo cambiara/)).toBeInTheDocument()
  expect(screen.queryByText(/^Motivo:/)).not.toBeInTheDocument()
  expect(screen.getByText('ninguna')).toBeInTheDocument()
})

test('con datos sintéticos lo avisa y lista las pasadas excluidas', async () => {
  const user = userEvent.setup()
  stub(() =>
    json(
      makeEvent({
        data_kind: 'synthetic',
        excluded_passes: [
          { granule: 'G1', series: 'T171D-F075', date: '2026-08-13', reason: 'producto defectuoso', evidence: 'x' },
        ],
      }),
    ),
  )
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))
  const answer = await screen.findByRole('article')
  expect(within(answer).getByText('Este veredicto usa datos sintéticos.')).toBeInTheDocument()
  expect(within(answer).getByText('2026-08-13 (T171D-F075): producto defectuoso')).toBeInTheDocument()
})

test('repite la última consulta en inglés al cambiar de idioma', async () => {
  const user = userEvent.setup()
  const fetch = stub((url) =>
    json(makeEvent({ cause_label: url.searchParams.get('lang') === 'en' ? 'no pass occurred' : 'sin pasada' })),
  )
  const { rerender } = render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))
  await screen.findByText('Motivo: sin pasada')

  await i18n.changeLanguage('en')
  rerender(<EventQuery aoi="parral" lang="en" />)
  expect(await screen.findByText('Reason: no pass occurred')).toBeInTheDocument()
  const events = fetch.mock.calls.filter(([r]) => (typeof r === 'string' ? r : r.url).includes('/events?'))
  expect(events).toHaveLength(2)
})

test('si la API rechaza la consulta, avisa y no muestra respuesta', async () => {
  const user = userEvent.setup()
  stub(() => json({ detail: [{ msg: 'invalid date' }] }, 422))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo hacer la consulta')
  expect(screen.queryByRole('article')).not.toBeInTheDocument()
})

test('sin fecha no consulta', async () => {
  const user = userEvent.setup()
  const fetch = stub(() => json(makeEvent()))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: 'Consultar' }))
  expect(fetch).not.toHaveBeenCalled()
})

const TIMELINE = {
  aoi: 'parral',
  published_at_basis: 'cmr_updated',
  passes: [
    {
      series: 'T048A-F015-4005-DHDH-P05023',
      granule_id: 'G1',
      acquired_at: '2026-06-29T12:24:34Z',
      published_at: '2026-07-20T00:00:00Z',
      latency_hours: 515.6,
      contains_aoi: true,
    },
  ],
  excluded: [],
  gaps: [],
  next_pass_estimates: [],
}

test('con la respuesta, monta la línea de tiempo con el evento y su supuesto', async () => {
  const user = userEvent.setup()
  const fetch = stub((url) => (url.pathname.endsWith('/timeline') ? json(TIMELINE) : json(makeEvent())))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))

  // La gráfica sale cuando llega el catálogo; antes solo está el título.
  expect(await screen.findByRole('group', { name: /1 pasada/ })).toBeInTheDocument()
  expect(document.querySelector('.atlas-linea-evento')).not.toBeNull()
  expect(document.querySelector('.atlas-linea-supuesto')?.textContent).toContain('Supuesto: el evento dura 24 h')
  const urls = fetch.mock.calls.map(([r]) => (typeof r === 'string' ? r : (r as Request).url))
  expect(urls.filter((u) => u.endsWith('/api/catalog/aois/parral/timeline'))).toHaveLength(1)
})

test('si el catálogo falla, la respuesta del evento sale igual y sin línea de tiempo', async () => {
  const user = userEvent.setup()
  stub((url) => (url.pathname.endsWith('/timeline') ? json({ detail: 'down' }, 503) : json(makeEvent())))
  render(<EventQuery aoi="parral" lang="es" />)
  await user.click(screen.getByRole('button', { name: /Probar con la tormenta/ }))

  expect(await screen.findByRole('article')).toBeInTheDocument()
  await waitFor(() => expect(document.querySelector('.atlas-linea')).toBeNull())
})
