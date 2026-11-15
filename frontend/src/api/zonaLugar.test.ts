import { expect, it } from 'vitest'
import { zonaParaLugar } from './zonaLugar'
import type { Bbox } from '../mapa/tipos'

const PARRAL = { aoi: 'parral', nombre: 'Hidalgo del Parral, Chihuahua', bbox: [-105.95, 26.7, -105.4, 27.15] as Bbox }
const DELICIAS = { aoi: 'z-delicias', nombre: 'Delicias, Chihuahua', bbox: [-105.52, 28.14, -105.42, 28.24] as Bbox }
const ZONAS = [PARRAL, DELICIAS]

it('buscar la misma ciudad reutiliza su zona', () => {
  expect(zonaParaLugar(ZONAS, { bbox: [-105.75, 26.87, -105.6, 26.98], source: 'gazetteer' })?.aoi).toBe('parral')
  expect(zonaParaLugar(ZONAS, { bbox: [-105.52, 28.15, -105.42, 28.23], source: 'gazetteer' })?.aoi).toBe('z-delicias')
  // La misma ciudad con la caja de Nominatim: centro a 0,08°, pero mismo nombre.
  expect(zonaParaLugar(ZONAS, { bbox: [-105.683, 27.968, -105.352, 28.277], source: 'nominatim', name: 'Delicias, Chihuahua, México' })?.aoi).toBe('z-delicias')
})

it('buscar un lugar distinto cuya caja cae en la zona marcada no regresa a ella', () => {
  // Santa Bárbara, Chihuahua (Nominatim): dentro de la caja de Parral, pero es otro lugar.
  expect(zonaParaLugar(ZONAS, { bbox: [-105.93, 26.66, -105.65, 26.93], source: 'nominatim', name: 'Santa Bárbara, Chihuahua, México' })).toBeUndefined()
})

it('un clic dentro de una zona usa esa zona', () => {
  expect(zonaParaLugar(ZONAS, { bbox: [-105.85, 26.75, -105.75, 26.85], source: 'map-click' })?.aoi).toBe('parral')
  expect(zonaParaLugar(ZONAS, { bbox: [-100.1, 25.6, -100.0, 25.7], source: 'map-click' })).toBeUndefined()
})
