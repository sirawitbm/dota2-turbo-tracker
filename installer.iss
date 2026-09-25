; release.ps1 passes these in from tools\project.ps1, which reads the version
; straight out of turbo_tracker.py. The fallbacks only apply when ISCC is run
; by hand on this file.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "Turbo Tracker"
#endif
#ifndef MyAppURL
  #define MyAppURL "https://github.com/sirawitbm/dota2-turbo-tracker"
#endif

#define MyAppName "Turbo Tracker"
#define MyAppExeName "TurboTracker.exe"

[Setup]
AppId={{F6ED86DA-D607-4E74-8497-C7EDA99D5D9A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={localappdata}\Programs\TurboTracker
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\release
OutputBaseFilename=TurboTracker-v{#MyAppVersion}-Setup
SetupIconFile=assets\TurboTracker.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
LicenseFile=LICENSE
AppMutex=Local\TurboTracker

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\TurboTracker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

