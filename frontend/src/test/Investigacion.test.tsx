import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { Investigacion } from '../components/Investigacion'
import i18n from '../i18n'

// Respuestas de prueba: historia sintética marcada como tal.
const historia = {
  id: 'S-1',
  research_id: 'R-1',
  title: 'Mina La Prieta, Parral, 2026–2026',
  data_kind: 'synthetic',
  traceability: { ok: true },
  evidence: [{ id: 'calc:p:T:1', kind: 'calculation', label: 'Par sintético', verdict_path: '/api/verdicts/x' }],
  chapters: [
    { key: 'title', title: 'Título', claims: [], map: null },
    { key: 'question', title: 'Pregunta de investigación', claims: [{ text: 'Pregunta', evidence: [], kind: 'statement' }], map: null },
    {
      key: 'findings',
      title: 'Hallazgos',
      claims: [{ text: '9,56 % de lo observado con cambio probable', evidence: ['calc:p:T:1'], kind: 'statement' }],
      map: { aoi: 'parral', series: 'T048A-F015', pair_id: '20260828_20260909' },
    },
  ],
}

function responder(url: string, init?: RequestInit) {
  const u = String(url)
  const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
  if (u.endsWith('/research?limit=8')) return ok([])
  if (u.endsWith('/research') && init?.method === 'POST') return ok({ id: 'R-1' })
  if (u.includes('/research/R-1/status')) return ok({ id: 'R-1', job: { id: 'J', state: 'done', step: null, error: null }, story_ids: ['S-1'] })
  if (u.endsWith('/stories/S-1')) return ok(historia)
  return Promise.resolve(new Response('{}', { status: 404 }))
}

beforeEach(async () => {
  await i18n.changeLanguage('es')
  vi.stubGlobal('fetch', vi.fn(responder))
})
afterEach(() => vi.unstubAllGlobals())

test('una pregunta lleva a la historia; cada capítulo mueve el mapa y muestra su evidencia', async () => {
  const onVerPar = vi.fn()
  const user = userEvent.setup()
  render(<Investigacion onVolar={vi.fn()} onVerPar={onVerPar} />)
  await user.type(screen.getByLabelText('Tu pregunta'), 'Zonas mineras de Hidalgo del Parral en 2026')
  await user.click(screen.getByRole('button', { name: 'Investigar' }))
  expect(await screen.findByRole('heading', { name: historia.title })).toBeInTheDocument()
  expect(screen.getByText(/Datos sintéticos/)).toBeInTheDocument()
  expect(screen.getByText(/Cada cifra cita su evidencia/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '2. Hallazgos' }))
  expect(onVerPar).toHaveBeenCalledWith('T048A-F015', '20260828_20260909')
  expect(screen.getByText(/9,56 %/)).toBeInTheDocument()
  expect(screen.getByText('1 evidencia')).toBeInTheDocument()
  const cuerpo = JSON.parse(String((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.find((c) => c[1]?.method === 'POST')![1].body))
  expect(cuerpo).toMatchObject({ question: 'Zonas mineras de Hidalgo del Parral en 2026', run: true, lang: 'es' })
})
