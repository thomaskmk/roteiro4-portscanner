"""Resolução do destino e tentativa de conexão TCP a uma porta.

Este módulo é o núcleo do scanner: abre um socket TCP, chama connect() com
tempo limite e INTERPRETA o que aconteceu (sucesso, recusa, timeout ou erro).
"""

from __future__ import annotations

import errno
import socket
import time
from datetime import datetime
from typing import Optional, Tuple

from .models import ProbeResult, Status

# errnos que indicam problema na máquina que executa o scanner, e não no destino.
# Ex.: EMFILE = acabaram os descritores de arquivo (workers demais);
#      EADDRNOTAVAIL = acabaram as portas efêmeras locais;
#      EPERM/EACCES = firewall LOCAL bloqueou a saída.
LOCAL_ERRNOS = {
    getattr(errno, name)
    for name in ("EMFILE", "ENFILE", "ENOBUFS", "EADDRNOTAVAIL", "EADDRINUSE", "EPERM", "EACCES")
    if hasattr(errno, name)
}

FAMILY_NAMES = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}


class TargetError(Exception):
    """Destino inválido ou impossível de resolver."""


def resolve(target: str, family: int = socket.AF_UNSPEC) -> Tuple[str, int]:
    """Converte IP/hostname em (endereço IP, família). Executada UMA vez, antes do scan.

    Com family=AF_UNSPEC, prefere IPv4 quando o nome tiver os dois tipos de endereço.
    """
    target = target.strip()
    if target.startswith("[") and target.endswith("]"):  # aceita [::1]
        target = target[1:-1]
    if not target:
        raise TargetError("destino vazio")

    try:
        infos = socket.getaddrinfo(target, None, family, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise TargetError(f"não foi possível resolver '{target}': {exc.strerror}") from exc
    except UnicodeError as exc:  # ex.: rótulo de hostname com mais de 63 caracteres
        raise TargetError(f"hostname inválido '{target}': {exc}") from exc

    if not infos:
        raise TargetError(f"nenhum endereço encontrado para '{target}'")

    chosen = infos[0]
    if family == socket.AF_UNSPEC:
        ipv4 = [info for info in infos if info[0] == socket.AF_INET]
        if ipv4:
            chosen = ipv4[0]

    fam, _type, _proto, _canon, sockaddr = chosen
    return sockaddr[0], fam


def _errno_name(exc: OSError) -> Optional[str]:
    if exc.errno is None:
        return None
    return errno.errorcode.get(exc.errno, str(exc.errno))


def _attempt(ip: str, port: int, family: int, timeout: float) -> Tuple[Status, float, Optional[str], str]:
    """Uma única tentativa de conexão. Retorna (estado, tempo_ms, errno, detalhe).

    A ORDEM dos except importa: ConnectionRefusedError e TimeoutError são
    subclasses de OSError, então precisam ser testadas antes dele.
    """
    start = time.perf_counter()

    def elapsed() -> float:
        return (time.perf_counter() - start) * 1000.0

    try:
        # O "with" garante que o socket é fechado (e o descritor liberado) em qualquer caso.
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            # settimeout() coloca o socket em modo com tempo limite: connect() lança
            # socket.timeout se o handshake não terminar dentro de `timeout` segundos.
            sock.settimeout(timeout)
            # connect() faz o SO enviar SYN e esperar SYN/ACK; se vier, responde ACK.
            sock.connect((ip, port))
            return Status.OPEN, elapsed(), None, "handshake TCP concluído"

    except ConnectionRefusedError as exc:
        # O destino respondeu: RST (nada escutando) ou ICMP port-unreachable.
        return Status.CLOSED, elapsed(), _errno_name(exc) or "ECONNREFUSED", \
            "recusada pelo destino (RST ou ICMP port-unreachable)"

    except (socket.timeout, TimeoutError) as exc:
        # Silêncio: pode ser firewall descartando (DROP), perda de pacotes,
        # host desligado ou timeout curto demais. NÃO é o mesmo que "fechada".
        return Status.TIMEOUT, elapsed(), _errno_name(exc), \
            f"sem resposta em {timeout:g}s (causa indeterminada)"

    except OSError as exc:
        status = Status.LOCAL_ERROR if exc.errno in LOCAL_ERRNOS else Status.ERROR
        message = exc.strerror or str(exc)
        if status is Status.LOCAL_ERROR:
            message = f"falha local: {message}"
        return status, elapsed(), _errno_name(exc), message


def probe(ip: str, port: int, family: int, timeout: float, retries: int = 0) -> ProbeResult:
    """Testa uma porta. Repete a tentativa (até `retries` vezes) apenas em caso de TIMEOUT.

    Recusa e erros são respostas explícitas do destino/rede, então repetir não
    mudaria o diagnóstico; o silêncio, por outro lado, pode ser perda de pacote.
    """
    attempts = 0
    while True:
        attempts += 1
        status, elapsed_ms, errno_name, detail = _attempt(ip, port, family, timeout)
        if status is not Status.TIMEOUT or attempts > retries:
            break

    return ProbeResult(
        port=port,
        status=status,
        elapsed_ms=round(elapsed_ms, 3),
        errno_name=errno_name,
        detail=detail,
        attempts=attempts,
        timestamp=datetime.now().astimezone().isoformat(timespec="milliseconds"),
    )


def service_hint(port: int) -> Optional[str]:
    """Nome convencional da porta segundo a base local de serviços (/etc/services).

    É apenas uma convenção (IANA): NÃO confirma qual serviço está realmente escutando.
    """
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return None
