#!/usr/bin/env bash
# Verificación local equivalente a la CI de GitHub Actions.
#
# Uso:
#   bash scripts/verifica-pr.sh 97            # un PR: lo prueba ya fusionado con main, como la CI
#   bash scripts/verifica-pr.sh main          # una rama
#   bash scripts/verifica-pr.sh 97 --sin-humo # sin levantar la pila (más rápido)
#   bash scripts/verifica-pr.sh 93 & bash scripts/verifica-pr.sh 101 & wait   # varios a la vez
#
# Hace lo mismo que .github/workflows/ci.yml y convenciones.yml:
#   1. Título del PR y nombre de la rama (solo con número de PR).
#   2. pytest -q de cada servicio con Python 3.11, como la CI.
#   3. docker compose up --build + scripts/smoke.sh con datos sintéticos.
# Y además, aunque la CI no lo hace: lint y vitest del frontend.
#
# Todo corre a la vez (servicios, frontend y pila) y con cachés en volúmenes de Docker:
# uv para Python y node_modules por versión de package-lock.json. La primera vez tarda más.
#
# Trabaja en un git worktree temporal: no toca tu copia, tu .env ni tus datos. Cada PR usa
# su propio proyecto de compose y sus puertos (20000+N y 30000+N; una rama, 18080 y 13000),
# así que convive con tu pila de 8080 y 3000 y con otras verificaciones.
set -uo pipefail

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[[ $# -ge 1 ]] || usage
REF="$1"; shift
SMOKE=1; FRONT=1
for a in "$@"; do
  case "$a" in
    --sin-humo) SMOKE=0 ;;
    --sin-frontend) FRONT=0 ;;
    *) usage ;;
  esac
done

# Git Bash en Windows: a docker se le pasa MSYS_NO_PATHCONV=1 solo en sus llamadas, para que no
# reescriba rutas como /src; exportarlo para todo rompería curl y git con rutas /tmp.
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
dk() { MSYS_NO_PATHCONV=1 docker "$@"; }

ROOT=$(git rev-parse --show-toplevel) || exit 2
cd "$ROOT"
START=$SECONDS

declare -a NAMES=() RESULTS=()
record() { NAMES+=("$1"); RESULTS+=("$2"); }

git fetch origin main --quiet || { echo "No se pudo traer origin/main" >&2; exit 2; }

if [[ "$REF" =~ ^[0-9]+$ ]]; then
  ID="pr$REF"
  SMOKE_PORT="${VERIFICA_PORT:-$((20000 + REF % 10000))}"
  FRONT_PORT="${VERIFICA_FRONT_PORT:-$((30000 + REF % 10000))}"
  INFO=$(gh pr view "$REF" --json title,headRefName,headRefOid,state \
    --jq '[.title, .headRefName, .headRefOid, .state] | @tsv') || exit 2
  IFS=$'\t' read -r TITLE BRANCH SHA STATE <<<"$INFO"
  git fetch origin "pull/$REF/head" --quiet || exit 2
  echo "[$ID] PR $REF ($STATE): $TITLE"
  echo "[$ID] Rama $BRANCH en ${SHA:0:7}"

  # Mismas expresiones que .github/workflows/convenciones.yml
  title_pattern='^(feat|fix|spec|docs|test|refactor|perf|build|ci|chore|revert)\((antena|eco|balanza|atlas|faro|contratos|repo)\)!?: [^ ].{0,71}$'
  branch_pattern='^(antena|eco|balanza|atlas|faro|contratos|repo)/[a-z0-9._-]+$'
  if [[ "$TITLE" =~ $title_pattern ]]; then record "titulo" OK; else record "titulo" FALLO; fi
  if [[ "$BRANCH" =~ $branch_pattern ]]; then record "rama" OK; else record "rama" FALLO; fi
  MERGE_MAIN=1
else
  ID=$(printf '%s' "$REF" | tr -c 'a-zA-Z0-9' '-')
  SMOKE_PORT="${VERIFICA_PORT:-18080}"
  FRONT_PORT="${VERIFICA_FRONT_PORT:-13000}"
  git fetch origin "$REF" --quiet || exit 2
  SHA=$(git rev-parse FETCH_HEAD)
  echo "[$ID] Rama $REF en ${SHA:0:7}"
  MERGE_MAIN=0
  [[ "$REF" == main ]] || MERGE_MAIN=1
fi

# Ruta C:/... en Windows: la entienden igual bash, git y docker.
WORK=$(winpath "$(mktemp -d)")
WT="$WORK/wt"
# Los registros quedan fuera del worktree, que se borra al terminar.
LOGS="$(dirname "$WORK")/verifica-$ID-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOGS"
PROJECT="verifica-$(printf '%s' "$ID" | tr 'A-Z' 'a-z')"
COMPOSE=(dk compose -p "$PROJECT" -f "$WT/docker-compose.yml" -f "$WORK/override.yml")

cleanup() {
  if [[ $SMOKE -eq 1 && -f "$WORK/override.yml" ]]; then
    "${COMPOSE[@]}" down -v --remove-orphans --rmi local >/dev/null 2>&1
  fi
  git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rm -rf "$WORK"
}
trap cleanup EXIT

git worktree add --detach --quiet "$WT" "$SHA" || exit 2

# La CI de pull_request prueba el commit de fusión con main, no la rama sola.
if [[ $MERGE_MAIN -eq 1 ]]; then
  if git -C "$WT" -c user.name=verifica -c user.email=verifica@localhost \
      merge --no-edit --quiet origin/main >"$LOGS/merge.log" 2>&1; then
    record "fusion-con-main" OK
  else
    record "fusion-con-main" FALLO
    echo "[$ID] La rama no se fusiona limpia con main; ver $LOGS/merge.log"
  fi
fi

# Cada contenedor recibe el código por la entrada estándar (git archive del commit probado) y lo
# desempaqueta en su propio disco: leer desde un volumen montado de Windows es muy lento.
src() { git -C "$WT" archive --format=tar HEAD; }

declare -A PIDS=()

# 2. Pruebas de cada servicio, todas a la vez, con uv y su caché.
for dir in "$WT"/services/*/; do
  s=$(basename "$dir")
  [[ -f "$dir/pyproject.toml" ]] || continue
  src | dk run --rm -i -v nisar-verifica-uv:/root/.cache/uv \
    -e UV_LINK_MODE=copy ghcr.io/astral-sh/uv:python3.11-bookworm \
    bash -c "mkdir /w && tar -C /w -xf - && cd /w/services/$s \
             && uv pip install --system -q -e '.[dev]' && pytest -q -p no:cacheprovider" \
    >"$LOGS/test-$s.log" 2>&1 &
  PIDS["test ($s)"]=$!
done

# Extra, la CI no lo hace: lint y vitest del frontend. node_modules en un volumen por versión
# de package-lock.json: npm ci solo corre cuando cambia.
if [[ $FRONT -eq 1 && -f "$WT/frontend/package.json" ]]; then
  LOCK=$(git -C "$WT" hash-object frontend/package-lock.json | cut -c1-12)
  src | dk run --rm -i -v "nisar-verifica-nm-$LOCK:/w/frontend/node_modules" \
    -v nisar-verifica-npm:/root/.npm node:22-alpine \
    sh -c 'tar -C /w -xf - && cd /w/frontend \
           && { test -f node_modules/.verifica-ok || { npm ci --no-audit --no-fund --loglevel=error && touch node_modules/.verifica-ok; }; } \
           && npm run lint && npm test' \
    >"$LOGS/frontend.log" 2>&1 &
  PIDS["frontend (extra)"]=$!
fi

# 3. Pila completa con datos sintéticos y prueba de humo, a la vez que las pruebas.
smoke() {
  "${COMPOSE[@]}" up -d --build >"$LOGS/compose-up.log" 2>&1 || return 1
  local base="http://localhost:$SMOKE_PORT" code
  # smoke.sh solo espera a verdicts; TiTiler puede tardar más en abrir su puerto.
  for _ in $(seq 1 90); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$base/tiles/cog/info" || true)
    [[ "$code" != 000 && "$code" != 502 && "$code" != 503 && "$code" != 504 ]] && break
    sleep 2
  done
  BASE="$base" bash "$WT/scripts/smoke.sh" >"$LOGS/smoke.log" 2>&1 && return 0
  "${COMPOSE[@]}" logs --no-color >"$LOGS/compose-logs.log" 2>&1
  return 1
}
if [[ $SMOKE -eq 1 ]]; then
  cat >"$WORK/override.yml" <<EOF
services:
  gateway:
    ports: !override
      - "$SMOKE_PORT:80"
  frontend:
    ports: !override
      - "$FRONT_PORT:80"
EOF
  smoke &
  PIDS["smoke"]=$!
fi

echo "[$ID] En marcha: ${!PIDS[*]}"
for name in $(printf '%s\n' "${!PIDS[@]}" | sort | tr ' ' '\001'); do
  name=${name//$'\001'/ }
  if wait "${PIDS[$name]}"; then record "$name" OK; else record "$name" FALLO; fi
done

# Resumen
echo
echo "[$ID] Resultado para ${REF} (${SHA:0:7}) en $((SECONDS - START)) s:"
status=0
for i in "${!NAMES[@]}"; do
  printf '  %-20s %s\n' "${NAMES[$i]}" "${RESULTS[$i]}"
  [[ "${RESULTS[$i]}" == OK ]] || status=1
done
echo "Registros: $LOGS"
if [[ $status -eq 0 ]]; then echo "TODO EN VERDE"; else echo "HAY FALLOS"; fi
exit $status
