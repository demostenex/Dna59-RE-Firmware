#!/usr/bin/env python3
import unittest

from dna59.cli import parse_usage


class CliTests(unittest.TestCase):
    def test_parse_usage_hex_and_decimal(self):
        self.assertEqual(parse_usage("0x2e"), 0x2E)
        self.assertEqual(parse_usage("71"), 71)

    def test_parse_usage_invalid_range(self):
        with self.assertRaises(Exception):
            parse_usage("0x100")


if __name__ == "__main__":
    unittest.main()

