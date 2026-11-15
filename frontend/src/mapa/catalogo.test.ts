// @vitest-environment node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const contrato = new URL("../../../contracts/catalog.openapi.json", import.meta.url);
const generado = fileURLToPath(new URL("./catalogo.d.ts", import.meta.url));

test("los tipos coinciden con contracts/catalog.openapi.json (si falla: npx openapi-typescript ../contracts/catalog.openapi.json -o src/mapa/catalogo.d.ts)", async () => {
  const nuevo = astToString(await openapiTS(contrato));
  const normalizar = (s: string) =>
    s.replace(/\r\n/g, "\n").replace(/^\/\*\*[\s\S]*?\*\/\n\n/, "").trim();
  expect(normalizar(readFileSync(generado, "utf8"))).toBe(normalizar(nuevo));
});
