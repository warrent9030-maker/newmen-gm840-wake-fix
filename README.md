# Newmen GM840 Bluetooth wake fix

Keep Bluetooth sleep, keep the first letter. An experimental patch for the
**Newmen GM840 with BYK916/SH68F90A + BK3632**, based on its official **3010** firmware.
An optional **Fn+B battery bar** lights the number row while held.

The wake-only revision passed real typing after approximately **48 seconds** and
**6 minutes** of idle on one GM840. Its complete flash readback was verified.
The battery-bar addition was then installed and physically confirmed to show the
number-row bar and restore normal lighting on release. The longer wake trial
was not repeated on that addition; the wake code is unchanged and offline
regression checks passed. See [test results](docs/testing.md).

**This is a community experiment, not an official Newmen release.** Model names
and USB IDs can cover different hardware revisions. The patcher checks exact
program and bootloader fingerprints, and refuses unknown images. Firmware
flashing can leave a keyboard unusable; keep a second input device and your own
backups. Do not bypass a mismatch or use a generic device preset.

## What it changes

- **Wake fix:** capture the key matrix earlier during wake-up and preserve that
  snapshot until the normal sending path can process it.
- **Sleep stays enabled:** no keep-alive traffic, changed idle threshold or
  disabled Bluetooth power management.
- **Optional Fn+B:** show a bar from `1` toward `0`, even with normal lighting
  switched off. Release either key to restore the previous lighting.
- **Battery is approximate:** the radio reports a coarse 0..7 level, not an exact
  percentage. The bar cannot measure ten distinct 10% bands.

No vendor firmware, device dumps, pairing data or flasher executable is included.
The patcher works offline on **your own full USB backup** and preserves its
configuration. It needs Python 3.9+ and no Python packages.

## Compatibility

| Item | Tested value |
| --- | --- |
| Keyboard | Newmen GM840 |
| Main controller | BYK916 / SH68F90A |
| Radio | BK3632 |
| Wired USB VID:PID | `12c9:6004` |
| Base firmware | Official 3010, exact fingerprint checked |
| Application / bootloader | 61,440 / 4,096 bytes |
| ISP interface / report | 1 / 5 |
| Flash page | 2,048 bytes |

Firmware 3009 is recognized for backup/recovery but **cannot be patched by this
release**. Back it up first, obtain the matching official 3010 update from
[Newmen's downloads](https://www.newmentech.com/download-en.php?cid=95), install it
according to the vendor's instructions, and make a new backup. The observed
3010 [vendor package](https://www.newmentech.com/uploads/2026/6/_source/GM840%20firmware.zip)
is linked for provenance; an exact program fingerprint is still required.
If the vendor changes its package or your fingerprint differs, stop and report it.

Other keyboards, Wobkey models, GM610, different GM840 revisions and different
bootloaders are not supported. The controller patch does not replace radio firmware.

## Install on Windows

1. Download and extract this repository's [latest release](https://github.com/warrent9030-maker/newmen-gm840-wake-fix/releases).
2. Install Python 3.9+ if needed. `py --version` should work.
3. Download and extract **sinowisp v2.1.0** for Windows from its
   [upstream release](https://github.com/carlossless/sinowisp/releases/tag/v2.1.0).
   This is a separate upstream tool, not bundled here.
4. Connect the GM840 directly by USB. Hold **Fn+Tab for three seconds** to select
   wired mode; the Tab indicator should be red. Leave USB connected until verification ends.
5. Open PowerShell in the extracted project folder. Substitute your actual
   path to `sinowisp.exe` in the command below.

Prepare only: read the full firmware twice, require matching backups, validate
fingerprints, and produce both a restore image and a patched image:

```powershell
.\install.ps1 -Flasher 'C:\Tools\sinowisp.exe' -Feature wake
```

Install **wake fix only**:

```powershell
.\install.ps1 -Flasher 'C:\Tools\sinowisp.exe' -Feature wake -Flash
```

Or install **wake fix + Fn+B battery bar**:

```powershell
.\install.ps1 -Flasher 'C:\Tools\sinowisp.exe' -Feature battery -Flash
```

If PowerShell blocks downloaded scripts, inspect the files and unblock this
downloaded script with `Unblock-File .\install.ps1`. Do not change a managed
computer's policy to get around an administrator restriction. The
[manual instructions](docs/manual-install.md) use the same operations directly.

Every run creates a separate `backups\<timestamp>\` directory containing
`install.log`, a transcript of the flasher and patcher output — include it when
reporting an issue. **Keep it private and save a copy elsewhere.** With `-Flash`, the helper writes only the application,
then performs an independent full readback and requires an exact application
match and an unchanged bootloader. There is no force option or automatic retry
after a validation failure. Reading via sinowisp uses its USB-normalized reset
vector representation and enables the application marker; it is not a passive
JTAG dump. See the [upstream tool notes](https://github.com/carlossless/sinowisp#reading).

After installation, check normal wired typing. Switch back to Bluetooth with
Fn+Tab, unplug USB, type a warm-up word, then leave the keyboard untouched for
45 seconds. Type `harbor` normally without a wake-up key or correction. Repeat
after six minutes. If behaviour regresses, use your saved
[recovery image](docs/manual-install.md#restore-your-own-backup).

## Fn+B battery display

While Fn+B is held, number keys fill from `1` to `0` against a dark background.
The display uses the existing radio status reports; it adds no polling.

| Radio level | Lights | Colour |
| --- | --- | --- |
| 0 or 1 | 1 | Red |
| 2 | 1 through 3 | Amber |
| 3 | 1 through 4 | Amber |
| 4 | 1 through 6 | Green |
| 5 | 1 through 7 | Green |
| 6 | 1 through 9 | Green |
| 7 | 1 through 0, all ten | Green |

This is a relative gauge, **not calibrated remaining capacity**. The lowest
level retains one red warning light. Blue `1` and `0` mean no valid battery
reading is available. Wired mode may not provide a current radio report;
check over Bluetooth. Battery drain/current has not been measured.

## Development and reporting

```powershell
py -m unittest discover -s tests -v
```

The committed tests use synthetic buffers: no keyboard or private/vendor dump
is needed. The release was also reproduced against the locally verified device
backups before publication. [Patch design](docs/patch-design.md) describes the
hooks and the authoring source for the LED overlay.

For an issue, include the keyboard model/board revision if known, selected
feature, USB IDs, code/bootloader **hashes**, idle duration and what arrived.
Do not upload a full firmware dump, pairing information or a general keyboard log.

Original scripts and patch code are [MIT licensed](LICENSE). Newmen firmware
and third-party tools retain their own rights. This project is not affiliated
with Newmen. Thanks to [sinowisp](https://github.com/carlossless/sinowisp),
[SMK](https://github.com/carlossless/smk) and
[emu8051](https://github.com/jarikomppa/emu8051) for tools and reference material.
