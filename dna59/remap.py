#!/usr/bin/env python3
import time
from dataclasses import dataclass
from typing import List

from .protocol import build_apply_sequence
from .transport import HidRawTransport


@dataclass
class ApplyResult:
    ok: bool
    missing_echo_packets: List[int]
    mismatch_packet: int | None
    error: str | None


def apply_packet_sequence(
    dev: HidRawTransport,
    sequence: List[bytes],
    verify: bool = True,
) -> ApplyResult:
    missing: List[int] = []
    for idx, packet in enumerate(sequence):
        resp = dev.send_packet(packet)
        if resp is None:
            if verify:
                return ApplyResult(
                    ok=False,
                    missing_echo_packets=missing + [idx],
                    mismatch_packet=None,
                    error=f"sem resposta no pacote #{idx}",
                )
            missing.append(idx)
            time.sleep(0.01)
            continue
        if verify and resp != packet:
            return ApplyResult(
                ok=False,
                missing_echo_packets=missing,
                mismatch_packet=idx,
                error=f"resposta diferente no pacote #{idx}",
            )
        time.sleep(0.01)
    return ApplyResult(
        ok=True,
        missing_echo_packets=missing,
        mismatch_packet=None,
        error=None,
    )


def apply_fn_mapping(
    dev: HidRawTransport,
    left_usage: int,
    right_usage: int,
    verify: bool = True,
) -> ApplyResult:
    sequence = build_apply_sequence(left_usage, right_usage)
    return apply_packet_sequence(dev=dev, sequence=sequence, verify=verify)
