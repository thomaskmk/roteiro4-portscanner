#!/bin/bash
# Funções e variáveis compartilhadas pelos scripts de experimento.
# Variáveis que podem ser sobrescritas no ambiente:
#   TARGET  (padrão 172.30.0.10)   PY (python3)   NMAP (nmap)
#   DC      comando do compose, ex.: DC="sudo docker compose"
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${TARGET:-172.30.0.10}"
PY="${PY:-python3}"
NMAP="${NMAP:-nmap}"

if [[ -z "${DC:-}" ]]; then
  if docker compose version >/dev/null 2>&1; then DC="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then DC="docker-compose"
  else DC=""; fi
fi
read -ra DC_ARR <<<"$DC"
LAB=("${DC_ARR[@]}" -f "$ROOT/lab/docker-compose.yml")
TEXEC=("${LAB[@]}" exec -T target)     # executa um comando dentro do alvo
SCAN=("$PY" -m portscanner)

require() {
  for bin in "$@"; do
    command -v "$bin" >/dev/null 2>&1 || { echo "erro: '$bin' não encontrado no PATH" >&2; exit 1; }
  done
}

require_lab() {
  [[ -n "$DC" ]] || { echo "erro: docker compose não encontrado (defina DC=...)" >&2; exit 1; }
  "${TEXEC[@]}" true 2>/dev/null || {
    echo "erro: container 'target' não está rodando. Suba com: ./scripts/lab.sh up" >&2; exit 1; }
}

# Cria evidencias/<data-hora>_<nome>/ e imprime o caminho.
new_outdir() {
  local dir="$ROOT/evidencias/$(date +%Y%m%d-%H%M%S)_$1"
  mkdir -p "$dir"
  echo "$dir"
}

# run LOG comando...  -> registra comando, horário, saída e código de saída no LOG.
run() {
  local log=$1; shift
  { printf '$ %s\n' "$*"; printf '# início: %s\n' "$(date -Is)"; } | tee -a "$log"
  set +e
  "$@" 2>&1 | tee -a "$log"
  local rc=${PIPESTATUS[0]}
  set -e
  printf '# exit=%s  fim: %s\n\n' "$rc" "$(date -Is)" | tee -a "$log"
}

# Registra o estado do ambiente (serviços, portas em escuta, firewall, latência, versões).
snapshot() {
  local file=$1
  {
    echo "### snapshot $(date -Is)"
    echo "## host: $(uname -srm) | $("$PY" --version 2>&1) | $("$NMAP" --version 2>/dev/null | head -1)"
    echo "## alvo: serviços (svc.sh status)"; "${TEXEC[@]}" svc.sh status || true
    echo "## alvo: portas em escuta (ss -ltnp)"; "${TEXEC[@]}" ss -ltnp || true
    echo "## alvo: firewall (iptables -S INPUT)"; "${TEXEC[@]}" firewall.sh show || true
    echo "## alvo: qdisc (latência)"; "${TEXEC[@]}" latency.sh show || true
    echo
  } >>"$file" 2>&1
}
