$ErrorActionPreference = "Stop"
$ApiKey = "ma_live_ARONAwrVTCwIvRFbQq3kYZFSaLIHRVAQ"
$BaseUrl = "https://api.meowa.ai"
$OutDir = "C:\Project\MindToDoc\docs\audio\generated\sfx"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$SfxList = @(
    @{ Id = "SFX_UI_CLICK";       Prompt = "Generic mobile game UI button tap click, soft plastic button, neutral positive feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_SELECT";      Prompt = "UI selection highlight blip, light tick pitch up, character picker feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_POPUP_OPEN";  Prompt = "Modal popup window appear, soft whoosh upward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_POPUP_CLOSE"; Prompt = "Modal popup window close, soft whoosh downward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_TOGGLE_ON";   Prompt = "UI toggle switch on, high pitch blip, targeting enabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_TOGGLE_OFF";  Prompt = "UI toggle switch off, low pitch blip, targeting disabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_NEGATIVE";    Prompt = "Soft error buzz, action denied, insufficient resources, mobile game UI, not harsh alarm, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_PAUSE_OPEN";  Prompt = "Game pause menu open, soft pop, game paused state, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_UI_PAUSE_CLOSE"; Prompt = "Game resume, pause menu close, soft pop, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_REWARD_POP";     Prompt = "Coin reward pop, bright chime sparkle, loot item appear, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_SLICE_ENTER";    Prompt = "Soft whoosh transition into soccer kickoff moment, subtle referee whistle hint in distance, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_MODE_LOCK";      Prompt = "Mode locked confirm thunk, firm mechanical latch click with short positive tail, decisive UI commit, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_BALL_RELEASE";   Prompt = "Snappy rubber band release pop with light whoosh, cartoon elastic snap, soccer mini game, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_KICK";           Prompt = "Soccer ball kick impact on grass, crisp thump, outdoor stadium foley, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix" },
    @{ Id = "SFX_SLICE_SUCCESS";  Prompt = "Soccer ball hits goal net rustle swish plus short victory sting, brief crowd cheer burst, satisfying mobile soccer success, no vocals, no full music bed, clean mix" }
)

function Submit-SfxJob($item) {
    $duration = if ($item.Duration) { $item.Duration } else { "0.5" }
    $args = @(
        "--ssl-no-revoke", "-s", "-X", "POST", "$BaseUrl/api/workflows/elevenlabs_generator/run",
        "-H", "Authorization: Bearer $ApiKey",
        "-F", "prompt=$($item.Prompt)",
        "-F", "duration=$duration",
        "-F", "variants=true",
        "-F", "count=4",
        "-F", "normalize_volume=true",
        "-F", "temperature=0.3"
    )
    $raw = & curl.exe @args
    if (-not $raw) { throw "Empty response for $($item.Id)" }
    return $raw | ConvertFrom-Json
}

function Get-JobStatus($jobId) {
    $raw = curl.exe --ssl-no-revoke -s "$BaseUrl/api/jobs?id=$jobId" -H "Authorization: Bearer $ApiKey"
    return $raw | ConvertFrom-Json
}

function Get-AudioUrls($job) {
    $urls = @()
    if ($job.result.audios) {
        foreach ($a in $job.result.audios) { if ($a.path) { $urls += $a.path } }
    }
    if ($job.result.audio_paths) { $urls += @($job.result.audio_paths) }
    if ($job.result.audio_path) { $urls += $job.result.audio_path }
    if ($job.result.url) { $urls += $job.result.url }
    return $urls | Select-Object -Unique
}

$jobs = @()
Write-Host "=== Submitting $($SfxList.Count) SFX jobs ==="
foreach ($item in $SfxList) {
    Write-Host "Submit: $($item.Id)"
    $resp = Submit-SfxJob $item
    $jobs += [PSCustomObject]@{ Id = $item.Id; JobId = $resp.job_id; Status = $resp.status }
    Start-Sleep -Seconds 1
}

Write-Host "`n=== Polling jobs ==="
$pending = $jobs | ForEach-Object { $_ }
$maxRounds = 60
for ($round = 1; $round -le $maxRounds; $round++) {
    $still = @()
    foreach ($j in $pending) {
        $st = Get-JobStatus $j.JobId
        Write-Host "[$round] $($j.Id): $($st.status)"
        if ($st.status -in @("success", "failure", "cancelled")) {
            $j | Add-Member -NotePropertyName FinalStatus -NotePropertyValue $st.status -Force
            $j | Add-Member -NotePropertyName Result -NotePropertyValue $st -Force
        } else {
            $still += $j
        }
    }
    $pending = $still
    if ($pending.Count -eq 0) { break }
    Start-Sleep -Seconds 8
}

Write-Host "`n=== Downloading ==="
$manifest = @()
foreach ($j in $jobs) {
    if ($j.FinalStatus -ne "success") {
        Write-Host "SKIP $($j.Id): $($j.FinalStatus)"
        $manifest += [PSCustomObject]@{ Id = $j.Id; JobId = $j.JobId; Status = $j.FinalStatus; Files = @() }
        continue
    }
    $urls = Get-AudioUrls $j.Result
    $files = @()
    $idx = 1
    foreach ($url in $urls) {
        $mp3 = Join-Path $OutDir "$($j.Id)_v$('{0:D2}' -f $idx).mp3"
        curl.exe --ssl-no-revoke -sL $url -o $mp3
        if (Test-Path $mp3) {
            $files += $mp3
            Write-Host "Saved: $mp3"
        }
        $idx++
    }
    $manifest += [PSCustomObject]@{ Id = $j.Id; JobId = $j.JobId; Status = "success"; Files = $files }
}

$manifestPath = Join-Path $OutDir "manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "`nDone. Manifest: $manifestPath"
