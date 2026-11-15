import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ContextoSesion, authApi, detalle, type EstadoSesion, type Perfil, type TokenOut } from './sesion'

/** Renueva al 80 % de la vida del token de acceso (15 min en auth). */
const MARGEN = 0.8

/**
 * Marca (sin datos: solo «1») de que este navegador abrió sesión. Sin ella no se pide /refresh al arrancar:
 * sin cookie, auth responde 401 y el navegador lo pinta en rojo en la consola en cada visita anónima. La
 * cookie de renovación es HttpOnly, así que la app no puede saber de otro modo si existe.
 */
const MARCA = 'sesion-posible'
function marcar(si: boolean) {
  try {
    if (si) localStorage.setItem(MARCA, '1')
    else localStorage.removeItem(MARCA)
  } catch {
    // Sin almacenamiento, se pide /refresh como antes.
  }
}
function hayMarca(): boolean {
  try {
    return localStorage.getItem(MARCA) === '1'
  } catch {
    return true
  }
}

/** Da la sesión a la app: comprueba la cookie al arrancar y renueva el token antes de que caduque. */
export function SesionProvider({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<EstadoSesion>({ estado: 'comprobando' })
  const temporizador = useRef<ReturnType<typeof setTimeout>>(undefined)
  // `abrir` programa la renovación y `renovar` llama a `abrir`: la referencia rompe el ciclo.
  const renovarLuego = useRef<() => void>(() => {})

  const abrir = useCallback((t: TokenOut) => {
    marcar(true)
    setSesion({ estado: 'abierta', token: t.access_token, perfil: t.role })
    clearTimeout(temporizador.current)
    temporizador.current = setTimeout(() => renovarLuego.current(), t.expires_in * 1000 * MARGEN)
  }, [])

  /** Pide un token nuevo con la cookie. 503: AUTH_ENABLED=0 en el gateway; otro error, sin sesión. */
  const renovar = useCallback(
    () =>
      authApi
        .POST('/refresh')
        .then(({ data, response }) => {
          if (data) return abrir(data)
          marcar(false)
          setSesion(response.status === 503 ? { estado: 'apagado' } : { estado: 'anonima' })
        })
        .catch(() => setSesion({ estado: 'apagado' })),
    [abrir],
  )

  useEffect(() => {
    renovarLuego.current = () => void renovar()
    if (hayMarca()) void renovar()
    else
      // Sin sesión previa basta saber si el acceso está encendido. Con AUTH_ENABLED=0 el gateway responde 200 con
      // `auth_enabled: false` (desde el 2026-11-15; antes, 503, que también se acepta).
      authApi
        .GET('/health')
        .then(({ data, response }) =>
          setSesion(response.status === 503 || (data as { auth_enabled?: boolean } | undefined)?.auth_enabled === false ? { estado: 'apagado' } : { estado: 'anonima' }),
        )
        .catch(() => setSesion({ estado: 'apagado' }))
    return () => clearTimeout(temporizador.current)
  }, [renovar])

  const entrar = useCallback(
    async (correo: string, clave: string) => {
      const { data, error } = await authApi.POST('/login', { body: { email: correo, password: clave } })
      if (data) {
        abrir(data)
        return null
      }
      return detalle(error) ?? 'error'
    },
    [abrir],
  )

  const registrar = useCallback(
    async (correo: string, clave: string, perfil: Perfil) => {
      const { data, error } = await authApi.POST('/register', { body: { email: correo, password: clave, role: perfil } })
      if (data) {
        abrir(data)
        return null
      }
      return detalle(error) ?? 'error'
    },
    [abrir],
  )

  const salir = useCallback(async () => {
    clearTimeout(temporizador.current)
    try {
      await authApi.POST('/logout')
    } finally {
      marcar(false)
      setSesion({ estado: 'anonima' })
    }
  }, [])

  const valor = useMemo(
    () => ({
      sesion,
      entrar,
      registrar,
      salir,
      cabeceras: (): Record<string, string> =>
        sesion.estado === 'abierta' ? { Authorization: `Bearer ${sesion.token}` } : {},
    }),
    [sesion, entrar, registrar, salir],
  )
  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}
