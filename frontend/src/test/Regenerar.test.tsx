import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import i18n from '../i18n'
import { Regenerar } from '../components/Regenerar'

afterEach(() => {
  vi.unstubAllGlobals()
})

it('regenera una zona en línea y recarga sus veredictos al terminar', async () => {
  await i18n.changeLanguage('es')
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') return new Response(JSON.stringify({ id: 'z-x', state: 'queued' }), { status: 202 })
    return new Response(JSON.stringify({ id: 'z-x', state: 'done', bbox: [0, 0, 1, 1], summary: null }), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  const onListo = vi.fn()
  render(<Regenerar aoi="z-x" onListo={onListo} />)
  fireEvent.click(screen.getByRole('button', { name: /Regenerar veredictos/ }))
  await waitFor(() => expect(onListo).toHaveBeenCalledWith('z-x', [0, 0, 1, 1], null))
  expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/online\/zones\/z-x\/regenerate$/)
})

it('las zonas de configuración no se regeneran desde aquí y lo dice', async () => {
  await i18n.changeLanguage('es')
  render(<Regenerar aoi="parral" onListo={() => {}} />)
  expect(screen.getByRole('button', { name: /Regenerar veredictos/ })).toBeDisabled()
  expect(screen.getByRole('status').textContent).toMatch(/fuera de línea/)
})
