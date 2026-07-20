$ErrorActionPreference = "Stop"

if (-not $env:VERSION) { throw "Set VERSION for the Windows installer build." }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Build = Join-Path $Root "exe/build"
$Dist = Join-Path $Root "exe/dist"
$Venv = Join-Path $Build "venv"

Remove-Item -Recurse -Force $Build, $Dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Build, $Dist | Out-Null
py -3 -m venv $Venv
& "$Venv/Scripts/python.exe" -m pip install --upgrade pip pyinstaller
& "$Venv/Scripts/python.exe" -m pip install "$Root/atonixcorpsdk" "$Root/atonixcorpcli" "$Root/toolbox"

$Icon = Join-Path $Build "AtonixCorp.ico"
magick "$Root/app/src/assets/icon-atonixcorp-mark.svg" -define icon:auto-resize=256,128,64,48,32,16 $Icon
& "$Venv/Scripts/pyinstaller.exe" --clean --noconfirm --onefile --name atonixcorp --icon $Icon --hidden-import atonixcorp_toolbox.main "$Root/exe/src/desktop_entry.py"
Move-Item "$Root/dist/atonixcorp.exe" "$Build/atonixcorp.exe" -Force

if (-not $env:WINDOWS_CERTIFICATE_BASE64 -or -not $env:WINDOWS_CERTIFICATE_PASSWORD) {
  throw "Refusing unsigned Windows release build: WINDOWS_CERTIFICATE_BASE64 and WINDOWS_CERTIFICATE_PASSWORD are required."
}
$CertificatePath = Join-Path $Build "signing.pfx"
[IO.File]::WriteAllBytes($CertificatePath, [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE_BASE64))
& signtool sign /fd SHA256 /f $CertificatePath /p $env:WINDOWS_CERTIFICATE_PASSWORD /tr http://timestamp.digicert.com /td SHA256 "$Build/atonixcorp.exe"

& iscc "/DMyAppVersion=$env:VERSION" "/DMyAppSource=$Build/atonixcorp.exe" "/O$Dist" "$Root/exe/installer.iss"
$Installer = Join-Path $Dist "AtonixCorpDeveloperTools-$env:VERSION.exe"
& signtool sign /fd SHA256 /f $CertificatePath /p $env:WINDOWS_CERTIFICATE_PASSWORD /tr http://timestamp.digicert.com /td SHA256 $Installer
