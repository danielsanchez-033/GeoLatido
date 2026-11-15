import { useTranslation } from 'react-i18next'
import { LANGS } from '../i18n'

export function LanguageSwitch() {
  const { t, i18n } = useTranslation()
  return (
    <div role="group" aria-label={t('language.label')} className="language-switch">
      {LANGS.map((lang) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={i18n.language === lang}
          aria-label={t(`language.${lang}`)}
          title={t(`language.${lang}`)}
          onClick={() => void i18n.changeLanguage(lang)}
        >
          {/* El código es el texto mínimo que distingue el idioma; el nombre completo va en aria-label. */}
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
