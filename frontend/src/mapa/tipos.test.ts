import type { MapProps } from "../types/map";
import type { crearMapa } from "./mapa";
import type { MapaAtlas, OpcionesMapa } from "./tipos";

// Comprobaciones de tipos: las verifica `tsc -b` (npm run build); en vitest no hacen nada.
test("las props de Faro (src/types/map.ts) sirven como opciones de crearMapa", () => {
  expectTypeOf<MapProps>().toExtend<OpcionesMapa>();
});

test("crearMapa devuelve un objeto con actualizar y destruir", () => {
  expectTypeOf<ReturnType<typeof crearMapa>>().toEqualTypeOf<MapaAtlas>();
  expectTypeOf<MapaAtlas["actualizar"]>().toBeFunction();
  expectTypeOf<MapaAtlas["destruir"]>().toBeFunction();
});

test("las opciones de la ola 2 son opcionales: basta con la zona y el tipo de dato (RF-INT-19)", () => {
  expectTypeOf<{ aoi: [number, number, number, number]; dataKind: "real" }>().toExtend<OpcionesMapa>();
  expectTypeOf<OpcionesMapa["modo3d"]>().toEqualTypeOf<boolean | undefined>();
  expectTypeOf<OpcionesMapa["control3d"]>().toEqualTypeOf<boolean | undefined>();
  expectTypeOf<OpcionesMapa["onModo3dChanged"]>().toEqualTypeOf<((modo3d: boolean) => void) | undefined>();
});
