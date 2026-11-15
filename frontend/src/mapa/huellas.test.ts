import { describe, expect, expectTypeOf, it } from "vitest";
import type { components } from "./catalogo";
import {
  anclaEtiqueta,
  anilloContinuo,
  centroZona,
  describirHuella,
  geojsonHuellas,
  huellasValidas,
  nombreCorto,
  puntoEtiqueta,
  type Huella,
  type Huellas,
} from "./huellas";
import { crearMapa } from "./mapa";
import { TEXTOS } from "./textos";
import type { OpcionesMapa } from "./tipos";

function huella(anillo: number[][], serie = "T048A-F015-4005-DHDH-P05023"): Huella {
  return {
    type: "Feature",
    properties: {
      series: serie,
      track: 48,
      direction: "A",
      frame: 15,
      granule_id: "NISAR_L2_PR_GCOV_025_048_A_015",
      basis: "latest_granule",
    },
    geometry: { type: "Polygon", coordinates: [anillo] },
  };
}

const PARRAL = huella([
  [-106.9, 26.0],
  [-104.6, 26.4],
  [-104.2, 28.4],
  [-106.5, 28.0],
  [-106.9, 26.0],
]);

const coleccion = (...features: Huella[]): Huellas => ({ type: "FeatureCollection", features });

describe("huellas de las series (T-ATL-13)", () => {
  it("acepta el footprint del catálogo sin tocarlo", () => {
    expectTypeOf<Huella>().toEqualTypeOf<components["schemas"]["SeriesFootprint"]>();
    expectTypeOf<{ aoi: OpcionesMapa["aoi"]; dataKind: "real"; huellas: Huellas }>().toMatchTypeOf<OpcionesMapa>();
  });

  it("deja fuera las que no se pueden dibujar", () => {
    const abierto = huella([
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ]);
    const corto = huella([
      [0, 0],
      [1, 1],
      [0, 0],
    ]);
    const conNaN = huella([
      [0, 0],
      [Number.NaN, 0],
      [1, 1],
      [0, 0],
    ]);
    expect(huellasValidas(coleccion(PARRAL, abierto, corto, conNaN))).toEqual([PARRAL]);
    expect(huellasValidas(undefined)).toEqual([]);
    expect(huellasValidas({ type: "FeatureCollection" } as unknown as Huellas)).toEqual([]);
  });

  it("pone el nombre en el vértice más al norte, para que dos series cruzadas no se tapen", () => {
    expect(puntoEtiqueta(PARRAL)).toEqual([-104.2, 28.4]);
    const descendente = huella([
      [-106.72795, 28.15477],
      [-107.37384, 26.02791],
      [-104.86019, 25.40417],
      [-104.18639, 27.52101],
      [-106.72795, 28.15477],
    ]);
    expect(puntoEtiqueta(descendente)).toEqual([-106.72795, 28.15477]);
    // Cada nombre crece hacia fuera de su huella, así que no se pisan al alejar.
    expect(anclaEtiqueta(PARRAL)).toBe("bottom-left");
    expect(anclaEtiqueta(descendente)).toBe("bottom-right");
  });

  it("nombra la huella con pista, sentido y marco, como el id de la serie", () => {
    expect(nombreCorto(PARRAL.properties)).toBe("T048A-F015");
    expect(nombreCorto({ ...PARRAL.properties, track: 171, direction: "D", frame: 75 })).toBe("T171D-F075");
  });

  it("no da la vuelta al mundo si la huella cruza el antimeridiano", () => {
    const fiyi = huella([
      [179.5, -17],
      [-179.5, -17],
      [-179.5, -16],
      [179.5, -16],
      [179.5, -17],
    ]);
    expect(anilloContinuo(fiyi.geometry.coordinates[0]).map((p) => p[0])).toEqual([
      179.5, 180.5, 180.5, 179.5, 179.5,
    ]);
    expect(puntoEtiqueta(fiyi)).toEqual([-179.5, -16]);
    expect(geojsonHuellas([fiyi]).features[0].properties.series).toBe(fiyi.properties.series);
  });

  it("describe pista, sentido y marco en los dos idiomas", () => {
    expect(describirHuella(PARRAL.properties, "es")).toBe("pista 48, ascendente, marco 15");
    expect(describirHuella({ ...PARRAL.properties, direction: "D" }, "en")).toBe(
      "track 48, descending, frame 15",
    );
  });

  it("marca el centro de la zona, también si cruza el antimeridiano", () => {
    const [lon, lat] = centroZona([-105.95, 26.7, -105.4, 27.15]).geometry.coordinates;
    expect(lon).toBeCloseTo(-105.675, 9);
    expect(lat).toBeCloseTo(26.925, 9);
    expect(centroZona([179, -17, -179, -16]).geometry.coordinates).toEqual([180, -16.5]);
  });

  it("sin WebGL 2, las lista en texto y siguen al idioma", () => {
    const c = document.createElement("div");
    const mapa = crearMapa(c, {
      aoi: [-105.95, 26.7, -105.4, 27.15],
      dataKind: "real",
      huellas: coleccion(PARRAL),
    });
    const lista = c.querySelector<HTMLElement>(".atlas-lista-huellas")!;
    expect(lista.hidden).toBe(false);
    expect(lista.getAttribute("aria-label")).toBe(TEXTOS.es.huellas);
    expect(lista.textContent).toBe("T048A-F015-4005-DHDH-P05023: pista 48, ascendente, marco 15");

    mapa.actualizar({ idioma: "en" });
    expect(lista.textContent).toContain("track 48, ascending, frame 15");

    mapa.actualizar({ huellas: undefined });
    expect(lista.hidden).toBe(true);
    mapa.destruir();
  });
});
