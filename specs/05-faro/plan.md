# Faro — plan técnico

## Estructura

- Faro elige el framework con Atlas. Debe tener licencia compatible con Apache-2.0 y generar un sitio estático, para poder publicarlo sin servidor propio.
- Frontera con Atlas: el mapa entra como un componente con la interfaz de `specs/04-atlas/plan.md`. Faro no toca su carpeta y Atlas no toca el resto.
- Los tipos de datos se generan a partir de `contracts/verdicts.openapi.json`, nunca se escriben a mano.
- `docker compose up --build` levanta también el frontend: el servicio `frontend` compila el sitio estático y lo sirve con nginx en `http://localhost:3000`. El navegador llama a la API en `http://localhost:8080` (`VITE_API_BASE`, fijado al compilar). `npm run dev` sigue siendo el camino para desarrollar.

## Jerarquía de la tarjeta de veredicto

1. Estado en una frase, con icono y texto, nunca solo color.
2. "Qué detectamos", "qué no prueba" y "qué falta", siempre visibles.
3. Hipótesis, rotuladas como hipótesis.
4. Recibo plegado: gránulos, CRID, madurez, avisos y frescura.

## Modo historia de Parral

| Escena | Llamada | Mensaje |
|---|---|---|
| 1. La tormenta | `GET /aois/parral/events?date=2026-07-01` | El satélite pasó el 29 de junio y el 8 de julio: no pudo verla |
| 2. Agosto | Veredicto de un par sin desplazamiento de toda la escena (T048, 08-16 → 08-28) | Qué dice el veredicto y qué no prueba, sin sugerir la lluvia como causa |
| 3. Los jales | Serie por píxel sobre La Prieta | Sin cambio detectable también es información |

Mientras los datos sean sintéticos, cada escena lo dice. La noticia de la tormenta debe abrirse y citarse antes de usarla.

## Idiomas y accesibilidad

- Textos de interfaz en archivos de traducción ES y EN; los del veredicto llegan de la API con `lang`.
- Revisión automática de accesibilidad en CI cuando exista el frontend.

## Riesgos

- La historia puede tentar a afirmar más de lo que hay. Cada escena se revisa con Balanza antes de la demo.
