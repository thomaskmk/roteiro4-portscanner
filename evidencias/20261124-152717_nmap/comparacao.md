# Comparação: portscanner × nmap -sT

- Alvo: `172.30.0.10` (172.30.0.10)
- portscanner 1.0.0: início 2026-11-24T15:27:17-03:00, timeout 2.0s, workers 8, retries 0, duração 2.0044s
- nmap 7.991: início Tue Nov 24 15:27:19 2026 — `/usr/lib/nmap/nmap --privileged -sT -Pn --reason -p 22,80,8080,9000-9004 -oA /home/thomaskmk/roteiro4-portscanner/evidencias/20261124-152717_nmap/nmap 172.30.0.10`

| Porta TCP | Estado esperado (configuração) | Scanner desenvolvido | Nmap (motivo) | Concordam? |
|---|---|---|---|---|
| 22 | sem serviço → recusada/closed | recusada (ECONNREFUSED) | closed (conn-refused) | sim |
| 80 | HTTP ativo → aberta/open | aberta | open (syn-ack) | sim |
| 8080 | HTTP ativo → aberta/open | aberta | open (syn-ack) | sim |
| 9000 | eco TCP alternável (A/B/C) → aberta/open quando ligado | aberta | open (syn-ack) | sim |
| 9001 | serviço ativo atrás de DROP → timeout/filtered | timeout | filtered (no-response) | sim |
| 9002 | sem serviço, REJECT icmp-port-unreachable → recusa via ICMP | recusada (ECONNREFUSED) | closed (conn-refused) | sim |
| 9003 | sem serviço, REJECT icmp-host-unreachable → erro (host inalcançável) | erro (EHOSTUNREACH) | filtered (host-unreach) | sim |
| 9004 | serviço ativo atrás de REJECT tcp-reset → recusada (RST forjado) | recusada (ECONNREFUSED) | closed (conn-refused) | sim |

Divergências: **0** de 8 portas.

Equivalência usada: aberta→open, recusada→closed, timeout→filtered, erro→filtered. É uma aproximação; as divergências devem ser explicadas, não escondidas.
