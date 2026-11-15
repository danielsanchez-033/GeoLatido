import type { NombreIcono } from './Iconos'
import { CIENCIA_EN, CIENCIA_ES } from './portalCiencia'
import { CREDITOS_EN, CREDITOS_ES, type ContenidoCreditos } from './portalCreditos'

/**
 * Textos de las ventanas informativas (components/Portal.tsx). Cada afirmación sale de lo que el sistema hace
 * hoy (MEMORY.md y las especificaciones): lo que solo está en la API se dice como API, y lo que no está
 * calibrado se dice así (constitución II.4).
 */
export interface DiapositivaTexto {
  icono: NombreIcono
  antetitulo?: string
  titulo: string
  texto: string
  puntos?: string[]
}

/** Sección «Radar y ciencia»: qué mide el radar, polarizaciones, zona de estudio, hipótesis, causas, implicaciones y
 * aplicaciones futuras. Las cifras de Parral salen de los veredictos reales de T048 y T171 (MEMORY.md, 2026-11-15). */
export interface ContenidoCiencia {
  titulo: string
  entrada: string
  mide: DiapositivaTexto[]
  polTitulo: string
  polEntrada: string
  polColumnas: [string, string, string]
  polarizaciones: { codigo: string; resalta: string; disponible: string }[]
  polParral: { titulo: string; cifras: { valor: string; texto: string }[]; lectura: string }
  zona: { titulo: string; texto: string; puntos: string[] }
  bloquesTitulo: string
  bloques: DiapositivaTexto[]
  nota: string
}

export interface ContenidoPortal {
  secciones: { inicio: string; como: string; ciencia: string; datos: string; cuenta: string }
  inicio: {
    antetitulo: string
    titulo: string
    entrada: string
    cifras: { valor: string; texto: string }[]
    carrusel: DiapositivaTexto[]
    empezar: string
  }
  como: { titulo: string; entrada: string; carrusel: DiapositivaTexto[]; estadosTitulo: string; estados: { titulo: string; texto: string }[] }
  datos: { titulo: string; entrada: string; carrusel: DiapositivaTexto[]; honestidad: string }
  creditos: ContenidoCreditos
  ciencia: ContenidoCiencia
  cuenta: {
    titulo: string
    entrada: string
    ventajas: DiapositivaTexto[]
    tablaTitulo: string
    columnas: [string, string, string]
    filas: { que: string; publico: boolean | string; estudiante: boolean | string; investigacion: boolean | string }[]
    crear: string
    entrar: string
    nota: string
  }
}

const ES: ContenidoPortal = {
  secciones: { inicio: 'Inicio', como: 'Cómo funciona', ciencia: 'Radar y ciencia', datos: 'Datos y créditos', cuenta: 'Tu cuenta' },
  ciencia: CIENCIA_ES,
  creditos: CREDITOS_ES,
  inicio: {
    antetitulo: 'Radar NISAR para todos',
    titulo: 'Qué cambió, qué no se detectó y qué no se puede saber',
    entrada:
      'GeoLatido convierte las imágenes de radar del satélite NISAR en veredictos que cualquiera puede leer y auditar, empezando por Hidalgo del Parral, Chihuahua. Cada veredicto dice también lo que el radar no pudo ver.',
    cifras: [
      { valor: '3', texto: 'estados posibles, nunca un «sí» o «no» sin matices' },
      { valor: '2', texto: 'series de radar sobre la zona, T048 y T171' },
      { valor: '12 días', texto: 'entre una pasada y la siguiente de cada serie' },
    ],
    carrusel: [
      {
        icono: 'hallazgos',
        antetitulo: 'Veredictos',
        titulo: 'Un veredicto por par de fechas',
        texto: 'Elige dos pasadas del satélite y lee qué detectamos, qué no prueba y qué falta, con el recibo de los datos que lo respaldan.',
      },
      {
        icono: 'historia',
        antetitulo: 'La historia de Parral',
        titulo: 'La tormenta del 1 de julio de 2026',
        texto: 'Un recorrido guiado: por qué el radar no pudo ver la inundación y qué sí cambió después en la zona.',
      },
      {
        icono: 'evento',
        antetitulo: '¿Pudo verlo?',
        titulo: 'Pregunta por un evento',
        texto: 'Indica cuándo pasó algo y cuánto duró: la app te dice si alguna pasada del radar lo alcanzó o por qué no.',
      },
      {
        icono: 'comparar',
        antetitulo: 'Antes y después',
        titulo: 'Compara con imágenes ópticas',
        texto: 'Desliza la división dentro de la zona para ver la escena Sentinel-2 de antes y la de después, también en el globo 3D.',
      },
      {
        icono: 'comunidad',
        antetitulo: 'Comunidad',
        titulo: 'Historias de otras personas',
        texto: 'Lee las investigaciones que publica la comunidad, con sus pares de fechas y sus notas, y valóralas con estrellas.',
      },
    ],
    empezar: 'Explorar el mapa',
  },
  como: {
    titulo: 'Del satélite al veredicto',
    entrada: 'Cinco pasos, todos abiertos: cualquiera puede ver los números que hay detrás de cada frase.',
    carrusel: [
      {
        icono: 'satelite',
        antetitulo: 'Paso 1',
        titulo: 'NISAR mide la superficie',
        texto: 'NISAR, de la NASA y la ISRO, es un radar de banda L: ve a través de las nubes y de noche, porque emite su propia señal.',
        puntos: ['Producto GCOV: retrodispersión en HH y HV', 'Una pasada cada 12 días por serie'],
      },
      {
        icono: 'mapa',
        antetitulo: 'Paso 2',
        titulo: 'Solo el recorte de la zona',
        texto: 'Cada gránulo pesa unos 7 GB. Leemos por HTTPS solo el recorte de la zona, unos 300 MB por fecha.',
        puntos: ['Misma malla de 10 m en todas las fechas', 'Sin remuestrear entre las dos series'],
      },
      {
        icono: 'capas',
        antetitulo: 'Paso 3',
        titulo: 'Diferencia de la señal',
        texto: 'Comparamos dos fechas en decibelios, restamos el cambio de nivel de toda la escena y marcamos lo que el radar no puede ver bien.',
        puntos: ['Pocos looks, relieve (layover y sombra) y fuera de la escena', 'Dispersión del par publicada como ruido'],
      },
      {
        icono: 'hallazgos',
        antetitulo: 'Paso 4',
        titulo: 'Un veredicto en tres estados',
        texto: 'Con las reglas declaradas sale cambio probable, sin cambio detectable o no observable con su causa. Siempre con el recibo de los gránulos.',
      },
      {
        icono: 'ver',
        antetitulo: 'Paso 5',
        titulo: 'Contraste con otras fuentes',
        texto: 'Mostramos la escena Sentinel-2 más cercana y el agua de OPERA DSWx-S1. Si no coinciden, lo decimos como desacuerdo entre métodos.',
      },
    ],
    estadosTitulo: 'Los tres estados',
    estados: [
      { titulo: 'Cambio probable', texto: 'La señal cambió más de lo que explica el ruido en una parte suficiente de la zona.' },
      { titulo: 'Sin cambio detectable', texto: 'El radar vio la zona y no encontró un cambio por encima del umbral. No prueba que nada cambiara.' },
      { titulo: 'No observable', texto: 'El radar no pudo medir: no hubo pasada, faltan datos o el relieve lo impide. No es «sin cambio».' },
    ],
  },
  datos: {
    titulo: 'Datos abiertos, con su origen',
    entrada: 'Todo lo que ves sale de fuentes públicas y lleva su atribución.',
    carrusel: [
      {
        icono: 'satelite',
        antetitulo: 'Radar',
        titulo: 'NASA/ISRO NISAR, GCOV',
        texto: 'Misión de NASA/JPL e ISRO; datos de ASF DAAC (colección provisional). Serie T048 ascendente (10 fechas) y T171 descendente (8 fechas útiles; una se excluye por un defecto del producto).',
      },
      {
        icono: 'ver',
        antetitulo: 'Óptico',
        titulo: 'Copernicus Sentinel-2',
        texto: 'La escena más cercana a ±10 días de cada pasada, con hasta un 30 % de nubes. Si solo hay una más nublada, la mostramos y lo avisamos.',
      },
      {
        icono: 'nube',
        antetitulo: 'Agua',
        titulo: 'OPERA DSWx-S1',
        texto: 'Mapa de agua superficial a partir de Sentinel-1 para contrastar el agua que ve el radar. Detecta masas de más de 3 ha.',
      },
      {
        icono: 'cubo',
        antetitulo: 'Relieve',
        titulo: 'Copernicus DEM GLO-30',
        texto: 'El modelo de elevación que usamos para marcar layover y sombra del radar y para el relieve del mapa.',
      },
      {
        icono: 'mapa',
        antetitulo: 'Mapa base',
        titulo: 'Sentinel-2 cloudless y OpenStreetMap',
        texto: 'La Tierra a color es el mosaico sin nubes de EOX (2016, CC BY 4.0); las calles, de OpenStreetMap.',
      },
    ],
    honestidad:
      'Los umbrales se fijaron con el ruido de 16 pares reales de Parral, sin verdad de campo: los declaramos como supuestos. Si una zona usa datos sintéticos, la app lo marca siempre.',
  },
  cuenta: {
    titulo: 'Con tu cuenta, firma lo que publicas',
    entrada: 'Toda la información se ve igual con o sin cuenta. La cuenta solo hace falta para publicar tus historias y valorar las de otros: así se sabe quién publica y con qué perfil.',
    ventajas: [
      {
        icono: 'subir',
        antetitulo: 'Publica',
        titulo: 'Publica tus investigaciones',
        texto: 'Arma una historia con los pares de fechas que elegiste y tus notas, y publícala para la comunidad. Solo guarda referencias a los datos, nunca textos inventados.',
      },
      {
        icono: 'cuenta',
        antetitulo: 'Autoría',
        titulo: 'Tu seudónimo y tu perfil',
        texto: 'Lo que publicas sale con un seudónimo estable (GL-XXXXXX) y tu perfil, estudiante o investigación. Nunca se muestra tu correo.',
      },
      {
        icono: 'estrella',
        antetitulo: 'Valora',
        titulo: 'Estrellas por perfil',
        texto: 'Valora de 1 a 5 las historias de los demás. Cada historia muestra su promedio y el de estudiantes y el de investigación por separado.',
      },
      {
        icono: 'buscar',
        antetitulo: 'Busca',
        titulo: 'Búsqueda de veredictos en la API',
        texto: 'Filtra por estado, fechas, texto libre o un rectángulo del mapa. Con investigación, también por ruido y hasta 500 resultados por página.',
      },
      {
        icono: 'recibo',
        antetitulo: 'Exporta',
        titulo: 'Exporta en CSV, GeoJSON o JSON',
        texto: 'Con el perfil de investigación, la API exporta la búsqueda completa con umbrales, supuestos y si cada uno está calibrado.',
      },
      {
        icono: 'llave',
        antetitulo: 'Automatiza',
        titulo: 'Tokens personales',
        texto: 'Con el perfil de investigación, crea tokens de 1 a 90 días para usar la API desde tus programas, y revócalos cuando quieras.',
      },
    ],
    tablaTitulo: 'Qué incluye cada perfil',
    columnas: ['Sin cuenta', 'Estudiante', 'Investigación'],
    filas: [
      { que: 'Veredictos, mapa, historia y consulta de eventos', publico: true, estudiante: true, investigacion: true },
      { que: 'Leer y descargar las historias de la comunidad', publico: true, estudiante: true, investigacion: true },
      { que: 'Evidencia explicada, en tabla y con enlace al JSON', publico: true, estudiante: true, investigacion: true },
      { que: 'Capas del radar y comparador', publico: true, estudiante: true, investigacion: true },
      { que: 'Publicar y valorar historias, con tu seudónimo y perfil', publico: false, estudiante: true, investigacion: true },
      { que: 'Búsqueda en la API', publico: false, estudiante: 'hasta 50 por página', investigacion: 'hasta 500, con ruido' },
      { que: 'Exportación y tokens personales', publico: false, estudiante: false, investigacion: true },
    ],
    crear: 'Crear cuenta',
    entrar: 'Ya tengo cuenta',
    nota: 'El perfil es declarado, no verificado: se muestra junto a lo que publicas, pero no cambia lo que ves. Los datos y los veredictos son iguales para todos.',
  },
}

const EN: ContenidoPortal = {
  secciones: { inicio: 'Home', como: 'How it works', ciencia: 'Radar & science', datos: 'Data & credits', cuenta: 'Your account' },
  ciencia: CIENCIA_EN,
  creditos: CREDITOS_EN,
  inicio: {
    antetitulo: 'NISAR radar for everyone',
    titulo: 'What changed, what was not detected and what cannot be known',
    entrada:
      'GeoLatido turns radar images from the NISAR satellite into verdicts anyone can read and audit, starting with Hidalgo del Parral, Chihuahua. Every verdict also says what the radar could not see.',
    cifras: [
      { valor: '3', texto: 'possible states, never a bare “yes” or “no”' },
      { valor: '2', texto: 'radar series over the area, T048 and T171' },
      { valor: '12 days', texto: 'between one pass and the next in each series' },
    ],
    carrusel: [
      {
        icono: 'hallazgos',
        antetitulo: 'Verdicts',
        titulo: 'One verdict per pair of dates',
        texto: 'Pick two satellite passes and read what we detected, what it does not prove and what is missing, with the receipt of the data behind it.',
      },
      {
        icono: 'historia',
        antetitulo: 'The Parral story',
        titulo: 'The storm of 1 July 2026',
        texto: 'A guided tour: why the radar could not see the flood and what did change in the area afterwards.',
      },
      {
        icono: 'evento',
        antetitulo: 'Could it see it?',
        titulo: 'Ask about an event',
        texto: 'Say when something happened and how long it lasted: the app tells you whether a radar pass reached it, or why not.',
      },
      {
        icono: 'comparar',
        antetitulo: 'Before and after',
        titulo: 'Compare with optical images',
        texto: 'Slide the split inside the area to see the Sentinel-2 scene before and after, also on the 3D globe.',
      },
      {
        icono: 'comunidad',
        antetitulo: 'Community',
        titulo: 'Stories from other people',
        texto: 'Read the research the community publishes, with its date pairs and notes, and rate it with stars.',
      },
    ],
    empezar: 'Explore the map',
  },
  como: {
    titulo: 'From the satellite to the verdict',
    entrada: 'Five steps, all open: anyone can see the numbers behind every sentence.',
    carrusel: [
      {
        icono: 'satelite',
        antetitulo: 'Step 1',
        titulo: 'NISAR measures the surface',
        texto: 'NISAR, by NASA and ISRO, is an L-band radar: it sees through clouds and at night, because it sends its own signal.',
        puntos: ['GCOV product: HH and HV backscatter', 'One pass every 12 days per series'],
      },
      {
        icono: 'mapa',
        antetitulo: 'Step 2',
        titulo: 'Only the area’s clip',
        texto: 'Each granule weighs about 7 GB. We read over HTTPS only the clip of the area, about 300 MB per date.',
        puntos: ['Same 10 m grid on every date', 'No resampling between the two series'],
      },
      {
        icono: 'capas',
        antetitulo: 'Step 3',
        titulo: 'Signal difference',
        texto: 'We compare two dates in decibels, subtract the level change of the whole scene and mark what the radar cannot see well.',
        puntos: ['Few looks, terrain (layover and shadow) and outside the scene', 'Pair dispersion published as noise'],
      },
      {
        icono: 'hallazgos',
        antetitulo: 'Step 4',
        titulo: 'A verdict in three states',
        texto: 'With declared rules we get probable change, no detectable change or not observable with its cause. Always with the receipt of the granules.',
      },
      {
        icono: 'ver',
        antetitulo: 'Step 5',
        titulo: 'Checked against other sources',
        texto: 'We show the nearest Sentinel-2 scene and OPERA DSWx-S1 water. If they disagree, we say it as a disagreement between methods.',
      },
    ],
    estadosTitulo: 'The three states',
    estados: [
      { titulo: 'Probable change', texto: 'The signal changed more than noise explains over a large enough part of the area.' },
      { titulo: 'No detectable change', texto: 'The radar saw the area and found no change above the threshold. It does not prove nothing changed.' },
      { titulo: 'Not observable', texto: 'The radar could not measure: no pass, missing data or terrain in the way. It is not “no change”.' },
    ],
  },
  datos: {
    titulo: 'Open data, with its origin',
    entrada: 'Everything you see comes from public sources and carries its attribution.',
    carrusel: [
      {
        icono: 'satelite',
        antetitulo: 'Radar',
        titulo: 'NASA/ISRO NISAR, GCOV',
        texto: 'NASA/JPL and ISRO mission; data from ASF DAAC (provisional collection). Series T048 ascending (10 dates) and T171 descending (8 usable dates; one is excluded for a product defect).',
      },
      {
        icono: 'ver',
        antetitulo: 'Optical',
        titulo: 'Copernicus Sentinel-2',
        texto: 'The nearest scene within ±10 days of each pass, with up to 30 % clouds. If only a cloudier one exists, we show it and say so.',
      },
      {
        icono: 'nube',
        antetitulo: 'Water',
        titulo: 'OPERA DSWx-S1',
        texto: 'Surface water map from Sentinel-1 to check the water the radar sees. It detects bodies larger than 3 ha.',
      },
      {
        icono: 'cubo',
        antetitulo: 'Terrain',
        titulo: 'Copernicus DEM GLO-30',
        texto: 'The elevation model we use to mark radar layover and shadow and for the map relief.',
      },
      {
        icono: 'mapa',
        antetitulo: 'Basemap',
        titulo: 'Sentinel-2 cloudless and OpenStreetMap',
        texto: 'The full-color Earth is the EOX cloudless mosaic (2016, CC BY 4.0); the streets come from OpenStreetMap.',
      },
    ],
    honestidad:
      'Thresholds were set with the noise of 16 real Parral pairs, without ground truth: we declare them as assumptions. If an area uses synthetic data, the app always marks it.',
  },
  cuenta: {
    titulo: 'With your account, sign what you publish',
    entrada: 'All information looks the same with or without an account. You only need one to publish your stories and rate others’: that way everyone knows who publishes and with which profile.',
    ventajas: [
      {
        icono: 'subir',
        antetitulo: 'Publish',
        titulo: 'Publish your research',
        texto: 'Build a story with the date pairs you chose and your notes, and publish it for the community. It only stores references to the data, never made-up text.',
      },
      {
        icono: 'cuenta',
        antetitulo: 'Authorship',
        titulo: 'Your alias and profile',
        texto: 'What you publish shows a stable alias (GL-XXXXXX) and your profile, student or research. Your email is never shown.',
      },
      {
        icono: 'estrella',
        antetitulo: 'Rate',
        titulo: 'Stars by profile',
        texto: 'Rate other people’s stories from 1 to 5. Each story shows its average and the student and research averages separately.',
      },
      {
        icono: 'buscar',
        antetitulo: 'Search',
        titulo: 'Verdict search in the API',
        texto: 'Filter by state, dates, free text or a map rectangle. With research, also by noise and up to 500 results per page.',
      },
      {
        icono: 'recibo',
        antetitulo: 'Export',
        titulo: 'Export as CSV, GeoJSON or JSON',
        texto: 'With the research profile, the API exports the full search with thresholds, assumptions and whether each is calibrated.',
      },
      {
        icono: 'llave',
        antetitulo: 'Automate',
        titulo: 'Personal tokens',
        texto: 'With the research profile, create tokens of 1 to 90 days to use the API from your programs, and revoke them anytime.',
      },
    ],
    tablaTitulo: 'What each profile includes',
    columnas: ['No account', 'Student', 'Research'],
    filas: [
      { que: 'Verdicts, map, story and event query', publico: true, estudiante: true, investigacion: true },
      { que: 'Read and download community stories', publico: true, estudiante: true, investigacion: true },
      { que: 'Evidence explained, in a table and with a link to the JSON', publico: true, estudiante: true, investigacion: true },
      { que: 'Radar layers and comparator', publico: true, estudiante: true, investigacion: true },
      { que: 'Publish and rate stories, with your alias and profile', publico: false, estudiante: true, investigacion: true },
      { que: 'API search', publico: false, estudiante: 'up to 50 per page', investigacion: 'up to 500, with noise' },
      { que: 'Export and personal tokens', publico: false, estudiante: false, investigacion: true },
    ],
    crear: 'Create account',
    entrar: 'I have an account',
    nota: 'The profile is declared, not verified: it is shown next to what you publish, but it does not change what you see. Data and verdicts are the same for everyone.',
  },
}

export function contenidoPortal(idioma: string): ContenidoPortal {
  return idioma.startsWith('en') ? EN : ES
}
