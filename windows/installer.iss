; ========================================
; Anonimizzatore PDF
; Installer Inno Setup
; ========================================
; La versione può essere sovrascritta da riga di comando (CI):
;   ISCC.exe /DMyAppVersion=1.8.0 installer.iss
; Il default qui sotto serve per la compilazione manuale.

#define MyAppName "Anonimizzatore PDF"
#ifndef MyAppVersion
  #define MyAppVersion "1.8.0"
#endif
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
OutputBaseFilename=AnonimizzatorePDF-Setup-v{#MyAppVersion}
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
; DEF-01: niente più "runhidden" — la finestra PowerShell resta VISIBILE
; durante il setup. Due motivi:
; 1. Trasparenza per l'utente: vede cosa viene scaricato/installato
;    invece di fissare una barra ferma per 15 minuti.
; 2. Un installer non firmato che lancia PowerShell nascosto, scarica
;    exe e li esegue in silenzio ha il profilo comportamentale di un
;    dropper: era uno dei motivi dei falsi positivi di Defender.
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\setup-dependencies.ps1"" -InstallPath ""{app}"""; \
    StatusMsg: "Configurazione di Python, Tesseract e dipendenze (10-15 minuti)..."; \
    Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppName} ora"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('Anonimizzatore PDF v' + '{#MyAppVersion}' + #13#10 + #13#10 +
         'Questa installazione scaricherà e configurerà:' + #13#10 +
         '- Python 3.12 (se non già presente)' + #13#10 +
         '- Tesseract OCR con supporto italiano (se non già presente)' + #13#10 +
         '- Tutte le librerie Python necessarie' + #13#10 +
         '- Il modello linguistico italiano per spaCy' + #13#10 + #13#10 +
         'Tutti i download vengono verificati con SHA256.' + #13#10 + #13#10 +
         'Richiede una connessione internet.' + #13#10 +
         'Tempo stimato: 10-15 minuti.', mbInformation, MB_OK);
end;
