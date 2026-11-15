// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'

const normalize = (s: string) => s.replace(/\r\n/g, '\n').replace(/^\/\*\*[\s\S]*?\*\/\n\n/, '').trim()

test.each(['verdicts', 'auth'])(
  'los tipos coinciden con contracts/%s.openapi.json (si falla: npm run gen:types)',
  async (name) => {
    const contract = new URL(`../../../contracts/${name}.openapi.json`, import.meta.url)
    const generated = fileURLToPath(new URL(`../api/${name}.d.ts`, import.meta.url))
    const fresh = astToString(await openapiTS(contract))
    expect(normalize(readFileSync(generated, 'utf8'))).toBe(normalize(fresh))
  },
)
