import type { MotivoSin3d } from "./globo";
import type { CapaRadar } from "./tipos";

export type Idioma = "es" | "en";

interface Textos {
  mapaDe: (zona: string) => string;
  extensionDe: (zona: string) => string;
  zonaPorDefecto: string;
  sintetico: string;
  capa: string;
  capas: Record<CapaRadar, string>;
  opacidad: string;
  leyenda: string;
  cambioProbable: string;
  sinCambio: string;
  sinCambioNota: string;
  noObservable: string;
  noObservableNota: string;
  causaPrincipal: string;
  bajo: string;
  subio: string;
  escalaDb: string;
  hundeMenos: string;
  hundeMas: string;
  escalaHundimiento: string;
  /** Con scene_shift.exceeds_threshold y sin corrected (PR 37). */
  avisoEscena: string;
  /** Con scene_shift.exceeds_threshold y corrected (PR 42). */
  notaEscenaCorregida: string;
  // Selección de punto (T-ATL-04)
  puntoSeleccionado: string;
  lon: string;
  lat: string;
  serie: string;
  cargandoSerie: string;
  fueraDeSerie: string;
  errorSerie: string;
  sinDato: string;
  fecha: string;
  valoresPorFecha: string;
  estadoPorPar: string;
  verTabla: string;
  graficaAria: string;
  ayudaTeclado: string;
  cerrar: string;
  // Comparador óptico (T-ATL-07)
  comparador: string;
  antes: string;
  despues: string;
  radar: string;
  optico: string;
  deslizador: string;
  escenaDel: (fechaHora: string) => string;
  diasRadar: (dias: number) => string;
  nubes: (porcentaje: string) => string;
  estadosOpticos: Record<
    "cloudy" | "partial_coverage" | "none_in_window" | "catalog_unavailable",
    string
  >;
  // Globo 3D (T-ATL-09)
  /** Sin WebGL 2 no hay mapa, ni en 2D: se dice y se deja la zona en texto. */
  sinMapa: string;
  /** Se pidió el 3D (`modo3d`) y el mapa está en 2D: por qué. */
  sin3d: Record<MotivoSin3d, string>;
  // Controles en 3D (T-ATL-10)
  /** Nombre accesible del botón; el estado lo da aria-pressed. */
  boton3d: string;
  boton3dPoner: string;
  boton3dQuitar: string;
  /** Escala oculta con inclinación o sobre el globo (RF-INT-13). */
  sinEscala: string;
  /** Teclas para girar, inclinar y volver al norte en 3D (RF-INT-15). */
  teclas3d: string;
  /** Lista de huellas de las series en el globo, para lectores de pantalla (RF-INT-16). */
  huellas: string;
  /** Igual que CAUSES de services/verdicts/src/verdicts/narrative.py. */
  causas: Record<string, string>;
}

const CAUSAS_ES: Record<string, string> = {
  outside_scene: "la zona queda fuera de la pasada",
  invalid_or_partial: "datos inválidos o parcialmente enfocados",
  input_exception: "anomalía en los datos de entrada",
  low_looks: "muy pocas muestras de radar por píxel",
  no_data: "píxeles sin dato utilizable",
  terrain: "relieve que oculta o distorsiona la señal",
};

const CAUSAS_EN: Record<string, string> = {
  outside_scene: "the area falls outside the pass",
  invalid_or_partial: "invalid or partially focused data",
  input_exception: "input data anomaly",
  low_looks: "too few radar samples per pixel",
  no_data: "pixels without usable data",
  terrain: "terrain hides or distorts the signal",
};

export const TEXTOS: Record<Idioma, Textos> = {
  es: {
    mapaDe: (z) => `Mapa de ${z}`,
    extensionDe: (z) => `Extensión de ${z}`,
    zonaPorDefecto: "la zona de estudio",
    sintetico: "Datos sintéticos: no son una observación real",
    capa: "Capa",
    capas: {
      state: "Estado",
      change_hh: "Cambio HH",
      change_hv: "Cambio HV",
      subsidence: "Hundimiento",
    },
    opacidad: "Opacidad",
    leyenda: "Leyenda",
    cambioProbable: "Cambio probable",
    sinCambio: "Sin cambio detectable",
    sinCambioNota: "sin color, se ve el mapa",
    noObservable: "No observable",
    noObservableNota: "el radar no pudo medir aquí; no es «sin cambio»",
    causaPrincipal: "Causa principal",
    bajo: "Bajó",
    subio: "Subió",
    hundeMenos: "Umbral de la zona",
    hundeMas: "≥ 2 × umbral",
    escalaHundimiento:
      "Cuánto se hunde el suelo respecto al resto de la zona (interferogramas NISAR). Sin color: por debajo del umbral de esta zona, que no se distingue del ruido; la cifra está en la tarjeta «¿Se hunde el suelo?».",
    escalaDb:
      "Cuánto cambió el brillo del radar, en decibelios (dB). Rojo: bajó; azul: subió. Entre −1,5 y +1,5 dB casi no cambió y no se pinta; desde 3 dB, color fuerte.",
    avisoEscena:
      "Aviso: entre estas dos fechas cambió el nivel de toda la escena. Parte de lo marcado puede no ser un cambio local.",
    notaEscenaCorregida:
      "Nota: entre estas dos fechas cambió el nivel de toda la escena; ese cambio ya se descontó antes de medir lo marcado.",
    puntoSeleccionado: "Punto seleccionado",
    lon: "Lon",
    lat: "Lat",
    serie: "Serie",
    cargandoSerie: "Cargando la historia del punto…",
    fueraDeSerie: "El punto queda fuera de la zona con datos.",
    errorSerie: "No se pudo cargar la historia del punto.",
    sinDato: "sin dato",
    fecha: "Fecha",
    valoresPorFecha: "Brillo del radar por fecha",
    estadoPorPar: "Resultado entre pasadas consecutivas",
    verTabla: "Ver los valores",
    graficaAria: "Brillo del radar HH y HV en este punto a lo largo del tiempo",
    ayudaTeclado: "Enter: ver la historia del punto central",
    cerrar: "Cerrar",
    comparador: "Imagen óptica",
    antes: "Antes",
    despues: "Después",
    radar: "Radar",
    optico: "Óptico Sentinel-2",
    deslizador: "Deslizador entre radar (izquierda) e imagen óptica (derecha)",
    escenaDel: (f) => `Escena del ${f} UTC`,
    diasRadar: (d) =>
      d === 0
        ? "el mismo día que la pasada de radar"
        : `${Math.abs(d)} ${Math.abs(d) === 1 ? "día" : "días"} ${d < 0 ? "antes" : "después"} de la pasada de radar`,
    nubes: (p) => `Nubes: ${p} % de la tesela completa, no de la zona`,
    estadosOpticos: {
      cloudy: "Escena nublada: supera el límite de nubes, puede ocultar el suelo",
      partial_coverage: "La escena no cubre toda la zona",
      none_in_window: "No hay escena Sentinel-2 cercana a esta fecha",
      catalog_unavailable: "El catálogo de imágenes ópticas no respondió",
    },
    sinMapa:
      "Este navegador no puede dibujar el mapa: necesita WebGL 2. La zona de estudio sigue arriba, en texto.",
    sin3d: {
      sin_aceleracion: "Mapa en 2D: el navegador no tiene aceleración gráfica para el globo 3D.",
      fallo_globo: "Mapa en 2D: el globo 3D falló en este navegador.",
      comparador: "Mapa en 2D mientras está el comparador, para que el radar y la imagen óptica casen.",
    },
    boton3d: "Globo 3D",
    boton3dPoner: "Ver el mapa como globo 3D, con giro e inclinación",
    boton3dQuitar: "Volver al mapa plano, con el norte arriba",
    sinEscala:
      "Sin barra de escala: en perspectiva o sobre el globo, las distancias cambian de un punto a otro de la pantalla.",
    teclas3d: "En 3D: Mayús + ← → gira, Mayús + ↑ ↓ inclina y N vuelve al norte.",
    huellas: "Huellas de las series en el mapa",
    causas: CAUSAS_ES,
  },
  en: {
    mapaDe: (z) => `Map of ${z}`,
    extensionDe: (z) => `Extent of ${z}`,
    zonaPorDefecto: "the study area",
    sintetico: "Synthetic data: not a real observation",
    capa: "Layer",
    capas: {
      state: "State",
      change_hh: "HH change",
      change_hv: "HV change",
      subsidence: "Subsidence",
    },
    opacidad: "Opacity",
    leyenda: "Legend",
    cambioProbable: "Probable change",
    sinCambio: "No detectable change",
    sinCambioNota: "no color, the map shows through",
    noObservable: "Not observable",
    noObservableNota: "the radar could not measure here; this is not “no change”",
    causaPrincipal: "Main cause",
    bajo: "Decreased",
    subio: "Increased",
    hundeMenos: "Area threshold",
    hundeMas: "≥ 2 × threshold",
    escalaHundimiento:
      "How much the ground sinks compared with the rest of the area (NISAR interferograms). No colour: below this area's threshold, which cannot be told apart from noise; the figure is in the «Is the ground sinking?» card.",
    escalaDb: "How much the radar brightness changed, in decibels (dB). Red: it fell; blue: it rose. Between −1.5 and +1.5 dB it barely changed and is not painted; from 3 dB, strong colour.",
    avisoEscena:
      "Warning: the level of the whole scene changed between these two dates. Some of what is marked may not be a local change.",
    notaEscenaCorregida:
      "Note: the level of the whole scene changed between these two dates; that change was subtracted before measuring what is marked.",
    puntoSeleccionado: "Selected point",
    lon: "Lon",
    lat: "Lat",
    serie: "Series",
    cargandoSerie: "Loading the point's history…",
    fueraDeSerie: "The point falls outside the area with data.",
    errorSerie: "The point's history could not be loaded.",
    sinDato: "no data",
    fecha: "Date",
    valoresPorFecha: "Radar brightness by date",
    estadoPorPar: "Result between consecutive passes",
    verTabla: "Show the values",
    graficaAria: "HH and HV radar brightness at this point over time",
    ayudaTeclado: "Enter: show the history of the center point",
    cerrar: "Close",
    comparador: "Optical image",
    antes: "Before",
    despues: "After",
    radar: "Radar",
    optico: "Sentinel-2 optical",
    deslizador: "Slider between radar (left) and optical image (right)",
    escenaDel: (f) => `Scene of ${f} UTC`,
    diasRadar: (d) =>
      d === 0
        ? "same day as the radar pass"
        : `${Math.abs(d)} ${Math.abs(d) === 1 ? "day" : "days"} ${d < 0 ? "before" : "after"} the radar pass`,
    nubes: (p) => `Clouds: ${p} % of the whole tile, not of the area`,
    estadosOpticos: {
      cloudy: "Cloudy scene: above the cloud limit, it may hide the ground",
      partial_coverage: "The scene does not cover the whole area",
      none_in_window: "No Sentinel-2 scene close to this date",
      catalog_unavailable: "The optical image catalog did not respond",
    },
    sinMapa:
      "This browser cannot draw the map: it needs WebGL 2. The study area is still shown above, as text.",
    sin3d: {
      sin_aceleracion: "Map in 2D: the browser has no graphics acceleration for the 3D globe.",
      fallo_globo: "Map in 2D: the 3D globe failed in this browser.",
      comparador: "Map in 2D while the comparator is on, so that radar and optical imagery line up.",
    },
    boton3d: "3D globe",
    boton3dPoner: "Show the map as a 3D globe, with rotation and tilt",
    boton3dQuitar: "Back to the flat map, north up",
    sinEscala:
      "No scale bar: in perspective or on the globe, distances change from one point of the screen to another.",
    teclas3d: "In 3D: Shift + ← → rotates, Shift + ↑ ↓ tilts and N resets north.",
    huellas: "Series footprints on the map",
    causas: CAUSAS_EN,
  },
};
