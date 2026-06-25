#!/usr/bin/env bash
# Divergencia RÁPIDA contra los replays curados de keidroid (15 partidas) — el medidor del
# bucle cerrado. Mucho más rápido que el decode del zip completo. Escribe reporte con fecha
# e imprime el resumen de agree% por contexto (lo que se compara entre iteraciones).
#
# Uso: tools/run_fast_divergence.sh [AGENT_DIR]
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"
ROOT="/Users/franmilla/FMA/proyectos/ptcg-ai-battle"; cd "$ROOT"
AGENT_DIR="${1:-agents_official/mega_starmie_v1}"
AGENT_TAG="$(basename "$AGENT_DIR")"
IMAGE="ptcg-cabt"

colima status >/dev/null 2>&1 || { echo "ERROR: colima no vivo"; exit 1; }
if docker ps --format '{{.Command}}' 2>/dev/null | grep -q "divergence"; then
  echo "ERROR: ya hay un decode corriendo (no paralelizar)"; exit 1
fi

STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUTDIR="$ROOT/research/divergence"; mkdir -p "$OUTDIR"
OUT="$OUTDIR/fast_${AGENT_TAG}_${STAMP}.txt"

docker run --platform=linux/amd64 --rm -v "$ROOT":/work -w /work/ptcg-abc "$IMAGE" \
  python -u tools/divergence_fast.py \
    "/work/$AGENT_DIR" "/work/data/megastarmie_analysis/keidroid_d21_*.json" 40 \
  >"$OUT" 2>"$OUTDIR/fast_${AGENT_TAG}.stderr.log" \
  || { echo "decode falló:"; tail -15 "$OUTDIR/fast_${AGENT_TAG}.stderr.log"; exit 1; }

echo "REPORTE: $OUT"
echo "RESUMEN agree% por contexto (arriba = más divergimos):"
grep -E "^# games|^=====" "$OUT"
