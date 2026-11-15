import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import es from './es.json'

export const LANGS = ['es', 'en'] as const
export type UiLang = (typeof LANGS)[number]

// Inglés por omisión (2026-11-15, para el jurado de Space Apps). Solo se recuerda el idioma que alguien elige con
// ES/EN, en `idioma-elegido`: la clave vieja `lang` se guardaba en cada carga, así que no distinguía una elección.
const CLAVE = 'idioma-elegido'

function initialLang(): UiLang {
  let saved: string | null = null
  try {
    saved = typeof localStorage !== 'undefined' ? localStorage.getItem(CLAVE) : null
  } catch {
    saved = null
  }
  return saved === 'es' || saved === 'en' ? saved : 'en'
}

void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: initialLang(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

// El idioma y el título del documento siguen al de la interfaz (lectores de pantalla y separación de sílabas).
function syncDocument(lang: string) {
  if (typeof document === 'undefined') return
  document.documentElement.lang = lang
  document.title = i18n.t('app.title', { lng: lang })
}
syncDocument(i18n.language)
i18n.on('languageChanged', (lang) => {
  syncDocument(lang)
  try {
    localStorage.setItem(CLAVE, lang)
  } catch {
    // Sin almacenamiento, la próxima visita vuelve a empezar en inglés.
  }
})

export default i18n
