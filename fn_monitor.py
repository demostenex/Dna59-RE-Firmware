#!/usr/bin/env python3
import argparse
import os
import select
import signal
import sys


running = True


def on_sigint(_signum, _frame):
    global running
    running = False


def open_hid(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    return fd


def main():
    p = argparse.ArgumentParser(description="Monitora pacotes hidraw para achar eventos Fn")
    p.add_argument("--devs", nargs="+", default=["/dev/hidraw0", "/dev/hidraw1"])
    p.add_argument("--max-bytes", type=int, default=64)
    args = p.parse_args()

    fds = []
    for dev in args.devs:
        try:
            fd = open_hid(dev)
            fds.append((dev, fd))
            print(f"[ok] {dev}")
        except OSError as e:
            print(f"[erro] {dev}: {e}")

    if not fds:
        print("Nenhum hidraw aberto.")
        return 2

    signal.signal(signal.SIGINT, on_sigint)
    print("Monitorando... pressione Fn esquerdo/direito. Ctrl+C para parar.")

    try:
        while running:
            ready, _, _ = select.select([fd for _, fd in fds], [], [], 1.0)
            for dev, fd in fds:
                if fd not in ready:
                    continue
                try:
                    data = os.read(fd, args.max_bytes)
                except BlockingIOError:
                    continue
                if data:
                    print(f"{dev}: {data.hex()}")
    finally:
        for _, fd in fds:
            os.close(fd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
