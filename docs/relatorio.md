# Relatório técnico — Roteiro 4: Port Scanner TCP

> **Rascunho.** Os trechos marcados com `TODO(evidência)` só podem ser escritos com as saídas
> reais geradas pelos scripts em `evidencias/`. Nenhum resultado deste relatório deve ser
> preenchido sem a saída correspondente.

## 1. Estratégia de implementação

O `portscanner` implementa um *TCP connect scan* usando apenas a biblioteca padrão. Para cada
porta, um socket TCP é criado, recebe um tempo limite (`settimeout`) e chama `connect()`; o
sistema operacional executa o *three-way handshake* e o desfecho é classificado em cinco estados:
`aberta` (handshake concluído), `recusada` (`ConnectionRefusedError`: RST ou ICMP
port-unreachable), `timeout` (nenhuma resposta: causa indeterminada), `erro` (outro `OSError`,
ex.: `EHOSTUNREACH`) e `erro-local` (falha na própria máquina, ex.: `EMFILE`).

O código separa as responsabilidades pedidas na seção 3.2: `cli.py` (recebe e valida parâmetros),
`probe.py` (resolve o destino, tenta a conexão e interpreta o resultado), `engine.py` (executa
as tentativas com concorrência limitada e trata Ctrl+C) e `report.py` (apresenta e exporta).
Os parâmetros são validados **antes** de qualquer pacote ser enviado e o destino é resolvido uma
única vez. Cada porta é testada de forma independente, e o socket é sempre fechado (`with`).

Melhorias: execução concorrente com limite (`--workers`), exportação JSON/CSV com medição de
tempo, log de execução, dica de serviço (IANA) e novas tentativas em timeout (`--retries`).

Ambiente: código desenvolvido no macOS; todos os experimentos executados na VM Kali, com o
scanner e o `nmap` na **mesma origem** (o host Kali) contra um alvo Docker (`172.30.0.10`) cujas
portas foram configuradas em estados conhecidos (tabela no README).
`TODO(evidência)`: versões (Python, nmap, kernel) — ver `contexto.txt`.

## 2. Fluxograma / pseudocódigo

Ver `docs/planejamento.md` (incluir aqui o fluxograma renderizado e o pseudocódigo resumido).

## 3. Resultados dos testes (seções 3.3 e 4)

`TODO(evidência)`: `evidencias/*_erros/` — tabela com os 7 cenários:

| # | Situação | Comando | Resultado observado | Código de saída |
|---|---|---|---|---|
| 1 | Porta com serviço ativo | `-p 80` | | |
| 2 | Porta sem serviço | `-p 22` | | |
| 3 | Porta inválida | `-p 70000` | | |
| 4 | Intervalo inválido | `-p 100-20` | | |
| 5 | Destino inválido | `naoexiste.invalid` | | |
| 6 | Timeout | `-p 9001 -t 2` | | |
| 7 | Interrupção (Ctrl+C) | `timeout -s INT 3 ...` | | |

Conferência com o sistema operacional: `ss -ltnp` no alvo (`contexto.txt`) — as portas abertas
reportadas coincidem com as portas em escuta? `TODO(evidência)`

## 4. Comparação com o Nmap (seção 5)

`TODO(evidência)`: colar `evidencias/*_nmap/comparacao.md`.

Discussão das divergências: `TODO(evidência)`. Hipóteses a confirmar ou descartar com os dados:
porta 9002 (ICMP port-unreachable — como cada ferramenta classifica?), porta 9003
(ICMP host-unreachable: `erro` × `filtered`), e o efeito do timeout fixo × timeout adaptativo do
Nmap (experimento de latência, `evidencias/*_timeout/resumo.md`).

## 5. Experimento de mudança de estado (seção 6)

`TODO(evidência)`: colar `evidencias/*_estado/resumo.md` (rodadas A, B, C e, se executadas, D e E).

Interpretação esperada a verificar: em B, o processo deixa de escutar mas o host continua ativo,
então a pilha TCP responde RST (`recusada`); a porta 80 (controle) não muda. Se o container
inteiro for parado (D), o IP deixa de existir: não há quem responda ARP e o resultado muda de
natureza (`erro EHOSTUNREACH` ou `timeout`), em vez de `recusada`.

## 6. Análise crítica

**6.1 Uso de sockets.** Cada teste é um `connect()` com tempo limite em um socket TCP novo; o
programa não monta pacotes — interpreta a reação da pilha TCP do destino (e da rede) a um pedido
de conexão comum.

**6.2 Limitações.** Handshake completo (mais lento e mais visível que um SYN scan, que exige raw
sockets); timeout fixo e uma tentativa por padrão; `timeout` não distingue DROP de perda ou de
host desligado; RST pode ser forjado por firewall (porta 9004); `aberta` não identifica o serviço;
Ctrl+C aguarda tentativas em andamento até o timeout; somente TCP.

**6.3 Influência do timeout.** Timeout menor que o RTT transforma portas abertas **e fechadas**
em `timeout` (o SYN/ACK ou o RST chegam depois de o programa desistir); timeout muito maior só
aumenta a duração quando há portas filtradas. `TODO(evidência)`: números do experimento de latência.

**6.4 Diferenças em relação ao Nmap.** `TODO(evidência)`.

**6.5 Mudança de estado.** O resultado é uma observação de um instante a partir de uma origem:
o mesmo alvo produziu estados diferentes conforme o serviço foi parado e reiniciado.
`TODO(evidência)`.

**6.6 Melhorias para confiabilidade e eficiência.** Timeout adaptativo ao RTT medido (como o
Nmap); retransmissão automática de portas filtradas; distinção ICMP × silêncio com raw sockets;
SYN scan (meio handshake) para reduzir carga e ruído nos serviços; controle de taxa
(pacotes/s); *banner grabbing* para passar de "porta aberta" para "serviço provável".

**Porta aberta × serviço × vulnerabilidade.** São etapas distintas: (1) alcançabilidade — algo
aceitou o handshake nesta origem e neste momento; (2) identificação — qual software e versão
(banner, sondas de protocolo; o número da porta é só convenção); (3) vulnerabilidade — exige
confrontar versão e configuração com falhas conhecidas e, idealmente, confirmar. Uma porta aberta,
sozinha, não demonstra vulnerabilidade: pode ser um serviço atualizado e bem configurado.

## 7. Respostas às questões do roteiro

- *Por que um timeout não deve ser interpretado como porta fechada?* Fechada significa que o
  destino respondeu recusando (RST). Timeout significa ausência de resposta, que pode vir de um
  firewall descartando pacotes (a porta 9001 tem um serviço ativo atrás do DROP), perda na rede,
  host desligado ou timeout menor que o RTT. Concluir "fechada" seria afirmar algo que não foi
  observado.
- *Por que o resultado é uma observação em um momento?* Serviços sobem e caem, regras de
  firewall mudam, endereços são reatribuídos e a rede varia; o scan registra a resposta obtida
  de uma origem específica num instante específico (o JSON guarda data/hora de cada porta).
- Demais questões: seções 3 a 6 acima.
