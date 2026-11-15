import { useEffect, useState } from 'react'

export type Live<T> = { status: 'loading' } | { status: 'error' } | { status: 'ready'; data: T }

type Stored<T> = Exclude<Live<T>, { status: 'loading' }> & { key: string }

/**
 * Pide datos a la API cuando cambia `key` (por ejemplo, al cambiar de idioma).
 * Mientras llega la respuesta de la clave actual, no se devuelve la anterior.
 */
export function useLive<T>(key: string, run: () => Promise<T | undefined>): Live<T> {
  const [stored, setStored] = useState<Stored<T>>()

  useEffect(() => {
    let current = true
    run()
      .then((data) => current && setStored(data === undefined ? { key, status: 'error' } : { key, status: 'ready', data }))
      .catch(() => current && setStored({ key, status: 'error' }))
    return () => {
      current = false
    }
    // `run` se rehace en cada render; la petición depende solo de `key`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return stored?.key === key ? stored : { status: 'loading' }
}
