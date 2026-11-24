# Comparação: portscanner × nmap -sT

- Alvo: `172.30.0.10` (172.30.0.10)
- portscanner 1.0.0: início 2026-11-24T15:27:47-03:00, timeout 0.1s, workers 3, retries 0, duração 0.101s
- nmap 7.991: início Tue Nov 24 15:27:52 2026 — `/usr/lib/nmap/nmap --privileged -sT -Pn --reason --initial-rtt-timeout 100ms --max-rtt-timeout 100ms --max-retries 0 -p 22,80,8080 -oA /home/thomaskmk/roteiro4-portscanner/evidencias/20261124-152747_timeout/nmap_rtt100ms 172.30.0.10`

| Porta TCP | Estado esperado (configuração) | Scanner desenvolvido | Nmap (motivo) | Concordam? |
|---|---|---|---|---|
| 22 | - | timeout | filtered (no-response) | sim |
| 80 | - | timeout | filtered (no-response) | sim |
| 8080 | - | timeout | filtered (no-response) | sim |

Divergências: **0** de 3 portas.

Equivalência usada: aberta→open, recusada→closed, timeout→filtered, erro→filtered. É uma aproximação; as divergências devem ser explicadas, não escondidas.
