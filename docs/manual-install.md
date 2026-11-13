# Manual installation and recovery

Read the root README and compatibility table first. These commands use
PowerShell and sinowisp 2.1.0. Substitute your own executable and file paths.
Do not use these parameters on an unrelated device.

```powershell
$flasher = 'C:\Tools\sinowisp.exe'
$device = @('--platform','sh68f90','--vendor_id','0x12c9','--product_id','0x6004',
  '--firmware_size','61440','--bootloader_size','4096','--page_size','2048',
  '--isp_iface_num','1','--isp_report_id','5','--format','bin','--retry','2')
```

Connect USB, then hold Fn+Tab for three seconds to select wired mode (red Tab
indicator). Make a new private directory for this installation and work there.
Do not reuse a backup filename: the upstream flasher can overwrite files.

## Back up before changing anything

```powershell
& $flasher read @device --reboot false --section full before-full.bin
# Stop if the command failed.
& $flasher read @device --reboot false --section full before-full-verify.bin
Get-FileHash before-full.bin, before-full-verify.bin -Algorithm SHA256
```

Both hashes must match. Retain both files. Passing `--reboot false` on the
backup reads keeps the keyboard in ISP mode between them; only the write and
the final readback reboot it. Pass the full backup to the patcher,
using the actual path to the script:

```powershell
py C:\Path\To\gm840_patch.py inspect before-full.bin
py C:\Path\To\gm840_patch.py extract-restore before-full.bin restore-application.bin
py C:\Path\To\gm840_patch.py patch before-full.bin patched.bin --feature wake
```

Use `--feature battery` for wake + Fn+B. Stop on **any** error. Unknown firmware
is refused; 3009 can be backed up/extracted but must be upgraded to the matching
official 3010 before patching. The patcher does not access the keyboard.

## Write and verify

Only `patched.bin`, an application-only 61,440-byte file, is a flash payload.
Never write the 65,536-byte full backup through the application-only command.

```powershell
& $flasher write @device --reboot true patched.bin
# Stop if the command failed. Keep USB connected.
& $flasher read @device --reboot true --section full after-full.bin
py C:\Path\To\gm840_patch.py verify before-full.bin patched.bin after-full.bin
```

Success requires the entire application to match and the original bootloader
to remain unchanged. Test normal wired typing and both Bluetooth idle periods
described in the README.

## Restore your own backup

Use the `restore-application.bin` produced from **your own pre-installation
backup**, paired with that same `before-full.bin`. This restores the application
you had before this particular patch, including its settings. In particular,
a backup made before adding Fn+B may restore the already working wake-only
revision. Files from another keyboard are not substitutes for your backup.

Reconnect USB and select wired mode. Run the same application-only write,
followed by independent readback:

```powershell
& $flasher write @device --reboot true restore-application.bin
& $flasher read @device --reboot true --section full restored-full.bin
py C:\Path\To\gm840_patch.py verify before-full.bin restore-application.bin restored-full.bin
```

If USB does not enumerate, try Fn+Tab in the connected state, a known data cable
and direct USB port. If it still cannot enumerate, stop: software recovery
depends on a functioning USB bootloader. No external programmer procedure is
provided or claimed tested here. Do not use `--force` or select a similar model.

## Packaging/privacy

The helper's `backups/` directory is git-ignored. Never include it in an issue,
fork, release or ZIP for someone else. Public release archives contain only
tracked source/documentation files, not generated firmware.
