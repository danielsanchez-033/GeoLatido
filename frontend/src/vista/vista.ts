// Vista: Público, Estudiante o Investigador (specs/08-interfaz). Desde el 2026-11-14 sale del perfil de la
// sesión, sin selector: sin sesión es Público. Es solo presentación: no cambia qué dice la API.
import { createContext, useContext } from 'react'
import type { EstadoSesion } from '../sesion/sesion'

export const VISTAS = ['public', 'student', 'researcher'] as const
export type Vista = (typeof VISTAS)[number]

/** La vista que corresponde a la sesión: la del perfil declarado, o Público si no hay sesión. */
export function vistaDeSesion(sesion: EstadoSesion): Vista {
  return sesion.estado === 'abierta' ? sesion.perfil : 'public'
}

export interface ValorVista {
  vista: Vista
}

export const ContextoVista = createContext<ValorVista | null>(null)

export function useVista(): ValorVista {
  const valor = useContext(ContextoVista)
  if (!valor) throw new Error('useVista necesita <VistaProvider>')
  return valor
}
