; Jarvis for Windows: a per-user installer (no admin) around the PyInstaller build in dist\Jarvis.
; release.yml compiles it from the repo's root:  ISCC /DAppVersion=x.y.z packaging\windows\jarvis.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{E14676D7-C683-4B70-9C7A-97787929DF07}
AppName=Jarvis
AppVersion={#AppVersion}
AppPublisherURL=https://github.com/Qssaf/jarvis-assistant
SourceDir=..\..
OutputDir=.
OutputBaseFilename=Jarvis-Setup-{#AppVersion}
PrivilegesRequired=lowest
DefaultDirName={autopf}\Jarvis
DisableProgramGroupPage=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Jarvis.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: startup; Description: "Start Jarvis when I log in"; Flags: unchecked

[InstallDelete]
; (an update's files replace the old ones, so nothing left from an older version gets loaded)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\Jarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Jarvis"; Filename: "{app}\Jarvis.exe"; Comment: "Voice assistant (say ""Hey Jarvis"")"

[Run]
Filename: "{app}\Jarvis.exe"; Description: "Start Jarvis"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userstartup}\Jarvis.bat"

[Code]
// "Start when I log in": the same Startup script Jarvis's own switch writes, and that switch turned on in its settings,
// so it shows the truth (saving settings with it off would remove the script again).
procedure StartAtLogin;
var
  Path, Rest: String;
  Json: AnsiString;
begin
  SaveStringToFile(ExpandConstant('{userstartup}\Jarvis.bat'),
    '@echo off'#13#10'start "" "' + ExpandConstant('{app}\Jarvis.exe') + '"'#13#10, False);
  Path := ExpandConstant('{userappdata}\Jarvis\settings.json');
  if not LoadStringFromFile(Path, Json) then
    Json := '{}';
  // (only settings that differ from the defaults are saved, as ASCII JSON: a missing key here means "off")
  if (Pos('"start_at_login"', String(Json)) = 0) and (Pos('{', String(Json)) > 0) then begin
    Rest := Trim(Copy(String(Json), Pos('{', String(Json)) + 1, Length(Json)));
    if Rest <> '}' then
      Rest := ', ' + Rest;
    ForceDirectories(ExtractFileDir(Path));
    SaveStringToFile(Path, AnsiString('{"start_at_login": true' + Rest), False);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('startup') then
    StartAtLogin;
end;

// Settings, memory, conversations and keys stay for a later install unless the user says otherwise.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent and
     (MsgBox('Also delete your Jarvis settings, memory and conversations from this PC?', mbConfirmation,
             MB_YESNO or MB_DEFBUTTON2) = IDYES) then
    DelTree(ExpandConstant('{userappdata}\Jarvis'), True, True, True);
end;
