#!/usr/bin/env python3
import unittest

from dna59.remap import apply_fn_mapping, apply_packet_sequence


class FakeDev:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []

    def send_packet(self, packet):
        self.sent.append(packet)
        if not self.responses:
            return None
        return self.responses.pop(0)


class RemapTests(unittest.TestCase):
    def test_apply_packet_sequence_verify_success(self):
        seq = [b"a" * 64, b"b" * 64]
        dev = FakeDev([seq[0], seq[1]])
        result = apply_packet_sequence(dev, seq, verify=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.missing_echo_packets, [])
        self.assertIsNone(result.mismatch_packet)

    def test_apply_packet_sequence_verify_missing_fails(self):
        seq = [b"a" * 64]
        dev = FakeDev([None])
        result = apply_packet_sequence(dev, seq, verify=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.missing_echo_packets, [0])

    def test_apply_packet_sequence_noverify_missing_ok(self):
        seq = [b"a" * 64, b"b" * 64]
        dev = FakeDev([None, seq[1]])
        result = apply_packet_sequence(dev, seq, verify=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.missing_echo_packets, [0])

    def test_apply_fn_mapping_runs_sequence(self):
        # 15 pacotes no fluxo Fn (AE + páginas A0/01..0E)
        dev = FakeDev([None] * 15)
        result = apply_fn_mapping(dev, 0x2E, 0x47, verify=False)
        self.assertTrue(result.ok)
        self.assertEqual(len(dev.sent), 15)


if __name__ == "__main__":
    unittest.main()

