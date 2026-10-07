# ============================================================
# Test della ricerca di Python 3.12 (PY-04 / PY-05 / PY-07)
#
# Uso:  pwsh -NoProfile -File windows/tests/test-python-discovery.ps1
#
# Gira su qualsiasi piattaforma: carica SOLO le definizioni di funzione
# di setup-dependencies.ps1 (via AST, senza eseguire il setup) e
# sostituisce registro, launcher "py" e interprete con dei finti.
#
# Riproduce i guasti visti sul server di Advais: Windows dichiarava una
# 3.12 in C:\Program Files\Python312 che non era utilizzabile, e
# l'installer ufficiale la considerava già presente uscendo con 0 in
# pochi secondi senza scrivere nulla.
# ============================================================
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path ./windows/setup-dependencies.ps1), [ref]$null, [ref]$null)
$funzioni = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)
foreach ($f in $funzioni) { Invoke-Expression $f.Extent.Text }

function Write-Log { param($m, $l = "INFO") }

# --- finti, sostituiscono quelli veri dopo il caricamento ---
$script:FINTO = @{}
function Get-RegistroPython312 { @($script:FINTO.Registro) | Where-Object { $_ } }
function py { foreach ($r in $script:FINTO.Launcher) { $r } }
function Get-PythonVersione {
    param([string]$Percorso)
    if ($script:FINTO.Versioni.ContainsKey($Percorso)) { return $script:FINTO.Versioni[$Percorso] }
    return [PSCustomObject]@{ Codice = 0; Output = "Python 3.12.8" }
}

$script:esiti = @()
function Esito($ok, $nome) {
    $r = if ($ok) { "PASS" } else { "FAIL" }
    Write-Host "$r  $nome"
    $script:esiti += $r
}

function Scenario {
    param($Registro = @(), $Launcher = @(), $Versioni = @{})
    $script:FINTO = @{ Registro = $Registro; Launcher = $Launcher; Versioni = $Versioni }
}

$tmp = [System.IO.Path]::GetTempPath()
$inesistente = Join-Path $tmp "py312-inesistente/python.exe"
$cartellaVuota = Join-Path $tmp "py312-vuota"
New-Item -ItemType Directory -Force -Path $cartellaVuota | Out-Null
$exeRotto = Join-Path $tmp "py312-rotto/python.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $exeRotto) | Out-Null
Set-Content -Path $exeRotto -Value ""
$exeBuono = Join-Path $tmp "py312-buono/python.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $exeBuono) | Out-Null
Set-Content -Path $exeBuono -Value ""

Write-Host "=== guasti dichiarati ==="

Scenario -Launcher @("-V:3.12 *        C:\Program Files\Python312\python.exe")
$g = @(Get-Python312Guasti)
Esito ($g.Count -eq 1 -and $g[0].Stato -eq "assente" -and -not $g[0].CartellaPresente) `
      "launcher dichiara un percorso inesistente -> assente, cartella assente"

Scenario -Registro @($inesistente)
$g = @(Get-Python312Guasti)
Esito ($g.Count -eq 1 -and $g[0].Stato -eq "assente") "registro che punta nel vuoto -> assente"

Scenario -Registro @(Join-Path $cartellaVuota "python.exe")
$g = @(Get-Python312Guasti)
Esito ($g.Count -eq 1 -and $g[0].CartellaPresente) "cartella senza python.exe -> assente, cartella presente (antivirus)"

# PY-07: il caso che la 2.1.1 mancava — il file c'è ma non parte
Scenario -Registro @($exeRotto) -Versioni @{
    $exeRotto = [PSCustomObject]@{ Codice = -1073741515; Output = "" } }
$g = @(Get-Python312Guasti)
Esito ($g.Count -eq 1 -and $g[0].Stato -eq "non avviabile" -and $g[0].Dettaglio -match "-1073741515") `
      "python.exe presente ma non avviabile -> non avviabile, con codice"

Scenario -Registro @($exeRotto) -Versioni @{
    $exeRotto = [PSCustomObject]@{ Codice = -1; Output = "This program is blocked by group policy." } }
$g = @(Get-Python312Guasti)
Esito ($g.Count -eq 1 -and $g[0].Dettaglio -match "group policy") "esecuzione bloccata -> il messaggio di Windows finisce nel dettaglio"

Scenario -Registro @($exeBuono)
Esito (@(Get-Python312Guasti).Count -eq 0) "interprete funzionante -> nessun guasto"
Esito ((Test-PythonExe $exeBuono) -eq $true) "Test-PythonExe accetta l'interprete funzionante"
Scenario -Registro @($exeRotto) -Versioni @{ $exeRotto = [PSCustomObject]@{ Codice = 1; Output = "" } }
Esito ((Test-PythonExe $exeRotto) -eq $false) "Test-PythonExe rifiuta quello che non parte"

Scenario -Launcher @("-V:3.12 *        C:\Users\X\AppData\Local\Microsoft\WindowsApps\python.exe")
Esito (@(Get-Python312Guasti).Count -eq 0) "alias WindowsApps ignorato"

Scenario
Esito (@(Get-Python312Guasti).Count -eq 0) "nessuna registrazione"

Scenario -Launcher @(" -V:3.13          C:\Python313\python.exe")
Esito (@(Get-Python312Guasti).Count -eq 0) "solo 3.13 dichiarata -> ignorata"

Scenario -Registro @($inesistente) -Launcher @("-V:3.12 *        $inesistente")
Esito (@(Get-Python312Dichiarati).Count -eq 1) "stesso percorso da registro e launcher -> contato una volta"

Write-Host "=== launcher ==="
# PY-07: l'elenco del launcher può arrivare su stderr: va letto comunque
function py { Write-Error "-V:3.12 *        C:\Program Files\Python312\python.exe" }
$l = @(Get-LauncherPython312)
Esito ($l.Count -eq 1 -and $l[0] -eq "C:\Program Files\Python312\python.exe") "elenco del launcher letto anche da stderr"

Write-Host "=== alias ==="
Esito (Test-AppExecutionAlias "C:\Users\Assistenza\AppData\Local\Microsoft\WindowsApps\python.exe") "alias riconosciuto"
Esito (-not (Test-AppExecutionAlias "C:\Program Files\Python312\python.exe")) "interprete vero non scambiato per alias"

Write-Host "=== Install-Python: riparazione ==="
# PY-07: la riparazione deve partire OGNI volta che dopo l'installazione
# non c'è un interprete — anche se la diagnosi non trova nulla. Era il
# caso del server: la 2.1.1 subordinava la riparazione alla diagnosi.
if (-not $env:TEMP) { $env:TEMP = $tmp }
$Binaries = @{ Python = @{ Url = "https://example.invalid/python.exe"; Sha256 = "x" } }
function Download-VerifiedFile { param($Url, $ExpectedSha256, $DestinationPath, $ComponentName) }
function Show-Progress { param($m, $p) }
function Update-PathCorrente { }
function Write-DiagnosiPython { }

function Prova-Installazione($nome, $interpreteDopoPrimoGiro, $attese) {
    $script:chiamate = @()
    $script:primoGiro = $interpreteDopoPrimoGiro
    function Invoke-PythonSetup { param($Installer, [switch]$Disinstalla)
        $script:chiamate += $(if ($Disinstalla) { "disinstalla" } else { "installa" }) }
    function Find-Python312 { param([switch]$Silenzioso)
        if ($script:primoGiro) { return "C:\Program Files\Python312\python.exe" } else { return $null } }
    Install-Python
    $ok = (($script:chiamate -join ",") -eq ($attese -join ","))
    Esito $ok "$nome -> $($script:chiamate -join ', ')"
}

Scenario   # nessuna registrazione dichiarata: la 2.1.1 qui NON riparava
Prova-Installazione "interprete assente, nessun guasto diagnosticato" $false @("installa", "disinstalla", "installa")
Prova-Installazione "interprete presente dopo il primo giro" $true @("installa")

Remove-Item -Recurse -Force $cartellaVuota, (Split-Path $exeRotto), (Split-Path $exeBuono) -ErrorAction SilentlyContinue
$falliti = @($script:esiti | Where-Object { $_ -eq "FAIL" }).Count
Write-Host ""
Write-Host "$($script:esiti.Count - $falliti) passati, $falliti falliti"
if ($falliti) { exit 1 }
