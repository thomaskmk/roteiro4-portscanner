| Rodada | Início | Timeout | 80/tcp | 9000/tcp |
|---|---|---|---|---|
| A: serviço ativo | 2026-11-24T15:27:23-03:00 | 2.0s | aberta, 0ms | aberta, 0ms |
| B: serviço interrompido | 2026-11-24T15:27:26-03:00 | 2.0s | aberta, 0ms | recusada ECONNREFUSED, 0ms |
| C: serviço reiniciado | 2026-11-24T15:27:29-03:00 | 2.0s | aberta, 0ms | aberta, 0ms |
| D: container parado | 2026-11-24T15:27:32-03:00 | 5.0s | erro EHOSTUNREACH, 3078ms | erro EHOSTUNREACH, 3078ms |
| E: container reiniciado | 2026-11-24T15:27:44-03:00 | 2.0s | aberta, 0ms | aberta, 0ms |
