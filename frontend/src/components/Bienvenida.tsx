import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Icono } from './Iconos'

/**
 * Mensaje de bienvenida de la primera visita (2026-11-15). Sustituye a abrir el portal entero, que ponía «Tu cuenta»
 * en primer plano y parecía un registro obligatorio: aquí se dice qué es GeoLatido y que no hace falta cuenta.
 * «Conocer más» abre el portal en Inicio.
 */
export function Bienvenida({ onCerrar, onConocerMas }: { onCerrar: () => void; onConocerMas: () => void }) {
  const { t } = useTranslation()
  const dialogo = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const d = dialogo.current
    if (!d || d.open) return
    if (typeof d.showModal === 'function') d.showModal()
    else d.setAttribute('open', '')
  }, [])

  return (
    <dialog
      ref={dialogo}
      className="bienvenida"
      aria-labelledby="bienvenida-titulo"
      aria-describedby="bienvenida-texto"
      onCancel={(e) => {
        e.preventDefault()
        onCerrar()
      }}
    >
      <div className="bienvenida-ventana vidrio">
        <p className="bienvenida-marca" aria-hidden="true">
          <Icono nombre="satelite" tamano={22} />
        </p>
        <h2 id="bienvenida-titulo">{t('welcome.title')}</h2>
        <p id="bienvenida-texto">{t('welcome.text')}</p>
        <p className="bienvenida-nota">{t('welcome.noAccount')}</p>
        <div className="bienvenida-acciones">
          <button type="button" className="boton-principal" onClick={onCerrar} autoFocus>
            <Icono nombre="mapa" tamano={18} /> {t('welcome.start')}
          </button>
          <button type="button" onClick={onConocerMas}>
            <Icono nombre="info" tamano={18} /> {t('welcome.more')}
          </button>
        </div>
      </div>
    </dialog>
  )
}
