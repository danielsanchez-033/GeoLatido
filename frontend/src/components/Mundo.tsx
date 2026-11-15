import { useEffect, useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import type { components } from '../mapa/catalogo'
import type { Bbox } from '../mapa/tipos'
import { Esqueleto } from './Esqueleto'
import { Icono } from './Iconos'
import { LineaPasadas } from './LineaPasadas'

export type GranuloMundo = components['schemas']['WorldGranuleOut']
type Respuesta = components['schemas']['WorldSearchOut']

const DIA = 86_400_000
const iso = (t: number) => new Date(t).toISOString().slice(0, 10)
const diaDe = (d: string) => Math.floor(Date.parse(d) / DIA)
// Primer día con productos GCOV públicos de NISAR que se consultan (los provisionales empiezan en la segunda mitad de
// 2025): extremo antiguo fijo de la línea de tiempo.
const INICIO_NISAR = '2025-07-01'
const fmt = (x: number) => x.toFixed(2)

/** La caja como la acepta CMR: dentro de ±180/±90 y sin cruzar el antimeridiano. */
function cajaBuscable(b: Bbox | null): Bbox {
  if (!b) return [-180, -90, 180, 90]
  const [o, s, e, n] = b
  const sur = Math.max(-90, s)
  const norte = Math.min(90, n)
  if (e - o >= 360 || o < -180 || e > 180 || o >= e) return [-180, sur, 180, norte]
  return [o, sur, e, norte]
}

/** Serie de un gránulo, con el mismo formato que las series procesadas: «T048A-F015». */
const serieDe = (g: Pick<GranuloMundo, 'track' | 'direction' | 'frame'>) =>
  `T${String(g.track).padStart(3, '0')}${g.direction}-F${String(g.frame).padStart(3, '0')}`

/**
 * Filtros de una zona sin veredictos procesados (2026-11-15). Lo que antes era la pestaña Mundo: las pasadas
 * NISAR GCOV reales de la zona, de CMR (NASA Earthdata Search) y con vista previa de ASF (Vertex), sin cuenta.
 * Los filtros se arman con lo que devuelve la búsqueda: las órbitas (pista, dirección y marco) que pasan por la zona
 * con su número de pasadas, y los atajos de periodo. Busca solo al cambiar la zona o el periodo.
 */
export function Mundo({
  zona,
  onResultados,
  elegido,
  onElegir,
  onInvestigar,
}: {
  zona: { name: string; bbox: Bbox }
  onResultados: (g: GranuloMundo[]) => void
  elegido: string | null
  onElegir: (g: GranuloMundo) => void
  onInvestigar?: () => void
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const ids = { titulo: useId() }
  const [hoy] = useState(() => iso(Date.now()))
  const minimo = diaDe(INICIO_NISAR)
  const maximo = diaDe(hoy)
  const [periodo, setPeriodo] = useState<[number, number]>(() => [minimo, maximo])
  const [activas, setActivas] = useState<string[]>([])
  const [estado, setEstado] = useState<{ tipo: 'cargando' } | { tipo: 'error' } | { tipo: 'listo'; datos: Respuesta }>({ tipo: 'cargando' })
  const caja = cajaBuscable(zona.bbox)
  const clave = caja.map((v) => v.toFixed(4)).join(',')

  // Una sola consulta por zona, de la fecha más antigua posible a hoy: la línea de tiempo filtra en el navegador.
  useEffect(() => {
    let vigente = true
    setEstado({ tipo: 'cargando' })
    setActivas([])
    setPeriodo([minimo, maximo])
    const q = new URLSearchParams({ bbox: clave, from: INICIO_NISAR, to: hoy, limit: '200' })
    // Sin respuesta en 30 s se avisa en vez de quedarse cargando (prueba de uso del 2026-11-14).
    fetch(`${API_BASE}/api/catalog/search/world?${q}`, { signal: AbortSignal.timeout(30_000) })
      .then((r) => (r.ok ? (r.json() as Promise<Respuesta>) : Promise.reject(new Error(String(r.status)))))
      .then((datos) => {
        if (!vigente) return
        setEstado({ tipo: 'listo', datos })
        onResultados(datos.granules)
      })
      .catch(() => {
        if (!vigente) return
        setEstado({ tipo: 'error' })
        onResultados([])
      })
    return () => {
      vigente = false
    }
    // onResultados cambia en cada render del padre; la búsqueda depende solo de la zona.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave])

  // La pasada elegida (también con un clic en su huella del mapa) se lleva a la vista en la lista.
  useEffect(() => {
    if (!elegido) return
    const li = document.querySelector(`.mundo-lista li[data-elegido='true']`)
    if (li && typeof li.scrollIntoView === 'function') li.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [elegido])

  const granulos = useMemo(() => (estado.tipo === 'listo' ? estado.datos.granules : []), [estado])
  // Órbitas presentes en la zona, con su número de pasadas: los carriles salen de los datos, no de una lista fija.
  const series = useMemo(() => {
    const cuenta = new Map<string, { id: string; direction: string; n: number }>()
    for (const g of granulos) {
      const id = serieDe(g)
      const s = cuenta.get(id) ?? { id, direction: g.direction, n: 0 }
      s.n += 1
      cuenta.set(id, s)
    }
    return [...cuenta.values()].sort((a, b) => b.n - a.n || a.id.localeCompare(b.id))
  }, [granulos])
  // Extremo antiguo: el inicio de NISAR o la pasada más antigua encontrada, lo que sea anterior.
  const masAntigua = granulos.length ? Math.min(minimo, ...granulos.map((g) => diaDe(g.acquired_at))) : minimo
  const [desde, hasta] = [Math.max(periodo[0], masAntigua), periodo[1]]
  const visibles = granulos.filter((g) => {
    const d = diaDe(g.acquired_at)
    return d >= desde && d <= hasta && (activas.length === 0 || activas.includes(serieDe(g)))
  })

  const fecha = (d: string) =>
    new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(
      new Date(d),
    )

  return (
    <section className="mundo" aria-labelledby={ids.titulo}>
      <h2 id={ids.titulo}>{zona.name}</h2>
      <p className="muted">{t('zone.passesOnly')}</p>
      <p className="mundo-vista">
        <Icono nombre="mapa" tamano={16} />
        <span className="mundo-caja">
          {fmt(caja[0])}°, {fmt(caja[1])}° → {fmt(caja[2])}°, {fmt(caja[3])}°
        </span>
      </p>
      {onInvestigar && (
        <button type="button" className="boton-con-texto" onClick={onInvestigar}>
          <Icono nombre="interprete" tamano={16} />
          {t('zone.research')}
        </button>
      )}

      <div aria-live="polite" aria-busy={estado.tipo === 'cargando'}>
        {estado.tipo === 'cargando' && <Esqueleto etiqueta={t('world.loading')} variante="lista" filas={4} />}
        {estado.tipo === 'error' && <p role="alert">{t('world.error')}</p>}
        {estado.tipo === 'listo' && (
          <>
            <LineaPasadas
              pasadas={granulos.map((g) => ({ id: g.id, serie: serieDe(g), direction: g.direction, acquired_at: g.acquired_at }))}
              minimo={masAntigua}
              maximo={maximo}
              desde={desde}
              hasta={hasta}
              onPeriodo={(a, b) => setPeriodo([a, b])}
              series={series}
              activas={activas}
              onSeries={setActivas}
            />
            <h3 className="resultados-titulo">{t('world.results', { count: visibles.length, total: estado.datos.total })}</h3>
            {granulos.length === 0 && <p className="resultados-vacio">{t('world.none')}</p>}
            <ol className="mundo-lista">
              {visibles.map((g) => (
                <li key={g.id} data-elegido={elegido === g.id}>
                  <button type="button" className="mundo-tarjeta" aria-pressed={elegido === g.id} onClick={() => onElegir(g)}>
                    {g.thumbnail_url ? (
                      <img src={g.thumbnail_url} alt="" loading="lazy" decoding="async" />
                    ) : (
                      <span className="mundo-sin-imagen" aria-hidden="true">
                        <Icono nombre="satelite" tamano={20} />
                      </span>
                    )}
                    <span className="mundo-texto">
                      <strong>{fecha(g.acquired_at)} UTC</strong>
                      <span>
                        {serieDe(g)} · {t(`search.direction.${g.direction}`)}
                      </span>
                      <span className="muted">
                        {g.polarization} · {(g.size_mb / 1024).toFixed(1)} GB
                      </span>
                    </span>
                  </button>
                  <div className="mundo-enlaces">
                    <a href={g.vertex_url} target="_blank" rel="noopener noreferrer">
                      ASF Vertex
                      <span className="sr-solo"> ({t('world.newTab')})</span>
                    </a>
                    <a href={g.earthdata_search_url} target="_blank" rel="noopener noreferrer">
                      Earthdata Search
                      <span className="sr-solo"> ({t('world.newTab')})</span>
                    </a>
                  </div>
                </li>
              ))}
            </ol>
            <p className="aviso-sesion muted">{t('world.note')}</p>
            <p className="muted mundo-fuentes">{t('world.sources')}</p>
          </>
        )}
      </div>
    </section>
  )
}
