// Historias de la comunidad (specs/06-acceso, RF-ACC-13 a 17). Una historia guarda referencias y notas;
// los textos de cada veredicto se vuelven a pedir a la API, así que nunca se congelan ni se cambian.
import type { TFunction } from 'i18next'
import type { components } from '../api/auth'
import type { Lang, Verdict } from '../api/client'

export type Historia = components['schemas']['StoryOut']
export type HistoriaNueva = components['schemas']['StoryIn']
export type ParHistoria = components['schemas']['StoryPair']

/** Límites del contrato de auth (RF-ACC-17): una historia cabe en los 4 KB del gateway. */
export const TITULO_MIN = 3
export const TITULO_MAX = 120
export const NOTAS_MAX = 800
export const PARES_MAX = 24

export const clavePar = (series: string, pair: string) => `${series}/${pair}`
export const claveVeredicto = (v: Verdict) => clavePar(v.series, v.id)

/** Filtros del buscador general. `series` vale 'all' para todas. */
export interface Filtro {
  series: string
  desde: string
  hasta: string
  estados: Verdict['state'][]
  ventanas: boolean
}

export const ESTADOS: Verdict['state'][] = ['change_probable', 'no_detectable_change', 'not_observable']

/** Veredictos del filtro, en orden de fecha y luego de serie. */
export function buscar(todos: Verdict[], f: Filtro): Verdict[] {
  return todos
    .filter(
      (v) =>
        (f.series === 'all' || v.series === f.series) &&
        (f.ventanas || v.kind === 'consecutive') &&
        f.estados.includes(v.state) &&
        (!f.desde || v.from_date >= f.desde) &&
        (!f.hasta || v.to_date <= f.hasta),
    )
    .sort((a, b) => a.from_date.localeCompare(b.from_date) || a.to_date.localeCompare(b.to_date) || a.series.localeCompare(b.series))
}

/** Cuántos pares hay en cada estado. */
export function recuento(vs: Verdict[]): Record<Verdict['state'], number> {
  const r = { change_probable: 0, no_detectable_change: 0, not_observable: 0 }
  for (const v of vs) r[v.state] += 1
  return r
}

/**
 * Archivo Markdown de una historia. Los textos de cada par salen de la API tal cual; las notas van al final,
 * en su propia sección y rotuladas como de quien escribió la historia (RF-ACC-16).
 */
export function markdownHistoria(
  h: { title: string; aoi: string; series: string; from_date: string; to_date: string; notes: string; author_role?: string },
  pares: { par: ParHistoria; veredicto: Verdict | undefined }[],
  t: TFunction,
  lang: Lang,
  ahora: Date,
): string {
  const lineas: string[] = [
    `# ${h.title}`,
    '',
    `- ${t('community.file.zone')}: ${h.aoi}`,
    `- ${t('community.file.series')}: ${h.series === 'all' ? t('search.allSeries') : h.series}`,
    `- ${t('community.file.range')}: ${h.from_date} → ${h.to_date}`,
  ]
  if (h.author_role) lineas.push(`- ${t('community.file.author')}: ${t(`community.role.${h.author_role}`)}`)
  lineas.push(
    `- ${t('community.file.generated', { date: ahora.toISOString().slice(0, 16).replace('T', ' ') })}`,
    '',
    `## ${t('community.file.apiHeading')}`,
    '',
    t('community.file.apiNote', { lang }),
    '',
  )
  for (const { par, veredicto: v } of pares) {
    if (!v) {
      lineas.push(`### ${par.series} · ${par.pair}`, '', t('community.file.missingPair'), '')
      continue
    }
    lineas.push(
      `### ${v.from_date} → ${v.to_date} · ${v.series} · ${t(`verdict.state.${v.state}`)}`,
      '',
      `- **${t('verdict.detected')}:** ${v.summary.detected}`,
      `- **${t('verdict.doesNotProve')}:** ${v.summary.does_not_prove}`,
      `- **${t('verdict.missing')}:** ${v.summary.missing}`,
    )
    if (v.state === 'not_observable' && v.cause_label) lineas.push(`- **${t('community.file.cause')}:** ${v.cause_label}`)
    lineas.push(
      `- **${t('receipt.dataKind')}:** ${t(`dataKind.${v.receipt.data_kind}`)} · ${v.receipt.maturity} · CRID ${v.receipt.crid}`,
      `- **${t('receipt.granules')}:** ${v.receipt.granules.join(', ')}`,
      '',
    )
  }
  lineas.push(`## ${t('community.file.notesHeading')}`, '', t('community.file.notesNote'), '')
  lineas.push(h.notes.trim() ? h.notes.trim() : t('community.file.noNotes'), '')
  return lineas.join('\n')
}

/** Nombre de archivo seguro a partir del título. */
export function nombreArchivo(titulo: string): string {
  const base = titulo
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
  return `${base || 'historia'}.md`
}

/** Entrega un texto como archivo al navegador. */
export function descargarTexto(nombre: string, texto: string) {
  const url = URL.createObjectURL(new Blob([texto], { type: 'text/markdown;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.append(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
