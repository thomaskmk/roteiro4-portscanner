"""Estruturas de dados compartilhadas: estados possíveis e resultados."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import List, Optional


class Status(str, Enum):
    """Resultado de uma tentativa de conexão TCP a uma porta.

    O valor (string) é o rótulo exibido ao usuário e gravado no JSON/CSV.
    """

    OPEN = "aberta"            # connect() concluiu o handshake (SYN -> SYN/ACK -> ACK)
    CLOSED = "recusada"        # o destino respondeu recusando (RST, ou ICMP port-unreachable convertido pelo kernel)
    TIMEOUT = "timeout"        # nenhuma resposta dentro do tempo limite: causa indeterminada
    ERROR = "erro"             # outra condição de rede (ex.: EHOSTUNREACH, ENETUNREACH)
    LOCAL_ERROR = "erro-local" # falha na NOSSA máquina (ex.: EMFILE), não diz nada sobre o destino


# Equivalência APROXIMADA com o vocabulário do Nmap, usada só para facilitar a comparação.
# "erro" vira "filtered" porque o Nmap classifica respostas ICMP de inalcançabilidade como filtradas.
NMAP_EQUIVALENT = {
    Status.OPEN: "open",
    Status.CLOSED: "closed",
    Status.TIMEOUT: "filtered",
    Status.ERROR: "filtered",
    Status.LOCAL_ERROR: "?",
}


@dataclass
class ProbeResult:
    """Resultado do teste de uma única porta."""

    port: int
    status: Status
    elapsed_ms: Optional[float] = None   # tempo da última tentativa (para OPEN, ~ tempo do handshake)
    errno_name: Optional[str] = None     # ex.: "ECONNREFUSED", "EHOSTUNREACH"
    detail: str = ""
    attempts: int = 1
    timestamp: str = ""                  # ISO 8601 do fim do teste desta porta
    service_hint: Optional[str] = None   # nome convencional da porta (NÃO confirma o serviço)

    @property
    def nmap_equivalent(self) -> str:
        return NMAP_EQUIVALENT[self.status]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["nmap_equivalent"] = self.nmap_equivalent
        return data


@dataclass
class ScanReport:
    """Resultado completo de uma execução do scanner, com os parâmetros usados."""

    target: str
    ip: str
    family: str
    ports_spec: str
    ports_requested: int
    timeout_s: float
    workers: int
    retries: int
    started_at: str
    finished_at: str = ""
    duration_s: float = 0.0
    interrupted: bool = False
    results: List[ProbeResult] = field(default_factory=list)

    def summary(self) -> dict:
        counts = {status.value: 0 for status in Status}
        for result in self.results:
            counts[result.status.value] += 1
        return counts

    def to_dict(self) -> dict:
        from . import __version__

        return {
            "scanner": "portscanner",
            "version": __version__,
            "target": self.target,
            "ip": self.ip,
            "family": self.family,
            "ports_spec": self.ports_spec,
            "ports_requested": self.ports_requested,
            "ports_tested": len(self.results),
            "timeout_s": self.timeout_s,
            "workers": self.workers,
            "retries": self.retries,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.duration_s, 4),
            "interrupted": self.interrupted,
            "summary": self.summary(),
            "results": [r.to_dict() for r in self.results],
        }
