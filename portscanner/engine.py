"""Execução do scan: distribui as portas entre threads, com limite de concorrência.

Com --workers 1 a execução é sequencial (uma porta por vez).
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .models import ProbeResult, Status
from .probe import probe

ResultCallback = Callable[[ProbeResult], None]


def _collect(future: Future, port: int) -> ProbeResult:
    """Extrai o resultado de uma tarefa. Uma exceção inesperada em UMA porta
    vira um resultado de erro, sem derrubar o scan das demais."""
    try:
        return future.result()
    except Exception as exc:  # noqa: BLE001 — proteção contra bugs inesperados
        return ProbeResult(port=port, status=Status.ERROR, detail=f"exceção inesperada: {exc!r}")


def run_scan(
    ip: str,
    family: int,
    ports: Sequence[int],
    timeout: float,
    workers: int,
    retries: int = 0,
    on_result: Optional[ResultCallback] = None,
) -> Tuple[List[ProbeResult], bool]:
    """Testa todas as portas. Retorna (resultados ordenados por porta, interrompido?).

    Ctrl+C (KeyboardInterrupt) cancela as tarefas que ainda não começaram e
    devolve o resultado parcial. Tentativas já em andamento terminam sozinhas
    em no máximo `timeout` segundos (não há como abortar um connect() bloqueante
    de outra thread).
    """
    results: List[ProbeResult] = []
    futures: Dict[Future, int] = {}
    interrupted = False
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="probe")

    try:
        for port in ports:
            futures[executor.submit(probe, ip, port, family, timeout, retries)] = port

        for future in as_completed(futures):
            result = _collect(future, futures[future])
            results.append(result)
            if on_result is not None:
                on_result(result)

    except KeyboardInterrupt:
        interrupted = True
        executor.shutdown(wait=False, cancel_futures=True)
        # Aproveita tarefas que terminaram mas ainda não tinham sido consumidas.
        seen = {r.port for r in results}
        for future, port in futures.items():
            if port not in seen and future.done() and not future.cancelled():
                results.append(_collect(future, port))
    else:
        executor.shutdown(wait=True)

    results.sort(key=lambda r: r.port)
    return results, interrupted
