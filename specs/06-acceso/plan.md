# Acceso: plan técnico

## Diseño

```
navegador ──Authorization: Bearer <jwt>──> gateway (nginx)
                                             │ auth_request /_auth  ──> auth:8000/verify
                                             │   200 + X-Auth-Role, X-Auth-Sub   (o 401)
                                             ├──> catalog   (X-Auth-Role, X-Auth-Sub)
                                             ├──> verdicts  (X-Auth-Role, X-Auth-Sub)
                                             └──> tiles     (sin cabeceras de perfil)
navegador ──POST /api/auth/login|refresh|logout──> gateway ──> auth
```

- **Servicio nuevo `services/auth`** (FastAPI, como el resto). Dueño: Antena. Guarda cuentas y sesiones en SQLite dentro de un volumen (`./data/auth`, ignorado por git). No importa código de otros servicios.
- **Validación en el gateway con `auth_request`.** nginx de código abierto no valida JWT por sí mismo (eso es de nginx Plus), así que el gateway hace una subpetición a `auth:8000/verify`. `verify` comprueba la firma con la clave pública en memoria y no toca la base de datos, así que cuesta microsegundos. Motivo: un único punto que decide el perfil, y los servicios no necesitan biblioteca de JWT.
- **Cabeceras de confianza.** El gateway hace `proxy_set_header X-Auth-Role $auth_role` siempre, lo que pisa cualquier valor del cliente. Los servicios solo son accesibles en la red interna de Docker (el compose no publica sus puertos), así que no hay forma de llegar a ellos sin pasar por el gateway.
- **Sin token, `public`.** `verify` responde 200 con `X-Auth-Role: public` si no hay `Authorization`. Con un token que falla, 401: el cliente renueva o vuelve a entrar. Así nadie ve una vista pública creyendo que está dentro.
- **Sin cabecera, sin subpetición.** Con `AUTH_ENABLED=1`, el gateway resuelve `public` sin llamar a `verify` cuando no hay `Authorization` (una cabecera vacía cuenta como ausente). Así, si `auth` cae, las consultas sin cuenta siguen funcionando; con token, el gateway responde 503 con `Retry-After`, nunca `public`. Decisión de Balanza en T-BAL-10.
- **Interruptor `AUTH_ENABLED`.** Con 0, el bloque `auth_request` no se incluye y el gateway fija `X-Auth-Role: public`. Las rutas nuevas responden 403 y las actuales siguen igual. `envsubst` solo sustituye variables y no puede quitar un bloque, así que hay dos archivos, `gateway/auth/auth-on.conf` y `gateway/auth/auth-off.conf`, y la plantilla los elige con `include /etc/nginx/auth/auth-${AUTH_MODE}.conf;` (`AUTH_MODE` vale `on` u `off` según `AUTH_ENABLED`). La plantilla es `gateway/default.conf.template` (antes `gateway/nginx.conf`), montada en `/etc/nginx/templates/`, que la imagen oficial procesa con `envsubst` al arrancar; `NGINX_ENVSUBST_FILTER=^AUTH_` evita que toque otras variables. `AUTH_MODE` lo fija `gateway/15-auth-mode.envsh`, que el entrypoint de la imagen ejecuta antes de las plantillas, y cualquier valor de `AUTH_ENABLED` distinto de 0 o 1 detiene el gateway. Con `AUTH_ENABLED=0`, `/api/auth/` responde 503 explicando que el acceso con cuenta está apagado, en lugar de dar tokens que nadie miraría; solo `/api/auth/health` responde 200 con `auth_enabled: false` (2026-11-15), para que la interfaz sepa que está apagado sin un error en la consola en cada carga. Observación de Balanza en el PR 66; hecho en T-BAL-10.

## Rutas de `auth`

| Ruta | Método | Descripción |
|---|---|---|
| `/register` | POST | `{email, password, role: student \| researcher}`. Devuelve el token de acceso y fija la cookie de renovación |
| `/login` | POST | `{email, password}`. Igual que `/register` |
| `/refresh` | POST | Lee la cookie, rota el token de renovación y devuelve un token de acceso nuevo |
| `/logout` | POST | Revoca la familia de la cookie y la borra |
| `/me` | GET | `{sub, email, role, created_at}` |
| `/verify` | GET | Solo para el gateway (`internal` en nginx). 200 con cabeceras o 401 |
| `/.well-known/jwks.json` | GET | Clave pública, por si un tercero quiere validar tokens |
| `/tokens` | GET, POST, DELETE | Tokens personales de `researcher` (P2) |

El gateway hoy solo deja pasar GET y OPTIONS. Se abre POST **solo** en `location /api/auth/` y con `client_max_body_size 4k`. No basta con eso: la comprobación `if ($request_method != GET) { return 405; }` está hoy a nivel de `server` y se ejecuta antes de elegir el `location`, así que se mueve a cada `location`, y en `/api/auth/` admite también POST (y DELETE para `/tokens`). Lo hace Balanza en T-BAL-10.

## Tokens

- Acceso: JWT EdDSA, 15 minutos. Claims `iss=nisar-veredictos`, `aud=nisar-api`, `sub` (UUID), `role`, `iat`, `exp`, `jti`. Se guarda en memoria en el navegador, nunca en `localStorage`.
- Renovación: 32 bytes aleatorios en cookie `refresh` con `Path=/api/auth/`, `HttpOnly`, `SameSite=Strict` y `Secure` salvo en localhost. Vida de 7 días. En SQLite solo el SHA-256, con `family_id`; usar uno ya rotado revoca la familia.
- Clave: Ed25519. Si `AUTH_PRIVATE_KEY` no está en el `.env`, `auth` genera una al primer arranque en `./data/auth/` y avisa en el registro. Rotar la clave cierra todas las sesiones, y es aceptable.
- CORS (el frontend está en `:3000` y el gateway en `:8080`, así que son orígenes distintos):
  - `/api/` (salvo `/api/auth/`): `Access-Control-Allow-Origin: *` sin credenciales, porque el token va en una cabecera y no en una cookie, y `Access-Control-Allow-Headers: Authorization, Content-Type`. El comodín `*` de hoy en `Allow-Headers` **no** cubre `Authorization`: la norma Fetch obliga a nombrarla, y sin eso la comprobación previa del navegador falla en cuanto el cliente manda el token.
  - `/api/auth/`: el origen exacto del frontend (`AUTH_ALLOWED_ORIGIN`), `Access-Control-Allow-Credentials: true`, `Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS` y las mismas cabeceras permitidas.
  - En nginx, un `add_header` dentro de un `location` anula todos los del `server`, así que cada `location` repite sus cabeceras CORS completas.
  - Observación de Balanza en el PR 66.

## Aplicación de permisos en los servicios

- Una función pequeña por servicio (`requiere_perfil("student")`) lee `X-Auth-Role` y responde 403 con `{"detail": ..., "required_role": ...}`. Se copia en cada servicio; no se comparte código (constitución VI.1).
- Las rutas actuales no llaman a esa función. Una prueba de cada servicio recorre su OpenAPI y falla si una ruta anterior al 2026-11-14 declara `security`.
- Los contratos de las rutas nuevas declaran `securitySchemes.bearer` y `x-required-role`.

## Cuotas (P1)

`limit_req_zone` de nginx con dos claves: `$binary_remote_addr` para `public` y `$auth_sub` para el resto, con un `map` sobre `$auth_role`. Se aplica **solo** en los `location` de las rutas nuevas (búsqueda, exportación y tokens personales); las rutas actuales y las teselas no llevan `limit_req`, porque en la demo todo el público comparte una IP (RF-ACC-07). Una tercera zona, estricta y por IP, cubre `POST /api/auth/login` y `/register` contra los intentos de adivinar contraseñas. Los valores de la matriz de la especificación son orientativos y se ajustan midiendo la pila (T-BAL-12).

## Dependencias propuestas

| Paquete | Uso | Licencia (comprobada en PyPI el 2026-11-14) |
|---|---|---|
| PyJWT con `cryptography` | Firmar y validar EdDSA | PyJWT MIT; `cryptography` Apache-2.0 o BSD-3-Clause |
| argon2-cffi | Hash de contraseñas | MIT, igual que argon2-cffi-bindings; cffi MIT-0 y pycparser BSD-3-Clause |

## Pruebas

- `services/auth`: registro, inicio de sesión con respuesta igual ante usuario inexistente, renovación con rotación, reutilización revocada, token caducado y `aud` distinto.
- Gateway (en `scripts/smoke.sh`): cabecera `X-Auth-Role` falsificada, 401 con token roto (también en una ruta actual), 403 en ruta nueva sin perfil, 429 al superar la cuota de una ruta nueva y de `login`, 200 en una ruta actual después de agotar esa cuota, comprobación previa de CORS con `Authorization` desde `Origin: http://localhost:3000`, y cuerpos idénticos de una ruta actual con los tres perfiles.
- Contratos: `python -m auth.export_openapi contracts/auth.openapi.json` y la prueba de coincidencia, como los demás.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Romper la demo con una pieza nueva | `AUTH_ENABLED=0` por omisión; se activa solo con la prueba de humo en verde |
| Fuga de la clave o de contraseñas | Fuera de git, en volumen o `.env`; el gancho de commit ya rechaza `.env` |
| Perfil declarado usado para aparentar autoridad | La interfaz nunca dice "verificado"; ningún perfil cambia lo que el veredicto afirma |
| La subpetición de `auth_request` añade latencia | `verify` no toca disco; se mide en la prueba de humo y se anota en MEMORY |
