#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{B13B8A9E-90FD-4C3A-9ED8-79C4BB2261A4}
AppName=wikiSpyder
AppVersion={#AppVersion}
AppPublisher=Omar Daniels
DefaultDirName={autopf}\wikiSpyder
DefaultGroupName=wikiSpyder
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\..\dist
OutputBaseFilename=wikiSpyder-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\assets\wikiSpyder.ico
UninstallDisplayIcon={app}\wikiSpyder.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\wikiSpyder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\wikiSpyder"; Filename: "{app}\wikiSpyder.exe"
Name: "{autodesktop}\wikiSpyder"; Filename: "{app}\wikiSpyder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\wikiSpyder.exe"; Description: "Launch wikiSpyder"; Flags: postinstall nowait skipifsilent
