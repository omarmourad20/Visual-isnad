[CmdletBinding()]
param(
    [string]$VisualDb,
    [string]$KnowledgeGraphDb,
    [string]$FawazJson,
    [string]$JaguarJson,
    [int]$ExpectedHadiths = 7252,
    [int]$ExpectedEdges = 41123,
    [string]$VisualEdition = 'windows-visual',
    [string]$KnowledgeGraphUrl = 'http://127.0.0.1:8077',
    [string]$DjangoUrl = 'http://127.0.0.1:8000',
    [switch]$VerifyOnly,
    [switch]$StartServer
)

$ErrorActionPreference = 'Stop'
$backend = Join-Path (Split-Path $PSScriptRoot -Parent) 'backend'
$python = Join-Path $backend 'venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw "Project Python not found: $python" }

foreach ($name in @('VisualDb', 'KnowledgeGraphDb', 'FawazJson', 'JaguarJson')) {
    $value = Get-Variable -Name $name -ValueOnly
    if ($value -and !$VerifyOnly) {
        Set-Variable -Name $name -Value (Resolve-Path -LiteralPath $value).ProviderPath
    }
}
Push-Location -LiteralPath $backend
try {
    $env:HADITH_KG_API_URL = $KnowledgeGraphUrl
    if ($VerifyOnly) {
        & $python -m isnad.setup_source_preview verify --django-url $DjangoUrl
        if ($LASTEXITCODE -ne 0) { throw 'Live source verification failed.' }
        return
    }

    if ($StartServer) {
        $url = [uri]$DjangoUrl
        if ($url.Scheme -ne 'http' -or $url.Host -ne '127.0.0.1' -or $url.AbsolutePath -ne '/') {
            throw '-StartServer requires an HTTP loopback URL such as http://127.0.0.1:8769.'
        }
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $url.Port)
        try {
            $listener.Start()
        } catch {
            throw "Port $($url.Port) is unavailable. Select a free port with -DjangoUrl. No process was stopped."
        } finally {
            $listener.Stop()
        }
    }

    if (!$VisualDb) { $VisualDb = Join-Path $backend 'db.sqlite3' }
    if (!$KnowledgeGraphDb) { throw 'Pass -KnowledgeGraphDb with the pinned relational hadith-kg.db path.' }
    $run = Join-Path $env:TEMP ("visual-isnad-sources-" + [guid]::NewGuid())
    $arguments = @(
        '-m', 'isnad.setup_source_preview', 'build',
        '--visual', $VisualDb,
        '--kg', $KnowledgeGraphDb,
        '--visual-edition', $VisualEdition, '--expected-hadiths', $ExpectedHadiths,
        '--expected-edges', $ExpectedEdges, '--output', $run
    )
    if ($FawazJson) { $arguments += @('--fawaz', $FawazJson) }
    if ($JaguarJson) { $arguments += @('--jaguar', $JaguarJson) }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Source crosswalk generation failed.' }
    $env:HADITH_SOURCE_PREVIEW_DB = $VisualDb
    $env:HADITH_SOURCE_CROSSWALK = Join-Path $run 'proposals.json'
    Write-Host "Crosswalk: $env:HADITH_SOURCE_CROSSWALK"
    if (!$StartServer) {
        Write-Host 'Start Django from this shell, or rerun with -StartServer to pass configuration to the child automatically.'
        return
    }

    $stdout = Join-Path $run 'django.stdout.log'
    $stderr = Join-Path $run 'django.stderr.log'
    $server = Start-Process -FilePath $python -WorkingDirectory $backend -PassThru -ArgumentList @(
        'manage.py', 'runserver', ("127.0.0.1:" + $url.Port), '--noreload'
    ) -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Write-Host "Started verification Django PID $($server.Id). Logs: $stdout and $stderr"
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        if ($server.HasExited) { throw "Django exited. Check $stderr" }
        try {
            $null = Invoke-RestMethod -Uri ($DjangoUrl.TrimEnd('/') + '/api/v1/hadiths/15/?chain=1') -TimeoutSec 2
            $ready = $true
            break
        } catch {
            if ($_.Exception.Response) { throw "Django responded with an error for Hadith 15. Check $stderr" }
            Start-Sleep -Seconds 1
        }
    }
    if (!$ready) { throw "Django did not become ready. Check $stderr" }
    & $python -m isnad.setup_source_preview verify --django-url $DjangoUrl
    if ($LASTEXITCODE -ne 0) { throw "Live source verification failed. Django logs: $stderr" }
} finally {
    Pop-Location
}
