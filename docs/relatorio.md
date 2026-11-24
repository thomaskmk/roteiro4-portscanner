# Relatório técnico — Roteiro 4: Port Scanner TCP

Ambiente dos experimentos (`evidencias/*/contexto*.txt`): VM Kali (Linux 7.2.15 arm64), Python 3.14.8, Nmap 7.991.
Scanner e Nmap executados na **mesma origem** (host Kali) contra o alvo Docker `172.30.0.10`, em
24/11/2026, entre 15:27 e 15:29 (UTC−3). Todas as tabelas abaixo foram geradas a partir das saídas brutas em `evidencias/`.

## 1. Estratégia de implementação

O `portscanner` faz um *TCP connect scan* usando apenas a biblioteca padrão. Para cada porta,
o programa cria um socket TCP, define o tempo limite com `settimeout()` e chama `connect()`. O
sistema operacional executa o *three-way handshake*, e o desfecho é classificado assim:

| Estado | Desfecho de `connect()` | ≈ Nmap |
|---|---|---|
| `aberta` | retornou (SYN → SYN/ACK → ACK) | open |
| `recusada` | `ConnectionRefusedError` (RST, ou ICMP port-unreachable traduzido pelo kernel) | closed |
| `timeout` | `socket.timeout`: nenhuma resposta, causa indeterminada | filtered |
| `erro` | outro `OSError` (`EHOSTUNREACH`, `ENETUNREACH`…) | filtered |
| `erro-local` | `OSError` da própria máquina (`EMFILE`, `EADDRNOTAVAIL`…): a porta não chegou a ser testada | — |

As responsabilidades estão separadas como pede a seção 3.2:

- `cli.py` recebe e valida os parâmetros, antes de qualquer pacote ser enviado.
- `probe.py` resolve o destino uma única vez, tenta a conexão e interpreta o resultado. A ordem dos `except` importa, porque `ConnectionRefusedError` e `TimeoutError` são subclasses de `OSError`. O `with` garante que o socket é fechado.
- `engine.py` executa as tentativas com concorrência limitada e trata o Ctrl+C.
- `report.py` apresenta e exporta os resultados.

Uma falha em uma porta não interrompe as demais.

**Melhorias implementadas (seção 7):** execução concorrente com `--workers`, exportação JSON/CSV
com medição de tempo, log (`--log`), nome provável do serviço e novas tentativas em timeout
(`--retries`). O pseudocódigo e o fluxograma estão em `docs/planejamento.md`.

## 2. Testes iniciais e tratamento de erros (seções 3.3 e 4) — `evidencias/20261124-152701_erros/`

A visão geral do alvo bateu com a configuração do lab (`lab_completo.json`).
As portas abertas que o scanner encontrou (80, 8080 e 9000) são exatamente as que o `ss -ltnp` lista
no alvo como acessíveis. As portas 9001 e 9004 também têm processo escutando, mas o firewall as encobre.

| # | Situação | Comando | Resultado observado | Saída |
|---|---|---|---|---|
| 1 | Serviço ativo | `-p 80` | `aberta`, 0,11 ms | 0 |
| 2 | Sem serviço | `-p 22` | `recusada` (ECONNREFUSED), 0,10 ms | 0 |
| 3 | Porta inválida | `-p 0`, `-p 70000`, `-p abc` | mensagem de uso, nenhum pacote enviado | 2 |
| 4 | Intervalo inválido | `-p 100-20`, `1-70000`, `10-`, `22,,80` | mensagem específica para cada caso | 2 |
| 5 | Destino inválido | `naoexiste.invalid`, `300.1.1.1` | "não foi possível resolver… Name or service not known" | 1 |
| 6 | Timeout | `-p 9001 -t 2` / `-t 1 -r 2` | `timeout` em 2002 ms / 3 tentativas, 3,006 s no total | 0 |
| 7 | Ctrl+C (SIGINT após 3 s) | `-p 10000-10099 -w 1 -t 1` | resultado parcial (2/100 portas), JSON gravado, sem traceback | ver nota |
| + | ICMP host-unreachable | `-p 9003` | `erro` EHOSTUNREACH, 0,05 ms | 0 |
| + | IP sem host na sub-rede | `172.30.0.99 -t 5` | `erro` EHOSTUNREACH depois de 3075 ms (ARP sem resposta) | 0 |

**Nota sobre o caso 7.** O código de saída registrado foi 124, que é o código do próprio `timeout`
do coreutils, e não o do scanner. O script foi corrigido para usar `--preserve-status`, e é preciso
reexecutá-lo para registrar o código 130 do scanner. O arquivo `unittest.log` nessa pasta é de
uma versão anterior do repositório, que tinha testes automatizados, removidos depois.

## 3. Comparação com o Nmap (seção 5) — `evidencias/20261124-152717_nmap/`

Os dois rodaram em seguida, a partir da mesma origem: `nmap -sT -Pn --reason -p 22,80,8080,9000-9004 172.30.0.10`.

| Porta TCP | Estado esperado (configuração) | Scanner desenvolvido | Nmap (motivo) |
|---|---|---|---|
| 22 | sem serviço | recusada (ECONNREFUSED) | closed (conn-refused) |
| 80 | HTTP ativo | aberta | open (syn-ack) |
| 8080 | HTTP ativo | aberta | open (syn-ack) |
| 9000 | eco TCP ativo | aberta | open (syn-ack) |
| 9001 | serviço atrás de DROP | timeout | filtered (no-response) |
| 9002 | REJECT icmp-port-unreachable | recusada (ECONNREFUSED) | closed (conn-refused) |
| 9003 | REJECT icmp-host-unreachable | erro (EHOSTUNREACH) | filtered (host-unreach) |
| 9004 | serviço atrás de REJECT tcp-reset | recusada (ECONNREFUSED) | closed (conn-refused) |

Nesta rede local, sem perdas, **os estados coincidiram nas 8 portas**. Ainda assim, quatro observações:

1. **Porta 9002.** Minha hipótese de planejamento era que o Nmap divergiria aqui, e ela estava errada.
   No connect scan, as duas ferramentas só enxergam o `errno` que o kernel devolve, e o kernel converte
   o ICMP port-unreachable no mesmo ECONNREFUSED de um RST. A técnica não distingue "nada escutando"
   de "firewall rejeitando com ICMP". Segundo a documentação do Nmap, o SYN scan (`-sS`, com raw sockets)
   marcaria essa porta como *filtered*. Isso não foi testado aqui.
2. **Porta 9004.** As duas ferramentas dizem "fechada", mas existe um serviço ativo atrás do firewall.
   Um RST forjado é indistinguível de um RST legítimo nessa camada.
3. **Duração.** O scanner levou 2,0 s (limitado pelo timeout da 9001); o Nmap levou 3,73 s.
4. **Nome do serviço.** Mesmo número de porta, nomes diferentes: o scanner diz `http-alt` para 8080
   e nada para 9000 (tabela `/etc/services`); o Nmap diz `http-proxy` e `cslistener` (tabela `nmap-services`).
   Os serviços reais são `python3 http.server` e `socat`. O nome é só uma convenção de tabela.

**Divergências apareceram quando as condições mudaram:**

- **Latência de 300 ms** (`evidencias/20261124-152747_timeout/`). O scanner com `-t 0.1` reportou as
  três portas como `timeout`. O Nmap padrão acertou as três (closed/open, com latência estimada de 0,30 s),
  porque ajusta o timeout ao RTT e retransmite. Com o Nmap forçado a `--max-rtt-timeout 100ms --max-retries 0`,
  ele também reportou as três como `filtered`. Os resultados voltam a concordar, o que mostra que a
  divergência vinha da configuração de tempo, e não da técnica.
- **Container parado** (rodada D, seção 4). O scanner (`-t 5`) reportou `erro EHOSTUNREACH` depois de
  3078 ms; o Nmap reportou `filtered (no-response)`. *Hipótese, não verificada:* o Nmap desistiu de
  cada tentativa antes dos cerca de 3 s em que o kernel desiste da resolução ARP e devolve EHOSTUNREACH.
  O scanner esperou o suficiente para ver o erro. Para verificar, basta repetir o Nmap com
  `--initial-rtt-timeout 4s --max-rtt-timeout 5s` e o scanner com `-t 2`.

## 4. Experimento de mudança de estado (seção 6) — `evidencias/20261124-152723_estado/`

A porta 80 serviu de controle. Tempos abaixo de 1 ms aparecem como 0 ms.

| Rodada | Ação | 80/tcp | 9000/tcp | Nmap 9000 |
|---|---|---|---|---|
| A (15:27:23) | serviço ativo | aberta | aberta | open (syn-ack) |
| B (15:27:26) | `svc.sh stop echo9000` | aberta | **recusada** ECONNREFUSED | closed (conn-refused) |
| C (15:27:29) | `svc.sh start echo9000` | aberta | aberta | open (syn-ack) |
| D (15:27:32) | container parado | **erro** EHOSTUNREACH, 3078 ms | **erro** EHOSTUNREACH, 3078 ms | filtered (no-response) |
| E (15:27:44) | container reiniciado | aberta | aberta | open (syn-ack) |

- **B.** O host continuou ativo, mas nenhum processo escutava a 9000. A pilha TCP do alvo respondeu
  RST e a porta passou a `recusada`. O controle (80) não mudou, o que isola o efeito no serviço parado.
- **C.** O estado voltou ao original.
- **D e E.** Com o container parado, o IP deixou de existir. Ninguém respondeu ao ARP e o resultado
  mudou de natureza, de "porta recusada" para "destino inalcançável", afetando também a porta de controle.
  Em D, o Nmap continuou dizendo "Host is up, received user-set": com `-Pn`, essa linha é uma premissa
  do usuário, não uma observação.

Em cerca de 20 s, o mesmo alvo produziu três respostas diferentes para a mesma porta. Por isso o
JSON registra a data e hora de cada teste.

## 5. Melhoria: concorrência e medição de desempenho — `evidencias/20261124-152754_desempenho/`

| Faixa | Comportamento | 1 worker | 10 | 50 | 100 |
|---|---|---|---|---|---|
| 10000-10099 (DROP, `-t 0.5`) | cada porta espera o timeout | 50,14 s | 5,01 s | 1,01 s | 0,52 s |
| 20000-20999 (RST imediato) | resposta em µs | 0,024 s | 0,023 s | 0,039 s | 0,032 s |

Com portas silenciosas, a duração seguiu ⌈portas/workers⌉ × timeout: 100 workers foram cerca de
97 vezes mais rápidos que 1. Com portas que respondem na hora, a concorrência não trouxe ganho: o
custo é de CPU e de criação de threads, não de espera. A concorrência só compensa quando a espera
pela rede domina o tempo total.

## 6. Análise crítica

1. **Uso de sockets.** O programa não monta pacotes. Cada teste é um `connect()` em um socket TCP novo,
   com tempo limite, e o programa interpreta a reação da pilha TCP do destino (e da rede) traduzida
   em exceções e `errno` pelo kernel da origem.
2. **Limitações observadas:**
   - O connect scan não distingue RST de ICMP port-unreachable (porta 9002).
   - Não detecta RST forjado (porta 9004).
   - O timeout é fixo, então, com latência, portas abertas e fechadas viram `timeout`.
   - O handshake completo é mais visível nos logs do alvo do que um SYN scan.
   - No Ctrl+C, o programa espera as tentativas em andamento terminarem (até o timeout).
   - Só testa TCP.
3. **Influência do timeout.** Com RTT de cerca de 300 ms, os timeouts de 0,1 e 0,25 s classificaram
   tudo como `timeout`; de 0,5 s em diante, todos os estados estavam corretos. O timeout também define
   o que é observável: com 5 s apareceu o EHOSTUNREACH do ARP (cerca de 3 s); com menos de 3 s,
   o mesmo destino seria classificado como `timeout`, mas isso é inferência e não foi medido.
4. **Diferenças em relação ao Nmap.** Nenhuma em condições normais. Apareceram divergências com
   latência alta e com o host ausente, e as duas se explicam pela estratégia de tempo (RTT adaptativo
   e retransmissões no Nmap, espera única e fixa no scanner).
5. **Mudança de estado.** O scanner acompanhou corretamente cada transição (seção 4).
6. **Melhorias para confiabilidade e eficiência:**
   - Timeout adaptativo calculado a partir do RTT das primeiras respostas.
   - Retransmissão automática só das portas em `timeout`.
   - SYN scan com raw sockets, para distinguir ICMP de RST e reduzir o ruído no alvo.
   - Controle de taxa de envio.
   - *Banner grabbing*, para passar de "porta aberta" a "serviço provável".

**Porta aberta, serviço e vulnerabilidade são etapas distintas.** Este trabalho só atinge a primeira:
uma porta aberta significa que algo aceitou o handshake, a partir desta origem, neste momento. A segunda
etapa (identificar o serviço) exige falar o protocolo; a seção 3 mostrou duas tabelas dando nomes
diferentes para a mesma porta. A terceira (vulnerabilidade) exige confrontar versão e configuração com
falhas conhecidas e confirmar. As portas 80 e 8080 abertas não indicam vulnerabilidade nenhuma por si só.

**Por que timeout ≠ porta fechada.** A porta 9001 tem um serviço ativo e deu `timeout`. Com latência,
as portas 80 e 8080, abertas, também deram `timeout`. Classificar silêncio como "fechada" teria sido
errado nos dois casos.
