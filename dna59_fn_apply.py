#!/usr/bin/env python3
import argparse
import sys

from dna59.remap import apply_fn_mapping
from dna59.transport import HidRawTransport


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
        with HidRawTransport(args.dev) as dev:
            result = apply_fn_mapping(
                dev=dev,
                left_usage=args.fn_left,
                right_usage=args.fn_right,
                verify=not args.no_verify,
            )
        if result.ok:
            for idx in result.missing_echo_packets:
                print(f"[warn] sem resposta no pacote #{idx}, seguindo (no-verify)")
            print(
                f"[ok] mapeamento aplicado: fn-left=0x{args.fn_left:02x}, fn-right=0x{args.fn_right:02x}"
            )
            return 0
        print(f"[erro] {result.error}")
        return 1
    except PermissionError:
        print("Permissao negada. Rode com sudo.")
        return 2
    except FileNotFoundError:
        print(f"Dispositivo nao encontrado: {args.dev}")
        return 2
    except OSError as e:
        print(f"Erro no hidraw: errno={e.errno} ({e.strerror})")
        return 2


if __name__ == "__main__":
    sys.exit(main())
