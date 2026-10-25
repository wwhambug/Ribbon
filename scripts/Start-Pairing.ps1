$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'
Write-Host 'Ribbon - Muse pairing' -ForegroundColor Cyan
Write-Host 'Get an SDK token: https://gadgets.muse.ai/settings/sdk-tokens'
Write-Host 'Paste the token below. It will be hidden. Do not paste it into chat.'
$secret = Read-Host 'SDK token' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $token | & wsl.exe -d Ribbon-Ubuntu -u root --exec /opt/ribbon/venv/bin/python /mnt/c/Users/hambu/Documents/Codex/2026-10-25/new-chat/Ribbon/scripts/Store-SdkToken.py
    $stored = $LASTEXITCODE
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $token = $null
    $secret.Dispose()
}
if ($stored -eq 0) {
    Write-Host 'On your phone: Muse > Settings > Devices > Developer mode > Add Device'
    Write-Host 'Choose the MuseGadget device named below. The pairing window lasts 10 minutes.'
    & wsl.exe -d Ribbon-Ubuntu -u root --exec /opt/ribbon/venv/bin/musegadget pair
}
Read-Host 'Press Enter to close'
