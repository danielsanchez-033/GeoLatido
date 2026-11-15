import { vistaDeSesion } from '../vista/vista'

test('la vista sale de la sesión: Público sin sesión y la del perfil declarado con ella', () => {
  expect(vistaDeSesion({ estado: 'comprobando' })).toBe('public')
  expect(vistaDeSesion({ estado: 'apagado' })).toBe('public')
  expect(vistaDeSesion({ estado: 'anonima' })).toBe('public')
  expect(vistaDeSesion({ estado: 'abierta', token: 't', perfil: 'student' })).toBe('student')
  expect(vistaDeSesion({ estado: 'abierta', token: 't', perfil: 'researcher' })).toBe('researcher')
})
