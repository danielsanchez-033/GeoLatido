import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'
import '../i18n'

afterEach(() => cleanup())

// Con todas las pruebas en paralelo, el primer render del App puede pasar de 1 s (el valor por defecto).
configure({ asyncUtilTimeout: 3000 })
