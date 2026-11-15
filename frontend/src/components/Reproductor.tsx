import { useTranslation } from 'react-i18next'
import type { Verdict } from '../api/client'
import { BotonIcono } from './Iconos'
import { Marca } from './Marca'

/** Milisegundos de un día, para situar cada par en la línea de la historia. */
const DIA = 86_400_000

function tiempo(fecha: string): number {
  return Date.parse(`${fecha}T00:00:00Z`)
}

/**
 * Reproducción de una historia de la comunidad (T-FAR-21, RF-INT-30): línea de tiempo con un tramo por par,
 * el actual marcado, y los controles para pausar, ir al anterior o al siguiente y cerrar. Cada tramo es un
 * botón que salta a su par. Los textos salen del veredicto de la API, sin añadir nada.
 */
export function Reproductor({
  titulo,
  pares,
  indice,
  enMarcha,
  onIr,
  onAlternar,
  onCerrar,
}: {
  titulo: string
  pares: Verdict[]
  indice: number
  enMarcha: boolean
  onIr: (i: number) => void
  onAlternar: () => void
  onCerrar: () => void
}) {
  const { t } = useTranslation()
  if (pares.length === 0) return null
  const actual = pares[Math.min(indice, pares.length - 1)]
  const inicio = Math.min(...pares.map((v) => tiempo(v.from_date)))
  const fin = Math.max(...pares.map((v) => tiempo(v.to_date)))
  const total = Math.max(fin - inicio, DIA)
  const pos = (fecha: string) => ((tiempo(fecha) - inicio) / total) * 100

  return (
    <section className="reproductor vidrio" aria-labelledby="reproductor-titulo">
      <div className="reproductor-cabecera">
        <h2 id="reproductor-titulo">{titulo}</h2>
        <p className="muted" aria-live="polite">
          {t('player.position', { n: Math.min(indice, pares.length - 1) + 1, total: pares.length })}
        </p>
        <div className="reproductor-controles">
          <BotonIcono icono="anterior" etiqueta={t('player.previous')} disabled={indice <= 0} onClick={() => onIr(indice - 1)} />
          <BotonIcono
            icono={enMarcha ? 'pausa' : 'reproducir'}
            etiqueta={t(enMarcha ? 'player.pause' : 'player.play')}
            className="boton-principal"
            onClick={onAlternar}
          />
          <BotonIcono
            icono="siguiente"
            etiqueta={t('player.next')}
            disabled={indice >= pares.length - 1}
            onClick={() => onIr(indice + 1)}
          />
          <BotonIcono icono="cerrar" etiqueta={t('player.close')} onClick={onCerrar} />
        </div>
      </div>
      <ol className="reproductor-linea" aria-label={t('player.timeline')}>
        {pares.map((v, i) => {
          const izq = pos(v.from_date)
          const ancho = Math.max(pos(v.to_date) - izq, 1.5)
          return (
            <li key={`${v.series}/${v.id}`} style={{ left: `${izq}%`, width: `${ancho}%` }}>
              <button
                type="button"
                className="reproductor-tramo"
                aria-current={i === indice ? 'step' : undefined}
                aria-label={`${v.from_date} → ${v.to_date}: ${t(`verdict.state.${v.state}`)}`}
                title={`${v.from_date} → ${v.to_date}: ${t(`verdict.state.${v.state}`)}`}
                onClick={() => onIr(i)}
              >
                <Marca estado={v.state} />
              </button>
            </li>
          )
        })}
      </ol>
      <p className="reproductor-actual">
        <Marca estado={actual.state} />
        <strong>{t(`verdict.state.${actual.state}`)}</strong>
        <span className="muted">
          {actual.from_date} → {actual.to_date} · {actual.series}
        </span>
      </p>
    </section>
  )
}
