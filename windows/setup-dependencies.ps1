# ============================================================
# Anonimizzatore PDF - Setup hardenato v$AppVersion (vedi sotto)
# Scarica e installa Python, Tesseract, librerie e modelli
#
# SICUREZZA:
# - URL ufficiali (no mirror non verificati)
# - SHA256 pinning per ogni download
# - $ErrorActionPreference = "Stop" (fail-fast)
# - Verifica integrità prima di eseguire qualsiasi binario
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$InstallPath,

    # H-01-R1 (#1): bypass esplicito per sviluppatori quando gli hash dei
    # binari di terze parti non sono ancora pinnati. NON usare in produzione.
    [switch]$DevMode,

    # VER-01: la versione la passa l'installer (installer.iss la conosce
    # già). Prima era scritta qui a mano ed era rimasta ferma alla 2.0.2:
    # i log della 2.1.1 si presentavano come "v2.0.2", facendo pensare
    # che sul server girasse ancora la versione vecchia.
    [string]$AppVersion = "sviluppo",

    # SIL-01: installazione silenziosa (/VERYSILENT). Niente finestre di
    # dialogo: in una sessione senza utente resterebbero aperte per sempre.
    [switch]$NonInterattivo
)

# I-02: fail-fast. Mai installare con setup parzialmente rotto.
$ErrorActionPreference = "Stop"

# ENV-01: se l'installer viene lanciato da una console PowerShell 7, la
# PowerShell 5.1 di questo script eredita il PSModulePath della 7 e non
# trova più i moduli di sistema: il setup si fermava con "Get-FileHash
# is not recognized". Emerso dal test su Windows reale. Si riparte dal
# PSModulePath di macchina, quello di un avvio normale.
if ($PSVersionTable.PSEdition -eq "Desktop" -and $env:PSModulePath -match "PowerShell\\7") {
    $env:PSModulePath = [Environment]::GetEnvironmentVariable("PSModulePath", "Machine")
}


# ============================================================
# CONFIGURAZIONE BINARI CON HASH PINNING
# ============================================================
#
# Hash SHA256 verificabili dalle fonti ufficiali:
# - Python: https://www.python.org/downloads/release/python-3128/
# - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
# - Tessdata: https://github.com/tesseract-ocr/tessdata
#
# Se Anthropic Anonimizzatore PDF rilascia una nuova versione, AGGIORNARE
# entrambi: URL e hash. Mai aggiornare solo l'URL.

$Binaries = @{
    Python = @{
        Url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        # SHA256 ufficiale verificato contro https://www.python.org/downloads/release/python-3128/
        # (cross-check con MD5 pubblicato 2f2ab2472a6aa29f8755c72c58f58f4b).
        # Riverificare prima del rilascio con:
        #   certutil -hashfile python-3.12.8-amd64.exe SHA256
        Sha256 = "71BD44E6B0E91C17558963557E4CDB80B483DE9B0A0A9717F06CF896F95AB598"
    }
    Tesseract = @{
        # URL UFFICIALE GitHub (NON il mirror universitario tedesco!)
        Url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
        # TODO(release): scaricare il file dall'URL sopra e pinnare l'hash con:
        #   Get-FileHash tesseract-ocr-w64-setup-5.4.0.20240606.exe -Algorithm SHA256
        # Il setup ora fallisce in produzione finché questo valore è il placeholder.
        Sha256 = "C885FFF6998E0608BA4BB8AB51436E1C6775C2BAFC2559A19B423E18678B60C9"
    }
    TessdataIta = @{
        # Tessdata ufficiale (mantained dal team Tesseract)
        Url = "https://github.com/tesseract-ocr/tessdata/raw/4.1.0/ita.traineddata"
        # TODO(release): pinnare l'hash del file servito al commit/tag 4.1.0.
        Sha256 = "4F7476C611312BEB8F8E182888DA08EA642D9824AE4402CC6235F61AB1406406"
    }
    SpacyModel = @{
        # MDL-01: wheel UFFICIALE del modello italiano (spacy-models su
        # GitHub). Era l'unico download SENZA hash pinning: passava da
        # "spacy download", che se il file arriva corrotto (rete
        # instabile, proxy, antivirus che tocca il temp) fallisce solo a
        # fine setup con "Wheel ... is invalid". Ora: download diretto,
        # verifica SHA256, retry, e pip install del file locale.
        # NB: la versione del modello (3.7.0) deve restare compatibile
        # col pin di spacy in $PythonPackages (>=3.7.0,<3.8.0).
        Url = "https://github.com/explosion/spacy-models/releases/download/it_core_news_lg-3.7.0/it_core_news_lg-3.7.0-py3-none-any.whl"
        # Verificato scaricando il wheel e testando l'archivio (zip integro):
        #   shasum -a 256 it_core_news_lg-3.7.0-py3-none-any.whl
        Sha256 = "F48BD152621C872C1F177DBE21929FBB28751E73EB3C61714CF6344C6D582BBF"
    }
}

# ============================================================
# LOGGING
# ============================================================

# PRM-01: verifica SUBITO i permessi di scrittura sull'InstallPath.
# Se lo script viene lanciato a mano da un prompt non elevato (visto
# succedere sul campo: pip che muore con "[WinError 5] Accesso negato"
# dentro Program Files), meglio un messaggio chiaro in italiano che un
# errore criptico a metà installazione.
$LogDir = Join-Path $InstallPath "logs"
try {
    New-Item -ItemType Directory -Force -Path $LogDir -ErrorAction Stop | Out-Null
    $probe = Join-Path $LogDir ".write-probe"
    Set-Content -Path $probe -Value "x" -ErrorAction Stop
    Remove-Item $probe -ErrorAction SilentlyContinue
} catch {
    Write-Host ""
    Write-Host "ERRORE: permessi insufficienti per scrivere in '$InstallPath'." -ForegroundColor Red
    Write-Host "Questo setup deve essere eseguito COME AMMINISTRATORE:" -ForegroundColor Red
    Write-Host " - usa l'installer AnonimizzatorePDF-Setup-vX.Y.Z.exe (doppio click, conferma UAC)," -ForegroundColor Red
    Write-Host " - oppure apri PowerShell con 'Esegui come amministratore' e rilancia lo script." -ForegroundColor Red
    Write-Host ""
    exit 1
}
$LogFile = Join-Path $LogDir "install-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogLine
    Write-Host $LogLine
}

function Show-Progress {
    param([string]$Message, [int]$PercentComplete)
    Write-Progress -Activity "Installazione Anonimizzatore PDF" `
        -Status $Message -PercentComplete $PercentComplete
    Write-Log $Message
}

# ============================================================
# ESECUZIONE COMANDI NATIVI (NAT-01)
# ============================================================
# In Windows PowerShell 5.1, con $ErrorActionPreference = "Stop", OGNI
# riga scritta su stderr da un comando nativo rediretto con 2>&1
# diventa un errore TERMINANTE (NativeCommandError). Conseguenze reali
# osservate sul campo:
#  - un "import" di prova fallito (comportamento atteso e gestito)
#    abortiva il setup mostrando solo "Traceback (most recent call
#    last):";
#  - un errore pip abortiva fuori dai retry con il testo grezzo di pip.
# Qui i comandi nativi girano con EAP locale "Continue": stdout+stderr
# finiscono nel log e il successo si giudica SOLO dall'exit code.

function Invoke-Native {
    param(
        [Parameter(Mandatory=$true)][string]$Exe,
        [string[]]$Arguments = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { "$_" } | Out-File -Append -FilePath $LogFile
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

# ============================================================
# DOWNLOAD CON VERIFICA INTEGRITÀ (H-01)
# ============================================================

function Download-VerifiedFile {
    param(
        [string]$Url,
        [string]$ExpectedSha256,
        [string]$DestinationPath,
        [string]$ComponentName
    )

    Write-Log "Download $ComponentName da $Url"

    try {
        # Forza TLS 1.2+ (Windows default può essere TLS 1.0)
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
        Invoke-WebRequest -Uri $Url -OutFile $DestinationPath -UseBasicParsing
    } catch {
        Write-Log "ERRORE download $ComponentName : $_" "ERROR"
        throw "Impossibile scaricare $ComponentName"
    }

    if (-not (Test-Path $DestinationPath)) {
        throw "File scaricato non trovato: $DestinationPath"
    }

    # H-01: VERIFICA HASH SHA256 OBBLIGATORIA
    Write-Log "Verifica hash SHA256 per $ComponentName"

    if ($ExpectedSha256 -eq "AGGIORNARE_AL_PRIMO_RILASCIO" -or [string]::IsNullOrEmpty($ExpectedSha256)) {
        # H-01-R1 (#1): fail-closed se l'hash non è pinnato. In dev mode
        # logghiamo l'hash effettivo per facilitare il pinning successivo.
        if (-not $script:DevMode) {
            $ActualHash = (Get-FileHash -Path $DestinationPath -Algorithm SHA256).Hash
            Write-Log "Hash placeholder per $ComponentName. Hash effettivo (da pinnare): $ActualHash" "ERROR"
            Remove-Item $DestinationPath -ErrorAction SilentlyContinue
            throw "Hash placeholder per $ComponentName. Aggiornare con valore reale prima del rilascio production (usare -DevMode per bypass esplicito in sviluppo)."
        }

        $ActualHash = (Get-FileHash -Path $DestinationPath -Algorithm SHA256).Hash
        Write-Log "DEV-MODE: hash bypass per $ComponentName. Hash effettivo: $ActualHash" "WARN"
        Write-Log "DEV-MODE: aggiungere questo hash in setup-dependencies.ps1 per il rilascio production" "WARN"
        return $true
    }

    $ActualHash = (Get-FileHash -Path $DestinationPath -Algorithm SHA256).Hash

    if ($ActualHash -ne $ExpectedSha256) {
        Write-Log "HASH MISMATCH per $ComponentName !" "ERROR"
        Write-Log "  Atteso:    $ExpectedSha256" "ERROR"
        Write-Log "  Effettivo: $ActualHash" "ERROR"
        Remove-Item $DestinationPath -ErrorAction SilentlyContinue
        throw "Verifica integrità fallita per $ComponentName. File rimosso. Possibile compromissione del download."
    }

    Write-Log "Hash SHA256 verificato per $ComponentName"
    return $true
}

# ============================================================
# 1. VERIFICA / INSTALLAZIONE PYTHON 3.12
# ============================================================

# PY-01: la ricerca di Python non può basarsi solo sul launcher "py".
# Se l'interprete è stato installato a mano, dallo Store o senza il
# launcher, "py -3.12" non lo trova: il setup credeva che Python
# mancasse, tentava di reinstallarlo e finiva in conflitto con quello
# già presente. Qui cerchiamo l'interprete in tutti i posti plausibili
# e ne restituiamo il PERCORSO, che poi viene usato ovunque.

# PY-04: gli "alias di esecuzione app" di Windows
# (%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe) sono segnaposto da
# zero byte, non interpreti. Test-Path li vede, ma eseguirli stampa
# "Failed to launch ... This may be a corrupt install or a system
# configuration issue": è il rumore che riempiva i log sul server.
function Test-AppExecutionAlias {
    param([string]$Percorso)
    return ($Percorso -like "*\AppData\Local\Microsoft\WindowsApps\*")
}

# PY-07: l'esito di "python.exe --version" CON il codice di uscita.
# Un python.exe può esistere e non partire — DLL mancanti, file
# troncato, bloccato da un criterio di sicurezza o dall'antivirus. La
# 2.1.1 guardava solo se il file c'era: un interprete presente ma rotto
# non veniva riconosciuto come guasto e la riparazione non partiva.
function Get-PythonVersione {
    param([string]$Percorso)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = (& $Percorso --version 2>&1 | Out-String).Trim()
        $codice = $LASTEXITCODE
    } catch {
        # Il processo non è nemmeno partito: il messaggio di Windows
        # ("file non trovato", "bloccato da criteri di gruppo"...) è
        # esattamente l'informazione che serve nel log.
        $out = $_.Exception.Message
        $codice = -1
    } finally {
        $ErrorActionPreference = $prevEap
    }
    return [PSCustomObject]@{ Codice = $codice; Output = $out }
}

function Test-PythonExe {
    param([string]$Percorso)
    if ([string]::IsNullOrWhiteSpace($Percorso) -or -not (Test-Path $Percorso)) {
        return $false
    }
    if (Test-AppExecutionAlias $Percorso) {
        return $false
    }
    return ((Get-PythonVersione $Percorso).Output -match "Python 3\.12")
}

# PY-07: il registro letto esplicitamente in ENTRAMBE le viste, a 64 e
# a 32 bit. Se lo script girasse in una PowerShell a 32 bit, la chiave
# HKLM:\SOFTWARE\Python verrebbe rediretta su WOW6432Node e una 3.12 a
# 64 bit resterebbe invisibile. Si legge prima ExecutablePath (PEP 514),
# poi la cartella di installazione.
function Get-RegistroPython312 {
    $trovati = @()
    foreach ($alveare in @([Microsoft.Win32.RegistryHive]::LocalMachine,
                           [Microsoft.Win32.RegistryHive]::CurrentUser)) {
        foreach ($vista in @([Microsoft.Win32.RegistryView]::Registry64,
                             [Microsoft.Win32.RegistryView]::Registry32)) {
            try {
                $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($alveare, $vista)
                foreach ($tag in @("3.12", "3.12-32")) {
                    $chiave = $base.OpenSubKey("SOFTWARE\Python\PythonCore\$tag\InstallPath")
                    if (-not $chiave) { continue }
                    $exe = $chiave.GetValue("ExecutablePath")
                    if (-not $exe) {
                        $dir = $chiave.GetValue("")
                        if ($dir) { $exe = Join-Path $dir "python.exe" }
                    }
                    if ($exe) { $trovati += "$exe" }
                    $chiave.Close()
                }
                $base.Close()
            } catch { }
        }
    }
    return @($trovati | Select-Object -Unique)
}

# Il launcher elenca le versioni note: "-V:3.12 *   C:\...\python.exe".
# Si cattura anche stderr: a seconda della versione del launcher
# l'elenco può finire lì, e con 2>$null andrebbe perso.
function Get-LauncherPython312 {
    $trovati = @()
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        foreach ($riga in (& py -0p 2>&1)) {
            if ("$riga" -match "3\.12.*?\s+([A-Za-z]:\\.*python\.exe)") {
                $trovati += $Matches[1].Trim()
            }
        }
    } catch { } finally { $ErrorActionPreference = $prevEap }
    return $trovati
}

# PY-05/PY-07: tutte le 3.12 che il sistema DICHIARA (registro,
# launcher, cartelle standard esistenti), ciascuna con il suo stato:
#   ok             → "--version" risponde Python 3.12
#   assente        → il file non c'è (registrazione residua, o file
#                    rimosso dall'antivirus se la cartella è rimasta)
#   non avviabile  → il file c'è ma non parte (installazione danneggiata
#                    o bloccata); Dettaglio riporta codice e messaggio
function Get-Python312Dichiarati {
    $dichiarati = @(Get-RegistroPython312) + @(Get-LauncherPython312)
    # Le cartelle standard contano solo se esistono: un avanzo di
    # installazione con dentro un python.exe rotto va diagnosticato.
    foreach ($radice in @($env:ProgramW6432, $env:ProgramFiles)) {
        if ([string]::IsNullOrWhiteSpace($radice)) { continue }
        $cartella = Join-Path $radice "Python312"
        if (Test-Path $cartella) { $dichiarati += (Join-Path $cartella "python.exe") }
    }

    $esiti = @()
    foreach ($exe in ($dichiarati | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-AppExecutionAlias $exe) { continue }
        $presente = Test-Path $exe
        $stato = "assente"
        $dettaglio = ""
        if ($presente) {
            $v = Get-PythonVersione $exe
            if ($v.Output -match "Python 3\.12") {
                $stato = "ok"
            } else {
                $stato = "non avviabile"
                $dettaglio = "codice $($v.Codice): $($v.Output)"
            }
        }
        $esiti += [PSCustomObject]@{
            Percorso         = $exe
            FilePresente     = $presente
            CartellaPresente = (Test-Path (Split-Path $exe -Parent))
            Stato            = $stato
            Dettaglio        = $dettaglio
        }
    }
    return $esiti
}

function Get-Python312Guasti {
    # Dichiarate ma non utilizzabili: assenti O non avviabili.
    return @(Get-Python312Dichiarati | Where-Object { $_.Stato -ne "ok" })
}

# PY-07: fotografia completa nel log. Due giri di diagnosi a distanza
# sono costati più del guasto: il prossimo log deve bastare da solo.
function Write-DiagnosiPython {
    $bit = if ([Environment]::Is64BitProcess) { "64" } else { "32" }
    Write-Log "Diagnosi Python: PowerShell $($PSVersionTable.PSVersion) a $bit bit"
    $tutti = @(Get-Python312Dichiarati)
    if ($tutti.Count -eq 0) {
        Write-Log "Diagnosi Python: nessuna 3.12 dichiarata da registro, launcher o cartelle standard" "WARN"
        return
    }
    foreach ($d in $tutti) {
        $extra = if ($d.Dettaglio) { " - $($d.Dettaglio)" } else { "" }
        Write-Log ("Diagnosi Python: $($d.Percorso) -> $($d.Stato)$extra " +
                   "(cartella presente: $($d.CartellaPresente))") "WARN"
    }
}

function Find-Python312 {
    param([switch]$Silenzioso)

    # 1. Launcher ufficiale
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $percorso = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and (Test-PythonExe $percorso)) {
            $ErrorActionPreference = $prevEap
            Write-Log "Python 3.12 trovato tramite launcher: $percorso"
            return "$percorso".Trim()
        }
    } catch { } finally { $ErrorActionPreference = $prevEap }

    # 2. Registro di sistema (per-macchina e per-utente, viste 64 e 32 bit)
    foreach ($exe in (Get-RegistroPython312)) {
        if (Test-PythonExe $exe) {
            Write-Log "Python 3.12 trovato nel registro: $exe"
            return $exe
        }
    }

    # 3. Percorsi d'installazione standard.
    #    Le basi si filtrano PRIMA di comporre il percorso: una variabile
    #    d'ambiente vuota (ProgramFiles(x86) su Windows a 32 bit,
    #    LOCALAPPDATA in certi contesti di servizio) farebbe fallire
    #    Join-Path e, con il fail-fast attivo, abortirebbe il setup.
    $candidati = @()
    foreach ($coppia in @(
        # ProgramW6432 punta sempre ai Program Files a 64 bit, anche da
        # una PowerShell a 32 bit (dove ProgramFiles diventa "(x86)")
        @($env:ProgramW6432,          "Python312\python.exe"),
        @($env:ProgramFiles,          "Python312\python.exe"),
        @(${env:ProgramFiles(x86)},   "Python312\python.exe"),
        @($env:LOCALAPPDATA,          "Programs\Python\Python312\python.exe")
    )) {
        if (-not [string]::IsNullOrWhiteSpace($coppia[0])) {
            $candidati += (Join-Path $coppia[0] $coppia[1])
        }
    }
    $candidati += "C:\Python312\python.exe"

    foreach ($exe in $candidati) {
        if (Test-PythonExe $exe) {
            Write-Log "Python 3.12 trovato in $exe"
            return $exe
        }
    }

    # 4. Un python.exe nel PATH che sia effettivamente 3.12
    try {
        foreach ($cmd in (Get-Command python.exe -All -ErrorAction SilentlyContinue)) {
            if (Test-PythonExe $cmd.Source) {
                Write-Log "Python 3.12 trovato nel PATH: $($cmd.Source)"
                return $cmd.Source
            }
        }
    } catch { }

    # PY-03: nessun 3.12 trovato. Registriamo quali Python esistono sul
    # sistema: se l'amministratore ne ha installato uno a mano ma di
    # versione diversa (3.13, 3.14...), il log lo dice esplicitamente
    # invece di lasciare intendere che Python manchi del tutto.
    if ($Silenzioso) { return $null }
    try {
        $altri = @()
        foreach ($cmd in (Get-Command python.exe, python3.exe -All -ErrorAction SilentlyContinue)) {
            if (Test-AppExecutionAlias $cmd.Source) { continue }   # PY-04
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            try { $v = (& $cmd.Source --version 2>&1 | Out-String).Trim() } catch { $v = "" }
            finally { $ErrorActionPreference = $prevEap }
            if ($v) { $altri += "$v ($($cmd.Source))" }
        }
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $elenco = (& py -0p 2>&1 | Out-String).Trim()
            if ($elenco) { $altri += "launcher py: $elenco" }
        } catch { } finally { $ErrorActionPreference = $prevEap }

        if ($altri.Count -gt 0) {
            Write-Log ("Python 3.12 non trovato. Altre versioni presenti sul sistema: " +
                       ($altri -join " | ") +
                       ". Serve specificamente la 3.12: le librerie usate " +
                       "dall'applicazione non hanno ancora pacchetti per le versioni successive.") "WARN"
        } else {
            Write-Log "Nessun interprete Python rilevato sul sistema" "WARN"
        }
    } catch { }

    return $null
}

function Invoke-PythonSetup {
    param(
        [string]$Installer,
        [ValidateSet("installa", "ripara", "disinstalla")]
        [string]$Modo = "installa"
    )

    # Un log per operazione: con un file unico ogni passaggio cancellava
    # il precedente, e proprio quello della riparazione fallita andava perso.
    $logPython = Join-Path $LogDir "python-$Modo.log"
    if ($Modo -eq "disinstalla") {
        $argomenti = @("/quiet", "/uninstall")
    } elseif ($Modo -eq "ripara") {
        $argomenti = @("/quiet", "/repair")
    } else {
        $argomenti = @(
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_test=0",
            "Include_launcher=1",
            "InstallLauncherAllUsers=1"
        )
    }
    # PY-02: log dell'installer Python, utile quando fallisce sul campo.
    # PY-08: il percorso va tra virgolette. Start-Process unisce gli
    # argomenti con uno spazio senza quotarli: "C:\Program Files\..."
    # arrivava all'installer spezzato in due ("C:\Program" e il resto),
    # il log finiva in un file C:\Program e quello indicato nel
    # messaggio d'errore non esisteva. Emerso dal test su Windows reale.
    $argomenti += "/log"
    $argomenti += "`"$logPython`""

    $cronometro = [System.Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $Installer -ArgumentList $argomenti -Wait -PassThru
    $codice = $process.ExitCode
    # Un'installazione vera richiede decine di secondi: un "successo" in
    # 3-4 secondi significa che l'installer ha creduto Python già
    # presente e non ha scritto nulla. Il tempo nel log lo rende evidente.
    Write-Log "Installer Python ($Modo) terminato: codice $codice in $([int]$cronometro.Elapsed.TotalSeconds) s"

    # Riparazione e disinstallazione sono tentativi: l'esito vero si
    # misura subito dopo, cercando un interprete che funzioni.
    if ($Modo -ne "installa") { return }

    # PY-02: non tutti i codici diversi da 0 sono errori.
    #  3010 = riuscito, richiede riavvio (prima faceva fallire il setup!)
    #  1638 = un'altra versione è già installata: non è un problema,
    #         basta usare quella (la cerchiamo subito dopo).
    switch ($codice) {
        0     { Write-Log "Python 3.12 installato con successo" }
        3010  { Write-Log "Python 3.12 installato (il sistema richiede un riavvio)" "WARN" }
        1638  { Write-Log "Una versione di Python 3.12 risulta già installata: uso quella" "WARN" }
        default {
            $spiegazione = switch ($codice) {
                1602 { "installazione annullata dall'utente" }
                1603 { "errore fatale dell'installer (spesso: Python già presente in una variante diversa, o permessi)" }
                1618 { "un'altra installazione è già in corso: attendere e riprovare" }
                default { "codice non documentato" }
            }
            Write-Log "ERRORE installazione Python (codice $codice - $spiegazione)" "ERROR"
            Write-Log "Log dell'installer Python: $logPython" "ERROR"
            throw ("Installazione Python fallita (codice $codice - $spiegazione). " +
                   "Dettagli in $logPython")
        }
    }
}

function Update-PathCorrente {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Install-Python {
    Show-Progress "Download Python 3.12..." 10

    $pythonInstaller = Join-Path $env:TEMP "python-3.12.8-amd64.exe"

    Download-VerifiedFile `
        -Url $Binaries.Python.Url `
        -ExpectedSha256 $Binaries.Python.Sha256 `
        -DestinationPath $pythonInstaller `
        -ComponentName "Python 3.12"

    Show-Progress "Installazione Python 3.12 in corso..." 20
    Invoke-PythonSetup -Installer $pythonInstaller -Modo installa
    Update-PathCorrente

    # PY-06/PY-07/PY-09: se dopo l'installazione l'interprete non c'è,
    # parte la riparazione automatica — sempre, a prescindere dalla
    # diagnosi (subordinarla a una diagnosi l'aveva resa inefficace sul
    # server). Non si rischia di toccare un Python funzionante: se ce ne
    # fosse uno, Find-Python312 lo avrebbe trovato.
    #
    # PY-09: prima /repair, poi disinstalla e reinstalla. Il test su
    # Windows reale ha mostrato che quando la cartella di Python è stata
    # cancellata (il caso del server) Windows Installer considera i
    # pacchetti ancora "presenti": la reinstallazione diventa una
    # modifica che non scrive nulla e la disinstallazione fallisce con
    # 1603. Solo la riparazione riscrive i file mancanti. La sequenza
    # disinstalla+reinstalla resta per i casi in cui la riparazione
    # non basta (python.exe presente ma danneggiato).
    if (-not (Find-Python312 -Silenzioso)) {
        Write-Log "Python 3.12 non utilizzabile dopo l'installazione: avvio la riparazione automatica" "WARN"
        Write-DiagnosiPython

        Show-Progress "Riparazione di Python 3.12..." 24
        Invoke-PythonSetup -Installer $pythonInstaller -Modo ripara
        Update-PathCorrente

        if (Find-Python312 -Silenzioso) {
            Write-Log "Riparazione riuscita"
        } else {
            Write-Log "La riparazione non basta: disinstallo e reinstallo Python 3.12" "WARN"
            Write-DiagnosiPython
            Show-Progress "Pulizia di un'installazione Python incompleta..." 26
            Invoke-PythonSetup -Installer $pythonInstaller -Modo disinstalla
            Update-PathCorrente
            Show-Progress "Reinstallazione di Python 3.12..." 28
            Invoke-PythonSetup -Installer $pythonInstaller -Modo installa
            Update-PathCorrente
        }
    }

    Remove-Item $pythonInstaller -ErrorAction SilentlyContinue
}

# ============================================================
# 2. VERIFICA / INSTALLAZIONE TESSERACT OCR
# ============================================================

function Test-TesseractInstalled {
    # L-02: cerchiamo SOLO nei path di sistema, non in %LOCALAPPDATA%
    # per evitare path hijacking
    $tesseractPaths = @(
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    )
    foreach ($path in $tesseractPaths) {
        if (Test-Path $path) {
            Write-Log "Tesseract già installato in $path"
            $tessdata = Split-Path $path
            $itaPath = Join-Path $tessdata "tessdata\ita.traineddata"
            if (Test-Path $itaPath) {
                Write-Log "Lingua italiana Tesseract presente"
                return $true
            } else {
                Write-Log "Tesseract presente ma lingua italiana mancante" "WARN"
                Install-TesseractItalian -TessdataPath (Join-Path $tessdata "tessdata")
                return $true
            }
        }
    }
    return $false
}

function Install-TesseractItalian {
    param([string]$TessdataPath)

    Show-Progress "Download lingua italiana per Tesseract..." 45

    $itaFile = Join-Path $TessdataPath "ita.traineddata"

    Download-VerifiedFile `
        -Url $Binaries.TessdataIta.Url `
        -ExpectedSha256 $Binaries.TessdataIta.Sha256 `
        -DestinationPath $itaFile `
        -ComponentName "Tessdata italiano"
}

function Install-Tesseract {
    Show-Progress "Download Tesseract OCR..." 30

    $tesseractInstaller = Join-Path $env:TEMP "tesseract-installer.exe"

    Download-VerifiedFile `
        -Url $Binaries.Tesseract.Url `
        -ExpectedSha256 $Binaries.Tesseract.Sha256 `
        -DestinationPath $tesseractInstaller `
        -ComponentName "Tesseract OCR"

    Show-Progress "Installazione Tesseract OCR..." 40

    $process = Start-Process -FilePath $tesseractInstaller `
        -ArgumentList "/S" -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Log "ERRORE installazione Tesseract (codice $($process.ExitCode))" "ERROR"
        throw "Installazione Tesseract fallita"
    }

    Write-Log "Tesseract installato con successo"

    $tessdataPath = "C:\Program Files\Tesseract-OCR\tessdata"
    if (Test-Path $tessdataPath) {
        $itaPath = Join-Path $tessdataPath "ita.traineddata"
        if (-not (Test-Path $itaPath)) {
            Install-TesseractItalian -TessdataPath $tessdataPath
        }
    } else {
        Write-Log "Tessdata directory non trovata dopo installazione" "WARN"
    }

    Remove-Item $tesseractInstaller -ErrorAction SilentlyContinue
}

# ============================================================
# 3. CREAZIONE VENV E INSTALLAZIONE PACCHETTI
# ============================================================

# Versioni pinnate con minimum security floor:
# - Pillow >= 10.2.0: fix CVE-2023-50447 (ImageMath.eval RCE)
# - streamlit >= 1.37.0: fix CVE-2024-42474 (path traversal Windows)
# I-01: presidio-anonymizer rimosso (non usato, redazione fatta da PyMuPDF)
$script:PythonPackages = @(
    "streamlit>=1.37.0,<2.0.0",
    "pymupdf>=1.24.0,<2.0.0",
    "presidio-analyzer>=2.2.0,<3.0.0",
    "spacy>=3.7.0,<3.8.0",
    "pytesseract>=0.3.10,<1.0.0",
    "Pillow>=10.2.0,<12.0.0"
)

# UPD-01: fingerprint delle dipendenze per aggiornamenti rapidi.
# Se il venv esiste, importa i moduli chiave e la lista pacchetti non è
# cambiata dall'ultima installazione, saltiamo la ricreazione: un
# aggiornamento di versione dell'app passa così da ~15 minuti a ~1.
function Get-DepsFingerprintPath {
    return Join-Path $InstallPath ".deps-fingerprint"
}

# Fingerprint canonico: pacchetti ordinati, join con LF singolo. Rendiamo
# il confronto insensibile ai fine-riga (Set-Content scrive CRLF su
# Windows) normalizzando CRLF→LF, altrimenti il fingerprint non
# combacerebbe mai e il venv verrebbe ricreato a ogni aggiornamento.
function Get-DepsFingerprint {
    return (($script:PythonPackages | Sort-Object) -join "`n")
}

function Normalize-Newlines {
    param([string]$Text)
    return ($Text -replace "`r`n", "`n").Trim()
}

function Test-PythonEnvironmentCurrent {
    $venvPath = Join-Path $InstallPath "venv"
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) { return $false }

    $fingerprintFile = Get-DepsFingerprintPath
    if (-not (Test-Path $fingerprintFile)) {
        Write-Log "Venv presente ma senza fingerprint (installazione pre-1.4): ricreo"
        return $false
    }
    $stored = Normalize-Newlines (Get-Content $fingerprintFile -Raw)
    $current = Normalize-Newlines (Get-DepsFingerprint)
    if ($stored -ne $current) {
        Write-Log "Le dipendenze sono cambiate rispetto all'installazione precedente: ricreo il venv"
        return $false
    }

    # Sanity check: i moduli chiave devono essere importabili
    # (NAT-01: può legittimamente fallire, non deve abortire il setup)
    $code = Invoke-Native -Exe $pythonExe -Arguments @(
        "-c", "import streamlit, fitz, pytesseract; from presidio_analyzer import AnalyzerEngine"
    )
    if ($code -ne 0) {
        Write-Log "Venv presente ma moduli non importabili: ricreo" "WARN"
        return $false
    }

    Write-Log "Ambiente Python già aggiornato: salto la reinstallazione delle librerie"
    return $true
}

function Setup-PythonEnvironment {
    Show-Progress "Creazione ambiente virtuale Python..." 55

    $venvPath = Join-Path $InstallPath "venv"

    if (Test-Path $venvPath) {
        Remove-Item -Path $venvPath -Recurse -Force
    }
    Remove-Item (Get-DepsFingerprintPath) -ErrorAction SilentlyContinue

    # PY-01: si usa l'interprete individuato da Find-Python312, non "py"
    $code = Invoke-Native -Exe $script:PythonExe -Arguments @("-m", "venv", $venvPath)
    if ($code -ne 0) {
        throw "Creazione venv fallita"
    }

    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    $pipExe = Join-Path $venvPath "Scripts\pip.exe"

    Show-Progress "Aggiornamento pip..." 60
    $code = Invoke-Native -Exe $pythonExe -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    if ($code -ne 0) {
        throw "Aggiornamento pip fallito"
    }

    Show-Progress "Installazione librerie Python..." 65

    $pipArgs = @("install", "--only-binary=:all:", "--no-cache-dir") + $script:PythonPackages
    $code = Invoke-Native -Exe $pipExe -Arguments $pipArgs
    if ($code -ne 0) {
        throw "Installazione pacchetti pip fallita - vedi $LogFile"
    }

    # UPD-01: fingerprint scritto SOLO a installazione riuscita
    Get-DepsFingerprint | Set-Content -Path (Get-DepsFingerprintPath)

    Write-Log "Pacchetti Python installati con successo"
}

# ============================================================
# 4. DOWNLOAD MODELLO LINGUISTICO ITALIANO
# ============================================================

function Test-SpacyModelInstalled {
    # UPD-01: se il modello è già importabile non riscarichiamo 580 MB
    $pythonExe = Join-Path $InstallPath "venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) { return $false }
    # NAT-01: questo import DEVE poter fallire senza abortire il setup —
    # su Windows PowerShell 5.1 il traceback su stderr diventava un
    # errore fatale ("Traceback (most recent call last):" e stop).
    $code = Invoke-Native -Exe $pythonExe -Arguments @("-c", "import it_core_news_lg")
    if ($code -eq 0) {
        Write-Log "Modello linguistico italiano già presente: salto il download"
        return $true
    }
    return $false
}

function Remove-SpacyModelLeftovers {
    # PRM-02: installazioni precedenti fallite a metà (download corrotto,
    # permessi, antivirus) possono lasciare in site-packages directory
    # parziali di it_core_news_lg che fanno fallire anche i tentativi
    # successivi ("[WinError 5] Accesso negato" su file bloccati o
    # read-only). Le rimuoviamo prima di riprovare.
    $sitePackages = Join-Path $InstallPath "venv\Lib\site-packages"
    if (-not (Test-Path $sitePackages)) { return }
    foreach ($pattern in @("it_core_news_lg", "it_core_news_lg-*")) {
        Get-ChildItem -Path $sitePackages -Filter $pattern -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                Write-Log "Rimuovo residuo di installazione precedente: $($_.FullName)" "WARN"
                # Toglie eventuali attributi read-only che bloccano la rimozione
                Get-ChildItem -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.Attributes = "Normal" }
                Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
    }
}

function Install-SpacyModel {
    # MDL-01: download diretto del wheel con hash pinning e retry,
    # al posto di "spacy download" (nessuna verifica d'integrità e
    # diagnosi pessima in caso di file corrotto).
    $pipExe = Join-Path $InstallPath "venv\Scripts\pip.exe"
    $wheelPath = Join-Path $env:TEMP "it_core_news_lg-3.7.0-py3-none-any.whl"

    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        Show-Progress "Download modello linguistico italiano (~580 MB, tentativo $attempt/$maxAttempts)..." 80

        try {
            # Download-VerifiedFile fallisce (e rimuove il file) se lo
            # SHA256 non corrisponde: un download troncato/corrotto
            # viene rilevato QUI, non a fine installazione.
            Download-VerifiedFile `
                -Url $Binaries.SpacyModel.Url `
                -ExpectedSha256 $Binaries.SpacyModel.Sha256 `
                -DestinationPath $wheelPath `
                -ComponentName "Modello linguistico it_core_news_lg"
        } catch {
            Write-Log "Tentativo $attempt fallito: $_" "WARN"
            if ($attempt -eq $maxAttempts) {
                throw "Download modello italiano fallito dopo $maxAttempts tentativi - verifica connessione internet/proxy/antivirus"
            }
            Start-Sleep -Seconds 5
            continue
        }

        Show-Progress "Installazione modello linguistico..." 90
        # PRM-02: via i residui di tentativi precedenti prima di installare
        Remove-SpacyModelLeftovers
        $code = Invoke-Native -Exe $pipExe -Arguments @("install", "--no-cache-dir", "--force-reinstall", "--no-deps", $wheelPath)
        if ($code -eq 0) {
            Remove-Item $wheelPath -ErrorAction SilentlyContinue
            Write-Log "Modello linguistico italiano installato"
            return
        }

        Write-Log "pip install del modello fallito al tentativo $attempt" "WARN"
        Remove-Item $wheelPath -ErrorAction SilentlyContinue
        if ($attempt -eq $maxAttempts) {
            throw "Installazione modello italiano fallita dopo $maxAttempts tentativi - vedi $LogFile"
        }
        Start-Sleep -Seconds 5
    }
}

# ============================================================
# 5. VERIFICA FINALE
# ============================================================

function Verify-Installation {
    Show-Progress "Verifica installazione..." 95

    $pythonExe = Join-Path $InstallPath "venv\Scripts\python.exe"

    # Verifica che tutti i moduli siano importabili
    $verifyScript = @"
import sys
try:
    import streamlit, fitz, pytesseract, spacy
    from presidio_analyzer import AnalyzerEngine
    from PIL import Image
    nlp = spacy.load('it_core_news_lg')
    print('OK: tutti i componenti caricati correttamente')
    sys.exit(0)
except Exception as e:
    print(f'ERRORE: {type(e).__name__}: {e}')
    sys.exit(1)
"@

    # NAT-01: anche qui il giudizio è SOLO sull'exit code; l'output
    # completo (incluso l'eventuale traceback) finisce nel log.
    $code = Invoke-Native -Exe $pythonExe -Arguments @("-c", $verifyScript)
    if ($code -ne 0) {
        throw "Verifica installazione fallita. Setup non completato correttamente - vedi $LogFile"
    }
    Write-Log "Verifica finale superata: tutti i componenti caricati"
}

# ============================================================
# MAIN
# ============================================================

try {
    Add-Type -AssemblyName System.Windows.Forms

    Write-Log "===== INIZIO SETUP ANONIMIZZATORE PDF v$AppVersion ====="
    Write-Log "Path installazione: $InstallPath"

    # 1. Python (PY-01: si cerca ovunque, si installa solo se manca davvero)
    $script:PythonExe = Find-Python312
    if (-not $script:PythonExe) {
        Write-Log "Python 3.12 non presente: procedo con l'installazione"
        Install-Python
        $script:PythonExe = Find-Python312
        if (-not $script:PythonExe) {
            # PY-05/PY-07: il messaggio deve dire la causa vera, non
            # mandare l'amministratore a riavviare il server a vuoto.
            Write-DiagnosiPython
            $guasti = Get-Python312Guasti
            $rimedio = (" Rimedio manuale: scarica python-3.12.8-amd64.exe da " +
                        "python.org, eseguilo e scegli Repair; poi rilancia questo setup.")
            if ($guasti.Count -gt 0) {
                $g = $guasti[0]
                if ($g.Stato -eq "non avviabile") {
                    $causa = ("$($g.Percorso) esiste ma non si avvia ($($g.Dettaglio)). " +
                              "L'installazione è danneggiata, oppure un antivirus o un " +
                              "criterio di sicurezza ne blocca l'esecuzione. Il setup ha già " +
                              "provato a reinstallarla senza riuscirci." + $rimedio)
                } elseif ($g.CartellaPresente) {
                    $causa = ("Windows dichiara Python 3.12 in $($g.Percorso): la cartella c'è " +
                              "ma python.exe no. Di norma significa che un antivirus lo ha messo " +
                              "in quarantena: controlla la cronologia delle protezioni di " +
                              "Microsoft Defender, ripristina il file o escludi la cartella, " +
                              "poi rilancia il setup.")
                } else {
                    $causa = ("Windows dichiara Python 3.12 in $($g.Percorso), ma quella cartella " +
                              "non esiste: è una registrazione rimasta da un'installazione " +
                              "rimossa a mano, e il setup non è riuscito a ripulirla." + $rimedio)
                }
            } else {
                $causa = ("L'installer di Python non ha lasciato un interprete utilizzabile." +
                          $rimedio)
            }
            throw ("Python 3.12 risulta installato ma non è utilizzabile. " +
                   $causa + " Dettagli nei log in $LogDir")
        }
    }
    Write-Log "Interprete Python in uso: $script:PythonExe"

    # 2. Tesseract
    if (-not (Test-TesseractInstalled)) {
        Install-Tesseract
    }

    # 3. Venv + pacchetti (saltato se già aggiornato — UPD-01)
    if (-not (Test-PythonEnvironmentCurrent)) {
        Setup-PythonEnvironment
    }

    # 4. Modello spaCy (saltato se già presente — UPD-01)
    if (-not (Test-SpacyModelInstalled)) {
        Install-SpacyModel
    }

    # 5. Verifica finale (NUOVA - I-02)
    Verify-Installation

    Show-Progress "Installazione completata!" 100
    Write-Log "===== SETUP COMPLETATO CON SUCCESSO ====="
    Start-Sleep -Seconds 2

    Write-Progress -Activity "Installazione" -Completed

    if (-not $NonInterattivo) {
    [System.Windows.Forms.MessageBox]::Show(
        "Anonimizzatore PDF v$AppVersion installato correttamente!`n`n" +
        "Tutti i componenti sono stati verificati.`n`n" +
        "Avvialo dal collegamento sul Desktop o dal Menu Start.",
        "Installazione completata",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    }

    exit 0

} catch {
    Write-Log "ERRORE FATALE: $_" "ERROR"
    Write-Log "Stack: $($_.ScriptStackTrace)" "ERROR"

    if (-not $NonInterattivo) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Errore durante l'installazione:`n`n$_`n`n" +
        "Log dettagliato salvato in:`n$LogFile`n`n" +
        "L'installazione NON è andata a buon fine. " +
        "Disinstalla e riprova, o contatta l'assistenza.",
        "Errore",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    }

    exit 1
}
