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
    [switch]$VerifyOnly
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
    Write-Host 'Start or restart Django from this shell, then run this script with -VerifyOnly.'
} finally {
    Pop-Location
}
