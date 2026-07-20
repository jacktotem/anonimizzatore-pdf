# ============================================================
# Anonimizzatore PDF — Rimozione modalità SERVER CONDIVISO
#
# Ferma e rimuove l'attività pianificata e il collegamento sul
# desktop pubblico. NON disinstalla l'app (per quella usare
# "Installazione applicazioni" di Windows).
#
# USO (PowerShell come Amministratore):
#   .\rimuovi-server.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$TaskName = "AnonimizzatorePDF Server"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRORE: eseguire questo script da PowerShell come Amministratore." -ForegroundColor Red
    exit 1
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Attività pianificata '$TaskName' rimossa." -ForegroundColor Green
} else {
    Write-Host "Nessuna attività '$TaskName' trovata." -ForegroundColor Yellow
}

$ShortcutPath = "$env:PUBLIC\Desktop\Anonimizzatore PDF.url"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Collegamento rimosso dal desktop pubblico." -ForegroundColor Green
}

Write-Host "Fatto."
