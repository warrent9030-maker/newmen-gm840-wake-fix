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
& $pythonPath -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.9 or newer is required, but '$pythonPath' could not provide it. Install Python 3.9+ and retry. Nothing was read or flashed."
}
$sessionDirectory = Join-Path $PSScriptRoot ('backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $sessionDirectory | Out-Null
$backupPath = Join-Path $sessionDirectory 'before-full.bin'
$secondBackupPath = Join-Path $sessionDirectory 'before-full-verify.bin'
$restorePath = Join-Path $sessionDirectory 'restore-application.bin'
$patchedPath = Join-Path $sessionDirectory ('patched-' + $Feature + '.bin')
$readbackPath = Join-Path $sessionDirectory 'installed-full-readback.bin'
$logPath = Join-Path $sessionDirectory 'install.log'
$deviceOptions = @('--platform','sh68f90','--vendor_id','0x12c9','--product_id','0x6004',
    '--firmware_size','61440','--bootloader_size','4096','--page_size','2048',
    '--isp_iface_num','1','--isp_report_id','5','--format','bin','--retry','2')
# Backup reads keep the keyboard in ISP mode; only the write and final readback reboot it.
$readOptions = $deviceOptions + @('--reboot','false')
$flashOptions = $deviceOptions + @('--reboot','true')
function Write-Transcript([scriptblock]$Call) {
    # Redirected native stderr becomes error records in Windows PowerShell 5.1;
    # Continue for the call so tool output reaches the transcript and console.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Call 2>&1 | Tee-Object -FilePath $logPath -Append
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}
function Invoke-Flasher([string[]]$ToolArguments) {
    Write-Transcript { & $flasherPath @ToolArguments }
    if ($LASTEXITCODE -ne 0) { throw "sinowisp failed ($LASTEXITCODE). No further operation will run." }
}
function Invoke-Patcher([string[]]$ToolArguments) {
    Write-Transcript { & $pythonPath $patcherPath @ToolArguments }
    if ($LASTEXITCODE -ne 0) { throw 'Firmware validation failed or the patcher could not run. See the error above. No further operation will run.' }
}
Write-Host 'Use a GM840 in wired mode (Fn+Tab held for 3 seconds, red Tab indicator). Keep USB connected.'
Invoke-Flasher (@('read') + $readOptions + @('--section','full',$backupPath))
Invoke-Flasher (@('read') + $readOptions + @('--section','full',$secondBackupPath))
if ((Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $secondBackupPath -Algorithm SHA256).Hash) {
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
Invoke-Flasher (@('write') + $flashOptions + @($patchedPath))
Invoke-Flasher (@('read') + $flashOptions + @('--section','full',$readbackPath))
Invoke-Patcher -ToolArguments @('verify',$backupPath,$patchedPath,$readbackPath)
Write-Host 'Installation and exact readback verified. Test normal wired typing, then Bluetooth idle/wake.'
