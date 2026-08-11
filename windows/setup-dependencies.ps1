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
    [switch]$DevMode
)

# I-02: fail-fast. Mai installare con setup parzialmente rotto.
$ErrorActionPreference = "Stop"

# N-05 (#9): single source of truth per la versione mostrata all'utente.
# Long-term: leggere da un file VERSION in repo root condiviso con
# installer.iss e src/app.py.
$AppVersion = "2.0.1"

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

function Test-PythonInstalled {
    try {
        $version = & py -3.12 --version 2>&1
        if ($version -match "Python 3\.12") {
            Write-Log "Python 3.12 già installato: $version"
            return $true
        }
    } catch { }
    return $false
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

    $pythonArgs = @(
        "/quiet",
        "InstallAllUsers=1",
        "PrependPath=1",
        "Include_test=0",
        "Include_launcher=1",
        "InstallLauncherAllUsers=1"
    )

    $process = Start-Process -FilePath $pythonInstaller -ArgumentList $pythonArgs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Log "ERRORE installazione Python (codice $($process.ExitCode))" "ERROR"
        throw "Installazione Python fallita"
    }

    # Refresh PATH per la sessione corrente
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Log "Python 3.12 installato con successo"
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

    $code = Invoke-Native -Exe "py" -Arguments @("-3.12", "-m", "venv", $venvPath)
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

    # 1. Python
    if (-not (Test-PythonInstalled)) {
        Install-Python
        if (-not (Test-PythonInstalled)) {
            throw "Python non disponibile dopo l'installazione"
        }
    }

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

    [System.Windows.Forms.MessageBox]::Show(
        "Anonimizzatore PDF v$AppVersion installato correttamente!`n`n" +
        "Tutti i componenti sono stati verificati.`n`n" +
        "Avvialo dal collegamento sul Desktop o dal Menu Start.",
        "Installazione completata",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null

    exit 0

} catch {
    Write-Log "ERRORE FATALE: $_" "ERROR"
    Write-Log "Stack: $($_.ScriptStackTrace)" "ERROR"

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

    exit 1
}
