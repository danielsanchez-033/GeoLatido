# Guía de GeoLatido

GeoLatido convierte el radar NISAR (NASA–ISRO) en veredictos claros sobre la superficie de la Tierra: qué cambió, qué
no se detectó y qué no se puede saber. Esta guía explica cómo instalarlo, cómo usar datos reales y cómo recorrer la app.

## 1. Instalación

Necesitas [Docker](https://www.docker.com/) con Compose y el motor en marcha.

```bash
git clone https://github.com/danielsanchez-033/GeoLatido.git
cd GeoLatido
docker compose up --build
```

- Aplicación: <http://localhost:3000>
- API: <http://localhost:8080>, con su documentación en `/api/verdicts/docs`, `/api/catalog/docs` y
  `/api/research/docs`.

Una copia recién clonada genera **datos sintéticos** para Hidalgo del Parral: sirven para probar el sistema sin
internet y no describen ningún lugar real. La app lo marca siempre con un aviso.

## 2. Datos reales de NISAR

1. Crea una cuenta gratuita en [NASA Earthdata](https://urs.earthdata.nasa.gov/) y genera un token en tu perfil.
2. Copia `.env.example` a `.env` y pon el token en `EARTHDATA_TOKEN=`. **Nunca subas el `.env` al repositorio.**
3. Vuelve a levantar la pila: `docker compose up -d`.

Con el token, el buscador de la app procesa en línea cualquier ciudad del mundo donde NISAR tenga HH y HV.

### Series completas de Parral (opcional)

`fetch` lee por HTTPS solo el recorte de la zona; si se interrumpe, al repetirlo continúa donde iba.

```bash
docker compose run --rm fetch --aoi parral --series T048A-F015
docker compose run --rm process --aoi parral --series T048A-F015 --input /data/raw/real/parral/T048A-F015
```

Repite con `T171D-F075` para la serie descendente. Cada fecha tarda unos minutos y ocupa unos 340 MB. T171 tiene una
fecha (2026-08-13) que `config/aois/parral.yaml` excluye por un defecto del propio producto.

Hundimiento de Parral con interferogramas NISAR GUNW (en memoria, sin guardar gránulos):

```bash
docker compose exec online sh -c 'python -m processor --aoi-dir /config/aois --data-dir /data subsidence --aoi parral'
```

Para volver a datos sintéticos, borra `data/artifacts/parral/<serie>` y levanta la pila otra vez.

## 3. Recorrido por la app

La primera vez sale una **bienvenida**. No necesitas cuenta: todo se ve igual sin iniciar sesión.

| Dónde | Qué hace |
|---|---|
| **Buscador** (arriba) | Escribe una ciudad o un punto de interés. Si ya está procesada, abre sus veredictos; si no, la procesa en línea (2 a 3 minutos) y enseña el avance en Hallazgos. |
| **Clic en el mapa** | Elige un punto. Dentro de una zona procesada, muestra la serie de ese píxel; fuera, ofrece procesar ese punto. |
| **Filtros** (izquierda) | Serie (órbita), periodo (de la primera a la última muestra), estados y el historial de hallazgos plegado por mes. |
| **Hallazgos** (derecha) | El veredicto del par elegido en lenguaje llano: qué detectamos, qué no prueba y qué falta; posibles explicaciones; «¿Se hunde el suelo?»; y, al final, **Regenerar veredictos** para reprocesar la zona con sus fechas más recientes. |
| **Historia** | La historia de la zona, capítulo a capítulo sobre el mapa, con acontecimientos citados. |
| **¿Pudo verlo?** | Pregunta si el radar pudo ver un evento de una fecha concreta. |
| **Investigar** | Una pregunta libre («¿Cómo cambió el terreno alrededor de las minas de Parral?») se convierte en una investigación con evidencia. |
| **Comunidad** | Historias publicadas por otras personas. Publicar y valorar sí pide cuenta. |

Barra inferior:

- **3D / 2D**: globo o mapa plano.
- **Diana**: acerca a la zona analizada; si ya estás en ella, aleja al espacio.
- **Capas**: estado del veredicto, cambio en HH, cambio en HV y hundimiento.
- **Comparador**: desliza entre dos vistas; en cada lado eliges óptico antes, óptico después, HH, HV o hundimiento.
- **Pantalla completa**.

**Acerca de GeoLatido** (arriba a la derecha) abre el portal: cómo funciona, **Radar y ciencia** (qué mide el radar,
polarizaciones, hipótesis, aplicaciones futuras) y **Datos y créditos** (fuentes, licencias y qué datos recabamos).

## 4. Cómo leer un veredicto

- **Cambio probable**: la señal cambió más que su propio ruido en al menos el 5 % de lo observado.
- **Sin cambio detectable**: el radar vio la zona y no encontró nada sobre el umbral. No prueba que nada cambiara.
- **No observable**: el radar no pudo medir (sin pasada, datos faltantes, relieve). La app dice la causa.

Los umbrales se fijaron con el ruido de 16 pares reales de Parral, sin verdad de campo, y se declaran como supuestos.
Las causas siempre son hipótesis: el radar mide el eco, no el porqué.

## 5. Pruebas

Cada servicio se prueba por separado desde su carpeta:

```bash
pip install -e ".[dev]"
pytest -q
```

Frontend: `npm ci && npm test` en `frontend/`. Prueba de humo con la pila levantada: `bash scripts/smoke.sh`.

## 6. Problemas frecuentes

- **El procesado en línea dice que falta el token**: revisa `EARTHDATA_TOKEN` en `.env` y reinicia `online`.
- **«Ninguna serie con HH y HV»**: NISAR solo tiene allí una polarización (por ejemplo en Alaska, la Antártida o
  Groenlandia); las pasadas se pueden ver igual, pero no se calcula el veredicto.
- **El procesado tarda más de lo esperado**: depende de la conexión; una zona de 0,3° baja unos 500 MB de trozos.
- **En Git Bash, `docker compose exec ... /data` no encuentra los archivos**: Git Bash convierte las rutas; usa
  `sh -c '...'` como en los ejemplos.
