$ErrorActionPreference = "Stop"

$project = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma"
$terminal = "C:\Program Files\MetaTrader 5\terminal64.exe"
$python = "python"
$agentLog = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\logs\20260309.log"
$sourceLogDir = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\MQL5\Files\triple_sigma_logs"
$packageScript = Join-Path $project "tools\package_step20_artifacts.py"

function Invoke-Step20Run {
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

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_control_trade.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_control_trade") `
    -Title "STEP20 Control Trade Artifact" `
    -Summary "_coord/logs/smoke/step20_control_trade_summary.md" `
    -ValidationClass "control" `
    -TriggerSource "actual-path" `
    -BaselineCompare "_coord/artifacts/step19_control_trade/"

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_live_pass_regression.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_live_pass_regression") `
    -Title "STEP20 Live Pass Regression Artifact" `
    -Summary "_coord/logs/smoke/step20_live_pass_regression_summary.md" `
    -ValidationClass "live-pass-regression" `
    -TriggerSource "actual-path" `
    -BaselineCompare "_coord/artifacts/step19_live_pass_regression/"

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_live_opposite_regression.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_live_opposite_regression") `
    -Title "STEP20 Live Opposite Regression Artifact" `
    -Summary "_coord/logs/smoke/step20_live_opposite_regression_summary.md" `
    -ValidationClass "live-opposite-regression" `
    -TriggerSource "synthetic-trigger + actual close path" `
    -Synthetic $true `
    -BaselineCompare "_coord/artifacts/step19_live_opposite_probe/"

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_live_be_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_live_be_probe") `
    -Title "STEP20 Live BE Probe Artifact" `
    -Summary "_coord/logs/smoke/step20_live_be_probe_summary.md" `
    -ValidationClass "live-be-probe" `
    -TriggerSource "actual modify path"

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_recovery_pending_modify.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_recovery_pending_modify") `
    -Title "STEP20 Recovery Pending Modify Artifact" `
    -Summary "_coord/logs/smoke/step20_recovery_pending_modify_summary.md" `
    -ValidationClass "recovery-pending-modify" `
    -TriggerSource "synthetic-trigger + recovery probe + actual modify path" `
    -Synthetic $true

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_reject_once_modify.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_reject_once_modify") `
    -Title "STEP20 Reject Once Modify Artifact" `
    -Summary "_coord/logs/smoke/step20_reject_once_modify_summary.md" `
    -ValidationClass "modify-reject-synthetic-negative-path" `
    -TriggerSource "synthetic-trigger + synthetic modify reject" `
    -Synthetic $true

Invoke-Step20Run `
    -Preset (Join-Path $project "_coord\tester\step20\step20_tester_close_vs_modify_precedence.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step20_close_vs_modify_precedence") `
    -Title "STEP20 Close Vs Modify Precedence Artifact" `
    -Summary "_coord/logs/smoke/step20_close_vs_modify_precedence_summary.md" `
    -ValidationClass "close-vs-modify-precedence" `
    -TriggerSource "synthetic close trigger + synthetic BE trigger + actual close path" `
    -Synthetic $true

Write-Output "step20 runs complete"
