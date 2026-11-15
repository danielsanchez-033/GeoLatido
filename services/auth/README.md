# auth

Cuentas, sesiones y tokens de los perfiles de la API (ola 2, [`specs/06-acceso`](../../specs/06-acceso/spec.md), T-ANT-14). Dueño: Antena.

Ningún perfil cambia lo que dice un veredicto (constitución X): una cuenta solo añade herramientas y cuotas. Sin cuenta se es `public`, y ninguna ruta actual pide token.

## Rutas

El gateway las publica bajo `/api/auth/` (T-BAL-10). Contrato: [`contracts/auth.openapi.json`](../../contracts/auth.openapi.json).

| Ruta | Método | Qué hace |
|---|---|---|
| `/register` | POST | `{email, password, role: student \| researcher}`. Crea la cuenta, devuelve el token de acceso y fija la cookie de renovación |
| `/login` | POST | `{email, password}`. Igual. Misma respuesta 401 si el correo no existe o la contraseña no coincide |
| `/refresh` | POST | Rota el token de la cookie y devuelve un token de acceso nuevo. Reutilizar uno ya rotado cierra toda la sesión |
| `/logout` | POST | Cierra la sesión de la cookie y la borra |
| `/me` | GET | `{sub, email, role, created_at, email_verified: false}` con `Authorization: Bearer` |
| `/verify` | GET | Solo para el gateway (`auth_request`). Sin `Authorization`, 200 con `X-Auth-Role: public`; con token válido, 200 con `X-Auth-Role` y `X-Auth-Sub`; con token no válido, 401. Un JWT no toca la base de datos; un token personal se busca por su hash |
| `/tokens` | POST | Solo con la sesión de un `researcher`. `{name, expires_in_days: 1-90, 30 por omisión}`: crea un token personal y lo devuelve en claro **solo esta vez**. 409 con 10 activos |
| `/tokens` | GET | Solo con la sesión de un `researcher`. Los tokens de la cuenta (`active`, `expired` o `revoked`), sin su valor |
| `/tokens/{id}` | DELETE | Solo con la sesión de un `researcher`. Lo revoca desde la petición siguiente; 404 si no es de la cuenta |
| `/.well-known/jwks.json` | GET | Clave pública Ed25519 |
| `/health` | GET | `{"status": "ok"}` |

## Tokens

- **Acceso:** JWT EdDSA (Ed25519) de 15 minutos con `iss=nisar-veredictos`, `aud=nisar-api`, `sub`, `role`, `iat`, `exp` y `jti`, y la huella de la clave en `kid`.
- **Renovación:** 32 bytes aleatorios en la cookie `refresh` (`HttpOnly`, `SameSite=Strict`, `Path=/api/auth/`, 7 días). Lleva `Secure` salvo cuando el `Host` o `X-Forwarded-Host` es localhost. En la base solo se guarda su SHA-256.
- **Personales (T-ANT-18, RF-ACC-11):** para scripts de `researcher`. `nvp_` seguido de 32 bytes aleatorios, en `Authorization: Bearer` como un JWT, y dan el perfil `researcher` de la cuenta. Caducan como mucho a los 90 días y se pueden revocar. En la base solo se guarda su SHA-256 y un prefijo de 10 caracteres para reconocerlos. Un token personal no sirve para crear, listar ni revocar tokens: eso pide la sesión de la cuenta, así que un token filtrado no puede generar otros.
- **Contraseñas:** Argon2id, mínimo 12 caracteres y sin reglas de composición. El correo no se verifica, y la API lo dice con `email_verified: false`.

## Configuración

| Variable | Por omisión | Uso |
|---|---|---|
| `AUTH_DATA_DIR` | `data/auth` (`/data/auth` en la imagen) | SQLite (`auth.sqlite3`) y, si no hay `AUTH_PRIVATE_KEY`, la clave generada (`ed25519.pem`, permisos 600). Va en un volumen, nunca en git |
| `AUTH_PRIVATE_KEY` | — | Clave Ed25519 en PEM (PKCS8). Si falta, se genera al primer arranque y se avisa en el registro. Rotarla cierra todas las sesiones |
| `AUTH_COOKIE_SECURE` | `auto` | `true`, `false` o `auto` (Secure salvo en localhost) |
| `AUTH_COOKIE_PATH` | `/api/auth/` | Ruta de la cookie de renovación, la que ve el navegador detrás del gateway |

## Cuentas de prueba (T-ANT-15)

No hay perfil de administración en la API. Las cuentas de prueba se crean con una orden que escribe en la misma base de datos que el servicio, con las contraseñas del `.env`:

| Variable | Por omisión | Uso |
|---|---|---|
| `AUTH_TEST_STUDENT_PASSWORD` | — | Contraseña de la cuenta `student`. Sin ella, no se crea |
| `AUTH_TEST_STUDENT_EMAIL` | `estudiante@prueba.test` | Correo de esa cuenta |
| `AUTH_TEST_RESEARCHER_PASSWORD` | — | Contraseña de la cuenta `researcher`. Sin ella, no se crea |
| `AUTH_TEST_RESEARCHER_EMAIL` | `investigacion@prueba.test` | Correo de esa cuenta |

Con la pila de Docker, desde la raíz del repositorio (monta solo el `.env` para leerlo):

```bash
docker compose run --rm -v ./.env:/run/env:ro auth python -m auth seed-accounts --env-file /run/env
```

Fuera de Docker, desde `services/auth`, con `AUTH_DATA_DIR` apuntando a la misma carpeta que usa el servicio:

```bash
AUTH_DATA_DIR=../../data/auth python -m auth seed-accounts --env-file ../../.env
```

- Del `.env` solo lee las variables `AUTH_TEST_*`; nunca `EARTHDATA_TOKEN` ni otras. Las del entorno mandan sobre las del archivo.
- Es idempotente: crea la cuenta que falta, deja igual la que ya tiene esa contraseña y actualiza la que tiene otra. Se puede repetir tras cambiar el `.env`.
- Nunca cambia el perfil de una cuenta existente: si el correo ya es de otro perfil, lo dice y termina con código 1.
- Exige el mismo mínimo de 12 caracteres que la API. Nunca imprime contraseñas.
- Son cuentas normales: el perfil sigue siendo declarado, no verificado (constitución X.3), y se pueden usar con `AUTH_ENABLED=1`.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest -q
python -m auth.export_openapi ../../contracts/auth.openapi.json
uvicorn --factory auth.main:create_app --port 8000
```

Dependencias y licencias (comprobadas en PyPI el 2026-11-14): PyJWT (MIT), cryptography (Apache-2.0 o BSD-3-Clause), argon2-cffi y argon2-cffi-bindings (MIT), cffi (MIT-0) y pycparser (BSD-3-Clause).

El servicio está en `docker-compose.yml` y el gateway lo usa con `auth_request` desde el PR 97 (Balanza, T-BAL-10).

Ejemplo de uso desde un script, con la pila en `AUTH_ENABLED=1`:

```bash
# Con la sesión de la cuenta (access_token de /login), una vez:
curl -s -X POST http://localhost:8080/api/auth/tokens -H "Authorization: Bearer $SESION" \
  -H 'content-type: application/json' -d '{"name": "exportación", "expires_in_days": 30}'
# Después, en el script, el token que devolvió ("token": "nvp_…"):
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/verdicts/search/verdicts?state=change_probable"
```
