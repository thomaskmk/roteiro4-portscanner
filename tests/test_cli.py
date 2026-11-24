import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from portscanner import engine
from portscanner.cli import EXIT_INTERRUPTED, EXIT_OK, EXIT_RUNTIME, EXIT_USAGE, main

from .helpers import Listener, free_port


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse encerra com SystemExit(2)
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_invalid_port(self):
        for spec in ["0", "70000", "abc"]:
            code, _, err = run_main(["127.0.0.1", "-p", spec])
            self.assertEqual(code, EXIT_USAGE, spec)
            self.assertIn("-p/--ports", err)

    def test_invalid_range(self):
        code, _, err = run_main(["127.0.0.1", "-p", "100-20"])
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("invertido", err)

    def test_invalid_timeout(self):
        for value in ["0", "-1", "abc", "nan", "999"]:
            code, _, _ = run_main(["127.0.0.1", "-p", "80", "-t", value])
            self.assertEqual(code, EXIT_USAGE, value)

    def test_invalid_target(self):
        code, _, err = run_main(["naoexiste.invalid", "-p", "80"])
        self.assertEqual(code, EXIT_RUNTIME)
        self.assertIn("não foi possível resolver", err)

    def test_scan_and_export(self):
        listener = Listener()
        closed = free_port()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "r.json")
            csv_path = os.path.join(tmp, "r.csv")
            log_path = os.path.join(tmp, "r.log")
            try:
                code, out, _ = run_main([
                    "127.0.0.1", "-p", f"{listener.port},{closed}", "-t", "1",
                    "--json", json_path, "--csv", csv_path, "--log", log_path,
                ])
            finally:
                listener.close()
            self.assertEqual(code, EXIT_OK)
            data = json.loads(read(json_path))
            states = {r["port"]: r["status"] for r in data["results"]}
            self.assertEqual(states[listener.port], "aberta")
            self.assertEqual(states[closed], "recusada")
            self.assertEqual(data["ports_tested"], 2)
            self.assertGreaterEqual(data["duration_s"], 0)
            self.assertEqual(len(read(csv_path).strip().splitlines()), 3)
            self.assertIn("porta=", read(log_path))
        self.assertIn("aberta", out)

    def test_export_to_invalid_path(self):
        code, _, err = run_main(["127.0.0.1", "-p", str(free_port()), "--json", "/nao/existe/r.json"])
        self.assertEqual(code, EXIT_RUNTIME)
        self.assertIn("não foi possível salvar", err)

    def test_keyboard_interrupt_returns_partial(self):
        real_as_completed = engine.as_completed

        def interrupt_after_first(futures):
            iterator = real_as_completed(futures)
            yield next(iterator)
            raise KeyboardInterrupt

        ports = [free_port() for _ in range(3)]
        with mock.patch.object(engine, "as_completed", interrupt_after_first):
            code, out, _ = run_main(["127.0.0.1", "-p", ",".join(map(str, ports)), "-w", "1"])
        self.assertEqual(code, EXIT_INTERRUPTED)
        self.assertIn("PARCIAL", out)


if __name__ == "__main__":
    unittest.main()
