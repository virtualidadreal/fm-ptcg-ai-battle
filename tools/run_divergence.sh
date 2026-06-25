#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BUCLE DE DIVERGENCIA — mide, decisión a decisión, dónde nuestro agente pilota
# distinto a keidroid (#1 del ladder, Mega Starmie ex) sobre sus replays reales.
#
# NO predice el score del ladder (la señal local está refutada: μ−3σ vs media).
# SÍ es un diagnóstico cualitativo de pilotaje: "en estas decisiones jugamos
# distinto al #1" — exactamente lo que cazó el bug de Salvatore, pero sistemático.
#
# El engine (libcg.so) es Linux x86-64 → corre dentro de Docker (ptcg-cabt, vía
# Rosetta en colima). colima SOLO monta $HOME por defecto, así que el zip de
# episodios (en /tmp) y el mapeo Elo se STAGEAN bajo el repo (data/) y se montan
# vía /work — montar /tmp directamente da un dir VACÍO dentro del contenedor.
#
# Uso:
#   tools/run_divergence.sh [AGENT_DIR] [MAX_GAMES] [CONTEXT]
#   tools/run_divergence.sh agents_official/mega_starmie_v1 116
#   tools/run_divergence.sh agents_official/mega_starmie_v1 116 MULLIGAN
#
# Salida: research/divergence/keidroid_<agente>_<fecha>.txt  (+ stderr log al lado)
# GOTCHAS (de ptcg-abc/CLAUDE.md): archetype EXACTO (se auto-resuelve), NUNCA
# `| tail` (contextos por agree% ASC → tail tira los peores), NO paralelizar
# decodes (CPU pileup → cuelga colima). Por eso corre UNO y a fuego lento.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"

ROOT="/Users/franmilla/FMA/proyectos/ptcg-ai-battle"
cd "$ROOT"

AGENT_DIR="${1:-agents_official/mega_starmie_v1}"
MAX_GAMES="${2:-116}"
CONTEXT="${3:-}"          # opcional: restringe a un SelectContext (ej MULLIGAN, MAIN)
PLAYER="keidroid"
IMAGE="ptcg-cabt"

# 1) Localiza el zip de episodios (los 720MB diarios de Kaggle), en /tmp o ya staged.
SRC_ZIP="$(ls -t /tmp/ep*/pokemon-tcg-ai-battle-episodes-*.zip "$ROOT"/data/episodes/pokemon-tcg-ai-battle-episodes-*.zip 2>/dev/null | head -1 || true)"
if [[ -z "${SRC_ZIP}" ]]; then
  echo "ERROR: no encuentro el zip de episodios. Descárgalo:"
  echo "  kaggle datasets download kaggle/pokemon-tcg-ai-battle-episodes-2026-06-22 -p /tmp/ep22"
  exit 1
fi
ZIP_NAME="$(basename "$SRC_ZIP")"

# 1b) STAGEA bajo el repo (colima monta $HOME, no /tmp). Copia solo si falta.
STAGE_EP="$ROOT/data/episodes"
mkdir -p "$STAGE_EP"
if [[ ! -f "$STAGE_EP/$ZIP_NAME" ]]; then
  echo "[divergencia] stageando zip bajo el repo (una vez, ~716MB)..."
  cp "$SRC_ZIP" "$STAGE_EP/$ZIP_NAME"
fi
echo "[divergencia] zip episodios (staged): $STAGE_EP/$ZIP_NAME"

# 1c) STAGEA el mapeo Elo (/tmp/lb) bajo el repo para montarlo en el contenedor.
STAGE_LB="$ROOT/data/lb"
mkdir -p "$STAGE_LB"
if [[ -d /tmp/lb ]]; then cp -f /tmp/lb/* "$STAGE_LB"/ 2>/dev/null || true; fi

# 2) colima vivo + sin otro decode corriendo (evita el CPU pileup que cuelga).
colima status >/dev/null 2>&1 || { echo "ERROR: colima no está vivo (colima start)"; exit 1; }
if docker ps --format '{{.Command}}' 2>/dev/null | grep -q "divergence_decode"; then
  echo "ERROR: ya hay un divergence_decode corriendo en Docker. Espera a que acabe (no paralelizar)."
  exit 1
fi

ZIP_IN="/work/data/episodes/$ZIP_NAME"   # ruta del zip DENTRO del contenedor (vía /work)

# 3) Resuelve el archetype con que ma.dk() clasifica el mazo de keidroid (el gotcha:
#    string equivocado → filtra TODAS sus partidas → agree 0/0). Probe ligero.
echo "[divergencia] resolviendo archetype de keidroid..."
ARCH="$(docker run --platform=linux/amd64 --rm \
  -v "$ROOT":/work -v "$STAGE_LB":/tmp/lb \
  -w /work/ptcg-abc "$IMAGE" python - "$PLAYER" "$ZIP_IN" <<'PY'
import sys, os, json, zipfile, importlib.util
ROOT=os.getcwd()
sys.path.insert(0, ROOT+'/docs/official/models/cg-lib')
spec=importlib.util.spec_from_file_location('ma', ROOT+'/tools/meta_analyze.py')
ma=importlib.util.module_from_spec(spec); spec.loader.exec_module(ma)
player, zp = sys.argv[1], sys.argv[2]
z=zipfile.ZipFile(zp)
from collections import Counter
seen=Counter()
for nm in (x for x in z.namelist() if x.endswith('.json')):
    try:
        d=json.loads(z.read(nm)); rw=d['rewards']
        if rw[0]==rw[1]: continue
        win=0 if rw[0]>rw[1] else 1
        names=[a['Name'] for a in d['info']['Agents']]
        if names[win]!=player: continue
        deck=d['steps'][1][win]['action']
        seen[ma.dk(deck)] += 1
    except Exception: continue
    if sum(seen.values())>=8: break
sys.stderr.write('PROBE games=%d dk=%r\n' % (sum(seen.values()), dict(seen)))
sys.stdout.write(seen.most_common(1)[0][0] if seen else '__NONE__')
PY
)" || ARCH="__ERR__"
echo "[divergencia] archetype resuelto: '$ARCH'"
if [[ "$ARCH" == "__ERR__" || "$ARCH" == "__NONE__" ]]; then
  echo "ERROR: el probe no encontró partidas de keidroid en el zip (o falló). ARCH='$ARCH'"; exit 1
fi

# 4) Corre el decode. Salida a archivo (NUNCA a tail). stderr a log aparte.
STAMP="$(date +%Y-%m-%d)"
OUTDIR="$ROOT/research/divergence"
mkdir -p "$OUTDIR"
AGENT_TAG="$(basename "$AGENT_DIR")"
OUT="$OUTDIR/keidroid_${AGENT_TAG}_${STAMP}.txt"
LOG="$OUTDIR/keidroid_${AGENT_TAG}_${STAMP}.stderr.log"

echo "[divergencia] corriendo decode (max-games=$MAX_GAMES, player=$PLAYER)..."
DECODE_ARGS=(python tools/divergence_decode.py "$ZIP_IN" "../$AGENT_DIR"
             --archetype "$ARCH" --player "$PLAYER" --max-games "$MAX_GAMES" --show 40)
[[ -n "$CONTEXT" ]] && DECODE_ARGS+=(--context "$CONTEXT")

docker run --platform=linux/amd64 --rm \
  -v "$ROOT":/work -v "$STAGE_LB":/tmp/lb \
  -w /work/ptcg-abc "$IMAGE" "${DECODE_ARGS[@]}" \
  >"$OUT" 2>"$LOG" || { echo "decode falló — revisa $LOG"; tail -20 "$LOG"; exit 1; }

echo ""
echo "[divergencia] LISTO. Reporte: $OUT"
echo "[divergencia] Contextos por agree% (los de ARRIBA = donde más divergimos):"
grep -E "^=====" "$OUT" | head -40
