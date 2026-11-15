# Qué datos recaba GeoLatido

Comprobado en el código el 2026-11-15. La app lo muestra en Acerca de GeoLatido → Datos y créditos
(`frontend/src/components/portalCreditos.ts`); si cambia lo que se guarda, se cambian los dos.

| Qué | Dónde se guarda | Quién lo ve |
|---|---|---|
| Texto buscado o punto con clic | Se envía a Nominatim (OpenStreetMap); `research` guarda la respuesta en caché por texto o punto, sin identificar a nadie | Política de privacidad de la OSMF para Nominatim |
| Zona procesada en línea | Nombre, caja y artefactos del veredicto (`data/aois-online`, `data/artifacts`) | Todas las personas que usan la app |
| Investigación | Pregunta, zona e historia generada (SQLite de `research`, `data/research`) | Todas las personas que usan la app |
| Cuenta (solo con `AUTH_ENABLED=1`) | Correo, contraseña con hash Argon2, perfil declarado y fecha (SQLite de `auth`, `data/auth`) | Nadie: el correo nunca se muestra |
| Sesión | Hash del token de renovación y cookie propia `HttpOnly` con ruta `/api/auth/` | Solo el servidor |
| Tokens personales | Solo su SHA-256, nombre, prefijo y fechas | Su dueño (sin el valor) |
| Historias y valoraciones | Título, notas, referencias a los datos, estrellas y perfil, con seudónimo `GL-XXXXXX` | Todas las personas que usan la app |
| Navegador | `localStorage`: `lang`, `portal-visto` y `sesion-posible` | Solo tu navegador |
| Registros del servidor | IP, ruta y hora de cada petición en los registros del gateway (Docker) | Quien administra el servidor |

No hay analítica ni cookies de terceros. El navegador pide las teselas del mapa base a EOX y OpenStreetMap, que ven
la IP como cualquier sitio web. El token de NASA Earthdata es del servidor (`.env`) y nunca llega al navegador.
