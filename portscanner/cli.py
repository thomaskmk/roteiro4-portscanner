"""Interface de linha de comando: recebe e valida parâmetros e orquestra a execução.

Códigos de saída:
    0   scan concluído
    1   erro de execução (destino não resolvido, falha ao gravar arquivo)
    2   parâmetros inválidos (argparse)
    130 interrompido pelo usuário (Ctrl+C)
"""

from __future__ import annotations

import argparse
import logging
import math
import socket
import sys
import time
from datetime import datetime
from typing import List, Optional, Tuple

from . import __version__
from . import report as rep
from .engine import run_scan
from .models import ProbeResult, ScanReport
from .probe import FAMILY_NAMES, TargetError, resolve

MIN_PORT, MAX_PORT = 1, 65535
MAX_TIMEOUT = 60.0
MAX_WORKERS = 1000
MAX_RETRIES = 5
FD_RESERVE = 64  # descritores reservados para stdout, log, arquivos de exportação etc.

EXIT_OK, EXIT_RUNTIME, EXIT_USAGE, EXIT_INTERRUPTED = 0, 1, 2, 130

log = logging.getLogger("portscanner")


# --------------------------------------------------------------------------- validação

def _to_port(text: str, context: str) -> int:
    text = text.strip()
    if not (text.isascii() and text.isdigit()):
        raise ValueError(f"porta não numérica: '{text}' em '{context}'")
    value = int(text)
    if not MIN_PORT <= value <= MAX_PORT:
        raise ValueError(f"porta fora da faixa {MIN_PORT}-{MAX_PORT}: {value}")
    return value


def parse_ports(spec: str) -> List[int]:
    """Converte '22', '20-25' ou '22,80,8000-8010' em lista ordenada e sem duplicatas."""
    if spec is None or not spec.strip():
        raise ValueError("lista de portas vazia")

    ports = set()
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            raise ValueError(f"item vazio em '{spec}' (vírgula sobrando?)")
        if "-" in item:
            start_text, _, end_text = item.partition("-")
            if not start_text.strip() or not end_text.strip():
                raise ValueError(f"intervalo incompleto: '{item}' (use INICIO-FIM, ex.: 20-25)")
            start, end = _to_port(start_text, item), _to_port(end_text, item)
            if start > end:
                raise ValueError(f"intervalo invertido: '{item}' (início {start} > fim {end})")
            ports.update(range(start, end + 1))
        else:
            ports.add(_to_port(item, item))
    return sorted(ports)


def _ports_type(spec: str) -> List[int]:
    try:
        return parse_ports(spec)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _timeout_type(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"timeout não numérico: '{text}'") from None
    if not math.isfinite(value) or not 0 < value <= MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(f"timeout deve estar em (0, {MAX_TIMEOUT:g}] segundos: '{text}'")
    return value


def _int_range_type(name: str, low: int, high: int):
    def convert(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} não é inteiro: '{text}'") from None
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"{name} deve estar entre {low} e {high}: {value}")
        return value
    return convert


def effective_workers(requested: int, n_ports: int) -> Tuple[int, Optional[str]]:
    """Limita o número de threads ao número de portas e ao limite de descritores do SO.

    Cada tentativa simultânea consome um descritor de arquivo; ultrapassar o
    limite causaria EMFILE (falha local, não do destino).
    """
    workers = min(requested, max(n_ports, 1))
    note = None
    try:
        import resource  # indisponível no Windows

        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft != resource.RLIM_INFINITY and workers > soft - FD_RESERVE:
            workers = max(1, soft - FD_RESERVE)
            note = f"workers reduzido para {workers} (limite de descritores do SO: {soft})"
    except ImportError:
        pass
    return workers, note


# --------------------------------------------------------------------------- argparse

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portscanner",
        description=(
            "Scanner de portas TCP por conexão completa (TCP connect scan), apenas com a "
            "biblioteca padrão do Python. Use somente em sistemas próprios ou autorizados."
        ),
        epilog=(
            "estados: aberta (handshake concluído) | recusada (RST/ICMP port-unreachable) | "
            "timeout (sem resposta: causa indeterminada) | erro (ex.: host inalcançável) | "
            "erro-local (falha na máquina que executa o scan)\n\n"
            "exemplos:\n"
            "  python3 -m portscanner 127.0.0.1 -p 22\n"
            "  python3 -m portscanner 172.30.0.10 -p 22,80,9000-9004 -t 2\n"
            "  python3 -m portscanner localhost -p 1-1024 -w 100 --open --json out.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="endereço IP ou hostname do destino")
    parser.add_argument(
        "-p", "--ports", type=_ports_type, default=parse_ports("1-1024"), metavar="PORTAS",
        help="porta, intervalo ou lista: 80 | 20-25 | 22,80,8000-8010 (padrão: 1-1024)",
    )
    parser.add_argument(
        "-t", "--timeout", type=_timeout_type, default=1.0, metavar="SEG",
        help=f"tempo limite de cada tentativa, em segundos (padrão: 1.0; máx.: {MAX_TIMEOUT:g})",
    )
    parser.add_argument(
        "-w", "--workers", type=_int_range_type("workers", 1, MAX_WORKERS), default=50, metavar="N",
        help=f"tentativas simultâneas; 1 = sequencial (padrão: 50; máx.: {MAX_WORKERS})",
    )
    parser.add_argument(
        "-r", "--retries", type=_int_range_type("retries", 0, MAX_RETRIES), default=0, metavar="N",
        help=f"novas tentativas para portas em timeout (padrão: 0; máx.: {MAX_RETRIES})",
    )

    family = parser.add_mutually_exclusive_group()
    family.add_argument("-4", dest="family", action="store_const", const=socket.AF_INET, help="forçar IPv4")
    family.add_argument("-6", dest="family", action="store_const", const=socket.AF_INET6, help="forçar IPv6")

    show = parser.add_mutually_exclusive_group()
    show.add_argument("--open", dest="show", action="store_const", const="open",
                      help="exibir apenas portas abertas")
    show.add_argument("--all", dest="show", action="store_const", const="all",
                      help=f"exibir todas as portas (por padrão, acima de {rep.AUTO_SHOW_ALL_LIMIT} portas "
                           "as recusadas são omitidas da tabela)")

    parser.add_argument("--json", metavar="ARQ", help="salvar resultados em JSON")
    parser.add_argument("--csv", metavar="ARQ", help="salvar resultados em CSV")
    parser.add_argument("--log", metavar="ARQ", help="registrar a execução (parâmetros, cada teste, erros) em arquivo")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="mostrar cada porta assim que for testada (stderr)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.set_defaults(family=socket.AF_UNSPEC, show="auto")
    return parser


# --------------------------------------------------------------------------- execução

def _setup_logging(path: Optional[str]) -> None:
    log.setLevel(logging.INFO)
    log.propagate = False
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()
    if path:
        handler: logging.Handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    else:
        handler = logging.NullHandler()
    log.addHandler(handler)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _on_result_factory(verbose: bool):
    def on_result(result: ProbeResult) -> None:
        log.info(
            "porta=%d estado=%s tempo_ms=%s tentativas=%d errno=%s detalhe=%s",
            result.port, result.status.value, result.elapsed_ms, result.attempts,
            result.errno_name or "-", result.detail,
        )
        if verbose:
            print(rep.format_live(result), file=sys.stderr, flush=True)
    return on_result


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)  # parâmetros inválidos -> mensagem + SystemExit(2)

    try:
        _setup_logging(args.log)
    except OSError as exc:
        print(f"erro: não foi possível abrir o arquivo de log '{args.log}': {exc.strerror}", file=sys.stderr)
        return EXIT_RUNTIME

    try:
        return _run(args)
    except KeyboardInterrupt:
        # Ctrl+C fora do laço de scan (ex.: durante a resolução de nome).
        print("\ninterrompido pelo usuário.", file=sys.stderr)
        log.warning("interrompido pelo usuário fora do scan")
        return EXIT_INTERRUPTED


def _run(args: argparse.Namespace) -> int:
    ports: List[int] = args.ports
    workers, note = effective_workers(args.workers, len(ports))
    if note:
        print(f"aviso: {note}", file=sys.stderr)

    log.info("início target=%s portas=%d timeout=%s workers=%d retries=%d",
             args.target, len(ports), args.timeout, workers, args.retries)

    try:
        ip, family = resolve(args.target, args.family)
    except TargetError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        log.error("destino inválido: %s", exc)
        return EXIT_RUNTIME

    report = ScanReport(
        target=args.target, ip=ip, family=FAMILY_NAMES.get(family, str(family)),
        ports_spec=_ports_spec(ports), ports_requested=len(ports), timeout_s=args.timeout,
        workers=workers, retries=args.retries, started_at=_now(),
    )
    print(f"portscanner {__version__} — TCP connect scan")
    print(rep.format_header(report))
    print(flush=True)

    t0 = time.perf_counter()
    report.results, report.interrupted = run_scan(
        ip, family, ports, args.timeout, workers, args.retries, _on_result_factory(args.verbose),
    )
    report.duration_s = time.perf_counter() - t0
    report.finished_at = _now()

    rep.add_service_hints(report)
    rep.print_report(report, args.show)
    log.info("fim duracao_s=%.3f interrompido=%s resumo=%s",
             report.duration_s, report.interrupted, report.summary())

    status = EXIT_OK
    for path, exporter, label in ((args.json, rep.export_json, "JSON"), (args.csv, rep.export_csv, "CSV")):
        if not path:
            continue
        try:
            exporter(report, path)
            print(f"{label} salvo em {path}")
        except OSError as exc:
            print(f"erro: não foi possível salvar {label} em '{path}': {exc.strerror}", file=sys.stderr)
            log.error("falha ao salvar %s em %s: %s", label, path, exc)
            status = EXIT_RUNTIME

    if report.interrupted:
        print(f"aguardando tentativas em andamento terminarem (até ~{args.timeout:g}s)...",
              file=sys.stderr, flush=True)
        return EXIT_INTERRUPTED
    return status


def _ports_spec(ports: List[int]) -> str:
    """Compacta a lista de portas de volta em texto: [20,21,22,80] -> '20-22,80'."""
    if not ports:
        return ""
    parts, start, prev = [], ports[0], ports[0]
    for port in ports[1:] + [None]:
        if port is not None and port == prev + 1:
            prev = port
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        if port is not None:
            start = prev = port
    return ",".join(parts)
