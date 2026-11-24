#!/bin/bash
# Regras de firewall do alvo (namespace de rede do container, não afeta o host).
#
#   9001        DROP                                  -> silêncio      (serviço ativo atrás)
#   9002        REJECT icmp-port-unreachable          -> recusa via ICMP
#   9003        REJECT icmp-host-unreachable          -> "host inalcançável" via ICMP
#   9004        REJECT tcp-reset                      -> RST forjado   (serviço ativo atrás)
#   10000-10099 DROP                                  -> faixa lenta (Ctrl+C, desempenho)
#
# Uso: firewall.sh apply | clear | show
set -euo pipefail
IPT="${IPTABLES:-iptables}"

apply() {
  "$IPT" -F INPUT
  "$IPT" -A INPUT -p tcp --dport 9001 -j DROP
  "$IPT" -A INPUT -p tcp --dport 9002 -j REJECT --reject-with icmp-port-unreachable
  "$IPT" -A INPUT -p tcp --dport 9003 -j REJECT --reject-with icmp-host-unreachable
  "$IPT" -A INPUT -p tcp --dport 9004 -j REJECT --reject-with tcp-reset
  "$IPT" -A INPUT -p tcp --dport 10000:10099 -j DROP
  echo "firewall aplicado"
}

case "${1:-show}" in
  apply) apply ;;
  clear) "$IPT" -F INPUT; echo "firewall removido (INPUT vazio)" ;;
  show)  "$IPT" -S INPUT ;;
  *) echo "uso: $0 apply|clear|show" >&2; exit 2 ;;
esac
