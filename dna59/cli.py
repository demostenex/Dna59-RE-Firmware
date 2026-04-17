#!/usr/bin/env python3
import argparse
import sys

from .protocol import (
    PRESETS,
    BASE_PAGES,
    build_led_guess_sequence,
    extract_fn_from_page_0d,
)
from .remap import apply_fn_mapping, apply_packet_sequence
from .transport import HidRawTransport, detect_device, iter_hidraw_paths


def parse_usage(value: str) -> int:
    n = int(value, 0)
    if not (0 <= n <= 0xFF):
        raise argparse.ArgumentTypeError("usage deve estar entre 0x00 e 0xFF")
    return n


def cmd_detect(_args: argparse.Namespace) -> int:
    found = detect_device()
    if not found:
        print("Nenhum DNA59 detectado automaticamente.")
        print(f"hidraw visiveis: {', '.join(iter_hidraw_paths()) or '<nenhum>'}")
        return 1
    print(f"[ok] dispositivo: {found.path}")
    print(f"readmeta: {found.response.hex()}")
    return 0


def resolve_dev_path(dev_arg: str | None) -> str:
    if dev_arg:
        return dev_arg
    found = detect_device()
    if found:
        return found.path
    raise RuntimeError("Nao foi possivel detectar o dispositivo automaticamente. Use --dev.")


def cmd_show_fn(_args: argparse.Namespace) -> int:
    left, right = extract_fn_from_page_0d(BASE_PAGES[0x0D])
    print("Mapeamento base conhecido (snapshot protocolo A0/0D):")
    print(f"fn-left=0x{left:02x}")
    print(f"fn-right=0x{right:02x}")
    return 0


def cmd_set_fn(args: argparse.Namespace) -> int:
    try:
        dev_path = resolve_dev_path(args.dev)
    except RuntimeError as e:
        print(str(e))
        return 2

    try:
        with HidRawTransport(dev_path) as dev:
            result = apply_fn_mapping(
                dev=dev,
                left_usage=args.left,
                right_usage=args.right,
                verify=not args.no_verify,
            )
    except PermissionError:
        print("Permissao negada. Rode com sudo.")
        return 2
    except FileNotFoundError:
        print(f"Dispositivo nao encontrado: {dev_path}")
        return 2
    except OSError as e:
        print(f"Erro no hidraw: errno={e.errno} ({e.strerror})")
        return 2

    if not result.ok:
        print(f"[erro] {result.error}")
        return 1
    for idx in result.missing_echo_packets:
        print(f"[warn] sem resposta no pacote #{idx}, seguindo (no-verify)")
    print(f"[ok] mapeamento aplicado: fn-left=0x{args.left:02x}, fn-right=0x{args.right:02x}")
    return 0


def cmd_preset(args: argparse.Namespace) -> int:
    if args.name not in PRESETS:
        print(f"Preset invalido: {args.name}")
        print(f"presets: {', '.join(sorted(PRESETS.keys()))}")
        return 2
    left, right = PRESETS[args.name]
    args.left = left
    args.right = right
    return cmd_set_fn(args)


def cmd_set_color(args: argparse.Namespace) -> int:
    if not args.unsafe:
        print("[bloqueado] set-color exige --unsafe (modo experimental sem captura oficial A9).")
        print("Exemplo: sudo python3 dna59ctl.py set-color --r 255 --g 0 --b 0 --unsafe --profile aggressive --no-verify")
        return 2

    try:
        dev_path = resolve_dev_path(args.dev)
    except RuntimeError as e:
        print(str(e))
        return 2

    try:
        sequence = build_led_guess_sequence(args.r, args.g, args.b, profile=args.profile)
    except ValueError as e:
        print(f"[erro] {e}")
        return 2

    try:
        with HidRawTransport(dev_path) as dev:
            result = apply_packet_sequence(
                dev=dev,
                sequence=sequence,
                verify=not args.no_verify,
            )
    except PermissionError:
        print("Permissao negada. Rode com sudo.")
        return 2
    except FileNotFoundError:
        print(f"Dispositivo nao encontrado: {dev_path}")
        return 2
    except OSError as e:
        print(f"Erro no hidraw: errno={e.errno} ({e.strerror})")
        return 2

    if not result.ok:
        print(f"[erro] {result.error}")
        return 2
    for idx in result.missing_echo_packets:
        print(f"[warn] sem resposta no pacote LED #{idx}, seguindo (no-verify)")
    print(
        f"[ok] tentativa de cor enviada: rgb=({args.r},{args.g},{args.b}) profile={args.profile}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CLI do DNA59 para Linux")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("detect", help="Detecta hidraw do DNA59 automaticamente")
    sp.add_parser("show-fn", help="Mostra mapeamento base conhecido de Fn")

    set_fn = sp.add_parser("set-fn", help="Aplica mapeamento Fn")
    set_fn.add_argument("--dev", default=None, help="hidraw (auto-detect se omitido)")
    set_fn.add_argument("--left", required=True, type=parse_usage, help="usage da Fn esquerda")
    set_fn.add_argument("--right", required=True, type=parse_usage, help="usage da Fn direita")
    set_fn.add_argument("--no-verify", action="store_true", help="nao exigir eco em todos os pacotes")

    preset = sp.add_parser("preset", help="Aplica preset de mapeamento Fn")
    preset.add_argument("--dev", default=None, help="hidraw (auto-detect se omitido)")
    preset.add_argument("--name", required=True, choices=sorted(PRESETS.keys()))
    preset.add_argument("--no-verify", action="store_true", help="nao exigir eco em todos os pacotes")

    color = sp.add_parser("set-color", help="(experimental) define cor LED")
    color.add_argument("--dev", default=None, help="hidraw (auto-detect se omitido)")
    color.add_argument("--r", type=int, required=True)
    color.add_argument("--g", type=int, required=True)
    color.add_argument("--b", type=int, required=True)
    color.add_argument("--profile", choices=["safe", "aggressive"], default="safe")
    color.add_argument("--no-verify", action="store_true", help="nao exigir eco em todos os pacotes")
    color.add_argument("--unsafe", action="store_true", help="aceita tentativa de LED sem protocolo confirmado")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "detect":
        return cmd_detect(args)
    if args.cmd == "show-fn":
        return cmd_show_fn(args)
    if args.cmd == "set-fn":
        return cmd_set_fn(args)
    if args.cmd == "preset":
        return cmd_preset(args)
    if args.cmd == "set-color":
        return cmd_set_color(args)
    print("comando invalido")
    return 2


if __name__ == "__main__":
    sys.exit(main())
