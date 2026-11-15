import type { Bbox } from '../mapa/tipos'

const centro = (b: Bbox): [number, number] => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
const contiene = (b: Bbox, [x, y]: [number, number]) => x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]
/** Margen para decir que una zona procesada es el lugar buscado: las zonas en línea se crean centradas en él. */
const MISMO_LUGAR_GRADOS = 0.05
/** Con el mismo nombre se admite más distancia: dos geocodificadores dan cajas distintas de la misma ciudad. */
const MISMO_NOMBRE_GRADOS = 0.25

/** «Delicias, Chihuahua, México» → «delicias»: primera parte del nombre, sin acentos ni mayúsculas. */
function nombreBase(n: string | undefined): string {
  return (n ?? '').split(',')[0].normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
}

/**
 * Zona procesada que corresponde a un lugar (2026-11-15). Un clic en el mapa (o la vista) usa la zona que contiene
 * el punto. Un lugar buscado solo reutiliza una zona si es el mismo lugar (centros a menos de 0,05°): antes bastaba
 * con que las cajas se tocaran, y buscar un sitio cercano (Santa Bárbara, dentro de la caja de Parral) devolvía a la
 * zona marcada en vez de analizar el lugar nuevo. Con el mismo nombre se admiten hasta 0,25°: la zona de Delicias
 * salió del nomenclátor y Nominatim da su centro a 0,08°.
 */
export function zonaParaLugar<Z extends { bbox: Bbox; nombre?: string }>(
  zonas: Z[],
  l: { bbox: Bbox; source?: string; id?: string; name?: string },
): Z | undefined {
  const c = centro(l.bbox)
  if (l.source === 'map-click' || l.id === 'vista') return zonas.find((z) => contiene(z.bbox, c))
  const cerca = zonas
    .map((z) => ({ z, d: Math.hypot(centro(z.bbox)[0] - c[0], centro(z.bbox)[1] - c[1]) }))
    .filter((x) => x.d <= MISMO_LUGAR_GRADOS || (x.d <= MISMO_NOMBRE_GRADOS && nombreBase(x.z.nombre) !== '' && nombreBase(x.z.nombre) === nombreBase(l.name)))
    .sort((a, b) => a.d - b.d)
  return cerca[0]?.z
}
