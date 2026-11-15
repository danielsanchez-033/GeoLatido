import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useCierreAnimado } from '../components/useCierreAnimado'
import { dentroDeAnillo } from '../mapa/huellas'

function movimiento(reducido: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: reducido && q.includes('reduce'), media: q }) as MediaQueryList)
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('useCierreAnimado', () => {
  it('al cerrar, el panel sigue a la vista e inerte mientras se encoge y después se oculta', () => {
    movimiento(false)
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ abierta }) => useCierreAnimado(abierta), { initialProps: { abierta: true } })
    expect(result.current).toEqual({ oculto: false, cerrando: false })
    rerender({ abierta: false })
    expect(result.current).toEqual({ oculto: false, cerrando: true })
    act(() => vi.advanceTimersByTime(299))
    expect(result.current.cerrando).toBe(true)
    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toEqual({ oculto: true, cerrando: false })
    // Abrir es inmediato (lo anima el CSS de apertura).
    rerender({ abierta: true })
    expect(result.current).toEqual({ oculto: false, cerrando: false })
  })

  it('con movimiento reducido se cierra al momento', () => {
    movimiento(true)
    const { result, rerender } = renderHook(({ abierta }) => useCierreAnimado(abierta), { initialProps: { abierta: true } })
    rerender({ abierta: false })
    expect(result.current).toEqual({ oculto: true, cerrando: false })
  })

  it('reabrir durante el cierre lo cancela', () => {
    movimiento(false)
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ abierta }) => useCierreAnimado(abierta), { initialProps: { abierta: true } })
    rerender({ abierta: false })
    rerender({ abierta: true })
    act(() => vi.advanceTimersByTime(400))
    expect(result.current).toEqual({ oculto: false, cerrando: false })
  })
})

describe('dentroDeAnillo', () => {
  const huella = [[-38.7, 66.2], [-37.9, 66.2], [-37.9, 66.6], [-38.7, 66.6], [-38.7, 66.2]]
  it('distingue dentro y fuera de una huella', () => {
    expect(dentroDeAnillo(-38.3, 66.4, huella)).toBe(true)
    expect(dentroDeAnillo(-37.5, 66.4, huella)).toBe(false)
    expect(dentroDeAnillo(-38.3, 66.7, huella)).toBe(false)
  })
  it('vale para huellas inclinadas como las de NISAR', () => {
    const inclinada = [[0, 0], [2, 0.5], [1.5, 2.5], [-0.5, 2], [0, 0]]
    expect(dentroDeAnillo(0.8, 1.2, inclinada)).toBe(true)
    expect(dentroDeAnillo(-0.3, 0.3, inclinada)).toBe(false)
  })
})
