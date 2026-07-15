# ============================================================
# Anonimizzatore PDF — Configurazione modalità SERVER CONDIVISO
#
# Per server Windows multiutente (desktop remoto / RDS): registra
# l'app come attività pianificata che parte all'avvio del server,
# come ISTANZA UNICA condivisa da tutte le sessioni utente.
#
# Gli utenti la usano aprendo il browser su http://localhost:8501
# (collegamento creato automaticamente sul desktop pubblico).
#
# PREREQUISITO: l'app deve essere già installata con
# AnonimizzatorePDF-Setup-vX.Y.Z.exe (che configura Python,
# Tesseract e le dipendenze).
#
# SICUREZZA:
# - L'app è vincolata a 127.0.0.1: raggiungibile SOLO dalle
#   sessioni desktop remoto sul server stesso. Nessuna porta
#   esposta in rete, nessuna regola firewall necessaria.
# - I documenti restano sul server dello studio.
#
# USO (PowerShell come Amministratore):
#   .\configura-server.ps1
#   .\configura-server.ps1 -InstallPath "D:\Apps\AnonimizzatorePDF"
#   .\configura-server.ps1 -Port 8600
# ============================================================

param(
    [string]$InstallPath = "$env:ProgramFiles\AnonimizzatorePDF",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$TaskName = "AnonimizzatorePDF Server"

# --- Verifica privilegi amministratore ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRORE: eseguire questo script da PowerShell come Amministratore." -ForegroundColor Red
    exit 1
}

# --- Verifica installazione esistente ---
$PythonExe = Join-Path $InstallPath "venv\Scripts\python.exe"
$AppPy     = Join-Path $InstallPath "app.py"

if (-not (Test-Path $PythonExe) -or -not (Test-Path $AppPy)) {
    Write-Host "ERRORE: installazione non trovata in '$InstallPath'." -ForegroundColor Red
    Write-Host "Installare prima l'app con AnonimizzatorePDF-Setup-vX.Y.Z.exe," -ForegroundColor Red
    Write-Host "oppure indicare il percorso corretto con -InstallPath." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Anonimizzatore PDF — modalità server" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Installazione : $InstallPath"
Write-Host " Porta (locale): $Port"
Write-Host ""

# --- Rimuovi eventuale attività precedente ---
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Attività esistente trovata: la sostituisco..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# --- Registra l'attività pianificata (istanza unica all'avvio) ---
$StreamlitArgs = @(
    "-m", "streamlit", "run", "app.py",
    "--server.headless", "true",
    "--server.address", "127.0.0.1",          # SOLO sessioni locali del server
    "--server.port", "$Port",
    "--browser.gatherUsageStats", "false"
) -join " "

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument $StreamlitArgs `
    -WorkingDirectory $InstallPath

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

# SYSTEM: l'app parte senza che nessun utente debba fare login
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Anonimizzatore PDF in modalità server condiviso (istanza unica su http://localhost:$Port per tutte le sessioni desktop remoto)." | Out-Null

Write-Host "Attività pianificata '$TaskName' registrata (avvio automatico col server)." -ForegroundColor Green

# --- Avvia subito e verifica lo stato di salute ---
Write-Host "Avvio in corso..."
Start-ScheduledTask -TaskName $TaskName

$healthy = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/_stcore/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}

if ($healthy) {
    Write-Host "L'app risponde su http://localhost:$Port" -ForegroundColor Green
} else {
    Write-Host "ATTENZIONE: l'app non risponde ancora su http://localhost:$Port." -ForegroundColor Yellow
    Write-Host "Al primo avvio il caricamento del modello linguistico può richiedere 1-2 minuti."
    Write-Host "Verificare tra qualche minuto; in caso di problemi vedere README-SERVER.md."
}

# --- Collegamento sul desktop pubblico (visibile a tutti gli utenti) ---
$ShortcutPath = "$env:PUBLIC\Desktop\Anonimizzatore PDF.url"
@"
[InternetShortcut]
URL=http://localhost:$Port
IconFile=%SystemRoot%\System32\SHELL32.dll
IconIndex=48
"@ | Set-Content -Path $ShortcutPath -Encoding ASCII
Write-Host "Collegamento creato sul desktop pubblico: 'Anonimizzatore PDF'." -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Configurazione completata." -ForegroundColor Cyan
Write-Host " Gli utenti aprono: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
