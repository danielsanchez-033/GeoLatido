import { describe, expect, it } from "vitest";
import {
  contenidoSerie,
  etiquetaEstado,
  fechasDelPar,
  formatoValorDb,
  puntoSeleccionado,
  redondear5,
  urlPixel,
  type SeriePixel,
} from "./seleccion";

describe("onPointSelected redondea a 5 decimales", () => {
  it.each([
    [-105.664912345, -105.66491],
    [26.931234567, 26.93123],
    [-105.000004, -105],
    [26.000005, 26.00001],
    [-0.000001, 0], // sin "-0"
  ])("%f → %f", (entrada, esperado) => {
    expect(redondear5(entrada)).toBe(esperado);
    expect(Object.is(redondear5(entrada), -0)).toBe(false);
  });

  it("nunca devuelve más de 5 decimales", () => {
    for (let i = 0; i < 1000; i++) {
      const x = (Math.random() - 0.5) * 360;
      const decimales = String(redondear5(x)).split(".")[1] ?? "";
      expect(decimales.length).toBeLessThanOrEqual(5);
    }
  });

  it("normaliza la longitud cuando el mapa da la vuelta al mundo", () => {
    expect(puntoSeleccionado(254.335087654, 26.9312345)).toEqual({ lon: -105.66491, lat: 26.93123 });
    expect(puntoSeleccionado(-465.66491, 26.93)).toEqual({ lon: -105.66491, lat: 26.93 });
  });
});

describe("llamada a la serie por píxel", () => {
  const base = "http://localhost:8080/api/verdicts/aois/parral/series/T048A-F015/pixel";

  it("añade lon y lat con 5 decimales a la ruta del contrato", () => {
    expect(urlPixel(base, puntoSeleccionado(-105.664912345, 26.931234567))).toBe(
      `${base}?lon=-105.66491&lat=26.93123`,
    );
  });

  it("respeta una consulta previa", () => {
    expect(urlPixel(`${base}?x=1`, { lon: 1, lat: 2 })).toBe(`${base}?x=1&lon=1&lat=2`);
  });
});

describe("textos de la serie", () => {
  it("lee las fechas del identificador del par", () => {
    expect(fechasDelPar("20260617_20260629")).toEqual(["2026-06-17", "2026-06-29"]);
    expect(fechasDelPar("otro")).toBeNull();
  });

  it("nombra cada estado y nunca confunde no observable con sin cambio", () => {
    expect(etiquetaEstado("change_probable", "es")).toBe("Cambio probable");
    expect(etiquetaEstado("no_change", "es")).toBe("Sin cambio detectable");
    expect(etiquetaEstado("low_looks", "es")).toBe("No observable: muy pocas muestras de radar por píxel");
    expect(etiquetaEstado("terrain", "en")).toBe("Not observable: terrain hides or distorts the signal");
    expect(etiquetaEstado(null, "es")).toBe("sin dato");
    // Una causa nueva de Eco sin texto todavía sigue diciendo que no se pudo observar.
    expect(etiquetaEstado("causa_nueva", "es")).toBe("No observable: causa_nueva");
  });

  it("escribe los dB con un decimal y marca los huecos", () => {
    expect(formatoValorDb(-10.64, "es")).toBe("−10.6 dB");
    expect(formatoValorDb(null, "es")).toBe("sin dato");
  });
});

describe("contenido de la ventana", () => {
  const serie: SeriePixel = {
    aoi: "parral",
    series: "T048A-F015",
    lon: -105.66491,
    lat: 26.93123,
    data_kind: "synthetic",
    values: [
      { date: "2026-06-17", hh_db: -10.6, hv_db: -17.3 },
      { date: "2026-06-29", hh_db: null, hv_db: null },
      { date: "2026-07-11", hh_db: -11.4, hv_db: -18.5 },
    ],
    changes: [
      { pair: "20260617_20260629", state: "low_looks" },
      { pair: "20260629_20260711", state: "change_probable" },
    ],
  };

  it("muestra las coordenadas, el distintivo sintético y una fila por fecha y por par", () => {
    const n = contenidoSerie(serie, "es");
    expect(n.textContent).toContain("Lon −105.66491° · Lat 26.93123°");
    expect(n.textContent).toContain("Datos sintéticos");
    expect(n.querySelectorAll("details tbody tr")).toHaveLength(3);
    expect(n.textContent).toContain("2026-06-29 → 2026-07-11");
    expect(n.textContent).toContain("No observable: muy pocas muestras");
    expect(n.querySelector("svg[role=img]")).not.toBeNull();
  });

  it("no muestra el distintivo con datos reales", () => {
    expect(contenidoSerie({ ...serie, data_kind: "real" }, "es").textContent).not.toContain(
      "Datos sintéticos",
    );
  });
});
