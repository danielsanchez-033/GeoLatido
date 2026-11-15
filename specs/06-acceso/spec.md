# Acceso: autenticación JWT y perfiles (RBAC): especificación

- **Responsables:** @KinzzoCS (servicio `auth`) y @lospapulindos2-netizen (gateway y aplicación de permisos)
- **Consumen:** @danielsanchez-033 (inicio de sesión y perfiles en la interfaz) y @Fransomware (herramientas del mapa por perfil)
- **Estado:** aprobada el 2026-11-14 por las cinco personas (PR 66)

## Misión

Saber quién consulta la API para ofrecer a cada perfil la profundidad y las herramientas que necesita, y proteger las capacidades costosas, **sin esconder a nadie la verdad del veredicto**.

## Principio rector

Los perfiles cambian la profundidad, las herramientas y las cuotas; nunca la verdad. Se propone como artículo X de la constitución (ver `specs/constitution.md`). En concreto:

- Cualquier persona, con o sin cuenta, ve el estado, `data_kind`, "qué no prueba", "qué falta", la causa de lo no observable y el recibo con los gránulos.
- Ningún permiso oculta un campo de una respuesta existente ni cambia su valor. Un perfil solo añade rutas, filtros, exportaciones o explicaciones.
- Cumple la demo mínima del sistema ("permite ver los gránulos usados") y la constitución II.2 y II.4 para todos los perfiles.

## Perfiles

| Código en la API | Nombre visible | Cómo se obtiene | Para quién |
|---|---|---|---|
| `public` | Público general | Sin cuenta, o con cuenta sin otro perfil | Habitantes, periodistas, jurado |
| `student` | Estudiante | Lo elige la persona al registrarse | Quien aprende teledetección y quiere entender cada número |
| `researcher` | Investigador | Lo elige la persona al registrarse | Quien busca, filtra, compara y exporta |

- El perfil es **declarado, no verificado**. Es aceptable porque ningún perfil da acceso a información que otro no pueda ver (principio rector); solo cambia herramientas y cuotas. La interfaz lo dice así y nunca muestra "investigador verificado".
- No hay perfil de administración en la API. Las cuentas de prueba se crean con una orden del servicio, con contraseñas leídas del `.env`.

## Historias de usuario

- Como persona del público, quiero usar la aplicación sin crear una cuenta.
- Como estudiante, quiero entrar con mi cuenta y que la aplicación me explique cada campo de la evidencia.
- Como investigadora, quiero un token para consultar la búsqueda y la exportación desde mis propios scripts.
- Como jurado, quiero comprobar que el público ve el mismo veredicto y el mismo recibo que un investigador.
- Como responsable de la pila, quiero que una petición no pueda hacerse pasar por otro perfil ni saltarse el gateway.

## Requisitos

| ID | Requisito | Prioridad |
|---|---|---|
| RF-ACC-01 | Servicio `auth` propio, reproducible con `docker compose`: registro, inicio de sesión, renovación, cierre de sesión y JWKS público | P0 |
| RF-ACC-02 | Tokens de acceso JWT firmados con EdDSA (Ed25519), con `iss`, `aud`, `sub`, `role`, `iat`, `exp` y `jti`; vida de 15 minutos | P0 |
| RF-ACC-03 | Renovación con un token opaco y rotativo en cookie `HttpOnly`, `Secure` fuera de localhost y `SameSite=Strict`; se guarda solo su hash, y reutilizar uno ya rotado revoca toda la familia | P0 |
| RF-ACC-04 | Contraseñas con Argon2id; mínimo 12 caracteres; sin requisitos de composición; respuesta idéntica para "no existe" y "contraseña incorrecta" | P0 |
| RF-ACC-05 | El gateway valida el token en cada petición a `/api/` y pasa a los servicios `X-Auth-Role` y `X-Auth-Sub`. Borra esas cabeceras si vienen del cliente | P0 |
| RF-ACC-06 | Sin cabecera `Authorization`, la petición es `public`. Con un token inválido, caducado o de otra audiencia, responde 401 en **cualquier** ruta, también en las actuales, y **no** degrada a `public` en silencio | P0 |
| RF-ACC-07 | Ninguna ruta que exista el 2026-11-14 pide token, cambia su respuesta según el perfil ni cuenta para las cuotas por perfil. La única diferencia posible es el 401 de RF-ACC-06, que depende de que el token sea válido y no del perfil | P0 |
| RF-ACC-08 | Las rutas nuevas declaran en su contrato el perfil mínimo; con un perfil insuficiente responden 403 con el perfil que haría falta | P0 |
| RF-ACC-09 | Cuotas por perfil en el gateway, **solo en las rutas nuevas**: `public` por IP, y `student` y `researcher` por `sub`. Además, una cuota estricta por IP en `POST /api/auth/login` y `/api/auth/register`, contra los intentos de adivinar contraseñas. Al pasarse, 429 con `Retry-After`. Las rutas actuales y las teselas no cuentan: en la demo todo el público comparte una IP | P1 |
| RF-ACC-10 | `AUTH_ENABLED=0` deja el gateway como hoy (todo `public`, rutas nuevas con 403). Es el valor por omisión hasta que el equipo apruebe activarlo | P0 |
| RF-ACC-11 | Tokens personales para scripts (`researcher`): se crean y revocan desde la cuenta, se muestran una sola vez y caducan como máximo a los 90 días | P2 |
| RF-ACC-12 | Registro sin datos personales más allá de un correo y una contraseña; sin verificación de correo en esta ola, y se dice así | P1 |
| RF-ACC-13 | Historias de la comunidad, guardadas en `auth` (`/api/auth/stories`): zona, serie, rango de fechas, pares elegidos, título y notas de quien la escribe. **No guardan textos de veredictos**: la interfaz los vuelve a pedir a la API al mostrar o descargar la historia, así que una historia nunca congela ni cambia lo que dice un veredicto | P2 |
| RF-ACC-14 | Leer y listar historias no pide cuenta. Crearlas, borrar las propias, valorarlas y descargarlas pide sesión (o token personal) de `student` o `researcher`; sin ella, 401 | P2 |
| RF-ACC-15 | Valoración con estrellas de 1 a 5: una por cuenta e historia (valorar otra vez la cambia), sin valorar la propia. Cada historia da el promedio general y el desglose por perfil declarado (`student` y `researcher`) | P2 |
| RF-ACC-16 | Las notas de la persona se muestran y se descargan separadas de los textos de la API y rotuladas como suyas (constitución II). La autoría se muestra con el perfil declarado, nunca con el correo | P2 |
| RF-ACC-17 | Cada historia cabe en los 4 KB que el gateway admite en `/api/auth/`: título de 3 a 120 caracteres, notas hasta 800, de 1 a 24 pares e identificadores de zona y serie de hasta 32 caracteres. Ninguna ruta nueva usa `PUT`, que el gateway no deja pasar | P2 |

## Matriz de acceso

| Capacidad | `public` | `student` | `researcher` |
|---|---|---|---|
| Veredictos, eventos, serie por píxel, teselas, catálogo y referencias (rutas actuales) | sí, sin cuenta | sí | sí |
| Recibo completo, `data_kind` y causa de lo no observable | sí | sí | sí |
| Búsqueda de veredictos y de pasadas (`specs/07-busqueda`) | no | sí, con filtros básicos y 50 resultados por página | sí, con todos los filtros y paginación |
| Exportar resultados con su recibo (CSV, GeoJSON, JSON) | no | no | sí |
| Tokens personales para scripts | no | no | sí |
| Leer historias de la comunidad y sus estrellas | sí, sin cuenta | sí | sí |
| Guardar, valorar con estrellas y descargar historias | no | sí | sí |
| Cuota en las rutas nuevas (T-BAL-12, sin calibrar con uso real) | 60 peticiones/min por IP | 120/min | 600/min |
| Cuota en las rutas actuales y las teselas | ninguna | ninguna | ninguna |
| Cuota de `login` y `register` (T-BAL-12, cuotas separadas) | 5 intentos/min por IP, para todos | | |

## Criterios de aceptación

- [x] Con `AUTH_ENABLED=1`, la misma petición a `/api/verdicts/aois/parral/series/T048A-F015/verdicts` devuelve un cuerpo idéntico sin token, con token de `student` y con token de `researcher` (prueba automática que compara los cuerpos). `scripts/smoke.sh` compara byte a byte esa ruta y otras cinco actuales (T-BAL-16, 2026-11-14).
- [x] Con `AUTH_ENABLED=0`, `bash scripts/smoke.sh` pasa sin cambios. Pila de Docker sintética, 2026-11-14 (T-BAL-10).
- [x] Una petición con `X-Auth-Role: researcher` y sin token llega a los servicios como `public`. Con los dos valores de `AUTH_ENABLED`, `/search/verdicts` del PR 91 responde 403 con `required_role: student` (T-BAL-10, 2026-11-14).
- [x] Un token caducado, con firma de otra clave o con `aud` distinto recibe 401, nunca 200 como `public`, también en una ruta actual. Probado a mano con `AUTH_ENABLED=1` en `/api/verdicts/aois` (T-BAL-10, 2026-11-14). Desde T-BAL-16, `scripts/smoke.sh` lo prueba en tres rutas actuales y en la búsqueda, también con un perfil inexistente, sin firma y con `Authorization: Basic`.
- [x] Superar la cuota de `public` en una ruta nueva no cambia la respuesta de las rutas actuales: siguen dando 200 desde la misma IP. `scripts/smoke.sh` con `AUTH_ENABLED=1`: 429 en la búsqueda y después 200 en tres rutas actuales y en una tesela, y `student` sigue buscando (T-BAL-12, 2026-11-14).
- [x] El sexto intento de `POST /api/auth/login` en un minuto desde la misma IP recibe 429 con `Retry-After`. Seis intentos seguidos dan 429 como tarde en el sexto (`scripts/smoke.sh`, T-BAL-12, 2026-11-14). La cuota es un cubo de nginx (`limit_req`): tras agotarla vuelve un intento cada 12 s, así que en un minuto entero caben hasta 10 si se reparten.
- [x] Desde el origen del frontend (`http://localhost:3000`), una petición a `/api/` con `Authorization` pasa la comprobación previa de CORS del navegador. `scripts/smoke.sh` comprueba que `Access-Control-Allow-Headers` nombra `Authorization` (T-BAL-10); no se probó en un navegador.
- [x] Reutilizar un token de renovación ya rotado revoca la sesión y obliga a entrar de nuevo. Prueba de `services/auth` y comprobado en Docker el 2026-11-14 (T-ANT-14).
- [ ] Ningún servicio salvo el gateway publica un puerto en `docker-compose.yml` (hoy se cumple; la prueba lo vigila).
- [x] El repositorio no contiene la clave privada ni contraseñas: la clave se genera al arrancar si falta, en un volumen fuera de git, o se lee del `.env`. `AUTH_DATA_DIR` (por omisión `data/auth`, ignorado por git) guarda la clave con permisos 600 (T-ANT-14).
- [x] La prueba de humo cubre las rutas de `auth` y comprueba 401, 403 y 429. Con `AUTH_ENABLED=1` (T-BAL-16 y T-BAL-12, 2026-11-14). La CI aún levanta la pila solo con `AUTH_ENABLED=0`.
- [x] Las dependencias nuevas tienen licencia compatible con la del proyecto (hoy Apache-2.0) y se anotan en MEMORY (PyPI, 2026-11-14).

## Interfaces

- **Produce:** `contracts/auth.openapi.json` (Antena), las cabeceras `X-Auth-Role` y `X-Auth-Sub` hacia los servicios (Balanza) y `securitySchemes` en los contratos de las rutas nuevas.
- **Consume:** nada externo. No depende de Earthdata ni de ningún proveedor de identidad.

## Fuera de alcance

- Inicio de sesión con proveedores externos (Google, ORCID, Earthdata Login). ORCID sería la vía para verificar a investigadores en otra ola.
- Verificación de correo, recuperación de contraseña por correo y doble factor.
- Ocultar o recortar campos según el perfil: lo prohíbe el principio rector.
- En las historias (RF-ACC-13): moderación, comentarios y edición. Para cambiar una historia se borra y se guarda otra.
- Impedir de verdad que alguien sin sesión arme la descarga: los datos de una historia son públicos (constitución II.4). La descarga con sesión es una función de la comunidad, que además cuenta las descargas, no una barrera de seguridad.

## Preguntas abiertas

- ¿Se activa `AUTH_ENABLED=1` en la demo del 15 de noviembre o después? Recomendación: después, para que la demo no dependa de una pieza nueva.
- ~~¿Las teselas (`/tiles/cog/`) cuentan para la cuota?~~ Resuelta el 2026-11-14 en la revisión del PR 66 (Faro y Balanza): ni las teselas ni ninguna ruta actual cuentan (RF-ACC-07 y RF-ACC-09).
