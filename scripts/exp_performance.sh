#!/bin/bash
# Melhoria (seção 7): execução concorrente + medição de desempenho.
# Compara a duração do scan com diferentes números de workers.
#   faixa lenta  10000-10099: DROP no alvo -> cada porta espera o timeout
#   faixa rápida 20000-20999: sem serviço  -> RST imediato
source "$(dirname "$0")/_common.sh"
require "$PY"; require_lab
T="${T:-0.5}"
OUT=$(new_outdir desempenho); LOG="$OUT/execucao.log"
files=()
for w in 1 10 50 100; do
  run "$LOG" "${SCAN[@]}" "$TARGET" -p 10000-10099 -t "$T" -w "$w" --json "$OUT/lenta_w$w.json"
  files+=("$OUT/lenta_w$w.json")
done
for w in 1 10 50 100; do
  run "$LOG" "${SCAN[@]}" "$TARGET" -p 20000-20999 -t "$T" -w "$w" --json "$OUT/rapida_w$w.json"
  files+=("$OUT/rapida_w$w.json")
done
"$PY" scripts/summarize.py perf "${files[@]}" -o "$OUT/resumo.md"
cat "$OUT/resumo.md"
echo "evidências em $OUT"
