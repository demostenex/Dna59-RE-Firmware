#!/usr/bin/env python3
import argparse
import fcntl
import os
import sys
import time


def open_dev(path: str):
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    return fd


def send_packet(fd: int, data: bytes, read_timeout: float = 0.25):
    pkt = bytearray(64)
    pkt[: len(data)] = data
    os.write(fd, pkt)

    deadline = time.time() + read_timeout
    while time.time() < deadline:
        try:
            out = os.read(fd, 64)
            if out:
                return bytes(out)
        except BlockingIOError:
            pass
        time.sleep(0.01)
    return None


def hx(b: bytes):
    return " ".join(f"{x:02x}" for x in b)


def _IOC(direction, ioc_type, nr, size):
    IOC_NRBITS = 8
    IOC_TYPEBITS = 8
    IOC_SIZEBITS = 14
    IOC_NRSHIFT = 0
    IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
    IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
    IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS
    return (
        (direction << IOC_DIRSHIFT)
        | (ioc_type << IOC_TYPESHIFT)
        | (nr << IOC_NRSHIFT)
        | (size << IOC_SIZESHIFT)
    )


def _HIDIOCSFEATURE(length):
    _IOC_WRITE = 1
    _IOC_READ = 2
    return _IOC(_IOC_WRITE | _IOC_READ, ord("H"), 0x06, length)


def _HIDIOCGFEATURE(length):
    _IOC_WRITE = 1
    _IOC_READ = 2
    return _IOC(_IOC_WRITE | _IOC_READ, ord("H"), 0x07, length)


def send_feature(fd: int, data: bytes, feature_len: int = 24, out_len: int = 8):
    tx = bytearray(feature_len)
    tx[: min(len(data), feature_len)] = data[:feature_len]
    fcntl.ioctl(fd, _HIDIOCSFEATURE(len(tx)), tx, True)
    rx = bytearray(max(1, out_len))
    rx[0] = tx[0]
    fcntl.ioctl(fd, _HIDIOCGFEATURE(len(rx)), rx, True)
    return bytes(tx), bytes(rx)


def cmd_key_read(fd: int, idx: int, quiet: bool = False):
    resp = send_packet(fd, bytes([0x04, 0xA8, idx & 0xFF]))
    if not resp:
        if not quiet:
            print(f"idx={idx:3d} sem resposta")
        return 1, None
    ok = resp[3]
    if not quiet:
        print(f"idx={idx:3d} ok={ok} resp={hx(resp)}")
    return 0, resp


def cmd_dump(fd: int, start: int, end: int):
    rc = 0
    for i in range(start, end + 1):
        one_rc, _ = cmd_key_read(fd, i)
        rc |= one_rc
    return rc


def cmd_scan(fd: int, start: int, end: int, only_ok: bool):
    found = []
    rc = 0
    for i in range(start, end + 1):
        one_rc, resp = cmd_key_read(fd, i, quiet=only_ok)
        rc |= one_rc
        if resp and resp[3] == 1:
            found.append(i)
            if only_ok:
                print(f"idx={i:3d} ok=1 resp={hx(resp)}")
    print(f"validos={found}")
    return rc


def cmd_a0_readmeta(fd: int):
    # A0 subcmd 0 (observado no firmware): devolve 2 bytes em resp[5:7]
    resp = send_packet(fd, bytes([0x04, 0xA0, 0x02, 0x00]))
    if not resp:
        print("A0/0 sem resposta")
        return 1
    print(f"A0/0 resp={hx(resp)}")
    return 0


def cmd_raw(fd: int, hexbytes: str):
    raw = bytes(int(x, 16) for x in hexbytes.strip().split())
    resp = send_packet(fd, raw)
    print(f"tx={hx(raw)}")
    if resp:
        print(f"rx={hx(resp)}")
    else:
        print("rx=<sem resposta>")
    return 0


def cmd_feature_raw(fd: int, hexbytes: str, feature_len: int, out_len: int):
    raw = bytes(int(x, 16) for x in hexbytes.strip().split())
    try:
        tx, rx = send_feature(fd, raw, feature_len=feature_len, out_len=out_len)
    except OSError as e:
        print(f"feature erro: errno={e.errno} ({e.strerror})")
        return 1
    print(f"feature_tx{feature_len}={hx(tx)}")
    print(f"feature_rx{out_len}={hx(rx)}")
    return 0


def cmd_feature_read(fd: int, idx: int, feature_len: int, out_len: int):
    try:
        tx, rx = send_feature(
            fd, bytes([0x04, 0xA8, idx & 0xFF]), feature_len=feature_len, out_len=out_len
        )
    except OSError as e:
        print(f"idx={idx:3d} feature erro: errno={e.errno} ({e.strerror})")
        return 1
    ok = rx[3] if len(rx) > 3 else 0
    print(f"idx={idx:3d} feature_ok={ok} tx{feature_len}={hx(tx)} rx={hx(rx)}")
    return 0


def cmd_a3_probe(fd: int, start: int, end: int, only_ok: bool):
    found = []
    rc = 0
    for idx in range(start, end + 1):
        resp = send_packet(fd, bytes([0x04, 0xA3, idx & 0xFF]))
        if not resp:
            rc = 1
            if not only_ok:
                print(f"idx={idx:3d} sem resposta")
            continue
        ok = resp[3]
        if ok == 1:
            found.append(idx)
        if (not only_ok) or ok == 1:
            print(f"idx={idx:3d} ok={ok} resp={hx(resp)}")
    print(f"a3_validos={found}")
    return rc


def main():
    p = argparse.ArgumentParser(description="DNA59 HID vendor tool")
    p.add_argument("--dev", default="/dev/hidraw1")
    sp = p.add_subparsers(dest="cmd", required=True)

    r = sp.add_parser("read")
    r.add_argument("index", type=int)

    d = sp.add_parser("dump")
    d.add_argument("start", type=int)
    d.add_argument("end", type=int)

    s = sp.add_parser("scan")
    s.add_argument("start", type=int)
    s.add_argument("end", type=int)
    s.add_argument("--only-ok", action="store_true")

    sp.add_parser("a0-readmeta")

    x = sp.add_parser("raw")
    x.add_argument("hexbytes", help='ex: "04 a8 6d"')

    fx = sp.add_parser("feature-raw")
    fx.add_argument("hexbytes", help='ex: "04 a8 6d"')
    fx.add_argument("--feature-len", type=int, default=24)
    fx.add_argument("--out-len", type=int, default=8)

    fr = sp.add_parser("feature-read")
    fr.add_argument("index", type=int)
    fr.add_argument("--feature-len", type=int, default=24)
    fr.add_argument("--out-len", type=int, default=8)

    a3 = sp.add_parser("a3-probe")
    a3.add_argument("start", type=int)
    a3.add_argument("end", type=int)
    a3.add_argument("--only-ok", action="store_true")

    args = p.parse_args()
    try:
        fd = open_dev(args.dev)
    except PermissionError:
        print("Permissao negada. Rode com sudo.")
        return 2
    except FileNotFoundError:
        print(f"Dispositivo nao encontrado: {args.dev}")
        return 2

    try:
        if args.cmd == "read":
            rc, _ = cmd_key_read(fd, args.index)
            return rc
        if args.cmd == "dump":
            return cmd_dump(fd, args.start, args.end)
        if args.cmd == "scan":
            return cmd_scan(fd, args.start, args.end, args.only_ok)
        if args.cmd == "a0-readmeta":
            return cmd_a0_readmeta(fd)
        if args.cmd == "raw":
            return cmd_raw(fd, args.hexbytes)
        if args.cmd == "feature-raw":
            return cmd_feature_raw(fd, args.hexbytes, args.feature_len, args.out_len)
        if args.cmd == "feature-read":
            return cmd_feature_read(fd, args.index, args.feature_len, args.out_len)
        if args.cmd == "a3-probe":
            return cmd_a3_probe(fd, args.start, args.end, args.only_ok)
        return 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
