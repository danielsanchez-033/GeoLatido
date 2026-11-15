import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Fuente del sistema de diseño (T-FAR-12): Atkinson Hyperlegible Next, SIL OFL 1.1, servida desde la app.
import '@fontsource/atkinson-hyperlegible-next/latin-400.css'
import '@fontsource/atkinson-hyperlegible-next/latin-700.css'
import './i18n'
import './tema/tokens.css'
import './index.css'
import './tema/vidrio.css'
import './tema/portal.css'
import App from './App.tsx'

// La vista sale de la sesión y el tema es solo oscuro (specs/08-interfaz, T-FAR-21): se borran los valores
// que dejaron el selector de vista y el botón de tema anteriores.
try {
  localStorage.removeItem('vista')
  localStorage.removeItem('tema')
} catch {
  // Sin almacenamiento no hay nada que borrar.
}

// Vidrio líquido: el brillo de cada pieza de vidrio sigue al puntero (variables --mx y --my que lee
// src/tema/vidrio.css). Un solo oyente pasivo para toda la página.
window.addEventListener(
  'pointermove',
  (e) => {
    const el = (e.target as Element | null)?.closest?.<HTMLElement>('.vidrio, .boton-flotante')
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${e.clientX - r.left}px`)
    el.style.setProperty('--my', `${e.clientY - r.top}px`)
  },
  { passive: true },
)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
