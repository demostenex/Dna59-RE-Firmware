#!/usr/bin/env python3
from typing import Dict, List, Tuple


def _norm64(pkt: bytes) -> bytes:
    if len(pkt) == 64:
        return pkt
    out = bytearray(64)
    out[: min(len(pkt), 64)] = pkt[:64]
    return bytes(out)


AE_PACKET = bytes.fromhex(
    "04ae010000030204000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

BASE_PAGES: Dict[int, bytes] = {
    0x01: bytes.fromhex(
        "04a00204010ea500000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000a50000"
    ),
    0x02: bytes.fromhex(
        "04a00204020ea500000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000a50000"
    ),
    0x03: bytes.fromhex(
        "04a00204030ea500000000000000000000000000000000000015000000000016"
        "00000000001700000000001800000000001900000000001a0000000000a50000"
    ),
    0x04: bytes.fromhex(
        "04a00204040ea51b00000000001c00000000001d00000000001e00000000001f"
        "0000000000200000000000000000000000000000000000000000000000a50000"
    ),
    0x05: bytes.fromhex(
        "04a00204050ea500000000000000000000000000000000000000000000000000"
        "00000000000000000000002a00000000002b00000000002c0000000000a50000"
    ),
    0x06: bytes.fromhex(
        "04a00204060ea52d00000000002e00000000002f000000000030000000000031"
        "0000000000320000000000330000000000340000000000350000000000a50000"
    ),
    0x07: bytes.fromhex(
        "04a00204070ea500000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000a50000"
    ),
    0x08: bytes.fromhex(
        "04a00204080ea53f000000000040000000000041000000000042000000000043"
        "0000000000440000000000450000000000460000000000470000000000a50000"
    ),
    0x09: bytes.fromhex(
        "04a00204090ea54800000000004900000000004a000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000a50000"
    ),
    0x0A: bytes.fromhex(
        "04a002040a0ea500000000000000000000000000000000000054000000000055"
        "0000000000560000000000570000000000580000000000590000000000a50000"
    ),
    0x0B: bytes.fromhex(
        "04a002040b0ea55a00000000005b00000000005c00000000005d00000000005e"
        "00000000005f0000000000000000000000000000000000000000000000a50000"
    ),
    0x0C: bytes.fromhex(
        "04a002040c0ea500000000000000000000000000000000000000000000000000"
        "00000000000000000000006900000000006a00000000006b0000000000a50000"
    ),
    0x0D: bytes.fromhex(
        "04a002040d0ea56c00000000006dfc003d00000000000000006f000000000070"
        "fc00410000710000000000720000000000730000000000740000000000a50000"
    ),
    0x0E: bytes.fromhex(
        "04a002040e0ea500000000000000000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000a50000"
    ),
}

AE_PACKET = _norm64(AE_PACKET)
BASE_PAGES = {k: _norm64(v) for k, v in BASE_PAGES.items()}

FN_LEFT_INDEX = 0x6D
FN_RIGHT_INDEX = 0x70
FN_LEFT_USAGE_OFFSET = 16
FN_RIGHT_USAGE_OFFSET = 34

PRESETS = {
    "linux-br-workaround": (0x2E, 0x47),  # '=' and ScrollLock
    "f4-f8": (0x3D, 0x41),
}


def build_page_0d(left_usage: int, right_usage: int) -> bytes:
    pkt = bytearray(BASE_PAGES[0x0D])
    pkt[14] = 0xFC
    pkt[15] = 0x00
    pkt[FN_LEFT_USAGE_OFFSET] = left_usage & 0xFF
    pkt[17] = 0x00

    pkt[32] = 0xFC
    pkt[33] = 0x00
    pkt[FN_RIGHT_USAGE_OFFSET] = right_usage & 0xFF
    pkt[35] = 0x00
    return bytes(pkt)


def build_pages(left_usage: int, right_usage: int) -> Dict[int, bytes]:
    pages = dict(BASE_PAGES)
    pages[0x0D] = build_page_0d(left_usage, right_usage)
    return pages


def build_apply_sequence(left_usage: int, right_usage: int) -> List[bytes]:
    pages = build_pages(left_usage, right_usage)
    return [AE_PACKET] + [pages[i] for i in range(1, 0x0F)]


def extract_fn_from_page_0d(page_0d: bytes) -> Tuple[int, int]:
    if len(page_0d) != 64:
        raise ValueError("page 0d packet must have 64 bytes")
    return page_0d[FN_LEFT_USAGE_OFFSET], page_0d[FN_RIGHT_USAGE_OFFSET]


def build_static_color_packet(_r: int, _g: int, _b: int) -> bytes:
    # Palpite conservador de payload A9 (não confirmado por captura).
    return build_led_guess_sequence(_r, _g, _b, profile="safe")[0]


def _clamp_rgb(r: int, g: int, b: int) -> Tuple[int, int, int]:
    for v in (r, g, b):
        if not (0 <= v <= 255):
            raise ValueError("RGB deve estar entre 0 e 255")
    return r, g, b


def _pkt(header: bytes, body: bytes = b"") -> bytes:
    pkt = bytearray(64)
    raw = header + body
    pkt[: min(len(raw), 64)] = raw[:64]
    return bytes(pkt)


def build_led_guess_sequence(r: int, g: int, b: int, profile: str = "safe") -> List[bytes]:
    """
    Gera sequência A9 de tentativa para LED sem captura oficial.
    profile=safe: 1 payload conservador
    profile=aggressive: 3 variações comuns observadas em teclados OEM similares
    """
    r, g, b = _clamp_rgb(r, g, b)

    # Formato 1: report 0x04, cmd 0xA9, subcmd 0x01, modo estático, RGB.
    p1 = _pkt(bytes([0x04, 0xA9, 0x01, 0x01, r, g, b]))
    # Formato 2: subcmd alternativo com sentinel A5 no final útil.
    p2 = _pkt(bytes([0x04, 0xA9, 0x02, 0x01, r, g, b, 0xA5, 0x00]))
    # Formato 3: header expandido (índice de perfil 0x00, brilho 0xFF).
    p3 = _pkt(bytes([0x04, 0xA9, 0x03, 0x00, 0x01, r, g, b, 0xFF]))

    if profile == "safe":
        return [p1]
    if profile == "aggressive":
        return [p1, p2, p3]
    raise ValueError("profile invalido para LED (use: safe/aggressive)")
