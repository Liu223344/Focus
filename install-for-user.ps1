# Run from the source directory after build-windows.bat. Installs per user.
$ErrorActionPreference = 'Stop'
$sourceExe = Join-Path $PSScriptRoot 'dist\SonyFocusViewer.exe'
if (-not (Test-Path $sourceExe)) { throw '请先运行 build-windows.bat。' }

$appDir = Join-Path $env:LOCALAPPDATA 'Programs\SonyFocusViewer'
New-Item -ItemType Directory -Path $appDir -Force | Out-Null
$targetExe = Join-Path $appDir 'SonyFocusViewer.exe'
Copy-Item $sourceExe $targetExe -Force
$command = '"' + $targetExe + '" "%1"'
$progid = 'SonyFocusViewer.Image'
$classRoot = 'HKCU:\Software\Classes'

New-Item "$classRoot\$progid\shell\open\command" -Force | Out-Null
Set-Item "$classRoot\$progid" 'Sony Focus Viewer image'
Set-Item "$classRoot\$progid\shell\open\command" $command
New-Item "$classRoot\Applications\SonyFocusViewer.exe\shell\open\command" -Force | Out-Null
Set-Item "$classRoot\Applications\SonyFocusViewer.exe\shell\open\command" $command

$capabilities = 'HKCU:\Software\SonyFocusViewer\Capabilities'
New-Item "$capabilities\FileAssociations" -Force | Out-Null
New-ItemProperty -Path $capabilities -Name 'ApplicationName' -Value 'Sony Focus Viewer' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $capabilities -Name 'ApplicationDescription' -Value 'Photo viewer with Sony ARW camera focus frames' -PropertyType String -Force | Out-Null

foreach ($ext in @('.arw','.jpg','.jpeg','.png','.bmp','.webp','.tif','.tiff','.gif','.heic','.heif')) {
    New-Item "$classRoot\$ext\OpenWithProgids" -Force | Out-Null
    New-ItemProperty -Path "$classRoot\$ext\OpenWithProgids" -Name $progid -Value '' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path "$capabilities\FileAssociations" -Name $ext -Value $progid -PropertyType String -Force | Out-Null
}
New-Item 'HKCU:\Software\RegisteredApplications' -Force | Out-Null
New-ItemProperty -Path 'HKCU:\Software\RegisteredApplications' -Name 'SonyFocusViewer' -Value 'Software\SonyFocusViewer\Capabilities' -PropertyType String -Force | Out-Null

$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$shortcut = Join-Path $startMenu 'Sony Focus Viewer.lnk'
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $targetExe
$link.WorkingDirectory = $appDir
$link.Save()

Write-Host "已安装：$targetExe"
Write-Host '已注册为可选默认看图应用。请在 Windows 设置 > 应用 > 默认应用 中选择 Sony Focus Viewer。'
Start-Process 'ms-settings:defaultapps'
