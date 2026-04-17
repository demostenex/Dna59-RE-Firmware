#!/usr/bin/env python3
import unittest

from dna59.protocol import (
    AE_PACKET,
    FN_LEFT_USAGE_OFFSET,
    FN_RIGHT_USAGE_OFFSET,
    build_apply_sequence,
    build_led_guess_sequence,
    build_page_0d,
)


class ProtocolTests(unittest.TestCase):
    def test_build_page_0d_updates_fn_offsets(self):
        page = build_page_0d(0x2E, 0x47)
        self.assertEqual(len(page), 64)
        self.assertEqual(page[14], 0xFC)
        self.assertEqual(page[15], 0x00)
        self.assertEqual(page[FN_LEFT_USAGE_OFFSET], 0x2E)
        self.assertEqual(page[32], 0xFC)
        self.assertEqual(page[33], 0x00)
        self.assertEqual(page[FN_RIGHT_USAGE_OFFSET], 0x47)

    def test_build_apply_sequence_shape(self):
        seq = build_apply_sequence(0x2E, 0x47)
        self.assertEqual(len(seq), 15)  # AE + 14 pages
        self.assertEqual(seq[0], AE_PACKET)
        self.assertTrue(all(len(p) == 64 for p in seq))

    def test_led_guess_sequence_profiles(self):
        safe = build_led_guess_sequence(255, 0, 0, profile="safe")
        aggressive = build_led_guess_sequence(255, 0, 0, profile="aggressive")
        self.assertEqual(len(safe), 1)
        self.assertEqual(len(aggressive), 3)
        self.assertTrue(all(len(p) == 64 for p in safe + aggressive))

    def test_led_rgb_range_validation(self):
        with self.assertRaises(ValueError):
            build_led_guess_sequence(256, 0, 0)


if __name__ == "__main__":
    unittest.main()

