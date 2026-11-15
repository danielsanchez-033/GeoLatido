import { beforeEach } from 'vitest'
import i18n from '../i18n'
import { makeVerdict } from '../test/fixtures'
import { buscar, markdownHistoria, nombreArchivo, recuento, type Filtro } from './historias'

beforeEach(async () => {
  await i18n.changeLanguage('es')
})

const todos = [
  makeVerdict(),
  makeVerdict({ id: '20260617_20260711', kind: 'full_window', to_date: '2026-07-11' }),
  makeVerdict({ id: '20260629_20260711', from_date: '2026-06-29', to_date: '2026-07-11', state: 'no_detectable_change' }),
  makeVerdict({ id: '20260626_20260708', series: 'T171D-F075', from_date: '2026-06-26', to_date: '2026-07-08', state: 'not_observable' }),
]
const base: Filtro = { series: 'all', desde: '', hasta: '', estados: ['change_probable', 'no_detectable_change', 'not_observable'], ventanas: false }

test('el buscador ordena por fecha y aplica serie, rango, estado y ventanas', () => {
  expect(buscar(todos, base).map((v) => v.id)).toEqual(['20260617_20260629', '20260626_20260708', '20260629_20260711'])
  expect(buscar(todos, { ...base, series: 'T171D-F075' }).map((v) => v.id)).toEqual(['20260626_20260708'])
  expect(buscar(todos, { ...base, desde: '2026-06-26', hasta: '2026-07-08' }).map((v) => v.id)).toEqual(['20260626_20260708'])
  expect(buscar(todos, { ...base, estados: ['change_probable'], ventanas: true }).map((v) => v.id)).toEqual([
    '20260617_20260629',
    '20260617_20260711',
  ])
  expect(recuento(buscar(todos, base))).toEqual({ change_probable: 1, no_detectable_change: 1, not_observable: 1 })
})

test('el archivo lleva los textos de la API por par y las notas aparte, rotuladas', () => {
  const v = todos[0]
  const md = markdownHistoria(
    { title: 'Junio', aoi: 'parral', series: 'all', from_date: '2026-06-17', to_date: '2026-07-11', notes: 'Mis notas', author_role: 'student' },
    [
      { par: { series: v.series, pair: v.id }, veredicto: v },
      { par: { series: 'T171D-F075', pair: '20990101_20990113' }, veredicto: undefined },
    ],
    i18n.t,
    'es',
    new Date('2026-11-14T18:00:00Z'),
  )
  const [api, notas] = md.split('## Notas de quien escribió la historia')
  expect(api).toContain('### 2026-06-17 → 2026-06-29 · T048A-F015 · Cambio probable')
  expect(api).toContain(`**Qué no prueba:** ${v.summary.does_not_prove}`)
  expect(api).toContain('NISAR_L2_PR_GCOV_023_048_A_015')
  expect(api).toContain('Este par ya no está en la API o es de otra zona.')
  expect(api).toContain('Autoría (perfil declarado): estudiante')
  expect(api).not.toContain('Mis notas')
  expect(notas).toContain('Estas notas no son texto de la API ni están comprobadas.')
  expect(notas).toContain('Mis notas')
})

test('el nombre del archivo es seguro', () => {
  expect(nombreArchivo('Agosto en Parral: ¿cambió?')).toBe('agosto-en-parral-cambio.md')
  expect(nombreArchivo('¿?')).toBe('historia.md')
})
