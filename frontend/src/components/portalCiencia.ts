import type { ContenidoCiencia } from './portalContenido'

/**
 * Textos de la sección «Radar y ciencia» del portal. Las cifras de Parral salen de los veredictos reales de T048
 * (9 pares consecutivos) y T171 (7) que sirve `verdicts`, consultados el 2026-11-15 (MEMORY.md); las causas se
 * dicen como hipótesis, nunca como hechos (constitución II.4).
 */
export const CIENCIA_ES: ContenidoCiencia = {
  titulo: 'Qué mide el radar y qué aprendimos',
  entrada:
    'El mapa muestra cambios en el eco del radar, no fotos. Aquí explicamos qué significa ese eco, qué polarización resalta cada cambio y qué hipótesis sacamos de Parral, junto con lo que el radar no pudo ver.',
  mide: [
    {
      icono: 'satelite',
      antetitulo: 'Luz propia',
      titulo: 'De día, de noche y a través de las nubes',
      texto:
        'NISAR emite pulsos de microondas y mide el eco que vuelve. No depende del Sol, y las nubes y la lluvia ligera son casi transparentes en banda L (ondas de unos 24 cm) y en banda S (unos 10 cm, el radar de la ISRO).',
    },
    {
      icono: 'cubo',
      antetitulo: 'Forma',
      titulo: 'Rugosidad y estructura',
      texto:
        'Una superficie rugosa, un bosque o un edificio devuelven mucho eco y se ven claros. El agua tranquila y el asfalto liso reflejan la señal lejos del satélite y se ven oscuros.',
    },
    {
      icono: 'nube',
      antetitulo: 'Agua',
      titulo: 'Humedad: la constante dieléctrica',
      texto:
        'El agua cambia cómo conduce el suelo la señal (su constante dieléctrica). Un suelo mojado devuelve más eco que uno seco, así que una lluvia puede aclarar toda la escena sin que cambie nada en el terreno.',
    },
    {
      icono: 'capas',
      antetitulo: 'Movimiento',
      titulo: 'Desplazamientos de centímetros (InSAR)',
      texto:
        'Comparando la fase de la onda entre dos pasadas (interferometría, InSAR), NISAR mide movimientos del suelo de centímetros: subsidencia, deslizamientos o deformación por sismos.',
      puntos: [
        'Esta app usa GCOV, la intensidad del eco, que no trae fase: aquí no medimos desplazamientos.',
        'La pestaña Investigar lista los productos InSAR que existen para la zona (NISAR GUNW, OPERA DISP-S1).',
      ],
    },
    {
      icono: 'evento',
      antetitulo: 'Ritmo',
      titulo: 'Una pasada cada 12 días',
      texto:
        'Cada serie vuelve a la misma zona con la misma geometría cada 12 días. Lo que aparece y desaparece entre dos pasadas, como una calle inundada unas horas, no queda registrado.',
    },
  ],
  polTitulo: 'Polarizaciones: qué resalta cada una',
  polEntrada:
    'El radar envía la onda en horizontal (H) o vertical (V) y escucha en H o en V. Cada combinación responde a un tipo de superficie.',
  polColumnas: ['Polarización', 'Qué resalta mejor', 'Dónde está'],
  polarizaciones: [
    {
      codigo: 'HH',
      resalta: 'Suelo, humedad, agua abierta e inundación bajo árboles (doble rebote tronco-agua). En hielo, la superficie y las grietas.',
      disponible: 'NISAR banda L. Es la que usamos para decidir el cambio, junto con HV.',
    },
    {
      codigo: 'HV',
      resalta: 'Vegetación y biomasa: la señal cambia de plano al rebotar muchas veces entre hojas y ramas. Deforestación, cultivos que crecen o se cosechan.',
      disponible: 'NISAR banda L, en las series de doble polarización (DH) que procesamos.',
    },
    {
      codigo: 'VV',
      resalta: 'Rugosidad del agua por el viento, suelo desnudo y hielo marino. Es la más usada para inundaciones en banda C.',
      disponible: 'Sentinel-1 (banda C) y NISAR solo en los modos de polarización cuádruple (QP).',
    },
    {
      codigo: 'VH',
      resalta: 'Vegetación en banda C, donde la onda corta se queda en las copas. Separa cultivos y bosque del suelo.',
      disponible: 'Sentinel-1 (banda C) y NISAR en modo QP.',
    },
  ],
  polParral: {
    titulo: 'Lo que midieron HH y HV en Parral',
    cifras: [
      { valor: '16 de 16', texto: 'pares en los que toda la escena se aclaró u oscureció en el mismo sentido en HH y en HV' },
      { valor: '1,18 dB', texto: 'desplazamiento medio de la escena en HH, frente a 0,74 dB en HV' },
      { valor: '1,19 dB', texto: 'dispersión de la diferencia en HH en el par del 17 al 29 de junio, frente a 0,90 dB en HV' },
    ],
    lectura:
      'En una zona semiárida con lluvias de verano, HH reacciona más a lo que cambia en toda la escena, como la humedad del suelo, y también es más ruidosa. HV es más estable y por eso ayuda a separar un cambio local de un cambio de toda la escena. Por eso el veredicto usa las dos: resta a cada par el desplazamiento de la escena y exige el cambio en HH o HV por encima del umbral. Comparada con Sentinel-1 (banda C, VV y VH) a través del agua de OPERA DSWx-S1, la banda L vio más agua (0,38 a 1,98 % de la zona frente a 0,08 %): las dos fuentes no coinciden, y lo decimos como desacuerdo entre métodos.',
  },
  zona: {
    titulo: 'Por qué Hidalgo del Parral',
    texto:
      'Parral, en el sur de Chihuahua, es una ciudad minera desde el siglo XVII, semiárida y con lluvias de monzón en verano. Es la zona del equipo: conocemos sus arroyos, sus minas y su clima.',
    puntos: [
      'Mezcla de causas: minería (jales y tajos), agricultura de temporal, crecimiento urbano y arroyos que se desbordan.',
      'Un evento verificado: la tormenta del 1 de julio de 2026, con 22,8 mm en una hora según Protección Civil de Chihuahua.',
      'Dos series de NISAR la cubren entera (T048 ascendente y T171 descendente) con 18 fechas útiles de junio a octubre de 2026.',
      'La misma app procesa en línea cualquier ciudad buscada en el mundo donde NISAR tenga HH y HV.',
    ],
  },
  bloquesTitulo: 'Hipótesis, causas y lo que implican',
  bloques: [
    {
      icono: 'ver',
      antetitulo: 'Lo que se ve',
      titulo: 'Hipótesis sobre lo que sí detectamos',
      texto: 'Son explicaciones posibles, no conclusiones: ninguna se comprobó en campo.',
      puntos: [
        'Los aclarados y oscurecidos de toda la escena siguen a las lluvias de julio a septiembre: humedad del suelo.',
        'Los dos pares con cambio probable (16 al 28 de agosto, 5,18 %, y 28 de agosto al 9 de septiembre, 9,56 %) caen en plena temporada de lluvias: crecimiento de vegetación y cultivos, o suelo removido.',
        'Junto a la Mina La Prieta no hubo cambio detectable en 9 pares: compatible con jales estables en ese periodo.',
      ],
    },
    {
      icono: 'info',
      antetitulo: 'Lo que no se ve',
      titulo: 'Hipótesis sobre lo que el radar no captó',
      texto: 'Que el radar no lo vea no significa que no ocurriera.',
      puntos: [
        'La tormenta del 1 de julio no se observó: no hubo pasada entre el 29 de junio y el 8 de julio, y el agua en calles dura horas.',
        'Calles inundadas y deslaves pequeños quedan por debajo de los 10 m del píxel y del 5 % de la zona que exige el veredicto.',
        'En laderas muy empinadas el radar no ve (layover y sombra, 0,05 % de la zona) y una fecha de T171 se excluyó por un defecto del producto.',
      ],
    },
    {
      icono: 'mapa',
      antetitulo: 'Causas naturales',
      titulo: 'Por qué cambia la superficie: la naturaleza',
      texto: 'Monzón de verano, sequía, crecimiento y secado de pastizales y matorral, erosión de laderas, crecidas de arroyos y nivel de las presas.',
    },
    {
      icono: 'cuenta',
      antetitulo: 'Causas humanas',
      titulo: 'Por qué cambia la superficie: las personas',
      texto: 'Minería (jales, tajos y caminos), siembra y cosecha de temporal, riego desde presas como La Boquilla, expansión urbana y obras en arroyos.',
    },
    {
      icono: 'hallazgos',
      antetitulo: 'Implicaciones',
      titulo: 'Qué significa un cambio para la zona',
      texto: 'Una lectura posible, para que cada persona decida qué revisar en campo.',
      puntos: [
        'Agua: la humedad y el agua superficial indican cuánto llovió y cómo responde el suelo, dato útil en una región con sequías.',
        'Agricultura: el ritmo de cultivos de temporal se ve cada 12 días, también con nubes.',
        'Infraestructura y comunidades: arroyos urbanos, laderas y presas de jales son lugares para vigilar tras una tormenta.',
        'Ecosistemas: el pastizal y el matorral cambian con el monzón; un cambio fuera de ese ritmo merece atención.',
      ],
    },
    {
      icono: 'satelite',
      antetitulo: 'Aplicaciones futuras',
      titulo: 'Lo que NISAR permitirá',
      texto: 'Con más fechas y otros productos de la misión:',
      puntos: [
        'Avisos de inundación de noche o con nubes, combinados con lluvia de satélite (GPM).',
        'Vigilancia de presas de jales y laderas con InSAR (GUNW) para movimientos de centímetros.',
        'Calendario de cultivos y humedad del suelo para planear el riego.',
        'Subsidencia por extracción de agua en ciudades y valles agrícolas.',
        'Glaciares, hielo marino y biomasa forestal a escala mundial, con banda L y S juntas.',
      ],
    },
  ],
  nota:
    'Ningún umbral está calibrado con verdad de campo: los fijamos con el ruido de 16 pares reales y los declaramos como supuestos. Las causas son hipótesis; el radar mide el eco, no el porqué.',
}

export const CIENCIA_EN: ContenidoCiencia = {
  titulo: 'What radar measures and what we learned',
  entrada:
    'The map shows changes in the radar echo, not photos. Here we explain what that echo means, which polarization highlights each change and which hypotheses we draw from Parral, along with what the radar could not see.',
  mide: [
    {
      icono: 'satelite',
      antetitulo: 'Own light',
      titulo: 'Day, night and through clouds',
      texto:
        'NISAR sends microwave pulses and measures the echo that returns. It does not need the Sun, and clouds and light rain are almost transparent at L band (waves of about 24 cm) and S band (about 10 cm, the ISRO radar).',
    },
    {
      icono: 'cubo',
      antetitulo: 'Shape',
      titulo: 'Roughness and structure',
      texto:
        'A rough surface, a forest or a building returns a strong echo and looks bright. Calm water and smooth pavement reflect the signal away from the satellite and look dark.',
    },
    {
      icono: 'nube',
      antetitulo: 'Water',
      titulo: 'Moisture: the dielectric constant',
      texto:
        'Water changes how the ground carries the signal (its dielectric constant). Wet soil returns more echo than dry soil, so rain can brighten a whole scene while nothing changes on the ground.',
    },
    {
      icono: 'capas',
      antetitulo: 'Motion',
      titulo: 'Centimetre displacements (InSAR)',
      texto:
        'By comparing the wave phase between two passes (interferometry, InSAR), NISAR measures ground motion of centimetres: subsidence, landslides or earthquake deformation.',
      puntos: [
        'This app uses GCOV, the echo intensity, which carries no phase: we do not measure displacement here.',
        'The Research tab lists the InSAR products that exist for the area (NISAR GUNW, OPERA DISP-S1).',
      ],
    },
    {
      icono: 'evento',
      antetitulo: 'Rhythm',
      titulo: 'One pass every 12 days',
      texto:
        'Each series returns to the same area with the same geometry every 12 days. Whatever appears and disappears between two passes, like a street flooded for a few hours, is not recorded.',
    },
  ],
  polTitulo: 'Polarizations: what each one highlights',
  polEntrada:
    'The radar sends the wave horizontally (H) or vertically (V) and listens in H or V. Each combination responds to a kind of surface.',
  polColumnas: ['Polarization', 'Best at highlighting', 'Where it is'],
  polarizaciones: [
    {
      codigo: 'HH',
      resalta: 'Soil, moisture, open water and flooding under trees (trunk-water double bounce). On ice, the surface and crevasses.',
      disponible: 'NISAR L band. We use it to decide change, together with HV.',
    },
    {
      codigo: 'HV',
      resalta: 'Vegetation and biomass: the signal switches plane after bouncing many times among leaves and branches. Deforestation, crops growing or harvested.',
      disponible: 'NISAR L band, in the dual-polarization (DH) series we process.',
    },
    {
      codigo: 'VV',
      resalta: 'Wind roughness on water, bare soil and sea ice. The most used for floods at C band.',
      disponible: 'Sentinel-1 (C band) and NISAR only in quad-polarization (QP) modes.',
    },
    {
      codigo: 'VH',
      resalta: 'Vegetation at C band, where the short wave stays in the canopy. Separates crops and forest from soil.',
      disponible: 'Sentinel-1 (C band) and NISAR in QP mode.',
    },
  ],
  polParral: {
    titulo: 'What HH and HV measured in Parral',
    cifras: [
      { valor: '16 of 16', texto: 'pairs in which the whole scene brightened or darkened in the same direction in HH and HV' },
      { valor: '1.18 dB', texto: 'mean scene shift in HH, against 0.74 dB in HV' },
      { valor: '1.19 dB', texto: 'spread of the HH difference in the 17–29 June pair, against 0.90 dB in HV' },
    ],
    lectura:
      'In a semi-arid area with summer rains, HH reacts more to what changes across the whole scene, such as soil moisture, and is also noisier. HV is steadier, which helps separate a local change from a scene-wide one. That is why the verdict uses both: it removes the scene shift from each pair and requires change in HH or HV above the threshold. Compared with Sentinel-1 (C band, VV and VH) through OPERA DSWx-S1 water, L band saw more water (0.38 to 1.98 % of the area against 0.08 %): the two sources disagree, and we report it as a disagreement between methods.',
  },
  zona: {
    titulo: 'Why Hidalgo del Parral',
    texto:
      'Parral, in southern Chihuahua, has been a mining town since the 17th century, semi-arid with monsoon rains in summer. It is the team’s home area: we know its streams, mines and climate.',
    puntos: [
      'A mix of causes: mining (tailings and pits), rain-fed farming, urban growth and streams that overflow.',
      'A verified event: the 1 July 2026 storm, with 22.8 mm in one hour according to Chihuahua Civil Protection.',
      'Two NISAR series cover it fully (T048 ascending and T171 descending) with 18 usable dates from June to October 2026.',
      'The same app processes online any city searched worldwide where NISAR has HH and HV.',
    ],
  },
  bloquesTitulo: 'Hypotheses, causes and what they imply',
  bloques: [
    {
      icono: 'ver',
      antetitulo: 'What is seen',
      titulo: 'Hypotheses about what we did detect',
      texto: 'Possible explanations, not conclusions: none was checked in the field.',
      puntos: [
        'Scene-wide brightening and darkening follows the July–September rains: soil moisture.',
        'The two pairs with probable change (16–28 August, 5.18 %, and 28 August–9 September, 9.56 %) fall in the middle of the rainy season: vegetation and crop growth, or disturbed soil.',
        'Next to the La Prieta mine there was no detectable change in 9 pairs: consistent with stable tailings in that period.',
      ],
    },
    {
      icono: 'info',
      antetitulo: 'What is not seen',
      titulo: 'Hypotheses about what the radar missed',
      texto: 'If the radar does not see it, that does not mean it did not happen.',
      puntos: [
        'The 1 July storm was not observed: there was no pass between 29 June and 8 July, and water in streets lasts hours.',
        'Flooded streets and small landslides fall below the 10 m pixel and the 5 % of the area the verdict requires.',
        'On very steep slopes the radar cannot see (layover and shadow, 0.05 % of the area), and one T171 date was excluded for a product defect.',
      ],
    },
    {
      icono: 'mapa',
      antetitulo: 'Natural causes',
      titulo: 'Why the surface changes: nature',
      texto: 'Summer monsoon, drought, grassland and shrub growing and drying, slope erosion, stream floods and reservoir levels.',
    },
    {
      icono: 'cuenta',
      antetitulo: 'Human causes',
      titulo: 'Why the surface changes: people',
      texto: 'Mining (tailings, pits and roads), rain-fed sowing and harvest, irrigation from reservoirs such as La Boquilla, urban growth and works in streams.',
    },
    {
      icono: 'hallazgos',
      antetitulo: 'Implications',
      titulo: 'What a change means for the area',
      texto: 'One possible reading, so each person decides what to check in the field.',
      puntos: [
        'Water: moisture and surface water show how much it rained and how the soil responds, useful in a drought-prone region.',
        'Farming: the rhythm of rain-fed crops is visible every 12 days, even under clouds.',
        'Infrastructure and communities: urban streams, slopes and tailings dams are places to watch after a storm.',
        'Ecosystems: grassland and shrubland change with the monsoon; a change outside that rhythm deserves attention.',
      ],
    },
    {
      icono: 'satelite',
      antetitulo: 'Future applications',
      titulo: 'What NISAR will make possible',
      texto: 'With more dates and other mission products:',
      puntos: [
        'Flood alerts at night or under clouds, combined with satellite rainfall (GPM).',
        'Monitoring tailings dams and slopes with InSAR (GUNW) for centimetre motion.',
        'Crop calendars and soil moisture to plan irrigation.',
        'Subsidence from groundwater pumping in cities and farming valleys.',
        'Glaciers, sea ice and forest biomass worldwide, with L and S band together.',
      ],
    },
  ],
  nota:
    'No threshold is calibrated against ground truth: we set them with the noise of 16 real pairs and declare them as assumptions. Causes are hypotheses; radar measures the echo, not the reason.',
}
