#!/usr/bin/env python3
import argparse
import os
import sys
import time


# Pacotes observados no fluxo real do app oficial (ciclo de save/apply).
AE_PACKET = bytes.fromhex(
    "04ae010000030204000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

BASE_PAGES = {
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


def open_dev(path: str) -> int:
    return os.open(path, os.O_RDWR | os.O_NONBLOCK)


def write_and_read(fd: int, packet: bytes, timeout: float = 0.25):
    os.write(fd, packet)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = os.read(fd, 64)
            if data:
                return data
        except BlockingIOError:
            pass
        time.sleep(0.01)
    return None


def build_page_0d(left_usage: int, right_usage: int) -> bytes:
    pkt = bytearray(BASE_PAGES[0x0D])
    # Entrada 0x6D (Fn esquerda): marcador FC 00 + usage.
    pkt[14] = 0xFC
    pkt[15] = 0x00
    pkt[16] = left_usage & 0xFF
    pkt[17] = 0x00
    # Entrada 0x70 (Fn direita): marcador FC 00 + usage.
    pkt[32] = 0xFC
    pkt[33] = 0x00
    pkt[34] = right_usage & 0xFF
    pkt[35] = 0x00
    return bytes(pkt)


def apply_mapping(fd: int, left_usage: int, right_usage: int, verify: bool) -> int:
    pages = dict(BASE_PAGES)
    pages[0x0D] = build_page_0d(left_usage, right_usage)

    sequence = [AE_PACKET] + [pages[i] for i in range(1, 0x0F)]
    for idx, packet in enumerate(sequence):
        resp = write_and_read(fd, packet)
        if resp is None and verify:
            print(f"[erro] sem resposta no pacote #{idx}")
            return 1
        if resp is None and not verify:
            print(f"[warn] sem resposta no pacote #{idx}, seguindo (no-verify)")
            time.sleep(0.01)
            continue
        if verify and resp != packet:
            print(f"[erro] resposta diferente no pacote #{idx}")
            print(f"tx={packet.hex()}")
            print(f"rx={resp.hex()}")
            return 1
        time.sleep(0.01)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Aplica mapeamento Fn no DNA59 via ciclo AE+A0 observado no Wireshark"
    )
    p.add_argument("--dev", default="/dev/hidraw1")
    p.add_argument("--fn-left", type=lambda x: int(x, 0), default=0x3D, help="HID usage Fn esquerda (default: 0x3D = F4)")
    p.add_argument("--fn-right", type=lambda x: int(x, 0), default=0x41, help="HID usage Fn direita (default: 0x41 = F8)")
    p.add_argument("--no-verify", action="store_true", help="Nao valida se RX == TX")
    args = p.parse_args()

    if not (0 <= args.fn_left <= 0xFF and 0 <= args.fn_right <= 0xFF):
        print("Uso invalido: --fn-left/--fn-right devem estar entre 0x00 e 0xFF")
        return 2

    try:
        fd = open_dev(args.dev)
    except PermissionError:
        print("Permissao negada. Rode com sudo.")
        return 2
    except FileNotFoundError:
        print(f"Dispositivo nao encontrado: {args.dev}")
        return 2

    try:
        rc = apply_mapping(
            fd=fd,
            left_usage=args.fn_left,
            right_usage=args.fn_right,
            verify=not args.no_verify,
        )
        if rc == 0:
            print(
                f"[ok] mapeamento aplicado: fn-left=0x{args.fn_left:02x}, fn-right=0x{args.fn_right:02x}"
            )
        return rc
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
