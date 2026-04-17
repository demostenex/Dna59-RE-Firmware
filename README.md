# DNA59 / Wings Tech MWV602 (Linux Reverse Engineering)

Este repositório reúne a investigação técnica para fazer o teclado **DNA59 (Wings Tech MWV602)** funcionar plenamente no Linux, com foco no remapeamento das teclas **Fn esquerda** e **Fn direita**.

## Objetivo

Remapear:

- **Fn esquerda** -> `=` e `+`
- **Fn direita** -> `\` e `|`

## Hardware e ambiente

- Dispositivo: **Wings Tech Gaming Keyboard**
- VID:PID: **2EA8:2122**
- Sistema: **Arch Linux**

## Arquivos analisados

- `ER_IROM1` (firmware principal ARM)
- `ER_IROM2` (dados/config em flash)
- `wtconfig.ini`
- `DNA59_Setup_v1.0_20220303.exe`

## Resumo do que foi feito

1. Tentativa de remapeamento direto no Linux com `keyd` (Fn físico não respondeu).
2. Capturas USB/HID via `usbmon`/`tshark` (sem pacote útil de gravação).
3. Monitoramento de `hidraw` (`/dev/hidraw0` e `/dev/hidraw1`) (Fn sem evento dedicado).
4. Reverse engineering de firmware/app com identificação de comandos e estrutura de protocolo.

## Descobertas principais

- O app oficial usa `SetFeature` com payload de **24 bytes**.
- `wtconfig.ini` indica:
  - `App_Report_ID=4`
  - `PSD=0x18,0x08` (24 bytes write / 8 bytes read)
- No firmware (`ER_IROM1`), o dispatch principal está em `0xF600`:
  - `byte[0]`: Report ID (`0x04`)
  - `byte[1]`: comando principal (`0xA0..0xA9`)
  - comandos relevantes:
    - `0xA8` = key read
    - `0xA6` = commit/save
    - `0xA7` = estado/toggle
    - `0xA9` = sub-dispatch (LED etc.)
- A hipótese `indice firmware == HID usage` foi descartada.
- Fluxo confirmado como multicamada: `matrix/index interno -> tabela/transformacao -> HID final`.
- As teclas Fn se comportam como estado/modificador interno, não como tecla HID normal.

## Scripts incluídos

- `dna59_hid_tool.py`
  - comandos: `read`, `dump`, `scan`, `raw`, `a0-readmeta`, `feature-read/raw`, `a3-probe`
- `fn_monitor.py`
  - monitoramento de `hidraw` em tempo real
- `dna59_fn_apply.py`
  - aplica ciclo `AE + A0 (01..0E)` para gravar Fn
  - default: `Fn esquerda = F4 (0x3D)` e `Fn direita = F8 (0x41)`

Exemplo:

```bash
sudo python3 dna59_fn_apply.py --dev /dev/hidraw1
```

## Estado funcional atual (validado)

- `Fn esquerda` mapeada para `=` (usage `0x2E`) via `dna59_fn_apply.py`
- `Fn direita` mapeada para `Scroll Lock` (usage `0x47`) via `dna59_fn_apply.py`
- No Linux, `Scroll Lock` remapeado para `\` no `keyd`

Comando usado:

```bash
sudo python3 dna59_fn_apply.py --dev /dev/hidraw1 --fn-left 0x2e --fn-right 0x47 --no-verify
```

## Resultados práticos

- `read 109` e `read 112` (índices do Cfg.ini para Fn): `ok=0`
- `a0-readmeta`: resposta válida (incluindo bytes `01 18 0a`)
- `scan 0..255` em `A8`: apenas índice `0` válido
- `A7` é aceito (teclado pisca), mas não desbloqueia índices
- `A3 probe`: sem índices úteis
- `A1`: sem resposta
- `Feature ioctl` em `hidraw0/hidraw1` (24/25 bytes, RID `00/04`): `errno 71 (Protocol error)`

## Conclusão atual

Pelo canal Linux/hidraw utilizado até aqui, ainda não foi possível alcançar o caminho real de escrita de keymap. Portanto, o remapeamento final das duas Fn ainda não pode ser gravado com segurança apenas com os pacotes conhecidos até agora.

## Próximo passo recomendado

Capturar no Windows (idealmente VM com USB passthrough funcional) os pacotes reais do app oficial:

1. Abrir o app.
2. Fazer um remapeamento mínimo.
3. Capturar com USBPcap/Wireshark.
4. Filtrar por `VID:PID 2EA8:2122`.
5. Extrair pacotes de `write + commit`.
6. Reproduzir no Linux.
