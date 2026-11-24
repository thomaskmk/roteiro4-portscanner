#!/bin/bash
# Seção 5: mesmo alvo, mesmas portas, mesma origem -> scanner vs nmap -sT.
# Uso: [PORTS=...] [TIMEOUT=2] ./scripts/exp_nmap.sh
source "$(dirname "$0")/_common.sh"
require "$PY" "$NMAP"; require_lab
PORTS="${PORTS:-22,80,8080,9000-9004}"
TIMEOUT="${TIMEOUT:-2}"
OUT=$(new_outdir nmap); LOG="$OUT/execucao.log"
snapshot "$OUT/contexto.txt"

run "$LOG" "${SCAN[@]}" "$TARGET" -p "$PORTS" -t "$TIMEOUT" --all --json "$OUT/scanner.json" --csv "$OUT/scanner.csv"
# -sT: TCP connect (mesma técnica do scanner) | -Pn: sem descoberta de host | --reason: motivo do estado
run "$LOG" "$NMAP" -sT -Pn --reason -p "$PORTS" "$TARGET" -oA "$OUT/nmap"
snapshot "$OUT/contexto.txt"

"$PY" scripts/compare.py "$OUT/scanner.json" "$OUT/nmap.xml" --expected lab/expected.json -o "$OUT/comparacao.md"
cat "$OUT/comparacao.md"
echo "evidências em $OUT"
