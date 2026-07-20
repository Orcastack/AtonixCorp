#define MyAppName "AtonixCorp Developer Tools"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyAppSource
  #define MyAppSource "build\atonixcorp.exe"
#endif

[Setup]
AppId={{E4C6DF8D-6C85-48C7-BE05-68C42CBE7C1B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=AtonixCorp
AppPublisherURL=https://atonixcorp.com
DefaultDirName={autopf}\AtonixCorp\Developer Tools
DefaultGroupName=AtonixCorp Developer Tools
DisableProgramGroupPage=yes
OutputBaseFilename=AtonixCorpDeveloperTools-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\atonixcorp.exe
ChangesEnvironment=yes

[Files]
Source: "{#MyAppSource}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AtonixCorp CLI"; Filename: "{app}\atonixcorp.exe"
Name: "{autodesktop}\AtonixCorp Developer Tools"; Filename: "{app}\atonixcorp.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "PATH"; ValueData: "{olddata};{app}"; Check: NeedsPathUpdate

[Code]
function NeedsPathUpdate(): Boolean;
begin
  Result := Pos(ExpandConstant('{app}'), GetEnv('PATH')) = 0;
end;
