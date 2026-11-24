"""Apresentação e registro dos resultados: tabela no terminal, resumo, JSON e CSV."""

from __future__ import annotations

import csv
import json
from typing import List, TextIO

from .models import ProbeResult, ScanReport, Status
from .probe import service_hint

# Acima deste número de portas, o modo "auto" esconde as recusadas (como o Nmap faz).
AUTO_SHOW_ALL_LIMIT = 50

CSV_FIELDS = [
    "target", "ip", "port", "status", "nmap_equivalent", "elapsed_ms",
    "attempts", "errno_name", "detail", "service_hint", "timestamp",
]


def add_service_hints(report: ScanReport) -> None:
    """Preenche o nome convencional de cada porta (executado na thread principal,
    porque getservbyport() não é garantidamente thread-safe)."""
    for result in report.results:
        result.service_hint = service_hint(result.port)


def format_header(report: ScanReport) -> str:
    return (
        f"Alvo: {report.target} ({report.ip}, {report.family})  |  "
        f"portas: {report.ports_requested}  |  timeout: {report.timeout_s:g}s  |  "
        f"workers: {report.workers}  |  retries: {report.retries}\n"
        f"Início: {report.started_at}"
    )


def _visible(report: ScanReport, mode: str) -> List[ProbeResult]:
    if mode == "open":
        return [r for r in report.results if r.status is Status.OPEN]
    if mode == "all" or report.ports_requested <= AUTO_SHOW_ALL_LIMIT:
        return list(report.results)
    return [r for r in report.results if r.status is not Status.CLOSED]


def format_table(report: ScanReport, mode: str = "auto") -> str:
    rows = _visible(report, mode)
    headers = ["PORTA", "ESTADO", "≈NMAP", "TEMPO(ms)", "TENT.", "ERRNO", "DETALHE", "SERVIÇO PROVÁVEL*"]
    body = [
        [
            f"{r.port}/tcp",
            r.status.value,
            r.nmap_equivalent,
            "-" if r.elapsed_ms is None else f"{r.elapsed_ms:.2f}",
            str(r.attempts),
            r.errno_name or "-",
            r.detail,
            r.service_hint or "-",
        ]
        for r in rows
    ]
    widths = [max(len(h), *(len(row[i]) for row in body)) if body else len(h) for i, h in enumerate(headers)]
    right_aligned = {3, 4}

    def fmt(cells: List[str]) -> str:
        return "  ".join(
            c.rjust(widths[i]) if i in right_aligned else c.ljust(widths[i]) for i, c in enumerate(cells)
        ).rstrip()

    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    if body:
        lines += [fmt(row) for row in body]
    elif not report.results:
        lines.append("(nenhuma porta chegou a ser testada)")
    else:
        lines.append("(nenhuma porta a exibir com este filtro)")

    hidden = len(report.results) - len(rows)
    if hidden:
        lines.append(f"... {hidden} porta(s) não exibida(s) pelo filtro (use --all para ver todas)")
    lines.append("* nome convencional do número da porta (IANA); NÃO confirma o serviço realmente em execução.")
    return "\n".join(lines)


def format_summary(report: ScanReport) -> str:
    counts = report.summary()
    parts = [f"{n} {label}" for label, n in counts.items() if n]
    text = (
        f"Resumo: {', '.join(parts) or 'nenhum resultado'} — "
        f"{len(report.results)}/{report.ports_requested} portas em {report.duration_s:.3f}s"
    )
    if report.interrupted:
        text += "\nINTERROMPIDO pelo usuário: resultado PARCIAL."
    if counts[Status.LOCAL_ERROR.value]:
        text += ("\nATENÇÃO: houve falhas locais (ex.: descritores esgotados). "
                 "Essas portas não foram realmente testadas; reduza --workers.")
    return text


def print_report(report: ScanReport, mode: str = "auto", out: TextIO = None) -> None:
    import sys

    out = out or sys.stdout
    print(format_table(report, mode), file=out)
    print(file=out)
    print(format_summary(report), file=out)


def export_json(report: ScanReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def export_csv(report: ScanReport, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in report.results:
            row = result.to_dict()
            row.update(target=report.target, ip=report.ip)
            writer.writerow({k: row.get(k) for k in CSV_FIELDS})


def format_live(result: ProbeResult) -> str:
    """Linha curta exibida assim que cada porta termina (modo --verbose)."""
    extra = f" {result.errno_name}" if result.errno_name else ""
    elapsed = "-" if result.elapsed_ms is None else f"{result.elapsed_ms:.1f}ms"
    return f"[{result.timestamp}] {result.port}/tcp {result.status.value}{extra} ({elapsed}, tent={result.attempts})"
