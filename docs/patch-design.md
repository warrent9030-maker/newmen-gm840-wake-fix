# Patch design

This is a binary patch for one fingerprinted 3010 program, not a full replacement
firmware or generic 8051 keyboard framework. The fingerprint covers offsets
`0x0000..0xc5ff`. Configuration `0xc600..0xefff` is retained from the owner's input;
bootloader `0xf000..0xffff` is checked and never included in the write payload.

Full application hashes therefore differ between owners with different settings.
Use the program-region hash and bootloader hash for compatibility, and your own
full image hash/readback for installation verification.

## Wake capture

| Offset | Original | Replacement | Purpose |
| --- | --- | --- | --- |
| `0x44cb` | `LCALL 0x000e` | `LCALL 0x9000` | Capture after GPIO/REGCON restoration |
| `0x4cd3` | `SJMP 0x4cfe` | `SJMP 0x4d00` | Keep pending matrix after connection-control dispatch |
| `0x9000` | Zero-filled code space | 12-byte routine below | Early wireless scan |

```asm
; 0x9000
LCALL 0x000e          ; original REGCON restoration
JB    bit_04, done    ; wired mode uses its original path
CLR   bit_53         ; permit a fresh matrix scan
LCALL 0x7f88          ; stock full scanner, which marks snapshot pending
done:
RET
```

The original wake path has a 30,003-iteration delay after this point. A simulated
press released during that delay is missed by the original first scan. Capturing
before the delay preserves its identity. This does not prove the exact timing of
every real loss; the held-key diagnostic and physical trial results support it.

The stock scanner refuses to overwrite a pending matrix. If a connection-control
command takes the first processing frame, retaining `bit_53` lets the ordinary
main loop process the same snapshot on the next frame. No new RAM or custom
radio readiness gate is used. The earlier, larger queue experiments were not
retained. Original sleep threshold and power-down instructions remain byte-identical.

## Fn+B overlay

The two LED hooks jump from `0x1c41` to `0x9100` (colour selection) and from
`0x1e63` to `0x91b6` (row enable). The authored overlay is 218 bytes, including
its light-count table. [tools/assemble_battery.py](../tools/assemble_battery.py)
contains the annotated assembler source; its output must exactly match
`BATTERY_CODE` in the patcher.

Fn is matrix index 65, IRAM `0x5e` bit 5. B is index 34, IRAM `0x59` bit 4.
Both must be held. When inactive, the displaced stock branches are reproduced.
During the chord, LEDs outside indices 22..31 are dark; those indices are physical
number keys `1..0`. Selected colour channels use PWM value 640. The normal
backlight-disable bit is not modified; only row enable during the chord is
overridden. Saved effects/configuration are never written by this code.

Battery comes from the existing validated radio status cached at XRAM `0x0f80`:
the 3-bit level is `(value >> 1) & 7`. The overlay requires the status marker
and validated-status flag before using that cache. It adds no radio queries.
Some unavailable/stale-reading states remain possible, especially in wired mode.
No absolute battery voltage or calibrated percentage has been recovered.

The mapping is `[1, 1, 3, 4, 6, 7, 9, 10]` lights for raw levels 0..7. Raw 0..1
is red, 2..3 amber, 4..7 green. Unavailable data shows blue endpoint lights.
This should be described as an approximate relative gauge, not accurate 10% steps.

## Reproducibility

The patcher normalizes recognized wake/battery variants to the reviewed 3010
program before applying the selected feature. Unknown changes are rejected.
This permits idempotent patching and removal of the battery addition while
retaining the wake fix, without replacing an owner's configuration.

Only authored patch bytes and a few original-byte guards are published. Users
provide their own full USB backup. Vendor code, personal settings and bootloader
binaries are not distributed by this project. The MIT license applies to the
authored tooling and patches, not to the resulting vendor-derived firmware.
