#!/bin/bash
# Seções 3.3 e 4: testes iniciais e tratamento de erros (7 situações + extras).
# Saída: evidencias/<data>_erros/{execucao.log, contexto.txt, lab_completo.json, interrompido.json}
source "$(dirname "$0")/_common.sh"
require "$PY"; require_lab
OUT=$(new_outdir erros); LOG="$OUT/execucao.log"
snapshot "$OUT/contexto.txt"

echo "## 3.3 visão geral do lab (todas as portas configuradas)" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 22,80,8080,9000-9004 -t 2 --all --json "$OUT/lab_completo.json"

echo "## 4.1 porta com serviço ativo" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 80

echo "## 4.2 porta sem serviço" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 22

echo "## 4.3 número de porta inválido" | tee -a "$LOG"
for spec in 0 70000 abc; do run "$LOG" "${SCAN[@]}" "$TARGET" -p "$spec"; done

echo "## 4.4 intervalo de portas inválido" | tee -a "$LOG"
for spec in 100-20 1-70000 10- 22,,80; do run "$LOG" "${SCAN[@]}" "$TARGET" -p "$spec"; done

echo "## 4.5 endereço de destino inválido" | tee -a "$LOG"
for host in naoexiste.invalid 300.1.1.1; do run "$LOG" "${SCAN[@]}" "$host" -p 80; done

echo "## 4.6 timeout de conexão (porta 9001: DROP)" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 9001 -t 2
run "$LOG" "${SCAN[@]}" "$TARGET" -p 9001 -t 1 -r 2

echo "## 4.7 interrupção pelo usuário (SIGINT após 3 s numa faixa com DROP)" | tee -a "$LOG"
run "$LOG" timeout --preserve-status -s INT 3 "${SCAN[@]}" "$TARGET" -p 10000-10099 -w 1 -t 1 --json "$OUT/interrompido.json"

echo "## extra: erros de comunicação" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 9002,9003 -t 2 --all
run "$LOG" "${SCAN[@]}" 172.30.0.99 -p 80 -t 5     # IP sem host na sub-rede (ARP sem resposta)

echo "## extra: parâmetros inválidos" | tee -a "$LOG"
run "$LOG" "${SCAN[@]}" "$TARGET" -p 80 -t 0
run "$LOG" "${SCAN[@]}" "$TARGET" -p 80 -w 0

echo "evidências em $OUT"
