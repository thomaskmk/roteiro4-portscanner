#!/bin/bash
# Seção 6: mudanças no estado do serviço (rodadas A, B, C).
#   A: serviço echo9000 ativo -> B: serviço parado -> C: serviço reiniciado
#   --container: acrescenta D (container do alvo parado) e E (container reiniciado)
# A porta 80 é escaneada junto como CONTROLE (não deve mudar nas rodadas A-C).
source "$(dirname "$0")/_common.sh"
require "$PY" "$NMAP"; require_lab
PORTS="${PORTS:-80,9000}"
SVC="${SVC:-echo9000}"
OUT=$(new_outdir estado); LOG="$OUT/execucao.log"
labels=()

round() {
  local name=$1 desc=$2
  echo "## Rodada $name — $desc" | tee -a "$LOG"
  snapshot "$OUT/contexto_$name.txt"
  run "$LOG" "${SCAN[@]}" "$TARGET" -p "$PORTS" -t 2 --all --json "$OUT/rodada_$name.json"
  run "$LOG" "$NMAP" -sT -Pn --reason -p "$PORTS" "$TARGET" -oN "$OUT/nmap_rodada_$name.txt"
  labels+=("$name: $desc=$OUT/rodada_$name.json")
}

run "$LOG" "${TEXEC[@]}" svc.sh start "$SVC"
round A "serviço ativo"

run "$LOG" "${TEXEC[@]}" svc.sh stop "$SVC"
round B "serviço interrompido"

run "$LOG" "${TEXEC[@]}" svc.sh start "$SVC"
round C "serviço reiniciado"

if [[ "${1:-}" == "--container" ]]; then
  run "$LOG" "${LAB[@]}" stop target
  echo "## Rodada D — container do alvo parado (IP deixa de existir)" | tee -a "$LOG"
  run "$LOG" "${SCAN[@]}" "$TARGET" -p "$PORTS" -t 5 --all --json "$OUT/rodada_D.json"
  run "$LOG" "$NMAP" -sT -Pn --reason -p "$PORTS" "$TARGET" -oN "$OUT/nmap_rodada_D.txt"
  labels+=("D: container parado=$OUT/rodada_D.json")
  run "$LOG" "${LAB[@]}" start target
  sleep 3
  round E "container reiniciado"
fi

"$PY" scripts/summarize.py timeline "${labels[@]}" -o "$OUT/resumo.md"
cat "$OUT/resumo.md"
echo "evidências em $OUT"
