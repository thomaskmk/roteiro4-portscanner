# Comparação: portscanner × nmap -sT

- Alvo: `172.30.0.10` (172.30.0.10)
- portscanner 1.0.0: início 2026-11-24T15:27:47-03:00, timeout 0.1s, workers 3, retries 0, duração 0.101s
- nmap 7.991: início Tue Nov 24 15:27:49 2026 — `/usr/lib/nmap/nmap --privileged -sT -Pn --reason -p 22,80,8080 -oA /home/thomaskmk/roteiro4-portscanner/evidencias/20261124-152747_timeout/nmap_padrao 172.30.0.10`

| Porta TCP | Estado esperado (configuração) | Scanner desenvolvido | Nmap (motivo) | Concordam? |
|---|---|---|---|---|
| 22 | - | timeout | closed (conn-refused) | **NÃO** |
| 80 | - | timeout | open (syn-ack) | **NÃO** |
| 8080 | - | timeout | open (syn-ack) | **NÃO** |

Divergências: **3** de 3 portas.

Equivalência usada: aberta→open, recusada→closed, timeout→filtered, erro→filtered. É uma aproximação; as divergências devem ser explicadas, não escondidas.
