#!/bin/bash
# Atalhos do laboratório.
# Uso: ./scripts/lab.sh up | down | rebuild | status | shell | svc ARGS | firewall ARGS | latency ARGS
source "$(dirname "$0")/_common.sh"
[[ -n "$DC" ]] || { echo "erro: docker compose não encontrado" >&2; exit 1; }

case "${1:-status}" in
  up)       "${LAB[@]}" up -d --build && sleep 2 && "${TEXEC[@]}" svc.sh status ;;
  down)     "${LAB[@]}" down ;;
  rebuild)  "${LAB[@]}" up -d --build --force-recreate ;;
  status)   "${LAB[@]}" ps; echo; snapshot /dev/stdout ;;
  logs)     "${LAB[@]}" logs target ;;
  shell)    "${LAB[@]}" exec target bash ;;
  svc)      shift; "${TEXEC[@]}" svc.sh "$@" ;;
  firewall) shift; "${TEXEC[@]}" firewall.sh "$@" ;;
  latency)  shift; "${TEXEC[@]}" latency.sh "$@" ;;
  *) echo "uso: $0 up|down|rebuild|status|logs|shell|svc ...|firewall ...|latency ..." >&2; exit 2 ;;
esac
