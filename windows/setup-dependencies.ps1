# ============================================================
# Setup automatico Anonimizzatore PDF
# Scarica e installa Python, Tesseract, librerie e modelli
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$InstallPath
)

$ErrorActionPreference = "Continue"

# Path dei log
$LogDir = Join-Path $InstallPath "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
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
    
    $pythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $pythonInstaller = Join-Path $env:TEMP "python-3.12.8-amd64.exe"
    
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
        Write-Log "Python installer scaricato in $pythonInstaller"
    } catch {
        Write-Log "ERRORE download Python: $_" "ERROR"
        throw "Impossibile scaricare Python da $pythonUrl"
    }
    
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
    $itaUrl = "https://github.com/tesseract-ocr/tessdata/raw/main/ita.traineddata"
    $itaFile = Join-Path $TessdataPath "ita.traineddata"
    try {
        Invoke-WebRequest -Uri $itaUrl -OutFile $itaFile -UseBasicParsing
        Write-Log "Lingua italiana Tesseract installata"
    } catch {
        Write-Log "ERRORE download lingua italiana: $_" "ERROR"
    }
}

function Install-Tesseract {
    Show-Progress "Download Tesseract OCR..." 30
    
    $tesseractUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
    $tesseractInstaller = Join-Path $env:TEMP "tesseract-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $tesseractUrl -OutFile $tesseractInstaller -UseBasicParsing
        Write-Log "Tesseract installer scaricato"
    } catch {
        Write-Log "ERRORE download Tesseract: $_" "ERROR"
        Write-Log "L'app funzionerà solo con PDF testuali" "WARN"
        return
    }
    
    Show-Progress "Installazione Tesseract OCR con supporto italiano..." 40
    
    $process = Start-Process -FilePath $tesseractInstaller `
        -ArgumentList "/S" -Wait -PassThru
    
    if ($process.ExitCode -ne 0) {
        Write-Log "ERRORE installazione Tesseract (codice $($process.ExitCode))" "WARN"
    } else {
        Write-Log "Tesseract installato con successo"
        $tessdataPath = "C:\Program Files\Tesseract-OCR\tessdata"
        if (Test-Path $tessdataPath) {
            $itaPath = Join-Path $tessdataPath "ita.traineddata"
            if (-not (Test-Path $itaPath)) {
                Install-TesseractItalian -TessdataPath $tessdataPath
            }
        }
    }
    
    Remove-Item $tesseractInstaller -ErrorAction SilentlyContinue
}

# ============================================================
# 3. CREAZIONE VENV E INSTALLAZIONE PACCHETTI
# ============================================================

function Setup-PythonEnvironment {
    Show-Progress "Creazione ambiente virtuale Python..." 55
    
    $venvPath = Join-Path $InstallPath "venv"
    
    if (Test-Path $venvPath) {
        Remove-Item -Path $venvPath -Recurse -Force
    }
    
    & py -3.12 -m venv $venvPath 2>&1 | Out-File -Append $LogFile
    if ($LASTEXITCODE -ne 0) {
        throw "Creazione venv fallita"
    }
    
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    $pipExe = Join-Path $venvPath "Scripts\pip.exe"
    
    Show-Progress "Aggiornamento pip..." 60
    & $pythonExe -m pip install --upgrade pip setuptools wheel 2>&1 | Out-File -Append $LogFile
    
    Show-Progress "Installazione librerie Python (può richiedere alcuni minuti)..." 65
    
    $packages = @(
        "streamlit>=1.30.0",
        "pymupdf>=1.23.0",
        "presidio-analyzer>=2.2.0",
        "presidio-anonymizer>=2.2.0",
        "spacy>=3.7.0,<3.8.0",
        "pytesseract>=0.3.10",
        "Pillow>=10.0.0"
    )
    
    & $pipExe install --only-binary=:all: @packages 2>&1 | Out-File -Append $LogFile
    if ($LASTEXITCODE -ne 0) {
        throw "Installazione pacchetti pip fallita - vedi $LogFile"
    }
    
    Write-Log "Pacchetti Python installati con successo"
}

# ============================================================
# 4. DOWNLOAD MODELLO LINGUISTICO ITALIANO
# ============================================================

function Install-SpacyModel {
    Show-Progress "Download modello linguistico italiano (~580 MB)..." 80
    
    $pythonExe = Join-Path $InstallPath "venv\Scripts\python.exe"
    & $pythonExe -m spacy download it_core_news_lg 2>&1 | Out-File -Append $LogFile
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERRORE download modello spaCy" "ERROR"
        throw "Download modello italiano fallito - verifica connessione internet"
    }
    
    Write-Log "Modello linguistico italiano installato"
}

# ============================================================
# MAIN
# ============================================================

try {
    Add-Type -AssemblyName System.Windows.Forms
    
    Write-Log "===== INIZIO SETUP ANONIMIZZATORE PDF ====="
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
    
    # 3. Venv + pacchetti
    Setup-PythonEnvironment
    
    # 4. Modello spaCy
    Install-SpacyModel
    
    Show-Progress "Installazione completata!" 100
    Write-Log "===== SETUP COMPLETATO CON SUCCESSO ====="
    Start-Sleep -Seconds 2
    
    Write-Progress -Activity "Installazione" -Completed
    
    [System.Windows.Forms.MessageBox]::Show(
        "Anonimizzatore PDF installato correttamente!`n`n" +
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
        "Log dettagliato salvato in:`n$LogFile",
        "Errore",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    
    exit 1
}
