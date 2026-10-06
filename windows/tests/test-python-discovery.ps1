# ============================================================
# Test della ricerca di Python 3.12 (PY-04 / PY-05)
#
# Uso:  pwsh -NoProfile -File windows/tests/test-python-discovery.ps1
#
# Gira su qualsiasi piattaforma: carica SOLO le definizioni di funzione
# di setup-dependencies.ps1 (via AST, senza eseguire il setup) e
# sostituisce registro e launcher "py" con dei finti.
#
# Copre il guasto visto sul server di Advais: Windows dichiarava
# installata una 3.12 in C:\Program Files\Python312 dove non c'era
# nulla, l'installer ufficiale la considerava gia' presente e usciva
# con 0 senza scrivere niente.
# ============================================================
# Estrae SOLO le definizioni di funzione tramite l'AST: il resto dello
# script (param, creazione cartelle, MAIN) non viene eseguito.
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path ./windows/setup-dependencies.ps1), [ref]$null, [ref]$null)
$funzioni = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)
foreach ($f in $funzioni) { Invoke-Expression $f.Extent.Text }

function Write-Log { param($m,$l="INFO") }

$script:FINTO = @{ Registro = @{}; Launcher = @() }
function Get-ItemProperty {
    param([string]$Path, $ErrorAction)
    if ($script:FINTO.Registro.ContainsKey($Path)) {
        return [PSCustomObject]@{ "(default)" = $script:FINTO.Registro[$Path] }
    }
    throw "non trovato"
}
function py { $script:FINTO.Launcher }

$esiti = @()
function Prova($nome, $registro, $launcher, $atteso) {
    $script:FINTO = @{ Registro = $registro; Launcher = $launcher }
    $f = @(Get-Python312Fantasma)
    if ($f.Count -eq $atteso) { $r = "PASS" } else { $r = "FAIL (attesi $atteso, trovati $($f.Count))" }
    Write-Host "$r  $nome"
    foreach ($x in $f) { Write-Host "          -> $($x.Percorso)  cartella=$($x.CartellaPresente)" }
    $script:esiti += $r
}

Write-Host "funzioni caricate: $($funzioni.Count)"
Write-Host "=== Get-Python312Fantasma ==="
Prova "caso Antonio: launcher dichiara un percorso inesistente" @{} @("-V:3.12 *        C:\Program Files\Python312\python.exe") 1
# Percorso inesistente ma valido sull'host, cosi' il test gira anche
# fuori da Windows (Join-Path rifiuta "C:\..." dove non c'e' il drive).
$inesistente = Join-Path ([System.IO.Path]::GetTempPath()) "python312-che-non-esiste"
Prova "registro che punta nel vuoto" @{ "HKLM:\SOFTWARE\Python\PythonCore\3.12\InstallPath" = $inesistente } @() 1
$cartellaSenzaExe = Join-Path ([System.IO.Path]::GetTempPath()) "python312-vuota"
New-Item -ItemType Directory -Force -Path $cartellaSenzaExe | Out-Null
Prova "cartella presente ma senza python.exe (quarantena antivirus)" @{ "HKLM:\SOFTWARE\Python\PythonCore\3.12\InstallPath" = $cartellaSenzaExe } @() 1
$vero = (Get-Command pwsh).Source
Prova "percorso esistente non e' un fantasma" @{} @("-V:3.12 *        $vero") 0
Prova "alias WindowsApps ignorato" @{} @("-V:3.12 *        C:\Users\X\AppData\Local\Microsoft\WindowsApps\python.exe") 0
Prova "nessuna registrazione" @{} @() 0
Prova "solo 3.13 dichiarata" @{} @(" -V:3.13          C:\Python313\python.exe") 0
Write-Host "=== Test-AppExecutionAlias ==="
foreach ($c in @(@("C:\Users\Assistenza\AppData\Local\Microsoft\WindowsApps\python.exe",$true),
                 @("C:\Program Files\Python312\python.exe",$false))) {
    if ((Test-AppExecutionAlias $c[0]) -eq $c[1]) { Write-Host "PASS  $($c[0])" } else { Write-Host "FAIL  $($c[0])"; $esiti += "FAIL" }
}
if ($esiti -match "FAIL") { exit 1 }
