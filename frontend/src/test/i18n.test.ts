import en from '../i18n/en.json'
import es from '../i18n/es.json'

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

test('español e inglés tienen exactamente las mismas claves', () => {
  expect(keys(en).sort()).toEqual(keys(es).sort())
})

test('ningún texto está vacío', () => {
  for (const dict of [es, en]) {
    for (const key of keys(dict)) {
      const value = key.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)[k], dict)
      expect(value, key).not.toBe('')
    }
  }
})

// Copia de FORBIDDEN en services/verdicts/tests/test_language.py (Balanza, T-BAL-03).
// Si cambia allí, cámbiala aquí. Se busca sobre texto en minúsculas y sin tildes.
const FORBIDDEN: Record<string, RegExp> = {
  confirmación: /\bconfirm\w*/,
  'causa afirmada (es)': /\b(causad|provocad|ocasionad|originad)[oa]s? por\b/,
  'causa afirmada (en)': /\b(caused|triggered|produced) by\b/,
  'causa en voz activa (es)':
    /\b(causo|causaron|provocan?|provoco|provocaron|ocasionan?|ocasiono|ocasionaron|origino|originaron)\b/,
  'causa en voz activa (en)': /\bcaused\b/,
  'debido a': /\bdebid[oa]s? a\b/,
  'se debe a': /\bse deben? a\b/,
  'a causa de': /\b(a causa|por culpa) de\b/,
  'due to': /\bdue to\b/,
  'because of': /\b(because of|as a result of)\b/,
  'daño (es)': /\bdan(o|os|ad[oa]s?|ar|an|aron|en|ino\w*)\b/,
  'damage (en)': /\bdamag\w*/,
  'destrucción (es)': /\bdestru\w*/,
  'destruction (en)': /\bdestr(oy|uct)\w*/,
  'certeza (es)': /\b(sin (ninguna )?duda|definitivamente|con (total )?certeza|indudablemente)\b/,
  'certeza (en)': /\b(without (a )?doubt|undoubtedly|definitely|certainly)\b/,
}

function normalize(text: string): string {
  return text.toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '')
}

test('ningún texto de interfaz afirma causas, daños ni certezas (RF-BAL-03)', () => {
  for (const dict of [es, en]) {
    for (const key of keys(dict)) {
      const value = key.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)[k], dict)
      const text = normalize(String(value))
      for (const [name, pattern] of Object.entries(FORBIDDEN)) {
        expect(pattern.test(text), `${key}: ${name}`).toBe(false)
      }
    }
  }
})
