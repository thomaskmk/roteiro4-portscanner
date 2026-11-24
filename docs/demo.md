# Roteiro de ensaio da demonstração (seção 9.4)

## Preparação (antes da aula)

```bash
cd portscanner && git pull
./scripts/lab.sh up && ./scripts/lab.sh status
python3 -m unittest discover -s tests -t .
```

## Pedidos prováveis do professor e o que fazer

| Pedido | Comando | O que explicar |
|---|---|---|
| Alterar porta/intervalo | `python3 -m portscanner 172.30.0.10 -p 75-85 --all` | `parse_ports` em `cli.py`; validação antes de enviar pacotes |
| Derrubar um serviço | `./scripts/lab.sh svc stop http8080` e escanear 8080 | sem `listen()`, a pilha responde RST → `ConnectionRefusedError` |
| Subir de novo | `./scripts/lab.sh svc start http8080` | o estado é uma observação no tempo |
| Mudar o timeout | `./scripts/lab.sh latency on 300` + `-t 0.1` e `-t 1` | `settimeout` em `probe.py`; timeout < RTT ⇒ `timeout` até em porta aberta |
| Porta filtrada | `-p 9001 -t 2` | DROP ⇒ silêncio ⇒ timeout; há serviço ativo atrás |
| Resultado inesperado | `-p 9004` | RST forjado pelo firewall com serviço ativo atrás |
| Explicar uma função | `_attempt()` em `probe.py` | ordem dos `except`; `with` fecha o socket |
| Ctrl+C | intervalo `10000-10099 -w 1` e Ctrl+C | `engine.py`: `cancel_futures`, resultado parcial, exit 130 |

## Perguntas para responder sem olhar o código

1. Onde e como o timeout é aplicado? Diferença entre `settimeout`, `setblocking(False)` e `setdefaulttimeout`.
2. Por que `ConnectionRefusedError` precisa vir antes de `OSError`?
3. Quais pacotes trafegam em cada estado (SYN, SYN/ACK, ACK, RST, ICMP, silêncio)?
4. Por que a rodada B dá `recusada` e o que muda se o container inteiro for parado?
5. Por que a resolução de nome acontece uma vez só, fora das threads?
6. O que é `erro-local` e por que não diz nada sobre o destino?
7. Por que `--retries` só repete timeouts?
8. Por que o Nmap pode discordar do scanner com timeout baixo?
9. Porta aberta ⇒ serviço identificado? ⇒ vulnerabilidade? Por quê não?

## Modificações ao vivo que você deve conseguir fazer

- Adicionar uma coluna ao CSV (`CSV_FIELDS` em `report.py` + campo em `ProbeResult`).
- Mudar o padrão de `--timeout` ou de `--workers` (`build_parser` em `cli.py`).
- Fazer `--retries` repetir também `erro` (condição em `probe()` em `probe.py`).
