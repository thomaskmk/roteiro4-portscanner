#!/bin/bash
# Inicializa o alvo: aplica o firewall, sobe os serviços e mantém o container vivo.
set -u

rm -rf /run/svc   # pidfiles antigos (de antes de um restart) não valem mais
echo "[entrypoint] aplicando regras de firewall"
if ! firewall.sh apply; then
  echo "[entrypoint] ERRO: não foi possível aplicar iptables (o container tem cap NET_ADMIN?)." >&2
  echo "[entrypoint] as portas 9001-9004 e 10000-10099 NÃO terão o comportamento esperado." >&2
fi

echo "[entrypoint] iniciando serviços"
svc.sh start all
svc.sh status

echo "[entrypoint] pronto"
exec sleep infinity
