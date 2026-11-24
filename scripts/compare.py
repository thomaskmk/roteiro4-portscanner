#!/usr/bin/env python3
"""Gera a tabela comparativa (seção 5) entre o JSON do portscanner e o XML do nmap (-oX/-oA).

Uso:
    python3 scripts/compare.py scanner.json nmap.xml [--expected lab/expected.json] [-o saida.md]

A comparação é feita FORA do scanner: o scanner nunca executa o nmap.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET


def parse_port_list(text):
    ports = set()
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            a, b = item.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(item))
    return ports


def load_nmap(path):
    """Retorna {porta: (estado, motivo)} e metadados. Trata portas agrupadas em <extraports>."""
    root = ET.parse(path).getroot()
    meta = {"args": root.get("args", ""), "version": root.get("version", ""),
            "start": root.get("startstr", "")}
    host = root.find("host")
    states, extras = {}, []
    if host is None:
        return states, extras, meta
    ports_el = host.find("ports")
    if ports_el is None:
        return states, extras, meta
    for port in ports_el.findall("port"):
        if port.get("protocol") != "tcp":
            continue
        st = port.find("state")
        states[int(port.get("portid"))] = (st.get("state"), st.get("reason", ""))
    for extra in ports_el.findall("extraports"):
        state = extra.get("state")
        listed = False
        for reason in extra.findall("extrareasons"):
            if reason.get("ports"):  # nmap >= 7.9x informa as portas agrupadas
                for p in parse_port_list(reason.get("ports")):
                    states.setdefault(p, (state, reason.get("reason", "")))
                listed = True
        if not listed:
            extras.append(state)
    return states, extras, meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scanner_json")
    parser.add_argument("nmap_xml")
    parser.add_argument("--expected", help="JSON {porta: estado esperado} (ex.: lab/expected.json)")
    parser.add_argument("-o", "--output", help="arquivo Markdown de saída (padrão: stdout)")
    args = parser.parse_args(argv)

    with open(args.scanner_json, encoding="utf-8") as fh:
        scan = json.load(fh)
    nmap_states, nmap_extras, nmap_meta = load_nmap(args.nmap_xml)
    expected = {}
    if args.expected:
        with open(args.expected, encoding="utf-8") as fh:
            expected = {int(k): v for k, v in json.load(fh).items() if not k.startswith("_")}

    lines = [
        "# Comparação: portscanner × nmap -sT",
        "",
        f"- Alvo: `{scan['target']}` ({scan['ip']})",
        f"- portscanner {scan['version']}: início {scan['started_at']}, timeout {scan['timeout_s']}s, "
        f"workers {scan['workers']}, retries {scan['retries']}, duração {scan['duration_s']}s",
        f"- nmap {nmap_meta['version']}: início {nmap_meta['start']} — `{nmap_meta['args']}`",
        "",
        "| Porta TCP | Estado esperado (configuração) | Scanner desenvolvido | Nmap (motivo) | Concordam? |",
        "|---|---|---|---|---|",
    ]
    divergences = 0
    for result in sorted(scan["results"], key=lambda r: r["port"]):
        port = result["port"]
        ours = result["status"] + (f" ({result['errno_name']})" if result.get("errno_name") else "")
        if port in nmap_states:
            n_state, n_reason = nmap_states[port]
        elif len(nmap_extras) == 1:
            n_state, n_reason = nmap_extras[0], "agrupada (extraports)"
        else:
            n_state, n_reason = "não listada", ""
        agree = result["nmap_equivalent"] == n_state
        divergences += not agree
        nmap_cell = f"{n_state} ({n_reason})" if n_reason else n_state
        lines.append(
            f"| {port} | {expected.get(port, '-')} | {ours} | {nmap_cell} | {'sim' if agree else '**NÃO**'} |"
        )

    lines += [
        "",
        f"Divergências: **{divergences}** de {len(scan['results'])} portas.",
        "",
        "Equivalência usada: aberta→open, recusada→closed, timeout→filtered, erro→filtered. "
        "É uma aproximação; as divergências devem ser explicadas, não escondidas.",
    ]
    text = "\n".join(lines) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
