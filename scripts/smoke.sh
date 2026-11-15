#!/usr/bin/env bash
# Prueba la pila levantada con docker compose a través del gateway (T-BAL-05).
#
# Cubre todas las rutas GET de catalog y verdicts, las teselas y las reglas del
# gateway. Al final compara las rutas probadas con el OpenAPI de cada servicio:
# una ruta nueva sin prueba hace fallar la prueba de humo.
#
# Las rutas de Antena que consultan CMR o Earth Search dependen de la red. Sin
# red responden 502 con su motivo; eso se acepta y se avisa, salvo con
# SMOKE_REQUIRE_NETWORK=1, que lo convierte en fallo.
#
# Vale para la pila sintética y para la real: mira el data_kind de la serie en
# /series y ajusta lo que depende de él. SMOKE_DATA=synthetic o SMOKE_DATA=real
# lo fija y falla si la pila trae otra cosa.
#
# Acceso (T-BAL-16): AUTH_ENABLED debe valer lo mismo que en la pila (0 por
# omisión). Con 1 prueba las rutas de auth, los 401, 403 y 429, la cabecera
# falsificada y que los tres perfiles reciben cuerpos idénticos. Los tokens
# caducados o de otra audiencia se firman dentro del contenedor auth con
# $SMOKE_COMPOSE (por omisión "docker compose" con el compose de este
# repositorio). Las cuotas (T-BAL-12) deben dar 429; SMOKE_REQUIRE_QUOTAS=0 lo
# deja en aviso. Agota la cuota de public y la de login desde tu IP: repetir la
# prueba antes de un minuto puede dar 429 al registrar o al entrar.
# Con contraseñas AUTH_TEST_* (entorno o .env) prueba también las cuentas de
# seed-accounts; SMOKE_REQUIRE_SEED=1 las exige. Los tokens personales se crean,
# se usan y se revocan (401 después).
set -euo pipefail

BASE="${BASE:-http://localhost:8080}"
REQUIRE_NETWORK="${SMOKE_REQUIRE_NETWORK:-0}"
REQUIRE_QUOTAS="${SMOKE_REQUIRE_QUOTAS:-1}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SMOKE_COMPOSE="${SMOKE_COMPOSE:-docker compose -f $ROOT/docker-compose.yml}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

AOI=parral
SERIES=T048A-F015
OTHER_SERIES=T171D-F075
EVENT_DATE=2026-07-01

COVERED=()
WARNINGS=()

# En Windows, python3 puede ser el alias de la Microsoft Store, que no ejecuta nada.
if python3 -c "" >/dev/null 2>&1; then
  PY=python3
elif python -c "" >/dev/null 2>&1; then
  PY=python
else
  echo "FALLO: hace falta python3 o python" >&2
  exit 1
fi

fail() {
  echo "FALLO: $*" >&2
  exit 1
}

# Marca una ruta del OpenAPI como probada: servicio y plantilla, p. ej. "catalog /aois/{aoi_id}".
covered() {
  COVERED+=("$1 $2")
}

# GET que debe responder 200; deja el cuerpo en $TMP/$1.json.
get() {
  local name=$1 path=$2 code
  code=$(curl -s -o "$TMP/$name.json" -w '%{http_code}' "$BASE$path") || fail "sin respuesta: $path"
  test "$code" = "200" || fail "$path respondió $code: $(head -c 300 "$TMP/$name.json")"
}

# GET que debe responder el código dado.
expect_code() {
  local expected=$1 path=$2 code
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$path")
  test "$code" = "$expected" || fail "$path respondió $code, se esperaba $expected"
}

# Ejecuta código Python sobre el JSON de $TMP/$2.json, disponible como `d`.
check() {
  local what=$1 name=$2 code=$3
  "$PY" - "$TMP/$name.json" "$code" <<'PY' || fail "$what"
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
exec(sys.argv[2])
PY
}

# GET a una ruta que depende de un servicio externo. 200: valida; 502: avisa o falla.
# Devuelve 0 si hay cuerpo que validar.
external() {
  local name=$1 path=$2 code
  code=$(curl -s -o "$TMP/$name.json" -w '%{http_code}' "$BASE$path") || fail "sin respuesta: $path"
  case "$code" in
    200) return 0 ;;
    502)
      local reason
      reason=$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['detail'])" "$TMP/$name.json") \
        || fail "$path respondió 502 sin motivo"
      test "$REQUIRE_NETWORK" = "1" && fail "$path sin red: $reason"
      WARNINGS+=("$path no se validó: $reason")
      return 1
      ;;
    *) fail "$path respondió $code: $(head -c 300 "$TMP/$name.json")" ;;
  esac
}

for _ in $(seq 1 60); do
  if curl -fsS "$BASE/api/verdicts/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

# --- Gateway ----------------------------------------------------------------

get gateway_health "/health"
check "gateway /health" gateway_health "assert d == {'status': 'ok'}"
expect_code 404 "/no-existe"
# Solo lectura: cualquier escritura se rechaza antes de llegar a los servicios.
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/verdicts/aois")
test "$code" = "405" || fail "POST respondió $code, se esperaba 405"
code=$(curl -s -o /dev/null -w '%{http_code}' -X OPTIONS "$BASE/api/verdicts/aois")
test "$code" = "204" || fail "OPTIONS respondió $code, se esperaba 204"

# Acceso en el gateway (T-BAL-10). AUTH_ENABLED es la misma variable que lee el compose: 0 por omisión.
# La prueba completa de acceso (registro, 403, 429 y perfiles) está al final, en "Acceso" (T-BAL-16).
AUTH_ENABLED="${AUTH_ENABLED:-0}"
# La comprobación previa de CORS con Authorization debe pasar desde el frontend, que está en otro origen.
curl -s -o /dev/null -D "$TMP/preflight.txt" -X OPTIONS -H "Origin: http://localhost:3000"   -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization" "$BASE/api/verdicts/aois"
grep -qi '^access-control-allow-headers:.*authorization' "$TMP/preflight.txt" || fail "CORS de /api/ sin Authorization"
code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer no-es-un-token" "$BASE/api/verdicts/aois")
code_auth=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/auth/health")
if [ "$AUTH_ENABLED" = "1" ]; then
  # Un token roto da 401 también en una ruta actual, nunca 200 como public (RF-ACC-06).
  test "$code" = "401" || fail "token roto en una ruta actual respondió $code, se esperaba 401"
  test "$code_auth" = "200" || fail "/api/auth/health respondió $code_auth"
  expect_code 404 "/api/auth/verify"
else
  # Sin validación, el token no se mira y todo es public; las rutas de auth dicen que el acceso está apagado.
  test "$code" = "200" || fail "con AUTH_ENABLED=0, una ruta actual con token respondió $code"
  test "$code_auth" = "200" || fail "con AUTH_ENABLED=0, /api/auth/health respondió $code_auth, se esperaba 200"
  curl -s "$BASE/api/auth/health" | grep -q '"auth_enabled":false' || fail "con AUTH_ENABLED=0, /api/auth/health no dice auth_enabled: false"
fi

# --- Catalog (Antena) -------------------------------------------------------

get catalog_health "/api/catalog/health"
check "catalog /health" catalog_health "assert d['status'] == 'ok'"
covered catalog /health

get catalog_aois "/api/catalog/aois"
check "catalog /aois" catalog_aois "
aoi = {a['id']: a for a in d}['$AOI']
assert len(aoi['bbox']) == 4 and aoi['collection'] and aoi['maturity'], aoi
"
covered catalog /aois
expect_code 404 "/api/catalog/aois/no-existe/series"

if external catalog_series "/api/catalog/aois/$AOI/series"; then
  check "catalog /series" catalog_series "
ids = {s['id'].split('-')[0] + '-' + s['id'].split('-')[1] for s in d}
assert {'$SERIES', '$OTHER_SERIES'} <= ids, ids
for s in d:
    assert s['granules'] and all(g['download_url'].startswith('https://') for g in s['granules']), s['id']
"
fi
covered catalog "/aois/{aoi_id}/series"

if external catalog_timeline "/api/catalog/aois/$AOI/timeline"; then
  check "catalog /timeline" catalog_timeline "
assert d['aoi'] == '$AOI' and d['published_at_basis'] == 'cmr_updated'
assert d['passes'] and all(p['acquired_at'] for p in d['passes'])
assert any(i['crosses_gap'] for i in d['intervals']), 'ningún intervalo cruza el hueco de agosto'
assert any(g['start'] <= '2026-08-01' <= g['end'] for g in d['gaps']), d['gaps']
assert all(e['basis'] == '12-day cycle' for e in d['next_pass_estimates'])
"
fi
covered catalog "/aois/{aoi_id}/timeline"

expect_code 422 "/api/catalog/aois/$AOI/references/optical"
if external catalog_optical "/api/catalog/aois/$AOI/references/optical?date=$EVENT_DATE"; then
  check "catalog /references/optical" catalog_optical "
assert d['aoi'] == '$AOI' and d['date'] == '$EVENT_DATE'
assert d['license_url'] and d['attribution'] and d['cloud_cover_basis'] == 'tile'
for acq in d['acquisitions']:
    for tile in acq['tiles']:
        assert tile['visual_url'].startswith('https://sentinel-cogs.s3.us-west-2.amazonaws.com/'), tile
"
fi
covered catalog "/aois/{aoi_id}/references/optical"

# Referencias OPERA DSWx-S1 (T-ANT-06). Se prueban en cuanto catalog las publique.
if curl -fsS "$BASE/api/catalog/openapi.json" | grep -q '/references/opera'; then
  if external catalog_opera "/api/catalog/aois/$AOI/references/opera?date=$EVENT_DATE"; then
    check "catalog /references/opera" catalog_opera "
assert d['aoi'] == '$AOI' and d['date'] == '$EVENT_DATE'
assert d['doi'] and d['attribution'] and d['data_access'] == 'earthdata_login'
for acq in d['acquisitions']:
    assert acq['tiles'] and all(t['wtr_url'] for t in acq['tiles']), acq
"
  fi
  covered catalog "/aois/{aoi_id}/references/opera"
fi

# Búsqueda de pasadas (T-ANT-16). Pide el perfil student: sin cuenta (public) responde 403 y dice cuál falta.
# No se prueba con X-Auth-Role a mano: hasta T-BAL-10 el gateway no borra esa cabecera del cliente.
if curl -fsS "$BASE/api/catalog/openapi.json" | grep -q '/search/passes'; then
  code=$(curl -s -o "$TMP/catalog_search_passes.json" -w '%{http_code}' "$BASE/api/catalog/search/passes")
  test "$code" = "403" || fail "/api/catalog/search/passes sin cuenta respondió $code, se esperaba 403"
  check "catalog /search/passes" catalog_search_passes "assert d['required_role'] == 'student', d"
  covered catalog "/search/passes"
fi

# Buscador mundial (2026-11-14): abierto a todos, depende de CMR. Comprueba la caja de la zona y que cada
# gránulo trae su huella y sus enlaces a Vertex y a Earthdata Search.
if curl -fsS "$BASE/api/catalog/openapi.json" | grep -q '/search/world'; then
  if external catalog_world "/api/catalog/search/world?bbox=-105.95,26.7,-105.4,27.15&from=2026-06-01&to=2026-11-14&limit=5"; then
    check "catalog /search/world" catalog_world "
assert d['data_kind'] == 'real' and d['total'] >= len(d['granules'])
for g in d['granules']:
    assert g['direction'] in ('A', 'D') and g['vertex_url'] and g['earthdata_search_url'], g
"
  fi
  covered catalog "/search/world"
fi

# --- Verdicts (Balanza) -----------------------------------------------------

get verdicts_health "/api/verdicts/health"
check "verdicts /health" verdicts_health "assert d['status'] == 'ok'"
covered verdicts /health

get verdicts_aois "/api/verdicts/aois"
check "verdicts /aois" verdicts_aois "assert '$AOI' in d, d"
covered verdicts /aois

get verdicts_series "/api/verdicts/aois/$AOI/series"
check "verdicts /series" verdicts_series "
by_id = {s['id']: s for s in d}
assert {'$SERIES', '$OTHER_SERIES'} <= set(by_id), list(by_id)
for s in d:
    assert s['data_kind'] in ('real', 'synthetic') and len(s['bbox']) == 4 and len(s['dates']) >= 2, s['id']
"
covered verdicts "/aois/{aoi}/series"
expect_code 404 "/api/verdicts/aois/no-existe/series"

# Hundimiento con NISAR GUNW: solo existe si se calculó (processor subsidence, con token). Si no, 404 declarado.
code=$(curl -s -o "$TMP/subsidence.json" -w '%{http_code}' "$BASE/api/verdicts/aois/$AOI/subsidence")
if [ "$code" = "200" ]; then
  check "verdicts /subsidence" subsidence "assert d['status'] in ('computed', 'no_interferograms') and d['summary']['detected'] and d['calibrated'] is False"
elif [ "$code" = "404" ]; then
  WARNINGS+=("verdicts /subsidence: $AOI no tiene cálculo de hundimiento (processor subsidence no se ejecutó)")
else
  fail "verdicts /subsidence: código $code"
fi
covered verdicts "/aois/{aoi}/subsidence"
expect_code 404 "/api/verdicts/aois/no-existe/subsidence"

# Datos de la serie principal: sintéticos o reales. Lo que depende de ello se comprueba según el caso.
DATA_KIND=$("$PY" -c "import json,sys; print({s['id']: s for s in json.load(open(sys.argv[1], encoding='utf-8'))}[sys.argv[2]]['data_kind'])" "$TMP/verdicts_series.json" "$SERIES")
if [ -n "${SMOKE_DATA:-}" ] && [ "$SMOKE_DATA" != "$DATA_KIND" ]; then
  fail "SMOKE_DATA=$SMOKE_DATA, pero $SERIES trae datos $DATA_KIND"
fi
echo "Datos de $SERIES: $DATA_KIND"

get event "/api/verdicts/aois/$AOI/events?date=$EVENT_DATE"
grep -q '"cause":"no_acquisition_during_event"' "$TMP/event.json" || fail "evento: causa"
grep -q '"next_pass":"2026-07-08"' "$TMP/event.json" || fail "evento: siguiente pasada"
# El corte se cuenta en horas: con 145 h ya no sale "observable". Con sintéticos no se sabe la hora de la
# pasada y sale la duda declarada; con datos reales catalog da la hora (07-08 01:44 UTC) y no llega.
get event145 "/api/verdicts/aois/$AOI/events?date=$EVENT_DATE&persistence_hours=145"
if [ "$DATA_KIND" = synthetic ]; then
  grep -q '"cause":"timing_uncertain"' "$TMP/event145.json" || fail "evento: 145 h sin hora"
else
  grep -q '"state":"not_observable"' "$TMP/event145.json" || fail "evento: 145 h con la hora real"
fi
get event_time "/api/verdicts/aois/$AOI/events?date=$EVENT_DATE&persistence_hours=145&time=12:00"
grep -q '"event_time":"12:00:00"' "$TMP/event_time.json" || fail "evento: hora UTC"
# T-BAL-06: la persistencia por tipo de evento sale declarada como supuesto.
get event_type "/api/verdicts/aois/$AOI/events?date=$EVENT_DATE&event_type=urban_storm"
grep -q '"persistence_hours":6' "$TMP/event_type.json" || fail "evento: persistencia por tipo"
grep -q '"source":"event_type"' "$TMP/event_type.json" || fail "evento: origen del supuesto"
grep -q '"calibrated":false' "$TMP/event_type.json" || fail "evento: supuesto sin calibrar"
covered verdicts "/aois/{aoi}/events"

get verdicts "/api/verdicts/aois/$AOI/series/$SERIES/verdicts"
verdicts=$(cat "$TMP/verdicts.json")
echo "$verdicts" | grep -q "\"data_kind\":\"$DATA_KIND\"" || fail "veredictos: data_kind"
# T-BAL-02: días entre fechas y frescura del dato en cada veredicto.
echo "$verdicts" | grep -q '"interval_days":' || fail "veredictos: interval_days"
if [ "$DATA_KIND" = synthetic ]; then
  # Los sintéticos se generan con cambio, y la latencia no aplica.
  echo "$verdicts" | grep -q '"state":"change_probable"' || fail "veredictos: change_probable"
  echo "$verdicts" | grep -q '"latency_status":"synthetic"' || fail "veredictos: latency_status"
else
  # Con datos reales vale cualquier estado; la latencia sale de catalog o se dice por qué no se sabe.
  check "veredictos: latencia real" verdicts "
for v in d:
    for side in ('before', 'after'):
        assert v['receipt']['freshness'][side]['latency_status'] != 'synthetic', v['id']
"
fi
# Ningún veredicto sin data_kind.
check "veredictos: data_kind en todos" verdicts "
assert d and all(v['receipt']['data_kind'] in ('real', 'synthetic') for v in d)
"
covered verdicts "/aois/{aoi}/series/{series_id}/verdicts"

# Textos en inglés con la misma estructura.
get verdicts_en "/api/verdicts/aois/$AOI/series/$SERIES/verdicts?lang=en"
check "veredictos en inglés" verdicts_en "assert d and all(v['summary'] for v in d)"

# Un par concreto coincide con el de la lista.
pair_id=$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))[-1]['id'])" "$TMP/verdicts.json")
get verdict "/api/verdicts/aois/$AOI/series/$SERIES/verdicts/$pair_id"
check "veredicto por par" verdict "assert d['id'] == '$pair_id' and d['receipt']['data_kind']"
covered verdicts "/aois/{aoi}/series/{series_id}/verdicts/{pair_id}"
expect_code 404 "/api/verdicts/aois/$AOI/series/$SERIES/verdicts/no-existe"
expect_code 404 "/api/verdicts/aois/$AOI/series/no-existe/verdicts"

# La otra serie también produce veredictos.
get verdicts_other "/api/verdicts/aois/$AOI/series/$OTHER_SERIES/verdicts"
check "veredictos de $OTHER_SERIES" verdicts_other "assert d and all(v['receipt']['data_kind'] for v in d)"

get pixel "/api/verdicts/aois/$AOI/series/$SERIES/pixel?lon=-105.67&lat=26.93"
grep -q '"values"' "$TMP/pixel.json" || fail "píxel: values"
covered verdicts "/aois/{aoi}/series/{series_id}/pixel"
expect_code 422 "/api/verdicts/aois/$AOI/series/$SERIES/pixel?lon=500&lat=26.93"

# Búsqueda (T-BAL-11). Sin token la petición es public, con AUTH_ENABLED a 0 o a 1: 403 con el perfil que haría
# falta, también si el cliente se inventa X-Auth-Role (el gateway la pisa). Los 200 con token, en "Acceso".
for role_header in "" "X-Auth-Role: researcher"; do
  code=$(curl -s -o "$TMP/search.json" -w '%{http_code}' ${role_header:+-H "$role_header"} \
    "$BASE/api/verdicts/search/verdicts?state=change_probable")
  test "$code" = "403" || fail "búsqueda sin token respondió $code con '${role_header:-sin cabecera}'"
  check "búsqueda: required_role" search "assert d['required_role'] == 'student', d"
done
covered verdicts "/search/verdicts"
# Exportación (T-BAL-13): solo researcher. Sin token, 403 con required_role researcher, también con la cabecera
# falsificada. Con token de researcher, en "Acceso" si está T-BAL-16.
for role_header in "" "X-Auth-Role: researcher"; do
  code=$(curl -s -o "$TMP/export.json" -w '%{http_code}' ${role_header:+-H "$role_header"} \
    "$BASE/api/verdicts/search/verdicts/export?format=csv")
  test "$code" = "403" || fail "exportación sin token respondió $code con '${role_header:-sin cabecera}'"
  check "exportación: required_role" export "assert d['required_role'] == 'researcher', d"
done
covered verdicts "/search/verdicts/export"

# --- Teselas ----------------------------------------------------------------

# Tesela real con las URLs que entrega la API, a un zoom que cubre la zona.
for layer in state change_hh; do
  template=$(echo "$verdicts" | "$PY" -c "import json,sys; print(json.load(sys.stdin)[-1]['layers']['$layer'])")
  tile=$(echo "$template" | sed 's/{z}/9/; s/{x}/106/; s/{y}/216/')
  content_type=$(curl -fsS -o "$TMP/tile.png" -w '%{content_type}' "$BASE$tile") || fail "tesela $layer"
  test "$content_type" = "image/png" || fail "tesela $layer: $content_type"
done

# Relieve (T-BAL-15): si el manifiesto trae dem, /series da una plantilla terrainrgb y su tesela es un PNG. Sin dem
# (el seed sintético aún no lo trae), relief es null y se avisa.
"$PY" - "$TMP/verdicts_series.json" >"$TMP/relief.txt" <<'PY' || fail "relieve en /series"
import json, sys
templates = set()
for item in json.load(open(sys.argv[1], encoding="utf-8")):
    relief = item["relief"]
    if relief is None:
        continue
    assert "algorithm=terrainrgb" in relief["tiles"] and relief["encoding"] == "mapbox", relief
    assert relief["attribution"] and relief["exaggeration"] == 1 and relief["units"] == "m", relief
    # Un DEM sintético (T-ECO-13) lo dice y no se atribuye a Copernicus; con radar real, nunca es sintético.
    assert relief["data_kind"] in ("real", "synthetic"), relief
    if relief["data_kind"] == "synthetic":
        assert "Copernicus" not in relief["attribution"] and item["data_kind"] == "synthetic", relief
    templates.add(relief["tiles"])
assert len(templates) <= 1, "cada zona tiene un solo DEM"
print(templates.pop() if templates else "")
PY
relief_template=$(tr -d '\r' <"$TMP/relief.txt")
if [ -n "$relief_template" ]; then
  tile=$(echo "$relief_template" | sed 's/{z}/9/; s/{x}/106/; s/{y}/216/')
  content_type=$(curl -fsS -o "$TMP/relief.png" -w '%{content_type}' "$BASE$tile") || fail "tesela de relieve"
  test "$content_type" = "image/png" || fail "tesela de relieve: $content_type"
  echo "Relieve: tesela terrainrgb servida"
else
  WARNINGS+=("relieve sin probar: ninguna serie trae dem en su manifiesto (falta un DEM sintético o reprocesar)")
fi
# Solo el algoritmo del relieve pasa el gateway: otro, sus parámetros o un segundo algorithm= dan 403.
DEM_URL="url=file%3A%2F%2F%2Fdata%2Fartifacts%2F$AOI%2Fdem.tif"
for query in "algorithm=hillshade" "algorithm=terrainrgb&algorithm=hillshade" "algorithm=terrainrgb&algorithm_params=%7B%7D"; do
  expect_code 403 "/tiles/cog/tiles/WebMercatorQuad/9/106/216.png?$DEM_URL&$query"
done

# El gateway no debe abrir archivos fuera de los artefactos.
expect_code 403 "/tiles/cog/info?url=file%3A%2F%2F%2Fetc%2Fpasswd"

# Un url= bueno seguido de otro malo, o un nombre codificado, tampoco pasa.
GOOD="url=file%3A%2F%2F%2Fdata%2Fartifacts%2Fx.tif"
for query in \
  "$GOOD&url=http%3A%2F%2Fcatalog%3A8000%2Faois" \
  "$GOOD&URL=file%3A%2F%2F%2Fetc%2Fpasswd" \
  "$GOOD&ur%6C=file%3A%2F%2F%2Fetc%2Fpasswd"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/tiles/cog/info?$query")
  test "$code" = "403" || fail "El gateway dejó pasar: $query ($code)"
done

# T-BAL-04: contraste óptico en cada veredicto, con estado aunque no haya red.
echo "$verdicts" | grep -q '"optical":{"data_kind":"real"' || fail "veredictos: óptico"
check "veredictos: estado óptico" verdicts "
for verdict in d:
    optical = verdict['evidence']['optical']
    assert optical['before']['status'] and optical['after']['status'] and optical['text'], verdict['id']
"

# T-BAL-07: QA de Eco en el recibo y desplazamiento de la escena (null si el manifiesto no trae qa).
check "veredictos: calidad y desplazamiento" verdicts "
for verdict in d:
    assert verdict['receipt']['quality']['source'] == 'manifest_qa', verdict['id']
    shift = verdict['evidence']['scene_shift']
    if shift is not None:
        assert shift['calibrated'] is False and shift['threshold_db'] > 0, verdict['id']
"

# Pasadas excluidas por catalog: el campo existe siempre; con sintéticos va vacío.
check "veredictos: pasadas excluidas" verdicts "
for verdict in d:
    excluded = verdict['receipt']['excluded_passes']
    assert isinstance(excluded, list), verdict['id']
    if verdict['receipt']['data_kind'] == 'synthetic':
        assert excluded == [], verdict['id']
"

# T-BAL-14: dispersión de la diferencia en evidence.noise, con su advertencia. null si el manifiesto no trae
# stats.noise_* (artefactos anteriores a T-ECO-09); el seed sintético ya los trae.
check "ruido de la diferencia" verdicts "
for verdict in d:
    noise = verdict['evidence']['noise']
    if verdict['receipt']['data_kind'] == 'synthetic':
        assert noise is not None, verdict['id']
    if noise is not None:
        assert noise['calibrated'] is False and noise['caveat'] and noise['basis'] == 'pair_stats', verdict['id']
        assert noise['hh_db'] is None or noise['hh_db'] >= 0, verdict['id']
"

# T-BAL-08: contraste con OPERA DSWx-S1. Con radar sintético se lista el producto pero nunca se compara.
check "veredictos: contraste de agua" verdicts "
for verdict in d:
    water = verdict['evidence']['water']
    assert water['data_kind'] == 'real' and water['text'], verdict['id']
    for side in (water['before'], water['after']):
        assert side['status'], verdict['id']
        if verdict['receipt']['data_kind'] == 'synthetic':
            assert side['status'] != 'compared' and side['assessment'] is None, verdict['id']
"

# El bucket público de Sentinel-2 sí pasa el filtro (sin red, TiTiler responde otro error, no 403).
S2_URL="https%3A%2F%2Fsentinel-cogs.s3.us-west-2.amazonaws.com%2Fsentinel-s2-l2a-cogs%2F13%2FR%2FCK%2F2026%2F6%2FS2C_13RCK_20260628_0_L2A%2FTCI.tif"
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/tiles/cog/info?url=$S2_URL")
test "$code" != "403" || fail "El gateway rechazó el bucket de Sentinel-2"
# Otro host HTTPS, otro prefijo del bucket o un segundo url= no pasan.
for query in \
  "url=https%3A%2F%2Fexample.com%2FTCI.tif" \
  "url=https%3A%2F%2Fsentinel-cogs.s3.us-west-2.amazonaws.com.example.com%2Fsentinel-s2-l2a-cogs%2Fx.tif" \
  "url=https%3A%2F%2Fsentinel-cogs.s3.us-west-2.amazonaws.com%2Fotro%2Fx.tif" \
  "url=$S2_URL&url=file%3A%2F%2F%2Fetc%2Fpasswd" \
  "url=$S2_URL&%75rl=file%3A%2F%2F%2Fetc%2Fpasswd"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/tiles/cog/info?$query")
  test "$code" = "403" || fail "El gateway dejó pasar: $query ($code)"
done

# --- Acceso (T-BAL-16) ------------------------------------------------------

# Petición libre: cuerpo en $TMP/$1.json y cabeceras en $TMP/$1.h. Imprime el código HTTP (000 sin respuesta).
call() {
  local name=$1
  shift
  curl -s -o "$TMP/$name.json" -D "$TMP/$name.h" -w '%{http_code}' "$@" || true
}

# Valor de una cabecera de la respuesta guardada por call, sin el retorno de carro.
header() {
  grep -i "^$2:" "$TMP/$1.h" | head -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//' || true
}

# Campo de primer nivel del JSON guardado por call.
field() {
  "$PY" -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))[sys.argv[2]])" "$TMP/$1.json" "$2"
}

# Desde T-BAL-12 el gateway tiene cuotas: no recibir 429 es un fallo. SMOKE_REQUIRE_QUOTAS=0 lo deja en aviso, para
# probar un gateway anterior.
quota_missing() {
  test "$REQUIRE_QUOTAS" = "1" && fail "$1"
  WARNINGS+=("$1 (SMOKE_REQUIRE_QUOTAS=0: se avisa en lugar de fallar)")
}

if [ "$AUTH_ENABLED" = "1" ]; then
  RUN="$(date +%s)-$RANDOM"
  PASSWORD="humo-de-prueba-$RUN"
  ORIGIN="${AUTH_ALLOWED_ORIGIN:-http://localhost:3000}"
  JSON=(-H "Content-Type: application/json")
  # Intentos contra la cuota por IP de login y register (RF-ACC-09): el 429 debe llegar como tarde al sexto login.
  LOGIN_ATTEMPTS=0

  # Rutas de auth. /health ya se probó arriba; /verify da 404 desde fuera.
  covered auth /health
  covered auth /verify
  test "$(call jwks "$BASE/api/auth/.well-known/jwks.json")" = "200" || fail "jwks"
  check "auth: jwks" jwks "
k = d['keys'][0]
assert k['kty'] == 'OKP' and k['crv'] == 'Ed25519' and k['alg'] == 'EdDSA' and 'd' not in k, k
"
  covered auth "/.well-known/jwks.json"

  # Registro: cuentas desechables con un correo nuevo en cada ejecución (example.org no recibe correo).
  register() {
    local role=$1 code
    code=$(call "reg_$role" -X POST "${JSON[@]}" -c "$TMP/$role.jar" \
      --data "{\"email\":\"humo-$role-$RUN@example.org\",\"password\":\"$PASSWORD\",\"role\":\"$role\"}" \
      "$BASE/api/auth/register")
    test "$code" = "201" || fail "register de $role respondió $code: $(head -c 300 "$TMP/reg_$role.json")"
    check "auth: register de $role" "reg_$role" "
assert d['role'] == '$role' and d['token_type'] == 'Bearer' and d['expires_in'] == 900, d
assert d['email_verified'] is False, d
"
  }
  register student
  register researcher
  LOGIN_ATTEMPTS=2
  STUDENT=$(field reg_student access_token)
  RESEARCHER=$(field reg_researcher access_token)
  cookie=$(header reg_student set-cookie)
  for attr in "refresh=" "HttpOnly" "Path=/api/auth/" "SameSite=strict"; do
    echo "$cookie" | grep -qi "$attr" || fail "cookie de renovación sin $attr: $cookie"
  done
  case "$BASE" in
    http://localhost* | http://127.0.0.1*)
      if echo "$cookie" | grep -qi "secure"; then fail "cookie con Secure en localhost: $cookie"; fi
      ;;
  esac
  covered auth /register

  test "$(call me_student -H "Authorization: Bearer $STUDENT" "$BASE/api/auth/me")" = "200" || fail "/me con token"
  check "auth: /me" me_student "
assert d['role'] == 'student' and d['email'] == 'humo-student-$RUN@example.org' and d['email_verified'] is False, d
"
  test "$(call me_none "$BASE/api/auth/me")" = "401" || fail "/me sin token no respondió 401"
  covered auth /me

  # Login: bien, con contraseña errónea y con un correo que no existe. Los dos fallos dicen lo mismo (RF-ACC-04).
  login() {
    local name=$1 email=$2
    LOGIN_ATTEMPTS=$((LOGIN_ATTEMPTS + 1))
    LOGIN_CODE=$(call "$name" -X POST "${JSON[@]}" --data "{\"email\":\"$email\",\"password\":\"$3\"}" \
      "$BASE/api/auth/login")
  }
  login login_ok "humo-student-$RUN@example.org" "$PASSWORD"
  test "$LOGIN_CODE" = "200" || fail "login respondió $LOGIN_CODE"
  check "auth: login" login_ok "assert d['role'] == 'student' and d['access_token'], d"
  login login_wrong "humo-student-$RUN@example.org" "otra-contrasena-larga"
  test "$LOGIN_CODE" = "401" || fail "login con contraseña errónea respondió $LOGIN_CODE"
  login login_unknown "nadie-$RUN@example.org" "otra-contrasena-larga"
  test "$LOGIN_CODE" = "401" || fail "login con correo inexistente respondió $LOGIN_CODE"
  cmp -s "$TMP/login_wrong.json" "$TMP/login_unknown.json" || fail "login: correo inexistente y contraseña errónea responden distinto"
  LOGINS=3
  covered auth /login

  # Renovación rotativa: la cookie vieja, ya rotada, da 401 y cierra la sesión entera (RF-ACC-03).
  code=$(call refresh_ok -X POST -b "$TMP/student.jar" -c "$TMP/student_new.jar" "$BASE/api/auth/refresh")
  test "$code" = "200" || fail "refresh respondió $code"
  check "auth: refresh" refresh_ok "assert d['role'] == 'student' and d['access_token'], d"
  code=$(call refresh_reused -X POST -b "$TMP/student.jar" "$BASE/api/auth/refresh")
  test "$code" = "401" || fail "refresh con una cookie ya rotada respondió $code"
  code=$(call refresh_family -X POST -b "$TMP/student_new.jar" "$BASE/api/auth/refresh")
  test "$code" = "401" || fail "tras reutilizar una cookie, la nueva sigue valiendo ($code)"
  covered auth /refresh

  # Cierre de sesión: después, su cookie ya no renueva.
  code=$(call logout -X POST -b "$TMP/researcher.jar" "$BASE/api/auth/logout")
  test "$code" = "204" || fail "logout respondió $code"
  code=$(call refresh_logout -X POST -b "$TMP/researcher.jar" "$BASE/api/auth/refresh")
  test "$code" = "401" || fail "refresh tras logout respondió $code"
  covered auth /logout

  # Cuentas de prueba (T-ANT-15), si hay contraseñas AUTH_TEST_* en el entorno o en el .env del repositorio. Se crean
  # antes con: docker compose run --rm -v ./.env:/run/env:ro auth python -m auth seed-accounts --env-file /run/env
  # Sin contraseñas no se prueban (aviso); SMOKE_REQUIRE_SEED=1 lo vuelve fallo. Nunca se imprime una contraseña.
  test_env() {
    local value="${!1:-}"
    if [ -z "$value" ] && [ -f "$ROOT/.env" ]; then
      value=$("$PY" - "$ROOT/.env" "$1" <<'PY'
import sys
value = ""
for raw in open(sys.argv[1], encoding="utf-8").read().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, rest = line.partition("=")
    if key.strip().removeprefix("export ").strip() == sys.argv[2]:
        rest = rest.strip()
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
            rest = rest[1:-1]
        value = rest
print(value, end="")
PY
)
    fi
    printf '%s' "$value"
  }
  SEEDED=0
  for role in student researcher; do
    upper=$(echo "$role" | tr '[:lower:]' '[:upper:]')
    seed_password=$(test_env "AUTH_TEST_${upper}_PASSWORD")
    seed_email=$(test_env "AUTH_TEST_${upper}_EMAIL")
    if [ "$role" = "student" ]; then
      seed_email=${seed_email:-estudiante@prueba.test}
    else
      seed_email=${seed_email:-investigacion@prueba.test}
    fi
    seed_email=$(echo "$seed_email" | tr '[:upper:]' '[:lower:]')
    if [ -z "$seed_password" ]; then
      test "${SMOKE_REQUIRE_SEED:-0}" = "1" && fail "falta AUTH_TEST_${upper}_PASSWORD para la cuenta de prueba $role"
      WARNINGS+=("cuenta de prueba $role sin probar: falta AUTH_TEST_${upper}_PASSWORD (SMOKE_REQUIRE_SEED=1 lo vuelve fallo)")
      continue
    fi
    seed_body=$("$PY" -c "import json,sys; print(json.dumps({'email': sys.argv[1], 'password': sys.argv[2]}))" \
      "$seed_email" "$seed_password")
    LOGIN_ATTEMPTS=$((LOGIN_ATTEMPTS + 1))
    LOGINS=$((LOGINS + 1))
    code=$(call "seed_$role" -X POST "${JSON[@]}" --data "$seed_body" "$BASE/api/auth/login")
    test "$code" = "200" || fail "login de la cuenta de prueba $role ($seed_email) respondió $code; ¿se ejecutó seed-accounts?"
    check "auth: cuenta de prueba $role" "seed_$role" "assert d['role'] == '$role' and d['access_token'], d"
    SEEDED=$((SEEDED + 1))
  done
  unset seed_password seed_body
  if [ "$SEEDED" -gt 0 ]; then
    echo "Cuentas de prueba: $SEEDED inician sesión con su perfil"
  fi
  # Los tokens personales se prueban con la cuenta researcher sembrada si la hay; si no, con la desechable.
  TOKEN_OWNER=$RESEARCHER
  if [ -s "$TMP/seed_researcher.json" ] && grep -q access_token "$TMP/seed_researcher.json"; then
    TOKEN_OWNER=$(field seed_researcher access_token)
  fi

  # /api/auth/ lleva cookie: CORS con el origen exacto y credenciales, nunca el comodín. Solo GET, POST y DELETE.
  call preflight_auth -X OPTIONS -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" "$BASE/api/auth/login" >/dev/null
  test "$(header preflight_auth access-control-allow-origin)" = "$ORIGIN" || fail "CORS de /api/auth/ sin el origen $ORIGIN"
  test "$(header preflight_auth access-control-allow-credentials)" = "true" || fail "CORS de /api/auth/ sin credenciales"
  test "$(call put_auth -X PUT "$BASE/api/auth/login")" = "405" || fail "PUT en /api/auth/ no respondió 405"

  # Tokens no válidos firmados con la clave de verdad: hace falta el contenedor auth. "valido" es el control:
  # mismo método, campos correctos; si no diera 200, los 401 de abajo no probarían nada.
  $SMOKE_COMPOSE exec -T auth python - >"$TMP/minted.txt" <<'PY' || fail "no se pudieron firmar tokens en el contenedor auth (SMOKE_COMPOSE='$SMOKE_COMPOSE')"
import os, time, uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from auth.tokens import AUDIENCE, ISSUER, Signer, load_or_create_key

key = load_or_create_key(Path(os.environ.get("AUTH_DATA_DIR", "/data/auth")), os.environ.get("AUTH_PRIVATE_KEY") or None)
kid = Signer(key).kid
now = int(time.time())


def token(signing_key=key, **changes):
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": str(uuid.uuid4()), "role": "researcher",
              "iat": now, "exp": now + 600, "jti": str(uuid.uuid4())}
    claims.update(changes)
    return jwt.encode(claims, signing_key, algorithm="EdDSA", headers={"kid": kid})


print("valido", token())
print("caducado", token(iat=now - 1200, exp=now - 60))
print("otra_clave", token(Ed25519PrivateKey.generate()))
print("otra_audiencia", token(aud="otra-api"))
print("perfil_inexistente", token(role="admin"))
PY
  VALID=$(awk '$1 == "valido" {print $2}' "$TMP/minted.txt" | tr -d '\r')
  test -n "$VALID" || fail "el contenedor auth no devolvió tokens"
  # Sin firma (alg none): no hace falta la clave.
  UNSIGNED=$("$PY" -c "
import base64, json, time
b = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b'=').decode()
n = int(time.time())
print(b({'alg': 'none', 'typ': 'JWT'}) + '.' + b({'iss': 'nisar-veredictos', 'aud': 'nisar-api', 'sub': 'x',
      'role': 'researcher', 'iat': n, 'exp': n + 600, 'jti': 'x'}) + '.')")

  test "$(call valid_aois -H "Authorization: Bearer $VALID" "$BASE/api/verdicts/aois")" = "200" || fail "el token de control no vale"
  test "$(call valid_search -H "Authorization: Bearer $VALID" "$BASE/api/verdicts/search/verdicts")" = "200" \
    || fail "el token de control no vale en la búsqueda"
  check "token de control" valid_search "assert d['query']['role'] == 'researcher', d['query']"

  # 401 en cualquier ruta /api/, también en las actuales, y nunca 200 como public (RF-ACC-06). Con CORS y
  # WWW-Authenticate, para que el navegador pueda leer el motivo.
  {
    echo "roto|Bearer no-es-un-token"
    awk '$1 != "valido" {print $1 "|Bearer " $2}' "$TMP/minted.txt" | tr -d '\r'
    echo "sin_firma|Bearer $UNSIGNED"
    echo "basic|Basic dXN1YXJpbzpjbGF2ZQ=="
  } >"$TMP/bad_tokens.txt"
  test "$(wc -l <"$TMP/bad_tokens.txt")" -ge 7 || fail "faltan tokens no válidos: $(cut -d'|' -f1 "$TMP/bad_tokens.txt" | tr '\n' ' ')"
  while IFS='|' read -r kind value; do
    for path in /api/verdicts/aois /api/catalog/aois "/api/verdicts/aois/$AOI/series/$SERIES/verdicts" \
      /api/verdicts/search/verdicts; do
      code=$(call bad_token -H "Authorization: $value" "$BASE$path")
      test "$code" = "401" || fail "token $kind en $path respondió $code, se esperaba 401"
      header bad_token www-authenticate | grep -qi '^bearer' || fail "401 sin WWW-Authenticate: $kind en $path"
      test "$(header bad_token access-control-allow-origin)" = "*" || fail "401 sin CORS: $kind en $path"
    done
  done <"$TMP/bad_tokens.txt"

  # Perfiles en la búsqueda (RF-ACC-08): 200 con su perfil, 403 con el que haría falta.
  search() {
    local name=$1 token=$2 query=$3
    shift 3
    call "$name" -H "Authorization: Bearer $token" "$@" "$BASE/api/verdicts/search/verdicts?$query"
  }
  test "$(search s_student "$STUDENT" "state=change_probable")" = "200" || fail "búsqueda de student"
  check "búsqueda: student" s_student "assert d['query']['role'] == 'student' and d['total'] >= 1, d['query']"
  test "$(search s_researcher "$RESEARCHER" "quality_flag=false&limit=500")" = "200" || fail "búsqueda de researcher"
  check "búsqueda: researcher" s_researcher "assert d['query']['role'] == 'researcher', d['query']"
  for query in "quality_flag=false" "limit=51"; do
    test "$(search s_denied "$STUDENT" "$query")" = "403" || fail "student con $query no recibió 403"
    check "búsqueda: student con $query" s_denied "assert d['required_role'] == 'researcher', d"
  done

  # Tokens personales (T-ANT-18, RF-ACC-11): crear con la sesión de un researcher, usarlo, y 401 al revocarlo.
  bearer() {
    local name=$1 token=$2
    shift 2
    call "$name" -H "Authorization: Bearer $token" "$@"
  }
  code=$(bearer tok_create "$TOKEN_OWNER" -X POST "${JSON[@]}" \
    --data "{\"name\":\"humo $RUN\",\"expires_in_days\":1}" "$BASE/api/auth/tokens")
  test "$code" = "201" || fail "POST /api/auth/tokens respondió $code: $(head -c 300 "$TMP/tok_create.json")"
  check "auth: token personal creado" tok_create "
assert d['token'].startswith('nvp_') and d['token'].startswith(d['prefix']) and d['status'] == 'active', d['status']
assert d['revoked_at'] is None and d['name'] == 'humo $RUN', d['name']
"
  PERSONAL=$(field tok_create token)
  PERSONAL_ID=$(field tok_create id)
  test "$(bearer tok_list "$TOKEN_OWNER" "$BASE/api/auth/tokens")" = "200" || fail "GET /api/auth/tokens"
  check "auth: lista de tokens" tok_list "
mine = [t for t in d['tokens'] if t['id'] == '$PERSONAL_ID']
assert len(mine) == 1 and mine[0]['status'] == 'active', mine
assert all('token' not in t for t in d['tokens']), 'la lista no debe traer el valor de ningún token'
"
  covered auth /tokens
  # Con el token personal: perfil researcher en la búsqueda, y el mismo cuerpo que public en una ruta actual.
  test "$(search s_personal "$PERSONAL" "quality_flag=false&limit=200")" = "200" || fail "búsqueda con token personal"
  check "búsqueda: token personal" s_personal "assert d['query']['role'] == 'researcher', d['query']"
  test "$(call same_public "$BASE/api/verdicts/aois")" = "200" || fail "/api/verdicts/aois sin token"
  test "$(bearer same_role "$PERSONAL" "$BASE/api/verdicts/aois")" = "200" || fail "/api/verdicts/aois con token personal"
  cmp -s "$TMP/same_public.json" "$TMP/same_role.json" || fail "/api/verdicts/aois responde distinto con token personal"
  # Ni student ni un token personal gestionan tokens (403); sin token, 401.
  code=$(bearer tok_student "$STUDENT" -X POST "${JSON[@]}" --data '{"name":"x"}' "$BASE/api/auth/tokens")
  test "$code" = "403" || fail "student creó un token personal ($code)"
  code=$(bearer tok_by_personal "$PERSONAL" -X POST "${JSON[@]}" --data '{"name":"x"}' "$BASE/api/auth/tokens")
  test "$code" = "403" || fail "un token personal creó otro token ($code)"
  test "$(bearer tok_list_personal "$PERSONAL" "$BASE/api/auth/tokens")" = "403" || fail "un token personal listó tokens"
  test "$(call tok_none "$BASE/api/auth/tokens")" = "401" || fail "GET /api/auth/tokens sin token no respondió 401"
  # La comprobación previa de CORS de DELETE pasa desde el frontend.
  call preflight_delete -X OPTIONS -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: DELETE" \
    -H "Access-Control-Request-Headers: authorization" "$BASE/api/auth/tokens/$PERSONAL_ID" >/dev/null
  test "$(header preflight_delete access-control-allow-origin)" = "$ORIGIN" || fail "CORS de DELETE en /api/auth/tokens sin el origen"
  header preflight_delete access-control-allow-methods | grep -qi delete || fail "CORS de /api/auth/ no permite DELETE"
  # Revocar: 204, y desde la petición siguiente 401 en la búsqueda y en rutas actuales, nunca 200 como public.
  test "$(bearer tok_revoke_personal "$PERSONAL" -X DELETE "$BASE/api/auth/tokens/$PERSONAL_ID")" = "403" \
    || fail "un token personal se revocó a sí mismo"
  test "$(bearer tok_revoke "$TOKEN_OWNER" -X DELETE "$BASE/api/auth/tokens/$PERSONAL_ID")" = "204" \
    || fail "DELETE /api/auth/tokens/{id} no respondió 204"
  for path in /api/verdicts/search/verdicts /api/verdicts/aois /api/catalog/aois; do
    code=$(bearer tok_revoked "$PERSONAL" "$BASE$path")
    test "$code" = "401" || fail "token personal revocado en $path respondió $code, se esperaba 401"
    test "$(header tok_revoked access-control-allow-origin)" = "*" || fail "401 sin CORS: token revocado en $path"
  done
  test "$(bearer tok_list "$TOKEN_OWNER" "$BASE/api/auth/tokens")" = "200" || fail "GET /api/auth/tokens tras revocar"
  check "auth: token revocado en la lista" tok_list "
mine = [t for t in d['tokens'] if t['id'] == '$PERSONAL_ID']
assert mine[0]['status'] == 'revoked' and mine[0]['revoked_at'], mine
"
  test "$(bearer tok_unknown "$TOKEN_OWNER" -X DELETE "$BASE/api/auth/tokens/no-existe-$RUN")" = "404" \
    || fail "DELETE de un token inexistente no respondió 404"
  covered auth "/tokens/{token_id}"

  # Historias de la comunidad (T-ANT-20, RF-ACC-12 a 17): leer y descargar sin cuenta; guardar y valorar con sesión.
  story_body="{\"title\":\"humo $RUN\",\"aoi\":\"$AOI\",\"series\":\"$SERIES\",\"from_date\":\"2026-06-01\",\"to_date\":\"2026-09-30\",\"pairs\":[{\"series\":\"$SERIES\",\"pair\":\"$pair_id\"}],\"notes\":\"Notas de la prueba de humo.\"}"
  test "$(call st_anon -X POST "${JSON[@]}" --data "$story_body" "$BASE/api/auth/stories")" = "401" \
    || fail "POST /api/auth/stories sin sesión no respondió 401"
  code=$(bearer st_create "$STUDENT" -X POST "${JSON[@]}" --data "$story_body" "$BASE/api/auth/stories")
  test "$code" = "201" || fail "POST /api/auth/stories respondió $code: $(head -c 300 "$TMP/st_create.json")"
  check "auth: historia creada" st_create "
assert d['is_mine'] is True and d['author_role'] == 'student' and d['downloads'] == 0, d
assert 'email' not in d and d['pairs'] == [{'series': '$SERIES', 'pair': '$pair_id'}], d
"
  STORY=$(field st_create id)
  test "$(call st_list "$BASE/api/auth/stories?aoi=$AOI&sort=recent")" = "200" || fail "GET /api/auth/stories sin cuenta"
  check "auth: lista de historias sin cuenta" st_list "
mine = [s for s in d['stories'] if s['id'] == '$STORY']
assert len(mine) == 1 and mine[0]['is_mine'] is False and mine[0]['my_stars'] is None, mine
"
  covered auth /stories
  test "$(call st_get "$BASE/api/auth/stories/$STORY")" = "200" || fail "GET /api/auth/stories/{id} sin cuenta"
  test "$(call st_missing "$BASE/api/auth/stories/no-existe-$RUN")" = "404" || fail "historia inexistente no dio 404"
  # Valorar: la propia no (409); otra cuenta sí, y quitar la valoración la deja sin estrellas.
  test "$(bearer st_rate_own "$STUDENT" -X POST "${JSON[@]}" --data '{"stars":5}' "$BASE/api/auth/stories/$STORY/rating")" = "409" \
    || fail "se pudo valorar la historia propia"
  test "$(bearer st_rate "$RESEARCHER" -X POST "${JSON[@]}" --data '{"stars":4}' "$BASE/api/auth/stories/$STORY/rating")" = "200" \
    || fail "POST /api/auth/stories/{id}/rating"
  check "auth: valoración" st_rate "assert d['my_stars'] == 4 and d['ratings']['count'] == 1 and d['ratings']['average'] == 4, d['ratings']"
  test "$(bearer st_unrate "$RESEARCHER" -X DELETE "$BASE/api/auth/stories/$STORY/rating")" = "200" \
    || fail "DELETE /api/auth/stories/{id}/rating"
  check "auth: valoración quitada" st_unrate "assert d['my_stars'] is None and d['ratings']['count'] == 0, d['ratings']"
  covered auth "/stories/{story_id}/rating"
  # Desde el 2026-11-14 descargar no pide sesión (toda la información es pública): cuenta con y sin cuenta.
  test "$(call st_dl_anon -X POST "$BASE/api/auth/stories/$STORY/download")" = "200" || fail "descarga sin sesión no dio 200"
  check "auth: descarga sin sesión contada" st_dl_anon "assert d['downloads'] == 1 and d['my_stars'] is None, d"
  test "$(bearer st_dl "$RESEARCHER" -X POST "$BASE/api/auth/stories/$STORY/download")" = "200" \
    || fail "POST /api/auth/stories/{id}/download"
  check "auth: descarga contada" st_dl "assert d['downloads'] == 2, d['downloads']"
  covered auth "/stories/{story_id}/download"
  # Borrar: solo quien la escribió (403 para otra cuenta, 204 para la suya).
  test "$(bearer st_del_other "$RESEARCHER" -X DELETE "$BASE/api/auth/stories/$STORY")" = "403" \
    || fail "otra cuenta borró la historia"
  test "$(bearer st_del "$STUDENT" -X DELETE "$BASE/api/auth/stories/$STORY")" = "204" \
    || fail "DELETE /api/auth/stories/{id} no respondió 204"
  test "$(call st_gone "$BASE/api/auth/stories/$STORY")" = "404" || fail "la historia borrada sigue respondiendo"
  covered auth "/stories/{story_id}"

  # Cabeceras falsificadas: con token de student, X-Auth-Role y X-Auth-Sub del cliente no cuentan (RF-ACC-05).
  forged=(-H "X-Auth-Role: researcher" -H "X-Auth-Sub: otra-persona")
  test "$(search s_forged "$STUDENT" "quality_flag=false" "${forged[@]}")" = "403" || fail "X-Auth-Role falsificada dio paso"
  test "$(search s_forged "$STUDENT" "state=change_probable" "${forged[@]}")" = "200" || fail "búsqueda con cabeceras falsificadas"
  check "búsqueda: perfil con cabecera falsificada" s_forged "assert d['query']['role'] == 'student', d['query']"

  # Mismo cuerpo, byte a byte, sin token, con student y con researcher en las rutas actuales (constitución X).
  for path in "/api/verdicts/aois/$AOI/series/$SERIES/verdicts" "/api/verdicts/aois/$AOI/series/$SERIES/verdicts/$pair_id" \
    "/api/verdicts/aois/$AOI/events?date=$EVENT_DATE" "/api/verdicts/aois/$AOI/series/$SERIES/pixel?lon=-105.67&lat=26.93" \
    /api/verdicts/aois /api/catalog/aois; do
    test "$(call same_public "$BASE$path")" = "200" || fail "$path sin token"
    for who in STUDENT RESEARCHER; do
      test "$(call same_role -H "Authorization: Bearer ${!who}" "$BASE$path")" = "200" || fail "$path con $who"
      cmp -s "$TMP/same_public.json" "$TMP/same_role.json" || fail "$path responde distinto a public y a $who"
    done
  done

  # Rutas actuales sin cuota: muchas peticiones seguidas desde la misma IP nunca dan 429 (RF-ACC-07).
  for _ in $(seq 1 80); do
    code=$(call burst_current "$BASE/api/verdicts/aois")
    test "$code" = "200" || fail "una ruta actual respondió $code en una ráfaga (sin cuota no puede dar 429)"
  done

  # Cuota de public en una ruta nueva (60/min por IP, a calibrar en T-BAL-12): 429 con Retry-After.
  got=""
  for i in $(seq 1 100); do
    code=$(call quota_search "$BASE/api/verdicts/search/verdicts")
    if [ "$code" = "429" ]; then
      got=$i
      break
    fi
    test "$code" = "403" || fail "búsqueda sin token respondió $code en la ráfaga"
  done
  if [ -n "$got" ]; then
    test -n "$(header quota_search retry-after)" || fail "429 de la búsqueda sin Retry-After"
    echo "Cuota de public en la búsqueda: 429 en la petición $got"
  else
    quota_missing "100 búsquedas sin token seguidas no dieron 429"
  fi
  # Pasada la cuota de public, las rutas actuales y las teselas siguen dando 200 desde la misma IP, y student
  # sigue buscando: su cuota va por sub, no por IP.
  for path in /api/verdicts/aois "/api/verdicts/aois/$AOI/series/$SERIES/verdicts" /api/catalog/aois "$tile"; do
    test "$(call after_quota "$BASE$path")" = "200" || fail "$path no responde 200 tras la cuota de public"
  done
  test "$(search s_after "$STUDENT" "state=change_probable")" = "200" || fail "student no busca tras la cuota de public"

  # Cuota estricta por IP en login (5/min, T-BAL-12): seis intentos seguidos dan 429 con Retry-After como tarde en
  # el sexto. El cubo se vacía a un intento cada 12 s, así que los logins de arriba, repartidos en la prueba, solo
  # adelantan el 429. Va al final porque deja la IP sin poder entrar hasta un minuto.
  got=""
  for i in $(seq 1 6); do
    login login_quota "nadie-$RUN@example.org" "otra-contrasena-larga"
    if [ "$LOGIN_CODE" = "429" ]; then
      got=$i
      break
    fi
    test "$LOGIN_CODE" = "401" || fail "login respondió $LOGIN_CODE durante la prueba de cuota"
  done
  if [ -n "$got" ]; then
    test -n "$(header login_quota retry-after)" || fail "429 de login sin Retry-After"
    check "auth: 429 de login" login_quota "assert d['retry_after_seconds'] > 0 and d['detail'], d"
    test "$(header login_quota access-control-allow-origin)" = "$ORIGIN" || fail "429 de login sin CORS del frontend"
    echo "Cuota de login: 429 en el intento seguido $got ($LOGIN_ATTEMPTS intentos de login y register en total)"
    # La cuota de login es solo de login y register: las rutas actuales siguen dando 200 desde la misma IP.
    test "$(call after_login_quota "$BASE/api/verdicts/aois")" = "200" || fail "una ruta actual cayó con la cuota de login"
  else
    quota_missing "6 intentos de login seguidos no dieron 429"
  fi
fi

# --- Cobertura --------------------------------------------------------------

# Toda ruta GET publicada por catalog o verdicts debe tener prueba arriba; con AUTH_ENABLED=1, también toda ruta
# de auth, con cualquier método.
printf '%s\n' "${COVERED[@]}" >"$TMP/covered.txt"
services="catalog verdicts"
if [ "$AUTH_ENABLED" = "1" ]; then
  services="$services auth"
fi
for service in $services; do
  get "openapi_$service" "/api/$service/openapi.json"
  "$PY" - "$TMP/openapi_$service.json" "$TMP/covered.txt" "$service" <<'PY' || fail "rutas de $service sin prueba de humo"
import json, sys
spec = json.load(open(sys.argv[1], encoding="utf-8"))
service = sys.argv[3]
covered = {line.split(" ", 1)[1] for line in open(sys.argv[2], encoding="utf-8").read().splitlines()
           if line.split(" ", 1)[0] == service}
published = {path for path, ops in spec["paths"].items() if service == "auth" or "get" in ops}
missing = sorted(published - covered)
if missing:
    print(f"{service}: rutas sin prueba en scripts/smoke.sh: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)
PY
done

for warning in "${WARNINGS[@]+"${WARNINGS[@]}"}"; do
  echo "AVISO: $warning" >&2
done
echo "Smoke OK"
