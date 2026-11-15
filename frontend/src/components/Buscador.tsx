import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { SeriesInfo, Verdict } from '../api/client'
import { ESTADOS, claveVeredicto, type Filtro } from '../comunidad/historias'
import { Esqueleto } from './Esqueleto'
import { Evolucion } from './Evolucion'
import { Icono } from './Iconos'
import { Marca } from './Marca'

const DIA = 86_400_000
const ms = (d: string) => Date.parse(`${d}T00:00:00Z`)
const iso = (t: number) => new Date(t).toISOString().slice(0, 10)

/** Filtro de partida: todo a la vista. También es lo que deja «Limpiar filtros». */
const FILTRO_INICIAL: Filtro = { series: 'all', desde: '', hasta: '', estados: [...ESTADOS], ventanas: false }

const esInicial = (f: Filtro) =>
  f.series === 'all' && !f.desde && !f.hasta && f.estados.length === ESTADOS.length && !f.ventanas

/** «T048A-F015» → pista 048 y dirección ascendente (A) o descendente (D). */
function describirSerie(id: string): { pista: string; direccion: 'A' | 'D' | null } {
  const m = id.match(/^T(\d+)([AD])/)
  return m ? { pista: `T${m[1]}`, direccion: m[2] as 'A' | 'D' } : { pista: id, direccion: null }
}

/** Fecha corta y legible en el idioma de la app: «16 ago 2026». Siempre en UTC, como las pasadas. */
function fechaCorta(d: string, lang: string, conAnio = true) {
  return new Intl.DateTimeFormat(lang, {
    day: 'numeric',
    month: 'short',
    year: conAnio ? 'numeric' : undefined,
    timeZone: 'UTC',
  }).format(new Date(ms(d)))
}

/** «2026-10» → «octubre de 2026», en el idioma de la app. */
function nombreMes(mes: string, lang: string) {
  return new Intl.DateTimeFormat(lang, { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${mes}-15T00:00:00Z`))
}

/**
 * Panel de Filtros (rediseño del 2026-11-14): tres pasos numerados en lenguaje llano (qué satélite, cuándo y qué
 * buscar) con botones grandes en lugar de listas desplegables, atajos de periodo y la lista de resultados con
 * fechas legibles. Todo se ve igual con o sin sesión.
 */
export function Buscador({
  series,
  todos,
  filtro,
  onFiltro,
  resultados,
  seleccion,
  onSeleccionar,
  cargando,
  error,
}: {
  series: SeriesInfo[]
  /** Todos los veredictos de la zona, sin filtrar: la gráfica de evolución los necesita para dar contexto. */
  todos: Verdict[]
  filtro: Filtro
  onFiltro: (f: Filtro) => void
  resultados: Verdict[]
  seleccion: string | undefined
  onSeleccionar: (v: Verdict) => void
  cargando: boolean
  error: boolean
  /** Ya no se usa: el panel enseña todo con o sin sesión. Se acepta para no romper a quien lo pase. */
  plegarAvanzado?: boolean
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const ids = { desde: useId(), hasta: useId(), titulo: useId(), serie: useId(), periodo: useId(), estados: useId() }
  const todas = series.flatMap((s) => s.dates).sort()
  const min = todas[0]
  const max = todas.at(-1)
  const cambiar = (parcial: Partial<Filtro>) => onFiltro({ ...filtro, ...parcial })
  // Grupos plegables del historial: por mes de la fecha final, en el orden en que llegan los resultados.
  const [abiertos, setAbiertos] = useState<Set<string>>(() => new Set())
  const [cerrados, setCerrados] = useState<Set<string>>(() => new Set())
  const grupos = [...resultados.reduce((m, v) => m.set(v.to_date.slice(0, 7), [...(m.get(v.to_date.slice(0, 7)) ?? []), v]), new Map<string, Verdict[]>())]
  // Las fechas van de la muestra más antigua a la más reciente: lo que se escriba fuera se ajusta a ese rango, y
  // con el periodo completo («Todo») los campos muestran esos dos extremos en vez de quedar vacíos.
  const ajustar = (v: string) => (!v ? v : min && v < min ? min : max && v > max ? max : v)

  // Atajos de periodo, contados desde la última pasada (no desde hoy: los datos acaban donde acaban).
  const atajos = max
    ? [
        { clave: 'all', desde: '', hasta: '' },
        { clave: 'last30', desde: iso(ms(max) - 30 * DIA), hasta: '' },
        { clave: 'last90', desde: iso(ms(max) - 90 * DIA), hasta: '' },
      ]
    : []
  const atajoActivo = atajos.find((a) => a.desde === filtro.desde && a.hasta === filtro.hasta)?.clave

  return (
    <section className="buscador" aria-labelledby={ids.titulo}>
      <h2 id={ids.titulo} className="sr-solo">
        {t('search.heading')}
      </h2>
      <p className="buscador-ayuda">
        <Icono nombre="info" tamano={16} />
        <span>{t('search.help')}</span>
      </p>

      {/* 1. Qué satélite: la serie de pasadas ascendentes o la de descendentes sobre la zona. */}
      <fieldset className="paso" aria-describedby={ids.serie}>
        <legend>
          <span className="paso-numero" aria-hidden="true">1</span>
          {t('picker.series')}
        </legend>
        <p id={ids.serie} className="paso-ayuda">
          {t('search.seriesHelp', { count: series.length })}
        </p>
        <div className="chips">
          <label className="chip">
            <input type="radio" name={`${ids.titulo}-serie`} checked={filtro.series === 'all'} onChange={() => cambiar({ series: 'all' })} />
            <span>{t('search.allShort')}</span>
          </label>
          {series.map((s) => {
            const { pista, direccion } = describirSerie(s.id)
            return (
              <label key={s.id} className="chip" title={s.id}>
                <input type="radio" name={`${ids.titulo}-serie`} checked={filtro.series === s.id} onChange={() => cambiar({ series: s.id })} />
                <span>
                  {direccion && (
                    <span aria-hidden="true" className="chip-flecha">
                      {direccion === 'A' ? '↗' : '↘'}
                    </span>
                  )}
                  {pista}
                  {direccion && <span className="chip-detalle"> · {t(`search.direction.${direccion}`)}</span>}
                  <span className="sr-solo">
                    {' '}
                    ({s.id}, {t(`dataKind.${s.data_kind}`)})
                  </span>
                </span>
              </label>
            )
          })}
        </div>
      </fieldset>

      {/* 2. Cuándo: atajos, la gráfica de evolución con su deslizador y las fechas exactas. */}
      <fieldset className="paso" aria-describedby={ids.periodo}>
        <legend>
          <span className="paso-numero" aria-hidden="true">2</span>
          {t('search.timeline')}
        </legend>
        <p id={ids.periodo} className="paso-ayuda">
          {t('search.periodHelp')}
        </p>
        <div className="chips" role="group" aria-label={t('search.shortcuts')}>
          {atajos.map((a) => (
            <button
              key={a.clave}
              type="button"
              className="chip"
              aria-pressed={atajoActivo === a.clave}
              onClick={() => cambiar({ desde: a.desde, hasta: a.hasta })}
            >
              {t(`search.shortcut.${a.clave}`)}
            </button>
          ))}
        </div>
        <Evolucion
          series={series}
          todos={todos}
          filtro={filtro}
          onFiltro={onFiltro}
          seleccion={seleccion}
          onSeleccionar={onSeleccionar}
        />
        <div className="rango-campos">
          <div className="campo">
            <label htmlFor={ids.desde}>{t('search.from')}</label>
            <input
              id={ids.desde}
              type="date"
              min={min}
              max={filtro.hasta || max}
              value={filtro.desde || min || ''}
              onChange={(e) => cambiar({ desde: ajustar(e.target.value) === min ? '' : ajustar(e.target.value) })}
            />
          </div>
          <div className="campo">
            <label htmlFor={ids.hasta}>{t('search.to')}</label>
            <input
              id={ids.hasta}
              type="date"
              min={filtro.desde || min}
              max={max}
              value={filtro.hasta || max || ''}
              onChange={(e) => cambiar({ hasta: ajustar(e.target.value) === max ? '' : ajustar(e.target.value) })}
            />
          </div>
        </div>
      </fieldset>

      {/* 3. Qué buscar: los tres estados, con su forma, y las ventanas completas. */}
      <fieldset className="paso buscador-estados" aria-describedby={ids.estados}>
        <legend>
          <span className="paso-numero" aria-hidden="true">3</span>
          {t('search.states')}
        </legend>
        <p id={ids.estados} className="paso-ayuda">
          {t('search.statesHelp')}
        </p>
        <div className="chips chips-columna">
          {ESTADOS.map((e) => (
            <label key={e} className="chip chip-estado">
              <input
                type="checkbox"
                checked={filtro.estados.includes(e)}
                onChange={(ev) =>
                  cambiar({ estados: ev.target.checked ? [...filtro.estados, e] : filtro.estados.filter((x) => x !== e) })
                }
              />
              <Marca estado={e} />
              <span>{t(`verdict.state.${e}`)}</span>
            </label>
          ))}
        </div>
        <label className="interruptor">
          <input type="checkbox" role="switch" checked={filtro.ventanas} onChange={(ev) => cambiar({ ventanas: ev.target.checked })} />
          <span className="interruptor-pista" aria-hidden="true" />
          <span className="interruptor-texto">
            {t('search.fullWindows')}
            <small>{t('search.fullWindowsHelp')}</small>
          </span>
        </label>
      </fieldset>

      <div className="resultados" aria-busy={cargando}>
        <div className="resultados-cabecera">
          <h3 className="resultados-titulo" aria-live="polite">
            {t('search.results', { count: resultados.length })}
          </h3>
          {!esInicial(filtro) && (
            <button type="button" className="chip chip-limpiar" onClick={() => onFiltro({ ...FILTRO_INICIAL, estados: [...ESTADOS] })}>
              <Icono nombre="volver" tamano={14} />
              {t('search.reset')}
            </button>
          )}
        </div>
        {!cargando && !error && resultados.length > 0 && <p className="paso-ayuda">{t('search.pickHelp')}</p>}
        {cargando && <Esqueleto etiqueta={t('picker.loading')} variante="lista" filas={6} />}
        {error && <p role="alert">{t('picker.error')}</p>}
        {!cargando && !error && resultados.length === 0 && <p className="resultados-vacio">{t('search.none')}</p>}
        {/* El historial de hallazgos, plegado por mes (2026-11-15): una lista larga entorpecía llegar al resto del
            panel. Queda abierto el mes del hallazgo elegido; los demás se abren con un clic. */}
        {grupos.map(([mes, lista]) => {
          const cambios = lista.filter((v) => v.state === 'change_probable').length
          const abierto = abiertos.has(mes) || (!cerrados.has(mes) && lista.some((v) => claveVeredicto(v) === seleccion))
          return (
            <details
              key={mes}
              className="resultados-grupo"
              open={abierto}
              onToggle={(e) => {
                const ahora = (e.currentTarget as HTMLDetailsElement).open
                if (ahora === abierto) return
                setAbiertos((s) => {
                  const n = new Set(s)
                  if (ahora) n.add(mes)
                  else n.delete(mes)
                  return n
                })
                setCerrados((s) => {
                  const n = new Set(s)
                  if (ahora) n.delete(mes)
                  else n.add(mes)
                  return n
                })
              }}
            >
              <summary>
                <span className="resultados-grupo-mes">{nombreMes(mes, lang)}</span>
                <span className="resultados-grupo-meta">
                  {t('search.groupCount', { count: lista.length })}
                  {cambios ? ` · ${t('search.groupChanges', { count: cambios })}` : ''}
                </span>
              </summary>
              <ol className="resultados-lista">
                {lista.map((v) => {
                  const clave = claveVeredicto(v)
                  const dias = Math.round((ms(v.to_date) - ms(v.from_date)) / DIA)
                  const mismoAnio = v.from_date.slice(0, 4) === v.to_date.slice(0, 4)
                  return (
                    <li key={clave}>
                      <button type="button" aria-pressed={seleccion === clave} onClick={() => onSeleccionar(v)}>
                        <Marca estado={v.state} />
                        <span className="resultado-texto">
                          <span className="resultado-estado">{t(`verdict.state.${v.state}`)}</span>
                          <span className="resultado-fechas">
                            {fechaCorta(v.from_date, lang, !mismoAnio)} → {fechaCorta(v.to_date, lang)}
                            <span className="sr-solo">
                              {' '}
                              ({v.from_date} → {v.to_date})
                            </span>
                          </span>
                          <span className="resultado-meta">
                            {describirSerie(v.series).pista} · {t('search.days', { count: dias })}
                            {v.kind === 'full_window' ? ` · ${t('picker.fullWindow')}` : ''}
                          </span>
                        </span>
                        <Icono nombre="siguiente" tamano={16} />
                      </button>
                    </li>
                  )
                })}
              </ol>
            </details>
          )
        })}
      </div>
    </section>
  )
}
