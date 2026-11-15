// Globo 3D y caída a 2D (T-ATL-09, RF-INT-10 y 17).
// El globo es la proyección "globe" de MapLibre 6.16.0, que pasa a Mercator por dentro al
// acercarse (plano desde el zoom 12, comprobado en el navegador el 2026-11-14).

/**
 * Qué puede dibujar el navegador. MapLibre 6 solo funciona con WebGL 2, así que sin él no hay
 * mapa ni en 2D. Sin aceleración gráfica (WebGL por software) el globo va a trompicones: 2D.
 */
export type CapacidadGrafica = "completa" | "sin_aceleracion" | "sin_webgl2";

/** Por qué el mapa está en 2D aunque se pidió el 3D. */
export type MotivoSin3d = "sin_aceleracion" | "fallo_globo" | "comparador";

type Lienzo = Pick<HTMLCanvasElement, "getContext">;

function contexto(lienzo: Lienzo, atributos: WebGLContextAttributes): WebGL2RenderingContext | null {
  try {
    return lienzo.getContext("webgl2", atributos) as WebGL2RenderingContext | null;
  } catch {
    return null;
  }
}

function liberar(gl: WebGL2RenderingContext | null) {
  gl?.getExtension("WEBGL_lose_context")?.loseContext();
}

export function capacidadGrafica(
  crearLienzo: () => Lienzo = () => document.createElement("canvas"),
): CapacidadGrafica {
  const conAceleracion = contexto(crearLienzo(), { failIfMajorPerformanceCaveat: true });
  if (conAceleracion) {
    liberar(conAceleracion);
    return "completa";
  }
  const cualquiera = contexto(crearLienzo(), {});
  if (!cualquiera) return "sin_webgl2";
  liberar(cualquiera);
  return "sin_aceleracion";
}

export interface EntradaProyeccion {
  /** Lo que pidió Faro con `modo3d`. */
  modo3d: boolean;
  capacidad: CapacidadGrafica;
  /** setProjection lanzó un error antes: no se vuelve a intentar. */
  falloGlobo: boolean;
  /** El comparador óptico no casa con el globo: mientras está, 2D (RF-INT-20). */
  comparadorActivo: boolean;
}

export interface Proyeccion {
  tipo: "globe" | "mercator";
  /** Solo si se pidió el 3D y no se puede: el mapa lo dice en pantalla. */
  motivo: MotivoSin3d | null;
}

export function elegirProyeccion(e: EntradaProyeccion): Proyeccion {
  if (!e.modo3d) return { tipo: "mercator", motivo: null };
  if (e.capacidad !== "completa") return { tipo: "mercator", motivo: "sin_aceleracion" };
  if (e.falloGlobo) return { tipo: "mercator", motivo: "fallo_globo" };
  if (e.comparadorActivo) return { tipo: "mercator", motivo: "comparador" };
  return { tipo: "globe", motivo: null };
}

/**
 * Cuánto se ve como globo, de 0 (plano) a 1 (globo). MapLibre lo expone como
 * `transitionState` de su proyección (interno); si no llega, se estima por el zoom:
 * globo hasta el 11 y plano desde el 12, medido en el navegador el 2026-11-14.
 */
export function transicionGlobo(zoom: number, leido?: number): number {
  if (typeof leido === "number" && Number.isFinite(leido)) return Math.min(1, Math.max(0, leido));
  if (zoom >= 12) return 0;
  if (zoom <= 11) return 1;
  return 12 - zoom;
}

export interface VistaCamara {
  tipo: Proyeccion["tipo"];
  /** Inclinación en grados. */
  pitch: number;
  /** Ver `transicionGlobo`. Solo cuenta con el globo. */
  transicion: number;
}

/**
 * La barra de escala solo vale en plano y sin inclinación (RF-INT-13): con perspectiva o
 * sobre el globo, la distancia de un píxel cambia de un punto a otro de la pantalla.
 */
export function escalaValida(v: VistaCamara): boolean {
  if (v.pitch > 0.5) return false;
  return v.tipo === "mercator" || v.transicion <= 0;
}
