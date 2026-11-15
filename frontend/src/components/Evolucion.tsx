import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import type { SeriesInfo, Verdict } from '../api/client'
import { claveVeredicto, type Filtro } from '../comunidad/historias'

const DIA = 86_400_000
const ms = (d: string) => Date.parse(`${d}T00:00:00Z`)

const ANCHO = 300
const ALTO = 132
const IZQ = 6
const DER = 6
const ARRIBA = 18
const ABAJO = 22

function porcentaje(x: number, lang: string) {
  const s = (x * 100).toFixed(x * 100 >= 10 ? 0 : 1)
  return `${lang === 'es' ? s.replace('.', ',') : s} %`
}

/**
 * Evolución del cambio en el tiempo (rediseño del 2026-11-14): una barra por par de pasadas seguidas, tan alta
 * como su fracción de cambio (`evidence.changed_fraction`), con el umbral de decisión como línea discontinua.
 * Los pares con cambio probable son picos que brillan y llevan su cifra; los no observables, una trama baja.
 * Encima, un deslizador de dos asas elige el periodo saltando de pasada en pasada, y tocar una barra abre ese
 * par en el mapa. Las asas son `input type=range` reales: teclado y lector de pantalla incluidos.
 */
export function Evolucion({
  series,
  todos,
  filtro,
  onFiltro,
  seleccion,
  onSeleccionar,
}: {
  series: SeriesInfo[]
  todos: Verdict[]
  filtro: Filtro
  onFiltro: (f: Filtro) => void
  seleccion: string | undefined
  onSeleccionar: (v: Verdict) => void
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const id = useId()
  const visibles = series.filter((s) => filtro.series === 'all' || filtro.series === s.id)
  const fechas = [...new Set(visibles.flatMap((s) => s.dates))].sort()
  if (fechas.length < 2) return null

  const ini = ms(fechas[0])
  const fin = ms(fechas.at(-1)!)
  const x = (d: string) => IZQ + ((ms(d) - ini) / Math.max(fin - ini, DIA)) * (ANCHO - IZQ - DER)
  const base = ALTO - ABAJO

  const pares = todos.filter(
    (v) => v.kind === 'consecutive' && (filtro.series === 'all' || v.series === filtro.series),
  )
  const umbral = pares.find((v) => v.evidence?.decision_rule)?.evidence.decision_rule.min_changed_fraction ?? null
  const maximo = Math.max(umbral ? umbral * 1.6 : 0, ...pares.map((v) => v.evidence?.changed_fraction ?? 0), 0.01)
  const y = (f: number) => base - (f / maximo) * (base - ARRIBA)

  // Asas del periodo: índices de pasada. Sin fecha en el filtro, el extremo de los datos.
  const iDesde = filtro.desde ? Math.max(0, fechas.findIndex((d) => d >= filtro.desde)) : 0
  let iHastaEncontrado = fechas.length - 1
  if (filtro.hasta) {
    iHastaEncontrado = -1
    fechas.forEach((d, i) => {
      if (d <= filtro.hasta) iHastaEncontrado = i
    })
  }
  const iHasta = iHastaEncontrado < 0 ? fechas.length - 1 : iHastaEncontrado
  const desde = fechas[iDesde]
  const hasta = fechas[iHasta]
  const fijar = (a: number, b: number) =>
    onFiltro({
      ...filtro,
      desde: a <= 0 ? '' : fechas[a],
      hasta: b >= fechas.length - 1 ? '' : fechas[b],
    })

  // La línea de evolución une la cima de cada barra por su punto medio.
  const puntos = [...pares]
    .sort((a, b) => a.from_date.localeCompare(b.from_date))
    .map((v) => `${((x(v.from_date) + x(v.to_date)) / 2).toFixed(1)},${y(v.evidence?.changed_fraction ?? 0).toFixed(1)}`)

  const fecha = (d: string) =>
    new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(ms(d)))

  return (
    <div className="evolucion">
      <svg className="evolucion-grafica" viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-labelledby={`${id}-desc`}>
        <desc id={`${id}-desc`}>{t('search.chartDesc', { count: pares.filter((v) => v.state === 'change_probable').length })}</desc>
        <defs>
          <pattern id={`${id}-trama`} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="4" stroke="#ffffff" strokeWidth="1.4" />
          </pattern>
          <linearGradient id={`${id}-area`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.32" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
          <filter id={`${id}-brillo`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Fuera del periodo, velo oscuro. */}
        <rect className="evolucion-fuera" x={0} y={ARRIBA - 8} width={Math.max(0, x(desde))} height={base - ARRIBA + 8} />
        <rect className="evolucion-fuera" x={x(hasta)} y={ARRIBA - 8} width={Math.max(0, ANCHO - x(hasta))} height={base - ARRIBA + 8} />

        {/* Área bajo la línea de evolución */}
        {puntos.length > 1 && (
          <>
            <polygon
              points={`${puntos[0].split(',')[0]},${base} ${puntos.join(' ')} ${puntos.at(-1)!.split(',')[0]},${base}`}
              fill={`url(#${id}-area)`}
            />
            <polyline className="evolucion-linea" points={puntos.join(' ')} />
          </>
        )}

        {/* Umbral de decisión */}
        {umbral !== null && (
          <g className="evolucion-umbral">
            <line x1={IZQ} x2={ANCHO - DER} y1={y(umbral)} y2={y(umbral)} />
            <text x={ANCHO - DER} y={y(umbral) - 3} textAnchor="end">
              {t('search.threshold', { value: porcentaje(umbral, lang) })}
            </text>
          </g>
        )}

        {/* Barras: una por par consecutivo */}
        {pares.map((v) => {
          const f = v.evidence?.changed_fraction ?? 0
          const x0 = x(v.from_date) + 1.2
          const ancho = Math.max(2.5, x(v.to_date) - x(v.from_date) - 2.4)
          const dentro = v.from_date >= desde && v.to_date <= hasta
          const clave = claveVeredicto(v)
          const pico = v.state === 'change_probable'
          const alto = v.state === 'not_observable' ? 6 : Math.max(2, base - y(f))
          return (
            <g
              key={clave}
              className={`evolucion-barra estado-${v.state}`}
              data-dentro={dentro}
              data-elegida={seleccion === clave}
              onClick={() => onSeleccionar(v)}
            >
              <title>
                {`${v.from_date} → ${v.to_date} · ${v.series} · ${t(`verdict.state.${v.state}`)}${
                  v.state === 'not_observable' ? '' : ` · ${porcentaje(f, lang)}`
                }`}
              </title>
              <rect
                x={x0}
                y={base - alto}
                width={ancho}
                height={alto}
                rx={1.5}
                fill={v.state === 'not_observable' ? `url(#${id}-trama)` : pico ? '#ffffff' : 'rgba(255,255,255,0.12)'}
                stroke="#ffffff"
                strokeWidth={pico ? 0 : 1}
                filter={pico ? `url(#${id}-brillo)` : undefined}
              />
              {pico && (
                <>
                  <circle className="evolucion-pico" cx={x0 + ancho / 2} cy={base - alto} r={3} />
                  <text className="evolucion-cifra" x={x0 + ancho / 2} y={base - alto - 6} textAnchor="middle">
                    {porcentaje(f, lang)}
                  </text>
                </>
              )}
            </g>
          )
        })}

        {/* Pasadas sobre el eje */}
        <line className="evolucion-eje" x1={IZQ} x2={ANCHO - DER} y1={base} y2={base} />
        {fechas.map((d) => (
          <circle key={d} className="evolucion-pasada" data-dentro={d >= desde && d <= hasta} cx={x(d)} cy={base} r={1.8} />
        ))}
        <text className="evolucion-etiqueta" x={IZQ} y={ALTO - 6}>
          {fecha(fechas[0])}
        </text>
        <text className="evolucion-etiqueta" x={ANCHO - DER} y={ALTO - 6} textAnchor="end">
          {fecha(fechas.at(-1)!)}
        </text>
      </svg>

      {/* Deslizador de dos asas, alineado con el eje de la gráfica. */}
      <div className="evolucion-deslizador" style={{ ['--izq' as string]: `${(x(desde) / ANCHO) * 100}%`, ['--der' as string]: `${(x(hasta) / ANCHO) * 100}%` }}>
        <span className="evolucion-tramo" aria-hidden="true" />
        <input
          type="range"
          min={0}
          max={fechas.length - 1}
          step={1}
          value={iDesde}
          aria-label={t('search.periodStart')}
          aria-valuetext={desde}
          onChange={(e) => fijar(Math.min(Number(e.target.value), iHasta - 1), iHasta)}
        />
        <input
          type="range"
          min={0}
          max={fechas.length - 1}
          step={1}
          value={iHasta}
          aria-label={t('search.periodEnd')}
          aria-valuetext={hasta}
          onChange={(e) => fijar(iDesde, Math.max(Number(e.target.value), iDesde + 1))}
        />
      </div>
      <p className="evolucion-rango" aria-live="polite">
        <span>{fecha(desde)}</span>
        <span aria-hidden="true">→</span>
        <span>{fecha(hasta)}</span>
      </p>
      <ul className="evolucion-leyenda" aria-hidden="true">
        <li>
          <span className="muestra muestra-pico" />
          {t('verdict.state.change_probable')}
        </li>
        <li>
          <span className="muestra muestra-sin" />
          {t('verdict.state.no_detectable_change')}
        </li>
        <li>
          <span className="muestra muestra-trama" />
          {t('verdict.state.not_observable')}
        </li>
      </ul>
    </div>
  )
}
