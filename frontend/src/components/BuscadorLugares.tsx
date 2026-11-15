import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import type { Bbox } from '../mapa/tipos'
import { Icono } from './Iconos'

/** Lugar de `GET /api/research/places`: nomenclátor del proyecto o OpenStreetMap (Nominatim). */
export type Lugar = { id: string; name: string; bbox: Bbox; source: string; approximate?: boolean }

/**
 * Buscador de lugares de la barra superior (2026-11-15). Sustituye al campo «Próximamente» y a la pestaña Mundo: al
 * elegir un lugar, el mapa vuela allí y el panel de Filtros pasa a esa zona (veredictos si están procesados; si no,
 * las pasadas de NISAR que hay). Patrón combobox de ARIA: flechas, Intro y Escape.
 */
export function BuscadorLugares({ vista, onElegir }: { vista: Bbox | null; onElegir: (l: Lugar) => void }) {
  const { t } = useTranslation()
  const ids = { lista: useId(), entrada: useId() }
  const [q, setQ] = useState('')
  const [abierta, setAbierta] = useState(false)
  const [estado, setEstado] = useState<'nada' | 'cargando' | 'error' | 'listo'>('nada')
  const [lugares, setLugares] = useState<Lugar[]>([])
  const [activo, setActivo] = useState(-1)
  const temporizador = useRef<number | undefined>(undefined)

  // Busca al dejar de escribir (400 ms): el geocodificador de OSM admite una petición por segundo.
  useEffect(() => {
    window.clearTimeout(temporizador.current)
    const texto = q.trim()
    if (texto.length < 2) return
    temporizador.current = window.setTimeout(async () => {
      setEstado('cargando')
      try {
        const r = await fetch(`${API_BASE}/api/research/places?q=${encodeURIComponent(texto)}`, { signal: AbortSignal.timeout(15_000) })
        if (!r.ok) throw new Error(String(r.status))
        const datos = (await r.json()) as { results: Lugar[] }
        setLugares(datos.results.slice(0, 8))
        setActivo(-1)
        setEstado('listo')
      } catch {
        setEstado('error')
      }
    }, 400)
    return () => window.clearTimeout(temporizador.current)
  }, [q])

  // Con menos de dos letras no se busca: lo anterior deja de valer sin tocar el estado.
  const corta = q.trim().length < 2
  const encontrados = corta ? [] : lugares
  const aviso = corta ? 'nada' : estado
  // Primera opción: lo que se ve del mapa, para buscar pasadas sin escribir un nombre.
  const opciones: Lugar[] = [
    ...(vista ? [{ id: 'vista', name: t('places.thisView'), bbox: vista, source: t('places.thisViewSource') }] : []),
    ...encontrados,
  ]

  function elegir(l: Lugar) {
    onElegir(l)
    setAbierta(false)
    setQ(l.id === 'vista' ? '' : l.name.split(',')[0])
  }

  function teclas(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setAbierta(true)
      setActivo((i) => Math.min(opciones.length - 1, i + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActivo((i) => Math.max(0, i - 1))
    } else if (e.key === 'Enter' && abierta && opciones[activo]) {
      e.preventDefault()
      elegir(opciones[activo])
    } else if (e.key === 'Escape') {
      setAbierta(false)
    }
  }

  return (
    <div className="buscador-ubicacion vidrio" onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setAbierta(false)}>
      <Icono nombre="buscar" />
      <input
        id={ids.entrada}
        type="search"
        role="combobox"
        aria-label={t('places.label')}
        aria-expanded={abierta}
        aria-controls={ids.lista}
        aria-autocomplete="list"
        aria-activedescendant={abierta && activo >= 0 ? `${ids.lista}-${activo}` : undefined}
        placeholder={t('places.placeholder')}
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setAbierta(true)
        }}
        onFocus={() => setAbierta(true)}
        onKeyDown={teclas}
        autoComplete="off"
      />
      {abierta && (
        <div className="lugares-lista vidrio">
          <ul id={ids.lista} role="listbox" aria-label={t('places.results')}>
            {opciones.map((l, i) => (
              <li
                key={l.id}
                id={`${ids.lista}-${i}`}
                role="option"
                aria-selected={i === activo}
                tabIndex={-1}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => elegir(l)}
              >
                <strong>{l.name}</strong>
                <span className="muted">{l.source}</span>
              </li>
            ))}
          </ul>
          <p className="muted lugares-aviso" role="status">
            {aviso === 'cargando' ? t('places.searching') : aviso === 'error' ? t('places.error') : aviso === 'listo' && encontrados.length === 0 ? t('places.none') : ''}
          </p>
        </div>
      )}
    </div>
  )
}
