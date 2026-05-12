; ========================================
; Anonimizzatore PDF v1.1.0
; Installer Inno Setup
; ========================================

#define MyAppName "Anonimizzatore PDF"
#define MyAppVersion "1.1.2"
#define MyAppPublisher "Anonimizzatore PDF"
#define MyAppExeName "AnonimizzatorePDF.bat"
#define MyAppId "{{B9E4D3F2-5C6D-5E9F-A2B3-3D4E5F6A7B8C}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AnonimizzatorePDF
DefaultGroupName=Anonimizzatore PDF
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=AnonimizzatorePDF-Setup-v1.1.0
;SetupIconFile=app\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
ShowLanguageDialog=no

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Collegamenti:"; Flags: checkedonce

[Files]
Source: "app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "setup-dependencies.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "AnonimizzatorePDF.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README-UTENTE.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Disinstalla {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\setup-dependencies.ps1"" -InstallPath ""{app}"""; \
    StatusMsg: "Configurazione di Python, Tesseract e dipendenze (10-15 minuti)..."; \
    Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppName} ora"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('Anonimizzatore PDF v1.1.0' + #13#10 + #13#10 +
         'Questa installazione scaricherà e configurerà:' + #13#10 +
         '- Python 3.12 (se non già presente)' + #13#10 +
         '- Tesseract OCR con supporto italiano (se non già presente)' + #13#10 +
         '- Tutte le librerie Python necessarie' + #13#10 +
         '- Il modello linguistico italiano per spaCy' + #13#10 + #13#10 +
         'Tutti i download vengono verificati con SHA256.' + #13#10 + #13#10 +
         'Richiede una connessione internet.' + #13#10 +
         'Tempo stimato: 10-15 minuti.', mbInformation, MB_OK);
end;
