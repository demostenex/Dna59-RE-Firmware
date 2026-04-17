# DNA59 no Linux sem Windows: como remapear Fn com engenharia reversa

Depois de várias tentativas, consegui um fluxo estável para usar o teclado DNA59 (Wings Tech MWV602) no Linux sem depender do software oficial no Windows para cada ajuste.

O problema central era simples de explicar e difícil de resolver: as teclas Fn físicas não apareciam como teclas HID comuns, então remapeadores tradicionais no Linux não conseguiam gravar o comportamento direto delas.

## O cenário

- Teclado: Wings Tech Gaming Keyboard (DNA59)
- VID:PID: `2EA8:2122`
- Sistema: Linux (Arch)
- Objetivo: deixar o teclado usável 100% no Linux, com foco em `=` e `\`

## O que não funcionou primeiro

1. Remap direto com `keyd` para Fn físico.
2. Captura inicial USB/HID sem o pacote certo de gravação.
3. Monitoramento de `hidraw` esperando evento dedicado das teclas Fn.

Nada disso resolvia o ponto principal: o Fn é tratado internamente pelo firmware como estado/modificador, não como tecla normal.

## Virada: captura certa no Windows + reprodução no Linux

A solução apareceu quando capturei no Windows (Wireshark + USBPcap) o fluxo real de salvar perfil e comparei os perfis exportados.

Com isso, foi possível identificar um ciclo consistente de pacotes (`AE + A0 páginas 01..0E`) que o teclado aceita para atualizar o mapa interno. A partir desse fluxo, criei um script Python para aplicar o remapeamento no Linux.

## Resultado prático que ficou funcionando

- `Fn esquerda` -> `=` (usage `0x2E`)
- `Fn direita` -> `Scroll Lock` (usage `0x47`)
- no `keyd`: `Scroll Lock` -> `\`

Esse caminho contorna o problema específico do firmware/layout com o backslash direto no Fn direito, mantendo o uso diário resolvido.

## Script usado

Arquivo no repositório:

- `dna59_fn_apply.py`

Exemplo:

```bash
sudo python3 dna59_fn_apply.py --dev /dev/hidraw1 --fn-left 0x2e --fn-right 0x47 --no-verify
```

## Próximo passo

Agora que o protocolo mínimo de remapeamento foi reproduzido no Linux, o próximo passo é transformar isso em uma ferramenta Python mais amigável (CLI simples, presets, leitura do estado atual e aplicação segura de perfis), para nunca mais depender de Windows com esse teclado.
