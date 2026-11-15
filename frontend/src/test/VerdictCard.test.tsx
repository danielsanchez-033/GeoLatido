import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach } from 'vitest'
import { VerdictCard } from '../components/VerdictCard'
import i18n from '../i18n'
import { makeVerdict } from './fixtures'

beforeEach(async () => {
  await i18n.changeLanguage('es')
})

test('muestra siempre los tres textos juntos, con el estado en texto y marca', () => {
  const { container } = render(<VerdictCard verdict={makeVerdict()} />)
  expect(screen.getByRole('heading', { name: /Cambio probable/ })).toBeInTheDocument()
  // La marca (relleno) es decorativa: el estado ya está en el texto del título.
  expect(container.querySelector('h3 .marca-change_probable')).toHaveAttribute('aria-hidden', 'true')
  expect(screen.getByText('del 2026-06-17 al 2026-06-29 · 12 días')).toBeInTheDocument()
  for (const label of ['Qué detectamos', 'Qué no prueba', 'Qué falta']) {
    expect(screen.getByText(label)).toBeVisible()
  }
  expect(screen.getByText(/cambió la señal de radar en el 4.1%/)).toBeVisible()
  expect(screen.getByText(/No identifica la causa/)).toBeVisible()
  expect(screen.getByText(/Falta contrastar/)).toBeVisible()
})

test('rotula las hipótesis como explicaciones sin comprobar y las omite si no hay', () => {
  const { rerender } = render(<VerdictCard verdict={makeVerdict()} />)
  const box = screen.getByRole('region', { name: 'Posibles explicaciones, sin comprobar' })
  expect(within(box).getByText(/secado del suelo/)).toBeInTheDocument()
  rerender(<VerdictCard verdict={makeVerdict({ hypotheses: [] })} />)
  expect(screen.queryByText('Posibles explicaciones, sin comprobar')).not.toBeInTheDocument()
})

test('no observable tiene su propio estilo, icono y causa, distinto de sin cambio', () => {
  const { container, rerender } = render(
    <VerdictCard
      verdict={makeVerdict({
        state: 'not_observable',
        cause: 'outside_scene',
        cause_label: 'la zona queda fuera de la pasada',
        hypotheses: [],
      })}
    />,
  )
  expect(screen.getByRole('heading', { name: /No observable/ })).toBeInTheDocument()
  expect(screen.getByText('Motivo de que no se pudiera medir: la zona queda fuera de la pasada')).toBeInTheDocument()
  expect(container.querySelector('article')).toHaveClass('verdict-not_observable')
  expect(container.querySelector('h3 .marca-not_observable')).toBeInTheDocument()

  rerender(<VerdictCard verdict={makeVerdict({ state: 'no_detectable_change', hypotheses: [] })} />)
  expect(screen.getByRole('heading', { name: /Sin cambio detectable/ })).toBeInTheDocument()
  expect(screen.queryByText(/Motivo de que no se pudiera medir/)).not.toBeInTheDocument()
  expect(container.querySelector('article')).toHaveClass('verdict-no_detectable_change')
  expect(container.querySelector('h3 .marca-no_detectable_change')).toBeInTheDocument()
})

// jsdom no abre `details` con Enter; en el navegador lo hace el elemento nativo (se comprobó a mano).
test('el recibo está plegado y muestra la procedencia al abrirlo', async () => {
  const user = userEvent.setup()
  render(<VerdictCard verdict={makeVerdict()} />)
  const summary = screen.getByText('Recibo: de dónde sale esta respuesta')
  const details = summary.closest('details')!
  expect(details).not.toHaveAttribute('open')

  await user.click(summary)
  expect(details).toHaveAttribute('open')
  const receipt = within(details)
  expect(receipt.getByText('T048A-F015: pista 48, ascendente, marco 15')).toBeInTheDocument()
  expect(receipt.getByText('P05023')).toBeInTheDocument()
  expect(receipt.getByText('NISAR_L2_PR_GCOV_023_048_A_015')).toBeInTheDocument()
  expect(receipt.getByText(/2026-06-17, hace 148 días; publicada 40 h después/)).toBeInTheDocument()
  expect(receipt.getByText(/latencia desconocida: el catálogo no respondió/)).toBeInTheDocument()
  expect(receipt.getByText(/Escena Sentinel-2 del 2026-06-18/)).toBeInTheDocument()
  expect(receipt.getByText('Contraste de agua (OPERA DSWx-S1)')).toBeInTheDocument()
  expect(receipt.getByText('Sin referencia OPERA DSWx-S1 a ±7 días.')).toBeInTheDocument()
  expect(receipt.getByText('Cruza un hueco sin adquisiciones')).toBeInTheDocument()
  expect(receipt.getByText(/se reprocesarán a VALIDATED/)).toBeInTheDocument()
})

test('con datos sintéticos la tarjeta lo dice; con datos reales no', () => {
  const { rerender } = render(<VerdictCard verdict={makeVerdict({ receipt: { data_kind: 'synthetic' } })} />)
  expect(screen.getByText('Este veredicto usa datos sintéticos.')).toBeInTheDocument()
  rerender(<VerdictCard verdict={makeVerdict()} />)
  expect(screen.queryByText('Este veredicto usa datos sintéticos.')).not.toBeInTheDocument()
})

test('en inglés usa los rótulos en inglés', async () => {
  await i18n.changeLanguage('en')
  render(<VerdictCard verdict={makeVerdict({ interval_days: 1 })} />)
  expect(screen.getByRole('heading', { name: /Probable change/ })).toBeInTheDocument()
  expect(screen.getByText('What it does not prove')).toBeInTheDocument()
  expect(screen.getByText('from 2026-06-17 to 2026-06-29 · 1 day')).toBeInTheDocument()
})
