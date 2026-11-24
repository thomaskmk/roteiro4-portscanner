import unittest

from portscanner.cli import _ports_spec, parse_ports


class ParsePortsTest(unittest.TestCase):
    def test_single(self):
        self.assertEqual(parse_ports("80"), [80])

    def test_range(self):
        self.assertEqual(parse_ports("20-25"), [20, 21, 22, 23, 24, 25])

    def test_list_mixed_dedupe_sorted(self):
        self.assertEqual(parse_ports("80,22,20-23,80"), [20, 21, 22, 23, 80])

    def test_spaces(self):
        self.assertEqual(parse_ports(" 22 , 80 , 9000 - 9001 "), [22, 80, 9000, 9001])

    def test_limits(self):
        self.assertEqual(parse_ports("1,65535"), [1, 65535])

    def test_invalid(self):
        invalid = ["0", "65536", "70000", "abc", "-5", "10-", "100-20", "1-70000",
                   "22,,80", "", "  ", "1-2-3", "²", "8o", "80,"]
        for spec in invalid:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    parse_ports(spec)

    def test_spec_roundtrip(self):
        self.assertEqual(_ports_spec([20, 21, 22, 80, 443, 444]), "20-22,80,443-444")
        self.assertEqual(_ports_spec(parse_ports("9000-9004,22")), "22,9000-9004")


if __name__ == "__main__":
    unittest.main()
