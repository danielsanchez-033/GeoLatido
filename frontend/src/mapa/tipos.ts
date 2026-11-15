// Interfaz del mapa para Faro. Fuente: specs/04-atlas/plan.md y src/types/map.ts.
import type { FeatureCollection, Polygon } from "geojson";
import type { MapLayerName, MapProps } from "../types/map";
import type { AvisoEscena } from "./escena";
import type { Huellas } from "./huellas";
import type { Idioma } from "./textos";

/** Extensión en WGS84 (EPSG:4326): [oeste, sur, este, norte]. */
export type Bbox = MapProps["aoi"];

export type CapaRadar = MapLayerName;

/**
 * Opciones de `crearMapa`. Cualquier `MapProps` de `src/types/map.ts` es válido tal cual;
 * aquí `layers`, `activeLayer` y `compare` son opcionales y hay extras propios de Atlas.
 */
export interface OpcionesMapa
  extends Omit<MapProps, "layers" | "activeLayer" | "compare"> {
  /** Plantillas de tesela de la API (`verdict.layers`) con el host del gateway delante. */
  layers?: MapProps["layers"];
  /** Capa visible. Por defecto, "state". */
  activeLayer?: MapProps["activeLayer"];
  /** Modo de comparación (T-ATL-07). Por defecto, "off". */
  compare?: MapProps["compare"];
  /** Nombre de la zona, para la etiqueta de extensión y lectores de pantalla. */
  nombreZona?: string;
  /** `verdict.cause_label`, si el veredicto es no observable. Se muestra en la leyenda. */
  causaNoObservable?: string;
  /**
   * Cambio de nivel de toda la escena: pasar `avisoEscena(verdict.evidence.scene_shift)`
   * de `escena.ts`. Con `sin_corregir`, la leyenda avisa de que el cambio puede no ser local;
   * con `corregido`, anota que ese desplazamiento ya se descontó. No cambia los colores.
   * `true` equivale a `sin_corregir` (compatibilidad con el PR 32).
   */
  desplazamientoEscena?: boolean | AvisoEscena;
  /** Idioma de los textos del mapa. Por defecto, "es". */
  idioma?: Idioma;
  /**
   * Ruta de la serie por píxel de la serie activa, con el host delante; por ejemplo,
   * `http://localhost:8080/api/verdicts/aois/parral/series/T048A-F015/pixel`.
   * Si está, al seleccionar un punto el mapa pide `?lon=…&lat=…` y enseña la historia.
   */
  pixelUrl?: string;
  /**
   * Globo 3D (T-ATL-09). Por defecto, false: plano, como hasta ahora. Si el navegador no tiene
   * aceleración gráfica, si el globo falla o mientras está el comparador, el mapa queda en 2D
   * y lo dice en pantalla.
   */
  modo3d?: boolean;
  /** Muestra el botón 2D/3D dentro del mapa (T-ATL-10). Por defecto, true. */
  control3d?: boolean;
  /** Se llama cuando la persona cambia entre 2D y 3D con el botón del mapa. */
  onModo3dChanged?: (modo3d: boolean) => void;
  /**
   * Huellas de las series de la zona (T-ATL-13, RF-INT-16): una Feature por serie, la de
   * `series[i].footprint` de `GET /api/catalog/aois/{aoi}/series` sin tocar (las `null` se
   * dejan fuera). El mapa las dibuja con su nombre y las lista para lectores de pantalla.
   * Sin huellas, solo la caja de la zona.
   */
  huellas?: Huellas;
  /** Muestra el selector de capa y la opacidad dentro del mapa. Por defecto, true. */
  controlCapas?: boolean;
  /**
   * Comparador antes/después: la escena óptica de antes y la de después del par, recortadas a la
   * zona y separadas por un deslizador que sigue al globo. Funciona en 2D y en 3D. Por defecto, false.
   */
  antesDespues?: boolean;
  /** Se llama cuando la persona cambia de capa con el selector del mapa. */
  onLayerChanged?: (capa: CapaRadar) => void;
}

/** Lo que se puede cambiar después de crear el mapa. */
export type CambiosMapa = Partial<
  Pick<
    OpcionesMapa,
    | "aoi"
    | "nombreZona"
    | "layers"
    | "activeLayer"
    | "causaNoObservable"
    | "desplazamientoEscena"
    | "dataKind"
    | "idioma"
    | "pixelUrl"
    | "optical"
    | "compare"
    | "modo3d"
    | "huellas"
    | "antesDespues"
  >
>;

/**
 * Resultados del buscador mundial (catalog /search/world): huellas de los gránulos, el elegido resaltado y su
 * vista previa de ASF colocada en la caja de su huella (aproximada: la PNG no trae georreferencia).
 */
export interface MundoMapa {
  huellas: FeatureCollection<Polygon, { id: string }>;
  elegido?: string | null;
  vista?: { url: string; bbox: Bbox } | null;
}

export interface MapaAtlas {
  /** Aplica cambios sin recrear el mapa; por ejemplo, al elegir otro veredicto. */
  actualizar(cambios: CambiosMapa): void;
  /** Opacidad de las capas radar, entre 0,2 y 1. */
  fijarOpacidad(opacidad: number): void;
  /** Vuelve a encuadrar la zona. */
  encuadrar(): void;
  /** Buscador mundial: pinta (o quita, con null) las huellas y la vista previa del gránulo elegido. */
  mostrarMundo(m: MundoMapa | null): void;
  /** Pone el nombre del lugar en la ventana del punto elegido, si sigue siendo ese punto (2026-11-15). */
  rotularPunto(p: { lon: number; lat: number }, nombre: string): void;
  /** Lleva la cámara a una caja [oeste, sur, este, norte]. */
  volarA(bbox: Bbox): void;
  destruir(): void;
}
