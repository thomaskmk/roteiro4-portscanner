import errno
import socket
import sys
import unittest
from unittest import mock

from portscanner import probe as probe_mod
from portscanner.models import Status
from portscanner.probe import TargetError, probe, resolve

from .helpers import BlackHole, Listener, free_port


class RealSocketTest(unittest.TestCase):
    """Testes com conexões reais em 127.0.0.1."""

    def test_open(self):
        listener = Listener()
        try:
            result = probe("127.0.0.1", listener.port, socket.AF_INET, timeout=1)
        finally:
            listener.close()
        self.assertEqual(result.status, Status.OPEN)
        self.assertIsNone(result.errno_name)

    def test_closed(self):
        result = probe("127.0.0.1", free_port(), socket.AF_INET, timeout=1)
        self.assertEqual(result.status, Status.CLOSED)
        self.assertEqual(result.errno_name, "ECONNREFUSED")

    @unittest.skipUnless(sys.platform.startswith("linux"), "comportamento de backlog específico do Linux")
    def test_timeout_and_retries(self):
        hole = BlackHole()
        try:
            result = probe("127.0.0.1", hole.port, socket.AF_INET, timeout=0.3, retries=1)
        finally:
            hole.close()
        self.assertEqual(result.status, Status.TIMEOUT)
        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(result.elapsed_ms, 250)


class ClassificationTest(unittest.TestCase):
    """Simula cada exceção que connect() pode lançar e confere a interpretação."""

    def run_with(self, exc):
        with mock.patch.object(probe_mod.socket, "socket") as fake:
            fake.return_value.__enter__.return_value.connect.side_effect = exc
            return probe("192.0.2.10", 80, socket.AF_INET, timeout=0.1)

    def test_refused(self):
        r = self.run_with(ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused"))
        self.assertEqual(r.status, Status.CLOSED)

    def test_socket_timeout(self):
        r = self.run_with(socket.timeout("timed out"))
        self.assertEqual(r.status, Status.TIMEOUT)

    def test_kernel_etimedout(self):
        r = self.run_with(OSError(errno.ETIMEDOUT, "Connection timed out"))
        self.assertEqual(r.status, Status.TIMEOUT)

    def test_host_unreachable(self):
        r = self.run_with(OSError(errno.EHOSTUNREACH, "No route to host"))
        self.assertEqual(r.status, Status.ERROR)
        self.assertEqual(r.errno_name, "EHOSTUNREACH")

    def test_net_unreachable(self):
        r = self.run_with(OSError(errno.ENETUNREACH, "Network is unreachable"))
        self.assertEqual(r.status, Status.ERROR)

    def test_local_error(self):
        r = self.run_with(OSError(errno.EMFILE, "Too many open files"))
        self.assertEqual(r.status, Status.LOCAL_ERROR)

    def test_retry_only_on_timeout(self):
        with mock.patch.object(probe_mod.socket, "socket") as fake:
            connect = fake.return_value.__enter__.return_value.connect
            connect.side_effect = ConnectionRefusedError(errno.ECONNREFUSED, "refused")
            r = probe("192.0.2.10", 80, socket.AF_INET, timeout=0.1, retries=3)
        self.assertEqual(r.attempts, 1)
        self.assertEqual(connect.call_count, 1)

    def test_socket_closed_on_success(self):
        with mock.patch.object(probe_mod.socket, "socket") as fake:
            probe("192.0.2.10", 80, socket.AF_INET, timeout=0.1)
        fake.return_value.__exit__.assert_called_once()


class ResolveTest(unittest.TestCase):
    def test_ipv4_literal(self):
        self.assertEqual(resolve("127.0.0.1"), ("127.0.0.1", socket.AF_INET))

    def test_localhost_prefers_ipv4(self):
        ip, fam = resolve("localhost")
        self.assertEqual(fam, socket.AF_INET)

    def test_invalid(self):
        for target in ["naoexiste.invalid", "300.1.1.1", "", "a" * 70 + ".com"]:
            with self.subTest(target=target):
                with self.assertRaises(TargetError):
                    resolve(target)


if __name__ == "__main__":
    unittest.main()
