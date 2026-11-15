import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import i18n from '../i18n'
import { Bienvenida } from '../components/Bienvenida'

it('la bienvenida presenta GeoLatido, dice que no hace falta cuenta y deja empezar o conocer más', async () => {
  await i18n.changeLanguage('es')
  const onCerrar = vi.fn()
  const onConocerMas = vi.fn()
  render(<Bienvenida onCerrar={onCerrar} onConocerMas={onConocerMas} />)
  expect(screen.getByRole('heading', { name: 'Bienvenido a GeoLatido' })).toBeInTheDocument()
  expect(screen.getByText(/No necesitas cuenta/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Empezar/ }))
  fireEvent.click(screen.getByRole('button', { name: /Conocer más/ }))
  expect(onCerrar).toHaveBeenCalledTimes(1)
  expect(onConocerMas).toHaveBeenCalledTimes(1)
})
