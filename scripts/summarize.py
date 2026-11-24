#!/usr/bin/env python3
"""Resume vários JSONs do portscanner em tabelas Markdown.

    timeline ROTULO=arq.json ...   estado de cada porta ao longo de rodadas (seções 6 e 8.3)
    perf arq.json ...              duração por número de workers (melhoria: concorrência)
"""

import argparse
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def timeline(items):
    runs = []
    for item in items:
        label, _, path = item.rpartition("=")
        runs.append((label or path, load(path)))
    ports = sorted({r["port"] for _, data in runs for r in data["results"]})
    head = "| Rodada | Início | Timeout | " + " | ".join(f"{p}/tcp" for p in ports) + " |"
    lines = [head, "|" + "---|" * (3 + len(ports))]
    for label, data in runs:
        by_port = {r["port"]: r for r in data["results"]}
        cells = []
        for p in ports:
            r = by_port.get(p)
            if r is None:
                cells.append("-")
                continue
            extra = f" {r['errno_name']}" if r.get("errno_name") else ""
            ms = f", {r['elapsed_ms']:.0f}ms" if r.get("elapsed_ms") is not None else ""
            cells.append(f"{r['status']}{extra}{ms}")
        lines.append(f"| {label} | {data['started_at']} | {data['timeout_s']}s | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def perf(paths):
    lines = ["| Portas | Timeout | Workers | Duração (s) | Resumo |", "|---|---|---|---|---|"]
    for path in paths:
        d = load(path)
        summary = ", ".join(f"{n} {k}" for k, n in d["summary"].items() if n)
        lines.append(f"| {d['ports_spec']} | {d['timeout_s']}s | {d['workers']} | {d['duration_s']:.3f} | {summary} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("timeline"); t.add_argument("items", nargs="+"); t.add_argument("-o", "--output")
    p = sub.add_parser("perf"); p.add_argument("files", nargs="+"); p.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    text = (timeline(args.items) if args.cmd == "timeline" else perf(args.files)) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
