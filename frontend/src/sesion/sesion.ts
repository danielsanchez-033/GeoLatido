// Sesión con el servicio auth (specs/06-acceso). El token de acceso vive solo en memoria, nunca en
// localStorage (RF-INT-06); la renovación usa la cookie HttpOnly que fija auth en /api/auth/.
import createClient from 'openapi-fetch'
import { createContext, useContext } from 'react'
import { API_BASE } from '../api/client'
import type { components, paths } from '../api/auth'

export type Perfil = 'student' | 'researcher'
export type TokenOut = components['schemas']['TokenOut']

/** Cliente tipado de auth. `credentials: include` para que viaje la cookie de renovación. */
export const authApi = createClient<paths>({
  baseUrl: `${API_BASE}/api/auth`,
  credentials: 'include',
  fetch: (request) => globalThis.fetch(request),
})

/**
 * - `comprobando`: preguntando si hay una sesión abierta (cookie).
 * - `apagado`: la pila tiene AUTH_ENABLED=0 o auth no responde; nadie puede entrar.
 * - `anonima`: se puede entrar, pero no hay sesión.
 * - `abierta`: hay token de acceso en memoria.
 */
export type EstadoSesion =
  | { estado: 'comprobando' }
  | { estado: 'apagado' }
  | { estado: 'anonima' }
  | { estado: 'abierta'; token: string; perfil: Perfil }

export interface ValorSesion {
  sesion: EstadoSesion
  entrar: (correo: string, clave: string) => Promise<string | null>
  registrar: (correo: string, clave: string, perfil: Perfil) => Promise<string | null>
  salir: () => Promise<void>
  /** Cabecera Authorization si hay sesión; vacía si no. */
  cabeceras: () => Record<string, string>
}

export const ContextoSesion = createContext<ValorSesion | null>(null)

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion)
  if (!valor) throw new Error('useSesion necesita <SesionProvider>')
  return valor
}

/** Texto de error que da auth (`detail`), o null si no lo trae. */
export function detalle(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const d = (error as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d[0] && typeof d[0] === 'object' && 'msg' in d[0]) return String(d[0].msg)
  }
  return null
}
