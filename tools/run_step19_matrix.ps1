$ErrorActionPreference = "Stop"

$project = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma"
$terminal = "C:\Program Files\MetaTrader 5\terminal64.exe"
$python = "python"
$agentLog = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\logs\20260309.log"
$sourceLogDir = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\MQL5\Files\triple_sigma_logs"
$packageScript = Join-Path $project "tools\package_step19_artifacts.py"

function Invoke-Step19Run {
    param(
        [string]$Preset,
        [string]$ArtifactDir,
        [string]$Title,
        [string]$Summary,
        [string]$ValidationClass,
        [string]$TriggerSource,
        [bool]$Synthetic = $false,
        [string]$BaselineCompare = ""
    )

    if (Test-Path $sourceLogDir) {
        Get-ChildItem $sourceLogDir | Remove-Item -Force
    }

    $offset = 0
    if (Test-Path $agentLog) {
        $offset = (Get-Item $agentLog).Length
    }

    Start-Process -FilePath $terminal -ArgumentList "/config:$Preset" -Wait

    $args = @(
        $packageScript,
        "--artifact-dir", $ArtifactDir,
        "--source-log-dir", $sourceLogDir,
        "--agent-log", $agentLog,
        "--log-offset", "$offset",
        "--title", $Title,
        "--preset", $Preset,
        "--summary", $Summary,
        "--validation-class", $ValidationClass,
        "--trigger-source", $TriggerSource
    )

    if ($Synthetic) {
        $args += "--synthetic"
    }
    if ($BaselineCompare -ne "") {
        $args += @("--baseline-compare", $BaselineCompare)
    }

    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Packaging failed for $Preset"
    }
}

Invoke-Step19Run `
    -Preset (Join-Path $project "_coord\tester\step19\step19_tester_control_trade.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step19_control_trade") `
    -Title "STEP19 Control Trade Artifact" `
    -Summary "_coord/logs/smoke/step19_control_trade_summary.md" `
    -ValidationClass "control" `
    -TriggerSource "actual-path" `
    -BaselineCompare "_coord/tester/step19/step19_tester_control_trade.ini"

Invoke-Step19Run `
    -Preset (Join-Path $project "_coord\tester\step19\step19_tester_live_pass_regression.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step19_live_pass_regression") `
    -Title "STEP19 Live Pass Regression Artifact" `
    -Summary "_coord/logs/smoke/step19_live_pass_regression_summary.md" `
    -ValidationClass "live-pass-regression" `
    -TriggerSource "actual-path" `
    -BaselineCompare "_coord/tester/step18/step18_tester_live_early_exit.ini"

Invoke-Step19Run `
    -Preset (Join-Path $project "_coord\tester\step19\step19_tester_live_opposite_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step19_live_opposite_probe") `
    -Title "STEP19 Live Opposite Probe Artifact" `
    -Summary "_coord/logs/smoke/step19_live_opposite_probe_summary.md" `
    -ValidationClass "live-opposite-probe" `
    -TriggerSource "synthetic-trigger + actual close path" `
    -Synthetic $true

Invoke-Step19Run `
    -Preset (Join-Path $project "_coord\tester\step19\step19_tester_recovery_pending_opposite_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step19_recovery_pending_opposite_probe") `
    -Title "STEP19 Recovery Pending Opposite Probe Artifact" `
    -Summary "_coord/logs/smoke/step19_recovery_pending_opposite_probe_summary.md" `
    -ValidationClass "recovery-probe" `
    -TriggerSource "synthetic-trigger + recovery probe" `
    -Synthetic $true

Invoke-Step19Run `
    -Preset (Join-Path $project "_coord\tester\step19\step19_tester_reject_once_opposite_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step19_reject_once_opposite_probe") `
    -Title "STEP19 Reject Once Opposite Probe Artifact" `
    -Summary "_coord/logs/smoke/step19_reject_once_opposite_probe_summary.md" `
    -ValidationClass "reject-synthetic-negative-path" `
    -TriggerSource "synthetic-trigger + synthetic reject" `
    -Synthetic $true

Write-Output "step19 runs complete"
