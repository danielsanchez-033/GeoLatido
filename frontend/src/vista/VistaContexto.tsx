import { useMemo, type ReactNode } from 'react'
import { useSesion } from '../sesion/sesion'
import { ContextoVista, vistaDeSesion } from './vista'

/** Da la vista a toda la app a partir de la sesión. Va dentro de <SesionProvider>. */
export function VistaProvider({ children }: { children: ReactNode }) {
  const { sesion } = useSesion()
  const vista = vistaDeSesion(sesion)
  const valor = useMemo(() => ({ vista }), [vista])
  return <ContextoVista.Provider value={valor}>{children}</ContextoVista.Provider>
}
