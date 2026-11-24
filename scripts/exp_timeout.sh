#!/bin/bash
# Seção 8.3: influência do timeout. Adiciona latência artificial no alvo e varia o timeout.
# Uso: [LAT_MS=300] [PORTS=22,80,8080] ./scripts/exp_timeout.sh
source "$(dirname "$0")/_common.sh"
require "$PY" "$NMAP"; require_lab
LAT_MS="${LAT_MS:-300}"
PORTS="${PORTS:-22,80,8080}"
OUT=$(new_outdir timeout); LOG="$OUT/execucao.log"
trap '"${TEXEC[@]}" latency.sh off >/dev/null 2>&1 || true' EXIT

echo "## linha de base: sem latência" | tee -a "$LOG"
"${TEXEC[@]}" latency.sh off >/dev/null
run "$LOG" "${SCAN[@]}" "$TARGET" -p "$PORTS" -t 2 --all --json "$OUT/base.json"

echo "## com ${LAT_MS}ms de atraso no alvo" | tee -a "$LOG"
run "$LOG" "${TEXEC[@]}" latency.sh on "$LAT_MS"
snapshot "$OUT/contexto.txt"
labels=("base=$OUT/base.json")
for t in 0.1 0.25 0.5 1 2; do
  run "$LOG" "${SCAN[@]}" "$TARGET" -p "$PORTS" -t "$t" --all --json "$OUT/t$t.json"
  labels+=("t=${t}s=$OUT/t$t.json")
done
run "$LOG" "$NMAP" -sT -Pn --reason -p "$PORTS" "$TARGET" -oA "$OUT/nmap_padrao"
run "$LOG" "$NMAP" -sT -Pn --reason --initial-rtt-timeout 100ms --max-rtt-timeout 100ms --max-retries 0 \
  -p "$PORTS" "$TARGET" -oA "$OUT/nmap_rtt100ms"
run "$LOG" "${TEXEC[@]}" latency.sh off

"$PY" scripts/summarize.py timeline "${labels[@]}" -o "$OUT/resumo.md"
"$PY" scripts/compare.py "$OUT/t0.1.json" "$OUT/nmap_padrao.xml" -o "$OUT/comparacao_t0.1_vs_nmap.md"
"$PY" scripts/compare.py "$OUT/t0.1.json" "$OUT/nmap_rtt100ms.xml" -o "$OUT/comparacao_t0.1_vs_nmap_rtt100.md"
cat "$OUT/resumo.md"
echo "evidências em $OUT"
