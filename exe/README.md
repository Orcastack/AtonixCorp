# AtonixCorp Windows Installer

This project creates a signed Windows 10/11 x64 installer containing the AtonixCorp developer toolchain: `atonixcorpcli`, `atonixcorpsdk`, and toolbox utilities.

Run only on a Windows release runner with Python 3, ImageMagick, Inno Setup 6, and the Windows SDK signing tools:

```powershell
$env:VERSION = "0.1.0"
$env:WINDOWS_CERTIFICATE_BASE64 = "..."
$env:WINDOWS_CERTIFICATE_PASSWORD = "..."
./exe/scripts/build_exe.ps1
```

The script creates branded binary and installer icons, compiles a self-contained CLI bundle, signs both the executable and installer with SHA-256 and a trusted timestamp, and produces `exe/dist/AtonixCorpDeveloperTools-<version>.exe`. The Inno Setup installer writes a standard uninstall entry and adds the installation directory to the current user PATH.

After installation, use `atonixcorp --help` or `atonixcorp toolbox sandbox-entity 1` from PowerShell.
