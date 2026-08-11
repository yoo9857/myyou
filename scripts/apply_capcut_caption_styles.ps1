param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath
)

$ErrorActionPreference = 'Stop'

if (Get-Process -Name CapCut -ErrorAction SilentlyContinue) {
    throw 'CapCut is running. Save the project and close CapCut completely before applying caption styles.'
}

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$draftRoot = (Resolve-Path (Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft')).Path
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$prefix = $draftRoot.TrimEnd('\') + '\'
if (-not $project.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Project must be inside the CapCut draft root: $draftRoot"
}

$cli = Join-Path $workspace 'tools\capcut-cli\dist\index.js'
$movieSrt = Join-Path $workspace 'output\capcut_import\movie_captions.srt'
$narrationSrt = Join-Path $workspace 'output\capcut_import\narration.srt'
$dialoguePreset = Join-Path $workspace 'styles\capcut\dialogue-modern.json'
$narrationPreset = Join-Path $workspace 'styles\capcut\narration-modern.json'

foreach ($required in @($cli, $movieSrt, $narrationSrt, $dialoguePreset, $narrationPreset)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file is missing: $required"
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $workspace 'backups\capcut'
$backup = Join-Path $backupRoot ((Split-Path $project -Leaf) + '-' + $stamp)
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
Copy-Item -LiteralPath $project -Destination $backup -Recurse

$beforeParsed = node $cli segments $project --track text | ConvertFrom-Json
$before = foreach ($item in $beforeParsed) { $item }
if ($before.Count -eq 0) {
    throw 'No existing text segments were found; nothing was replaced.'
}

$ops = $before | ForEach-Object {
    @{ cmd = 'remove'; id = $_.id } | ConvertTo-Json -Compress
}
$batchResult = ($ops -join "`n") | node $cli batch $project | ConvertFrom-Json
if (-not $batchResult.ok) {
    throw 'The existing caption tracks could not be removed transactionally.'
}

node $cli import-srt $project $movieSrt --track-name 'MOVIE_DIALOGUE' | Out-Null
node $cli import-srt $project $narrationSrt --track-name 'REVIEW_NARRATION' | Out-Null

$draft = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $project 'template-2.tmp') | ConvertFrom-Json
$styleOps = @()
foreach ($track in @($draft.tracks | Where-Object { $_.type -eq 'text' })) {
    if ($track.name -eq 'MOVIE_DIALOGUE') {
        foreach ($segment in $track.segments) {
            $styleOps += @{ cmd = 'text-style'; id = $segment.id; preset = $dialoguePreset } | ConvertTo-Json -Compress
        }
    }
    elseif ($track.name -eq 'REVIEW_NARRATION') {
        foreach ($segment in $track.segments) {
            $styleOps += @{ cmd = 'text-style'; id = $segment.id; preset = $narrationPreset } | ConvertTo-Json -Compress
        }
    }
}
if ($styleOps.Count -eq 0) {
    throw 'No separated caption tracks were found for styling.'
}
$styleResult = ($styleOps -join "`n") | node $cli batch $project | ConvertFrom-Json
if (-not $styleResult.ok) {
    throw 'Caption styles could not be applied transactionally.'
}

$tracksParsed = node $cli tracks $project | ConvertFrom-Json
$tracks = foreach ($item in $tracksParsed) { $item }
$textTracks = @($tracks | Where-Object { $_.type -eq 'text' })
$afterParsed = node $cli segments $project --track text | ConvertFrom-Json
$after = foreach ($item in $afterParsed) { $item }
$lintOutput = node $cli lint $project 2>&1
$lintExit = $LASTEXITCODE

[pscustomobject]@{
    Project = $project
    Backup = $backup
    RemovedTextSegments = $before.Count
    ImportedTextSegments = $after.Count
    TextTracks = $textTracks.Count
    LintExitCode = $lintExit
    Lint = ($lintOutput -join "`n")
} | ConvertTo-Json -Depth 6
