import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Verdict } from '../api/client'
import {
  NOTAS_MAX,
  PARES_MAX,
  TITULO_MAX,
  TITULO_MIN,
  claveVeredicto,
  clavePar,
  recuento,
  type Filtro,
  type Historia,
  type HistoriaNueva,
} from '../comunidad/historias'
import { useSesion } from '../sesion/sesion'
import { BotonIcono } from './Iconos'
import { Marca } from './Marca'

/** Un par del borrador: estado, fechas y los tres textos de la API, tal cual. */
function ParTexto({ v }: { v: Verdict }) {
  const { t } = useTranslation()
  return (
    <>
      <span className="par-cabecera">
        <Marca estado={v.state} />
        <strong>{t(`verdict.state.${v.state}`)}</strong>
        <span className="muted">
          {v.from_date} → {v.to_date} · {v.series}
        </span>
      </span>
      <details className="par-mas">
        <summary>{t('interpreter.readTexts')}</summary>
        <dl>
          <dt>{t('verdict.detected')}</dt>
          <dd>{v.summary.detected}</dd>
          <dt>{t('verdict.doesNotProve')}</dt>
          <dd>{v.summary.does_not_prove}</dd>
          <dt>{t('verdict.missing')}</dt>
          <dd>{v.summary.missing}</dd>
        </dl>
      </details>
    </>
  )
}

/** Frase de resumen hecha con los recuentos: no añade nada que la API no diga. */
function Resumen({ pares }: { pares: Verdict[] }) {
  const { t } = useTranslation()
  const r = recuento(pares)
  return (
    <p className="interprete-resumen">
      {t('interpreter.summary', {
        count: pares.length,
        change: r.change_probable,
        nochange: r.no_detectable_change,
        notobs: r.not_observable,
      })}
    </p>
  )
}

/** Avisos de sesión para guardar y descargar. */
function AvisoSesion() {
  const { t } = useTranslation()
  const { sesion } = useSesion()
  if (sesion.estado === 'abierta') return null
  return (
    <p className="aviso-sesion muted">
      {sesion.estado === 'apagado' ? t('session.off') : t('interpreter.loginToSave')}
    </p>
  )
}

/**
 * Intérprete de historias: arma un borrador con los veredictos del buscador (los textos son los de la API) y deja
 * añadir notas propias, que se guardan aparte y rotuladas como de quien escribe (RF-ACC-13 y 16).
 */
export function Interprete({
  aoi,
  nombreZona,
  filtro,
  resultados,
  abierta,
  todos,
  onCerrar,
  onGuardar,
  onDescargar,
  onReproducir,
}: {
  aoi: string
  /** Nombre legible de la zona para el título por omisión; si falta, su id. */
  nombreZona?: string
  filtro: Filtro
  resultados: Verdict[]
  /** Historia guardada que se está leyendo; sin ella, el borrador. */
  abierta: Historia | null
  todos: Map<string, Verdict>
  onCerrar: () => void
  onGuardar: (h: HistoriaNueva) => Promise<string | null>
  onDescargar: (h: HistoriaNueva | Historia, pares: Verdict[]) => Promise<void>
  /** Reproduce la historia abierta en el mapa, par a par (T-FAR-21, RF-INT-30). */
  onReproducir?: (pares: Verdict[]) => void
}) {
  const { t } = useTranslation()
  const { sesion } = useSesion()
  const ids = { titulo: useId(), notas: useId(), notasAyuda: useId() }
  const [titulo, setTitulo] = useState('')
  const [notas, setNotas] = useState('')
  const [fuera, setFuera] = useState<Set<string>>(new Set())
  const [estado, setEstado] = useState<{ tipo: 'ok' | 'error'; texto: string } | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const conSesion = sesion.estado === 'abierta'

  if (abierta) {
    const pares = abierta.pairs.map((p) => ({ p, v: todos.get(clavePar(p.series, p.pair)) }))
    const encontrados = pares.flatMap(({ v }) => (v ? [v] : []))
    return (
      <section className="interprete" aria-labelledby="interprete-abierta">
        <p className="interprete-etiqueta muted">{t('interpreter.reading')}</p>
        <h3 id="interprete-abierta">{abierta.title}</h3>
        <p className="muted">
          <strong className="autoria">{abierta.author_alias}</strong>
          {' · '}
          {t('community.meta', {
            role: t(`community.role.${abierta.author_role}`),
            from: abierta.from_date,
            to: abierta.to_date,
          })}
        </p>
        {abierta.aoi !== aoi && <p role="alert">{t('interpreter.otherZone', { aoi: abierta.aoi })}</p>}
        <Resumen pares={encontrados} />
        <ol className="interprete-pares">
          {pares.map(({ p, v }) => (
            <li key={clavePar(p.series, p.pair)}>
              {v ? <ParTexto v={v} /> : <span className="muted">{t('interpreter.missingPair', { pair: `${p.series} ${p.pair}` })}</span>}
            </li>
          ))}
        </ol>
        <section className="notas-autoria" aria-labelledby="notas-abierta">
          <h4 id="notas-abierta">{t('interpreter.authorNotes')}</h4>
          <p className="muted">{t('interpreter.notesDisclaimer')}</p>
          <blockquote>{abierta.notes || t('community.file.noNotes')}</blockquote>
        </section>
        <div className="acciones">
          {onReproducir && encontrados.length > 0 && (
            <BotonIcono
              icono="reproducir"
              etiqueta={t('player.playStory')}
              className="boton-principal"
              onClick={() => onReproducir(encontrados)}
            />
          )}
          <BotonIcono
            icono="descargar"
            etiqueta={t('community.download')}
            className="boton-principal"
            disabled={ocupado}
            onClick={async () => {
              setOcupado(true)
              await onDescargar(abierta, encontrados)
              setOcupado(false)
            }}
          />
          <BotonIcono icono="volver" etiqueta={t('interpreter.backToDraft')} onClick={onCerrar} />
        </div>
        <AvisoSesion />
      </section>
    )
  }

  const incluidos = resultados.filter((v) => !fuera.has(claveVeredicto(v)))
  const tituloAuto = t('interpreter.defaultTitle', {
    zone: nombreZona ?? aoi,
    series: filtro.series === 'all' ? t('search.allSeries') : filtro.series,
    from: filtro.desde || resultados[0]?.from_date || '…',
    to: filtro.hasta || resultados.at(-1)?.to_date || '…',
  })
  const tituloFinal = (titulo.trim() || tituloAuto).slice(0, TITULO_MAX)
  const demasiados = incluidos.length > PARES_MAX
  const vacio = incluidos.length === 0
  const borrador = (): HistoriaNueva => ({
    title: tituloFinal,
    aoi,
    series: filtro.series,
    from_date: filtro.desde || incluidos[0]?.from_date || '',
    to_date: filtro.hasta || incluidos.at(-1)?.to_date || '',
    pairs: incluidos.map((v) => ({ series: v.series, pair: v.id })),
    notes: notas.trim(),
  })

  return (
    <section className="interprete" aria-labelledby="interprete-titulo">
      <h3 id="interprete-titulo" className="sr-solo">
        {t('interpreter.heading')}
      </h3>
      <p className="muted interprete-intro">{t('interpreter.intro')}</p>
      <div className="campo">
        <label htmlFor={ids.titulo}>{t('interpreter.title')}</label>
        <input
          id={ids.titulo}
          type="text"
          value={titulo}
          maxLength={TITULO_MAX}
          placeholder={tituloAuto}
          onChange={(e) => setTitulo(e.target.value)}
        />
      </div>

      <h4 className="interprete-sub">{t('interpreter.fromApi')}</h4>
      {vacio ? <p>{t('interpreter.empty')}</p> : <Resumen pares={incluidos} />}
      {demasiados && <p role="alert">{t('interpreter.tooMany', { max: PARES_MAX, count: incluidos.length })}</p>}
      <ol className="interprete-pares">
        {resultados.map((v) => {
          const clave = claveVeredicto(v)
          return (
            <li key={clave} className={fuera.has(clave) ? 'fuera' : undefined}>
              <label className="casilla">
                <input
                  type="checkbox"
                  checked={!fuera.has(clave)}
                  onChange={(e) => {
                    const sig = new Set(fuera)
                    if (e.target.checked) sig.delete(clave)
                    else sig.add(clave)
                    setFuera(sig)
                  }}
                />
                <span className="sr-solo">{t('interpreter.include', { from: v.from_date, to: v.to_date, series: v.series })}</span>
              </label>
              <div>
                <ParTexto v={v} />
              </div>
            </li>
          )
        })}
      </ol>

      <div className="campo">
        <label htmlFor={ids.notas}>{t('interpreter.notes')}</label>
        <textarea
          id={ids.notas}
          rows={4}
          maxLength={NOTAS_MAX}
          value={notas}
          aria-describedby={ids.notasAyuda}
          onChange={(e) => setNotas(e.target.value)}
        />
        <p id={ids.notasAyuda} className="muted ayuda">
          {t('interpreter.notesHelp', { n: notas.length, max: NOTAS_MAX })}
        </p>
      </div>

      <div className="acciones">
        <BotonIcono
          icono="guardar"
          etiqueta={t('interpreter.save')}
          className="boton-principal"
          disabled={!conSesion || vacio || demasiados || tituloFinal.length < TITULO_MIN || ocupado}
          onClick={async () => {
            setOcupado(true)
            const error = await onGuardar(borrador())
            setOcupado(false)
            setEstado(error ? { tipo: 'error', texto: error } : { tipo: 'ok', texto: t('interpreter.saved') })
            if (!error) {
              setTitulo('')
              setNotas('')
            }
          }}
        />
        <BotonIcono
          icono="descargar"
          etiqueta={t('community.download')}
          disabled={vacio || ocupado}
          onClick={async () => {
            setOcupado(true)
            await onDescargar(borrador(), incluidos)
            setOcupado(false)
          }}
        />
      </div>
      {estado && (
        <p role={estado.tipo === 'error' ? 'alert' : 'status'} className={estado.tipo === 'error' ? undefined : 'muted'}>
          {estado.texto}
        </p>
      )}
      <AvisoSesion />
    </section>
  )
}
