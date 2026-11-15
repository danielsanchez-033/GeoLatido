import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, expect, it } from 'vitest'
import axe from 'axe-core'
import i18n from '../i18n'
import { Portal, type SeccionPortal } from '../components/Portal'

function Abierto({ inicial }: { inicial: SeccionPortal }) {
  const [s, setS] = useState<SeccionPortal>(inicial)
  return <Portal abierta seccion={s} onSeccion={setS} onCerrar={() => {}} />
}

afterEach(async () => {
  await i18n.changeLanguage('es')
})

it('la portada lleva a «Radar y ciencia», que explica el radar, las cuatro polarizaciones y las aplicaciones futuras', async () => {
  await i18n.changeLanguage('es')
  render(<Abierto inicial="inicio" />)
  await userEvent.click(screen.getByRole('button', { name: 'Radar y ciencia' }))
  expect(screen.getByRole('tab', { name: 'Radar y ciencia' })).toHaveAttribute('aria-selected', 'true')
  const panel = screen.getByRole('tabpanel')
  const tabla = within(panel).getByRole('table')
  expect(within(tabla).getAllByRole('rowheader').map((x) => x.textContent)).toEqual(['HH', 'HV', 'VV', 'VH'])
  for (const texto of [/constante dieléctrica/, /InSAR/, /a través de las nubes/i, /Por qué Hidalgo del Parral/, /Aplicaciones futuras/, /Lo que no se ve/, /Causas humanas/, /Implicaciones/]) {
    expect(panel.textContent).toMatch(texto)
  }
  const resultado = await axe.run(panel, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }, rules: { 'color-contrast': { enabled: false } } })
  expect(resultado.violations.map((v) => v.id)).toEqual([])
})

it('«Radar y ciencia» también está en inglés, con las mismas filas', async () => {
  await i18n.changeLanguage('en')
  render(<Abierto inicial="ciencia" />)
  const panel = screen.getByRole('tabpanel')
  expect(within(panel).getAllByRole('rowheader').map((x) => x.textContent)).toEqual(['HH', 'HV', 'VV', 'VH'])
  expect(panel.textContent).toMatch(/dielectric constant/)
  expect(panel.textContent).toMatch(/Future applications/)
})

it('«Datos y créditos» lista a NASA/JPL, ISRO y ASF DAAC, la licencia Apache 2.0 y qué datos recaba la app', async () => {
  await i18n.changeLanguage('es')
  render(<Abierto inicial="datos" />)
  const panel = screen.getByRole('tabpanel')
  const filas = within(panel).getAllByRole('rowheader').map((x) => x.textContent)
  expect(filas[0]).toMatch(/NISAR/)
  expect(panel.textContent).toMatch(/NASA\/JPL e ISRO; distribuye ASF DAAC/)
  expect(panel.textContent).toMatch(/licencia Apache 2\.0/)
  for (const t of ['Qué datos recabamos', 'Búsquedas de lugares', 'Si creas una cuenta', 'En tu navegador', 'En el servidor']) {
    expect(within(panel).getByText(t)).toBeInTheDocument()
  }
})
