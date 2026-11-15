/**
 * Créditos de los datos y aviso de lo que la app recaba, para la sección «Datos y créditos» del portal. Mismo
 * contenido que `NOTICE` y `docs/PRIVACIDAD.md`: si cambia una fuente o lo que se guarda, se cambian los tres.
 * Lo que se guarda se comprobó en el código el 2026-11-15 (tablas de `auth` y `research`, `localStorage` del
 * frontend y procesado en línea).
 */
export interface Credito {
  datos: string
  quien: string
  licencia: string
}

export interface ContenidoCreditos {
  creditosTitulo: string
  columnas: [string, string, string]
  creditos: Credito[]
  licencia: string
  privacidadTitulo: string
  privacidadEntrada: string
  privacidad: { titulo: string; texto: string }[]
}

export const CREDITOS_ES: ContenidoCreditos = {
  creditosTitulo: 'Créditos de los datos',
  columnas: ['Datos', 'De quién', 'Licencia o condiciones'],
  creditos: [
    { datos: 'NISAR L2 GCOV (radar, HH y HV)', quien: 'NASA/JPL e ISRO; distribuye ASF DAAC (NASA Earthdata)', licencia: 'Datos abiertos de NASA; cuenta gratuita de Earthdata' },
    { datos: 'Catálogo y vistas previas de pasadas', quien: 'NASA CMR y ASF DAAC (Vertex)', licencia: 'Abiertos' },
    { datos: 'OPERA DSWx-S1 (agua desde Sentinel-1)', quien: 'NASA/JPL, proyecto OPERA; distribuye PO.DAAC', licencia: 'Abiertos, con cuenta de Earthdata' },
    { datos: 'Copernicus Sentinel-2 L2A (óptico)', quien: 'ESA y Comisión Europea, vía Earth Search de Element 84', licencia: 'Términos de Copernicus, con atribución' },
    { datos: 'Sentinel-2 cloudless 2016 (mapa base)', quien: 'EOX IT Services, con datos de Copernicus', licencia: 'CC BY 4.0' },
    { datos: 'Calles y nombres de lugares (Nominatim)', quien: 'Colaboradores de OpenStreetMap', licencia: 'ODbL' },
    { datos: 'Copernicus DEM GLO-30 (relieve)', quien: 'ESA y Airbus, vía AWS Open Data', licencia: 'Licencia de Copernicus DEM, con atribución' },
    { datos: 'Sismos (ComCat)', quien: 'USGS', licencia: 'Dominio público' },
    { datos: 'Alertas de desastres', quien: 'GDACS (Comisión Europea y ONU)', licencia: 'Abiertos, con atribución' },
    { datos: 'Activaciones de emergencia', quien: 'Copernicus EMS Rapid Mapping', licencia: 'Abiertos, con atribución' },
    { datos: 'Eventos naturales y deslizamientos', quien: 'NASA EONET y NASA Global Landslide Catalog', licencia: 'Abiertos' },
    { datos: 'Ciclones tropicales (IBTrACS)', quien: 'NOAA NCEI', licencia: 'Dominio público' },
    { datos: 'Cuencas, uso de suelo y localidades de México', quien: 'INEGI', licencia: 'Términos de libre uso de INEGI' },
    { datos: 'Archivo RADARSAT-1 y RCM (búsqueda)', quien: 'Agencia Espacial Canadiense, vía EODMS', licencia: 'Abierto (RADARSAT-1)' },
    { datos: 'Tormenta del 1 de julio de 2026 en Parral', quien: 'Protección Civil del Gobierno de Chihuahua y prensa local', licencia: 'Citado con enlace' },
  ],
  licencia:
    'El código de GeoLatido es abierto bajo la licencia Apache 2.0. Los datos conservan la licencia de su fuente; el archivo NOTICE del repositorio repite estos créditos.',
  privacidadTitulo: 'Qué datos recabamos',
  privacidadEntrada: 'Sin cuenta no guardamos nada que te identifique. Esto es todo lo que la app guarda o envía:',
  privacidad: [
    {
      titulo: 'Búsquedas de lugares',
      texto:
        'El texto que buscas o el punto donde haces clic se envía a Nominatim de OpenStreetMap para obtener el nombre y las coordenadas. Guardamos esa respuesta en caché, sin saber quién la pidió.',
    },
    {
      titulo: 'Zonas procesadas e investigaciones',
      texto:
        'Al procesar una zona guardamos su nombre, su caja y los resultados del veredicto, que quedan visibles para todos. Las investigaciones guardan la pregunta y la historia generada, sin datos de quien preguntó.',
    },
    {
      titulo: 'Si creas una cuenta',
      texto:
        'Guardamos tu correo, la contraseña cifrada con Argon2 (nunca en claro), el perfil que declaras y la fecha. La sesión usa una cookie propia solo para renovar el acceso. Lo que publicas sale con un seudónimo (GL-XXXXXX); tu correo nunca se muestra.',
    },
    {
      titulo: 'Historias y valoraciones',
      texto:
        'Una historia publicada guarda su título, tus notas y las referencias a los datos; una valoración guarda las estrellas y tu perfil. Son visibles para todos con tu seudónimo.',
    },
    {
      titulo: 'En tu navegador',
      texto:
        'Guardamos el idioma, si ya viste la ventana de bienvenida y si tienes sesión. Sin analítica ni cookies de terceros. Las imágenes del mapa base las pide tu navegador a EOX y OpenStreetMap, que ven tu dirección IP como cualquier sitio web.',
    },
    {
      titulo: 'En el servidor',
      texto:
        'El servidor guarda registros técnicos de cada petición (dirección IP, ruta y hora) para detectar fallos. La cuenta de NASA Earthdata que lee los datos es del servidor, no tuya.',
    },
  ],
}

export const CREDITOS_EN: ContenidoCreditos = {
  creditosTitulo: 'Data credits',
  columnas: ['Data', 'From', 'Licence or terms'],
  creditos: [
    { datos: 'NISAR L2 GCOV (radar, HH and HV)', quien: 'NASA/JPL and ISRO; distributed by ASF DAAC (NASA Earthdata)', licencia: 'NASA open data; free Earthdata account' },
    { datos: 'Pass catalogue and previews', quien: 'NASA CMR and ASF DAAC (Vertex)', licencia: 'Open' },
    { datos: 'OPERA DSWx-S1 (water from Sentinel-1)', quien: 'NASA/JPL OPERA project; distributed by PO.DAAC', licencia: 'Open, with Earthdata account' },
    { datos: 'Copernicus Sentinel-2 L2A (optical)', quien: 'ESA and European Commission, via Element 84 Earth Search', licencia: 'Copernicus terms, with attribution' },
    { datos: 'Sentinel-2 cloudless 2016 (base map)', quien: 'EOX IT Services, with Copernicus data', licencia: 'CC BY 4.0' },
    { datos: 'Streets and place names (Nominatim)', quien: 'OpenStreetMap contributors', licencia: 'ODbL' },
    { datos: 'Copernicus DEM GLO-30 (terrain)', quien: 'ESA and Airbus, via AWS Open Data', licencia: 'Copernicus DEM licence, with attribution' },
    { datos: 'Earthquakes (ComCat)', quien: 'USGS', licencia: 'Public domain' },
    { datos: 'Disaster alerts', quien: 'GDACS (European Commission and UN)', licencia: 'Open, with attribution' },
    { datos: 'Emergency activations', quien: 'Copernicus EMS Rapid Mapping', licencia: 'Open, with attribution' },
    { datos: 'Natural events and landslides', quien: 'NASA EONET and NASA Global Landslide Catalog', licencia: 'Open' },
    { datos: 'Tropical cyclones (IBTrACS)', quien: 'NOAA NCEI', licencia: 'Public domain' },
    { datos: 'Watersheds, land use and towns in Mexico', quien: 'INEGI', licencia: 'INEGI free-use terms' },
    { datos: 'RADARSAT-1 and RCM archive (search)', quien: 'Canadian Space Agency, via EODMS', licencia: 'Open (RADARSAT-1)' },
    { datos: '1 July 2026 storm in Parral', quien: 'Chihuahua State Civil Protection and local press', licencia: 'Cited with link' },
  ],
  licencia:
    'The GeoLatido code is open source under the Apache License 2.0. Data keep the licence of their source; the repository NOTICE file repeats these credits.',
  privacidadTitulo: 'What data we collect',
  privacidadEntrada: 'Without an account we keep nothing that identifies you. This is everything the app stores or sends:',
  privacidad: [
    {
      titulo: 'Place searches',
      texto:
        'The text you search or the point you click is sent to OpenStreetMap Nominatim to get the name and coordinates. We cache that answer without knowing who asked.',
    },
    {
      titulo: 'Processed areas and research',
      texto:
        'When an area is processed we keep its name, its box and the verdict results, which everyone can see. Research keeps the question and the generated story, with no data about who asked.',
    },
    {
      titulo: 'If you create an account',
      texto:
        'We keep your email, your password hashed with Argon2 (never in plain text), the profile you declare and the date. The session uses a first-party cookie only to renew access. What you publish appears under a pseudonym (GL-XXXXXX); your email is never shown.',
    },
    {
      titulo: 'Stories and ratings',
      texto:
        'A published story keeps its title, your notes and the data references; a rating keeps the stars and your profile. Everyone can see them under your pseudonym.',
    },
    {
      titulo: 'In your browser',
      texto:
        'We store the language, whether you saw the welcome window and whether you have a session. No analytics and no third-party cookies. Base map images are requested by your browser from EOX and OpenStreetMap, which see your IP address like any website.',
    },
    {
      titulo: 'On the server',
      texto:
        'The server keeps technical logs of each request (IP address, path and time) to detect failures. The NASA Earthdata account that reads the data belongs to the server, not to you.',
    },
  ],
}
