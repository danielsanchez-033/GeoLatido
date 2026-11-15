import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useSesion, type Perfil } from '../sesion/sesion'
import { BotonIcono, Icono } from './Iconos'

/** Abre el diálogo como modal; sin `showModal` (navegadores viejos, jsdom), como no modal. */
function abrir(d: HTMLDialogElement | null) {
  if (!d) return
  if (typeof d.showModal === 'function') d.showModal()
  else d.setAttribute('open', '')
}

function cerrar(d: HTMLDialogElement | null) {
  if (!d) return
  if (typeof d.close === 'function') d.close()
  else d.removeAttribute('open')
}

/**
 * Icono de la cuenta (RF-INT-06 y RF-INT-02). Sin sesión abre el formulario para entrar o crear cuenta; con
 * sesión enseña el perfil declarado, que decide la vista, y el botón de salir. Con AUTH_ENABLED=0 explica que
 * el acceso está apagado en esta pila.
 */
export function SesionBoton() {
  const { t } = useTranslation()
  const { sesion, entrar, registrar, salir } = useSesion()
  const dialogo = useRef<HTMLDialogElement>(null)
  const ids = { correo: useId(), clave: useId(), perfil: useId(), titulo: useId() }
  const [modo, setModo] = useState<'entrar' | 'registrar'>('entrar')
  const [correo, setCorreo] = useState('')
  const [clave, setClave] = useState('')
  const [perfil, setPerfil] = useState<Perfil>('student')
  const [error, setError] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const abierta = sesion.estado === 'abierta'

  // Al entrar se cierra el formulario: la vista cambia sola con el perfil.
  useEffect(() => {
    if (abierta) cerrar(dialogo.current)
  }, [abierta])

  // Las ventanas informativas (components/Portal.tsx) abren este mismo formulario con el evento
  // `sar:abrir-sesion`; `detail: 'registrar'` lo abre en «Crear cuenta».
  useEffect(() => {
    function alPedir(e: Event) {
      const pedido = (e as CustomEvent<'entrar' | 'registrar' | undefined>).detail
      if (pedido) setModo(pedido)
      setError(null)
      abrir(dialogo.current)
    }
    window.addEventListener('sar:abrir-sesion', alPedir)
    return () => window.removeEventListener('sar:abrir-sesion', alPedir)
  }, [])

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setOcupado(true)
    setError(null)
    const fallo = modo === 'entrar' ? await entrar(correo, clave) : await registrar(correo, clave, perfil)
    setOcupado(false)
    if (fallo) setError(fallo === 'error' ? t('session.error') : fallo)
    else setClave('')
  }

  const etiqueta = abierta ? t('session.account', { role: t(`community.role.${sesion.perfil}`) }) : t('session.login')
  const titulo = abierta ? t('session.accountTitle') : modo === 'entrar' ? t('session.login') : t('session.register')

  return (
    <div className="sesion">
      <button
        type="button"
        className={`boton-cuenta${abierta ? ' con-sesion' : ''}`}
        aria-label={etiqueta}
        title={etiqueta}
        disabled={sesion.estado === 'comprobando'}
        onClick={() => {
          setError(null)
          abrir(dialogo.current)
        }}
      >
        <Icono nombre="cuenta" tamano={22} />
      </button>
      <dialog ref={dialogo} className="dialogo" aria-labelledby={ids.titulo}>
        <h2 id={ids.titulo}>{titulo}</h2>
        {abierta ? (
          <>
            <p>{t('session.as', { role: t(`community.role.${sesion.perfil}`) })}</p>
            <p className="muted ayuda">{t('session.viewFromRole')}</p>
            <div className="acciones">
              <BotonIcono
                icono="salir"
                etiqueta={t('session.logout')}
                className="boton-principal"
                onClick={() => {
                  cerrar(dialogo.current)
                  void salir()
                }}
              />
            </div>
          </>
        ) : sesion.estado === 'apagado' ? (
          <p>{t('session.off')}</p>
        ) : (
          <form onSubmit={enviar} className="formulario">
            <div className="campo">
              <label htmlFor={ids.correo}>{t('session.email')}</label>
              <input id={ids.correo} type="email" autoComplete="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} />
            </div>
            <div className="campo">
              <label htmlFor={ids.clave}>{t('session.password')}</label>
              <input
                id={ids.clave}
                type="password"
                autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'}
                required
                minLength={12}
                value={clave}
                onChange={(e) => setClave(e.target.value)}
              />
            </div>
            {modo === 'registrar' && (
              <div className="campo">
                <label htmlFor={ids.perfil}>{t('session.role')}</label>
                <select id={ids.perfil} value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)}>
                  <option value="student">{t('community.role.student')}</option>
                  <option value="researcher">{t('community.role.researcher')}</option>
                </select>
                <p className="muted ayuda">{t('session.declared')}</p>
              </div>
            )}
            {error && <p role="alert">{error}</p>}
            <div className="acciones">
              <BotonIcono
                type="submit"
                icono="entrar"
                etiqueta={modo === 'entrar' ? t('session.login') : t('session.register')}
                className="boton-principal"
                disabled={ocupado}
              />
              <button type="button" className="enlace-boton" onClick={() => setModo(modo === 'entrar' ? 'registrar' : 'entrar')}>
                {modo === 'entrar' ? t('session.toRegister') : t('session.toLogin')}
              </button>
            </div>
          </form>
        )}
        <form method="dialog" className="dialogo-cerrar">
          <BotonIcono type="submit" icono="cerrar" etiqueta={t('session.close')} />
        </form>
      </dialog>
    </div>
  )
}
