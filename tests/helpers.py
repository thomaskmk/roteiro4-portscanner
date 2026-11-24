"""Servidores locais para testes: porta aberta, porta fechada e porta "buraco negro"."""

import socket
import threading


class Listener:
    """Socket escutando em 127.0.0.1 numa porta efêmera (porta ABERTA)."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()
        self.sock.settimeout(0.1)
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
                conn.close()
            except OSError:
                continue

    def close(self):
        self._stop.set()
        self.thread.join(1)
        self.sock.close()


class BlackHole:
    """Porta cuja fila de conexões está cheia: o kernel (Linux) descarta novos SYN,
    simulando um firewall com DROP -> o scanner observa TIMEOUT."""

    def __init__(self, fillers: int = 8):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(0)
        self.port = self.sock.getsockname()[1]
        self.fill = []
        for _ in range(fillers):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setblocking(False)
            try:
                client.connect(("127.0.0.1", self.port))
            except BlockingIOError:
                pass
            self.fill.append(client)

    def close(self):
        for client in self.fill:
            client.close()
        self.sock.close()


def free_port() -> int:
    """Porta que estava livre há instantes (provavelmente FECHADA)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
