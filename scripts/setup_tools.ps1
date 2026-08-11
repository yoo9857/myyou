param(
    [switch]$SkipSkillInstall
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$toolDir = Join-Path $workspace 'tools\capcut-cli'
$patchFile = Join-Path $workspace 'patches\capcut-cli-batch-caption-style.patch'
$pinnedCommit = 'ffe45394754a250cb954a156b01c15f476ba2137'

foreach ($command in @('git', 'node', 'npm.cmd', 'python', 'ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command is missing: $command"
    }
}

if (-not (Test-Path -LiteralPath $toolDir)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $toolDir -Parent) | Out-Null
    git clone https://github.com/renezander030/capcut-cli.git $toolDir
    git -C $toolDir checkout $pinnedCommit
}

$currentCommit = (git -C $toolDir rev-parse HEAD).Trim()
if ($currentCommit -ne $pinnedCommit) {
    throw "Unexpected capcut-cli commit: $currentCommit. Expected: $pinnedCommit"
}

$savedErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$patchCheck = git -C $toolDir apply --check $patchFile 2>&1
$patchCheckExit = $LASTEXITCODE
$ErrorActionPreference = $savedErrorAction
if ($patchCheckExit -eq 0) {
    git -C $toolDir apply $patchFile
}
else {
    git -C $toolDir diff --quiet -- src/index.ts test/batch-transaction.test.mjs
    $patchAlreadyApplied = $LASTEXITCODE -ne 0
    if ($patchAlreadyApplied) {
        Write-Host 'CapCut CLI patch is already applied.'
    }
    else {
        throw "CapCut CLI patch cannot be applied: $patchCheck"
    }
}

Push-Location $toolDir
try {
    npm.cmd install --no-audit --no-fund
    npm.cmd run build
    node --test --test-name-pattern="removes text segments|applies a text preset" test\batch-transaction.test.mjs
}
finally {
    Pop-Location
}

if (-not $SkipSkillInstall) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
    $skillSource = Join-Path $workspace 'skills\edit-movie-review'
    $skillTarget = Join-Path $codexRoot 'skills\edit-movie-review'
    New-Item -ItemType Directory -Force -Path $skillTarget | Out-Null
    Get-ChildItem -LiteralPath $skillSource -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $skillTarget -Recurse -Force
    }
    Write-Host "Installed Codex skill: $skillTarget"
}

Write-Host 'Setup complete.'
