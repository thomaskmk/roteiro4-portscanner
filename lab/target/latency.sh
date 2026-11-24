#!/bin/bash
# Adiciona/remove atraso artificial na interface do alvo com tc netem.
# Afeta TODO o tráfego que sai do alvo (inclusive SYN/ACK e RST), simulando uma rede lenta.
# Uso: latency.sh on [ms] | off | show
set -euo pipefail
IFACE=$(ip route | awk '/^default/ {print $5; exit}')
IFACE=${IFACE:-eth0}

case "${1:-show}" in
  on)   ms=${2:-300}
        tc qdisc replace dev "$IFACE" root netem delay "${ms}ms"
        echo "latência de ${ms}ms ativada em $IFACE" ;;
  off)  tc qdisc del dev "$IFACE" root 2>/dev/null || true
        echo "latência removida de $IFACE" ;;
  show) tc qdisc show dev "$IFACE" ;;
  *) echo "uso: $0 on [ms] | off | show" >&2; exit 2 ;;
esac
