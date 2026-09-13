<#
.SYNOPSIS
Back up and prepare a fingerprint-checked GM840 firmware patch; -Flash installs it.
.EXAMPLE
.\install.ps1 -Flasher C:\Tools\sinowisp.exe -Feature wake
.EXAMPLE
.\install.ps1 -Flasher C:\Tools\sinowisp.exe -Feature battery -Flash
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Flasher,
    [ValidateSet('wake','battery')][string]$Feature = 'wake',
    [switch]$Flash
)
$ErrorActionPreference = 'Stop'
$flasherPath = (Resolve-Path -LiteralPath $Flasher).Path
$patcherPath = Join-Path $PSScriptRoot 'gm840_patch.py'
$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction Stop }
$pythonPath = $pythonCommand.Source
$sessionDirectory = Join-Path $PSScriptRoot ('backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $sessionDirectory | Out-Null
$backupPath = Join-Path $sessionDirectory 'before-full.bin'
$secondBackupPath = Join-Path $sessionDirectory 'before-full-verify.bin'
$restorePath = Join-Path $sessionDirectory 'restore-application.bin'
$patchedPath = Join-Path $sessionDirectory ('patched-' + $Feature + '.bin')
$readbackPath = Join-Path $sessionDirectory 'installed-full-readback.bin'
$deviceOptions = @('--platform','sh68f90','--vendor_id','0x12c9','--product_id','0x6004',
    '--firmware_size','61440','--bootloader_size','4096','--page_size','2048',
    '--isp_iface_num','1','--isp_report_id','5','--reboot','true','--format','bin','--retry','2')
function Invoke-Flasher([string[]]$ToolArguments) {
    & $flasherPath @ToolArguments
    if ($LASTEXITCODE -ne 0) { throw "sinowisp failed ($LASTEXITCODE). No further operation will run." }
}
function Invoke-Patcher([string[]]$ToolArguments) {
    & $pythonPath $patcherPath @ToolArguments
    if ($LASTEXITCODE -ne 0) { throw 'Firmware validation failed. No further operation will run.' }
}
Write-Host 'Use a GM840 in wired mode (Fn+Tab held for 3 seconds, red Tab indicator). Keep USB connected.'
Invoke-Flasher (@('read') + $deviceOptions + @('--section','full',$backupPath))
Invoke-Flasher (@('read') + $deviceOptions + @('--section','full',$secondBackupPath))
if ((Get-FileHash -LiteralPath $backupPath).Hash -ne (Get-FileHash -LiteralPath $secondBackupPath).Hash) {
    throw 'The two backups differ. Both are retained; nothing will be flashed.'
}
Invoke-Patcher -ToolArguments @('inspect',$backupPath)
Invoke-Patcher -ToolArguments @('extract-restore',$backupPath,$restorePath)
Invoke-Patcher -ToolArguments @('patch',$backupPath,$patchedPath,'--feature',$Feature)
Write-Host "Your private backup and recovery files are in: $sessionDirectory"
if (-not $Flash) {
    Write-Host 'Preparation complete. Firmware has not been flashed. Run with -Flash when ready to install.'
    return
}
Invoke-Flasher (@('write') + $deviceOptions + @($patchedPath))
Invoke-Flasher (@('read') + $deviceOptions + @('--section','full',$readbackPath))
Invoke-Patcher -ToolArguments @('verify',$backupPath,$patchedPath,$readbackPath)
Write-Host 'Installation and exact readback verified. Test normal wired typing, then Bluetooth idle/wake.'
