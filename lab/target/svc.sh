#!/bin/bash
# Controle dos serviços de teste do alvo (permite ligar/desligar sem derrubar o container).
#
#   http80    python3 -m http.server 80
#   http8080  python3 -m http.server 8080
#   echo9000  socat (eco TCP)              <- usado no experimento A/B/C
#   echo9001  socat (eco TCP) atrás de DROP
#   echo9004  socat (eco TCP) atrás de REJECT tcp-reset
#
# Uso: svc.sh start|stop|restart NOME|all  |  svc.sh status  |  svc.sh list
set -uo pipefail

RUN_DIR=/run/svc
LOG_DIR=/var/log/svc
mkdir -p "$RUN_DIR" "$LOG_DIR"

ALL=(http80 http8080 echo9000 echo9001 echo9004)

cmd_for() {
  case "$1" in
    http80)   echo "python3 -m http.server 80 --directory /srv/www" ;;
    http8080) echo "python3 -m http.server 8080 --directory /srv/www" ;;
    echo9000) echo "socat TCP-LISTEN:9000,reuseaddr,fork EXEC:cat" ;;
    echo9001) echo "socat TCP-LISTEN:9001,reuseaddr,fork EXEC:cat" ;;
    echo9004) echo "socat TCP-LISTEN:9004,reuseaddr,fork EXEC:cat" ;;
    *) return 1 ;;
  esac
}

port_of() { echo "${1//[!0-9]/}"; }

is_running() {
  local pidfile="$RUN_DIR/$1.pid"
  [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null
}

listening() { ss -Hltn "sport = :$(port_of "$1")" | grep -q LISTEN; }

start_one() {
  local name=$1 cmd
  cmd=$(cmd_for "$name") || { echo "serviço desconhecido: $name" >&2; return 2; }
  if is_running "$name"; then echo "$name já está em execução"; return 0; fi
  setsid $cmd >>"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$RUN_DIR/$name.pid"
  for _ in $(seq 1 50); do listening "$name" && break; sleep 0.1; done
  if listening "$name"; then
    echo "$(date -Is) $name iniciado (porta $(port_of "$name"))"
  else
    echo "$(date -Is) ERRO: $name não abriu a porta $(port_of "$name")" >&2; return 1
  fi
}

stop_one() {
  local name=$1
  cmd_for "$name" >/dev/null || { echo "serviço desconhecido: $name" >&2; return 2; }
  if ! is_running "$name"; then echo "$name já está parado"; rm -f "$RUN_DIR/$name.pid"; return 0; fi
  local pid; pid=$(cat "$RUN_DIR/$name.pid")
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"   # grupo inteiro (socat faz fork)
  for _ in $(seq 1 50); do listening "$name" || break; sleep 0.1; done
  rm -f "$RUN_DIR/$name.pid"
  if listening "$name"; then
    echo "$(date -Is) ERRO: porta $(port_of "$name") ainda em escuta" >&2; return 1
  fi
  echo "$(date -Is) $name parado (porta $(port_of "$name") liberada)"
}

status() {
  printf "%-10s %-6s %-10s\n" SERVIÇO PORTA ESTADO
  for name in "${ALL[@]}"; do
    local state="parado"
    is_running "$name" && state="rodando"
    listening "$name" && state="$state/escuta" || state="$state/sem-escuta"
    printf "%-10s %-6s %-10s\n" "$name" "$(port_of "$name")" "$state"
  done
}

action=${1:-status}; target=${2:-}
targets=("$target"); [[ "$target" == "all" ]] && targets=("${ALL[@]}")

case "$action" in
  start)   [[ -n "$target" ]] || { echo "uso: $0 start NOME|all" >&2; exit 2; }
           for t in "${targets[@]}"; do start_one "$t"; done ;;
  stop)    [[ -n "$target" ]] || { echo "uso: $0 stop NOME|all" >&2; exit 2; }
           for t in "${targets[@]}"; do stop_one "$t"; done ;;
  restart) for t in "${targets[@]}"; do stop_one "$t"; start_one "$t"; done ;;
  status)  status ;;
  list)    printf "%s\n" "${ALL[@]}" ;;
  *) echo "uso: $0 start|stop|restart NOME|all | status | list" >&2; exit 2 ;;
esac
