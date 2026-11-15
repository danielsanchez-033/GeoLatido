import { describe, expect, it } from "vitest";
import { fuentesDisponibles } from "./antesDespues";

const escena = { tiles: ["http://t/{z}/{x}/{y}.png"] } as never;

describe("fuentes del comparador", () => {
  it("ofrece las escenas ópticas que tienen teselas y las capas de radar que existen", () => {
    expect(fuentesDisponibles({ optical: { before: escena }, capas: { change_hh: "hh", change_hv: "hv" } })).toEqual([
      "before", "change_hh", "change_hv",
    ]);
  });

  it("el hundimiento solo aparece si la zona tiene su capa", () => {
    expect(fuentesDisponibles({ optical: { before: escena, after: escena }, capas: { change_hh: "hh", change_hv: "hv", subsidence: "s" } })).toEqual([
      "before", "after", "change_hh", "change_hv", "subsidence",
    ]);
    expect(fuentesDisponibles({ optical: undefined, capas: undefined })).toEqual([]);
  });
});
