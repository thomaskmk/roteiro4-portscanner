# portscanner — Roteiro 4 (Tecnologias Hacker, Insper)

Scanner de portas TCP por **conexão completa** (*TCP connect scan*), escrito em Python usando
**somente a biblioteca padrão**. Para cada porta, o programa chama `connect()`; o sistema
operacional executa o *three-way handshake* e o resultado da tentativa indica o estado da porta.

> Use apenas em sistemas próprios ou expressamente autorizados. O laboratório Docker deste
> repositório existe para isso.

## Requisitos

- Python **3.9+** (usa `ThreadPoolExecutor.shutdown(cancel_futures=True)`); nenhuma dependência externa.
- Para o laboratório e os experimentos: Linux com Docker + Docker Compose v2 e **nmap** (usados na VM Kali).

## Execução

A partir da raiz do repositório:

```bash
python3 -m portscanner ALVO [-p PORTAS] [opções]
python3 -m portscanner --help
```

### Parâmetros

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `ALVO` | — | IP (v4/v6) ou hostname. Resolvido **uma vez** antes do scan. |
| `-p, --ports` | `1-1024` | Porta (`80`), intervalo (`20-25`) ou lista (`22,80,8000-8010`). Faixa válida 1–65535. |
| `-t, --timeout` | `1.0` | Tempo limite de **cada** tentativa, em segundos (0 < t ≤ 60). |
| `-w, --workers` | `50` | Tentativas simultâneas (1 = sequencial; máx. 1000; limitado pelo nº de descritores do SO). |
| `-r, --retries` | `0` | Novas tentativas **apenas** para portas em timeout (máx. 5). |
| `-4` / `-6` | auto | Força IPv4 / IPv6 (no automático, IPv4 é preferido). |
| `--open` / `--all` | auto | Mostra só abertas / todas. No automático, acima de 50 portas as recusadas são omitidas da tabela (mas contadas no resumo e exportadas). |
| `--json ARQ` | — | Exporta resultados + metadados (parâmetros, início, fim, duração). |
| `--csv ARQ` | — | Exporta uma linha por porta. |
| `--log ARQ` | — | Registra parâmetros, cada teste e erros em arquivo. |
| `-v, --verbose` | — | Mostra cada porta assim que termina (stderr). |

### Estados reportados

| Estado | O que aconteceu | Exceção Python | ≈ Nmap |
|---|---|---|---|
| `aberta` | handshake concluído (SYN → SYN/ACK → ACK) | — | open |
| `recusada` | destino recusou: RST, ou ICMP *port-unreachable* convertido pelo kernel | `ConnectionRefusedError` | closed |
| `timeout` | nenhuma resposta dentro do tempo limite — **causa indeterminada** (DROP, perda, host desligado, timeout curto) | `socket.timeout` / `TimeoutError` | filtered |
| `erro` | outra condição de rede, ex.: `EHOSTUNREACH`, `ENETUNREACH` | `OSError` | filtered |
| `erro-local` | falha na máquina que executa o scan (ex.: `EMFILE`, `EADDRNOTAVAIL`) — a porta **não** foi testada | `OSError` | — |

Códigos de saída: `0` concluído · `1` erro de execução (destino não resolvido, falha ao gravar) ·
`2` parâmetros inválidos · `130` interrompido (Ctrl+C, resultado parcial exibido).

### Exemplos

```bash
python3 -m portscanner 127.0.0.1 -p 22
python3 -m portscanner 172.30.0.10 -p 22,80,8080,9000-9004 -t 2 --all
python3 -m portscanner 172.30.0.10 -p 1-1024 -w 100 --open --json r.json --csv r.csv --log r.log
python3 -m portscanner 172.30.0.10 -p 9001 -t 1 -r 2          # timeout com novas tentativas
python3 -m portscanner 172.30.0.10 -p 10000-10099 -w 1 -v      # sequencial, mostrando o progresso
```

## Melhorias implementadas (seção 7)

1. **Execução concorrente com limite** — `ThreadPoolExecutor` com `--workers` (1 a 1000), limitado
   também ao nº de portas e ao limite de descritores (`RLIMIT_NOFILE`). Ctrl+C cancela as tarefas
   pendentes e mostra o resultado parcial; tentativas já em andamento terminam em até `timeout` s.
2. **Exportação JSON/CSV + medição de desempenho** — duração total, início/fim e tempo de cada
   tentativa (≈ RTT do handshake para portas abertas).
3. **Registro de execução** (`--log`) — parâmetros, cada teste e erros, com data/hora.
4. **Identificação provável de serviço** — `socket.getservbyport()`; é só a convenção IANA para o
   número da porta e **não confirma** o serviço realmente em execução.
5. **Novas tentativas em timeout** (`--retries`) — reduz falsos "timeout" por perda de pacotes;
   recusas e erros não são repetidos porque são respostas explícitas.

## Organização do código

```
portscanner/
  cli.py      recebe e valida parâmetros (argparse), orquestra, códigos de saída
  probe.py    resolve o destino; tenta a conexão e INTERPRETA o resultado
  engine.py   distribui as portas entre threads; trata Ctrl+C
  report.py   tabela, resumo, JSON, CSV
  models.py   Status (enum) e estruturas de resultado
lab/          alvo Docker com portas em estados controlados
scripts/      experimentos (geram evidências) e ferramentas de comparação
docs/         planejamento, relatório e roteiro da demonstração
evidencias/   saídas brutas dos experimentos
```

## Laboratório (VM Kali)

O alvo `172.30.0.10` roda em um container com `NET_ADMIN`; firewall e latência ficam no
namespace de rede do container (não alteram o host).

| Porta | Configuração |
|---|---|
| 22 | nada escutando |
| 80, 8080 | HTTP (`python3 -m http.server`) |
| 9000 | eco TCP (`socat`) — ligado/desligado no experimento de estado |
| 9001 | eco TCP atrás de `DROP` |
| 9002 | `REJECT --reject-with icmp-port-unreachable` |
| 9003 | `REJECT --reject-with icmp-host-unreachable` |
| 9004 | eco TCP atrás de `REJECT --reject-with tcp-reset` |
| 10000–10099 | `DROP` (faixa lenta: Ctrl+C e desempenho) |
| 172.30.0.99 | IP sem host na sub-rede (ARP sem resposta) |

```bash
./scripts/lab.sh up                  # build + sobe o alvo
./scripts/lab.sh status              # serviços, portas em escuta, firewall, latência
./scripts/lab.sh svc stop echo9000   # svc start|stop|restart NOME|all, svc status
./scripts/lab.sh latency on 300      # latency on [ms] | off | show
./scripts/lab.sh firewall show       # firewall apply | clear | show
./scripts/lab.sh down
```

Se o Docker exigir sudo: `DC="sudo docker compose" ./scripts/lab.sh up` (vale para todos os scripts).
Se `iptables` falhar dentro do container, troque `IPTABLES: iptables` por `iptables-legacy` em
`lab/docker-compose.yml`.

### Experimentos (cada um grava em `evidencias/<data-hora>_<nome>/`)

| Script | Seção do roteiro | O que faz |
|---|---|---|
| `./scripts/exp_erros.sh` | 3.3 e 4 | os 7 cenários de erro + erros de comunicação |
| `./scripts/exp_nmap.sh` | 5 | scanner e `nmap -sT -Pn --reason` nas mesmas portas; gera `comparacao.md` |
| `./scripts/exp_state.sh [--container]` | 6 | rodadas A/B/C (e D/E com o container parado); gera `resumo.md` |
| `./scripts/exp_timeout.sh` | 8.3 | latência artificial × timeouts 0.1–2 s × nmap; gera `resumo.md` |
| `./scripts/exp_performance.sh` | 7 | duração com 1/10/50/100 workers; gera `resumo.md` |

Os scripts guardam o comando exato, data/hora, saída e código de saída de cada execução
(`execucao.log`) e o estado do alvo antes do teste (`contexto*.txt`).

## Limitações conhecidas

- *Connect scan* completa o handshake: é mais lento e mais visível (aparece nos logs da aplicação)
  que um SYN scan, que exige raw sockets/privilégios.
- Uma tentativa por porta (salvo `--retries`) e timeout fixo; o Nmap adapta o timeout ao RTT medido
  e retransmite.
- `timeout` não distingue DROP de perda de pacotes ou de host desligado.
- Um firewall pode forjar RST (porta 9004): `recusada` não prova que não há serviço.
- Porta `aberta` só prova que *algo* aceitou o handshake (pode ser um proxy/NAT); não identifica o
  serviço nem indica vulnerabilidade.
- Ctrl+C: tentativas em andamento terminam em até `timeout` s antes de o processo encerrar.
- Somente TCP; sem varredura de UDP.
