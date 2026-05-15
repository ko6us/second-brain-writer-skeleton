param(
    [Parameter(Mandatory=$true)]
    [string]$FolderName,

    [Parameter(Mandatory=$true)]
    [string]$Title,

    [Parameter(Mandatory=$false)]
    [string]$MarkdownFileName = "decision-table.md"
)

$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = Split-Path $scriptDir -Parent
$articlesDir = Join-Path $repoRoot "articles"
$targetDir = Join-Path $articlesDir $FolderName

Write-Host "Target: $targetDir"

if (-not (Test-Path $articlesDir)) {
    New-Item -Path $articlesDir -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path $targetDir)) {
    New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
}

$articleFile = Join-Path $targetDir "$FolderName.md"
if (-not (Test-Path $articleFile)) {
    $content = "---\ntitle: `"$Title`"\nnote_url: `"`"\n---\n\n# $Title\n\nBody here.\n\n## Table\n![[$MarkdownFileName]]"
    $content | Set-Content -Path $articleFile -Encoding UTF8
}

$tableFile = Join-Path $targetDir $MarkdownFileName
if (-not (Test-Path $tableFile)) {
    $tableContent = "| H1 | H2 |\n|---|---|\n| S | D |"
    $tableContent | Set-Content -Path $tableFile -Encoding UTF8
}

$metaFile = Join-Path $targetDir "meta.json"
if (-not (Test-Path $metaFile)) {
    $gistFileName = "${FolderName}__${MarkdownFileName}"
    $meta = @{
        article_title  = $Title
        article_folder = "articles/$FolderName"
        note_url       = ""
        items          = @(
            @{
                source_file      = "articles/$FolderName/$MarkdownFileName"
                gist_filename    = $gistFileName
                gist_description = "note embed for $Title"
                gist_id          = ""
                gist_url         = ""
            }
        )
    }
    $meta | ConvertTo-Json -Depth 10 | Set-Content -Path $metaFile -Encoding UTF8
}

Write-Host "Done"
