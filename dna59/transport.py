#!/usr/bin/env python3
import glob
import os
import time
from dataclasses import dataclass
from typing import Iterable, Optional


A0_READMETA_REQUEST = bytes([0x04, 0xA0, 0x02, 0x00])


@dataclass
class DetectResult:
    path: str
    response: bytes


class HidRawTransport:
    def __init__(self, path: str):
        self.path = path
        self.fd: Optional[int] = None

    def open(self) -> None:
        self.fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def send_packet(self, packet: bytes, timeout: float = 0.25) -> Optional[bytes]:
        if self.fd is None:
            raise RuntimeError("hidraw transport is closed")
        if len(packet) != 64:
            raise ValueError("packet must be exactly 64 bytes")
        os.write(self.fd, packet)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data = os.read(self.fd, 64)
                if data:
                    return data
            except BlockingIOError:
                pass
            time.sleep(0.01)
        return None

    def probe_readmeta(self, timeout: float = 0.25) -> Optional[bytes]:
        pkt = bytearray(64)
        pkt[: len(A0_READMETA_REQUEST)] = A0_READMETA_REQUEST
        return self.send_packet(bytes(pkt), timeout=timeout)


def iter_hidraw_paths() -> list[str]:
    return sorted(glob.glob("/dev/hidraw*"))


def detect_device(
    paths: Optional[Iterable[str]] = None, timeout: float = 0.25
) -> Optional[DetectResult]:
    candidates = list(paths) if paths is not None else iter_hidraw_paths()
    for path in candidates:
        try:
            with HidRawTransport(path) as dev:
                resp = dev.probe_readmeta(timeout=timeout)
                if not resp:
                    continue
                if len(resp) >= 7 and resp[:4] == bytes([0x04, 0xA0, 0x02, 0x00]):
                    return DetectResult(path=path, response=resp)
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return None

