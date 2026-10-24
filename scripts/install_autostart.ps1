# OPTIONAL. Registers a Windows scheduled task that brings the local Zetaris stack up 90 s after you sign in
# (after Docker Desktop has started). Run once from PowerShell:   powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
# Remove it with:                                                 Unregister-ScheduledTask -TaskName ZetarisUp -Confirm:$false
# The UI also repairs Zetaris by itself when it starts, so this only matters if you want it ready before you open the UI.
$repo = Split-Path -Parent $PSScriptRoot
$bash = (Get-Command bash.exe -ErrorAction Stop).Source
$action = New-ScheduledTaskAction -Execute $bash -Argument "-lc `"cd '$($repo -replace '\','/')' && bash scripts/zetaris_up.sh`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT90S"
Register-ScheduledTask -TaskName ZetarisUp -Action $action -Trigger $trigger -Description "Start local Zetaris after Docker Desktop" -Force | Out-Null
Write-Host "Registered scheduled task ZetarisUp"
