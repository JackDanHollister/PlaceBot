; Inno Setup script for the PlaceBot Windows installer.
;
; Packages the self-contained runtime assembled by build.ps1 (a portable
; embeddable Python with placebot[gui] pip-installed into it) and creates
; Desktop + Start Menu shortcuts that launch the GUI.
;
; Per-user install (no administrator rights required) so museum staff on
; locked-down machines can install without IT.
;
; Compile with, e.g.:
;   iscc /DMyAppVersion=1.2.5 ^
;        /DStageDir=..\..\build\win\PlaceBot ^
;        /DIconFile=..\assets\placebot.ico ^
;        installer\windows\placebot.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef StageDir
  #define StageDir "..\..\build\win\PlaceBot"
#endif
#ifndef IconFile
  #define IconFile "..\assets\placebot.ico"
#endif

#define MyAppName "PlaceBot"
#define MyAppPublisher "Jack Hollister"
#define MyAppURL "https://github.com/JackDanHollister/PlaceBot"
; The shortcut runs the bundled Python with -m so it never depends on the
; per-user Scripts\ entry-point shims being on PATH.
#define PyExe "{app}\python\python.exe"

[Setup]
AppId={{A7E6B0C2-9C4E-4A1E-9C2B-PLACEBOT0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=PlaceBot-Setup-{#MyAppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\placebot.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; The whole staged runtime (python\ + site-packages with placebot[gui]).
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#IconFile}";   DestDir: "{app}"; DestName: "placebot.ico"; Flags: ignoreversion

[Icons]
; python.exe (console visible) so the window doubles as PlaceBot's on/off switch,
; matching the launcher's "keep this window open; close it to quit" banner.
Name: "{group}\{#MyAppName}";            Filename: "{#PyExe}"; Parameters: "-m placebot.gui.launcher"; WorkingDir: "{app}"; IconFilename: "{app}\placebot.ico"
Name: "{userdesktop}\{#MyAppName}";      Filename: "{#PyExe}"; Parameters: "-m placebot.gui.launcher"; WorkingDir: "{app}"; IconFilename: "{app}\placebot.ico"; Tasks: desktopicon
Name: "{group}\Uninstall {#MyAppName}";  Filename: "{uninstallexe}"

[Run]
Filename: "{#PyExe}"; Parameters: "-m placebot.gui.launcher"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
