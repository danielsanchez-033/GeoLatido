import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import es from './es.json'

export const LANGS = ['es', 'en'] as const
export type UiLang = (typeof LANGS)[number]

function initialLang(): UiLang {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('lang') : null
  if (saved === 'es' || saved === 'en') return saved
  return typeof navigator !== 'undefined' && navigator.language.startsWith('en') ? 'en' : 'es'
}

void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: initialLang(),
  fallbackLng: 'es',
  interpolation: { escapeValue: false },
})

// El idioma y el título del documento siguen al de la interfaz (lectores de pantalla y separación de sílabas).
function syncDocument(lang: string) {
  if (typeof document === 'undefined') return
  document.documentElement.lang = lang
  document.title = i18n.t('app.title', { lng: lang })
  localStorage.setItem('lang', lang)
}
syncDocument(i18n.language)
i18n.on('languageChanged', syncDocument)

export default i18n
