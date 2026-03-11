$ErrorActionPreference = "Stop"

$project = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma"
$terminal = "C:\Program Files\MetaTrader 5\terminal64.exe"
$python = "python"
$agentLog = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\logs\20260309.log"
$sourceLogDir = "C:\Users\awdse\AppData\Roaming\MetaQuotes\Tester\D0E8209F77C8CF37AD8BF550E51FF075\Agent-127.0.0.1-3000\MQL5\Files\triple_sigma_logs"
$packageScript = Join-Path $project "tools\package_step21_artifacts.py"

function Invoke-Step21Run {
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

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_control_trade.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_control_trade") `
    -Title "STEP21 Control Trade Artifact" `
    -Summary "_coord/logs/smoke/step21_control_trade_summary.md" `
    -ValidationClass "control-regression" `
    -TriggerSource "feature-off regression gate" `
    -BaselineCompare "_coord/artifacts/step20_control_trade"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_live_pass_regression.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_live_pass_regression") `
    -Title "STEP21 Live Pass Regression Artifact" `
    -Summary "_coord/logs/smoke/step21_live_pass_regression_summary.md" `
    -ValidationClass "live-pass-regression" `
    -TriggerSource "feature-off live early-exit regression gate" `
    -BaselineCompare "_coord/artifacts/step20_live_pass_regression"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_live_opposite_regression.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_live_opposite_regression") `
    -Title "STEP21 Live Opposite Regression Artifact" `
    -Summary "_coord/logs/smoke/step21_live_opposite_regression_summary.md" `
    -ValidationClass "live-opposite-regression" `
    -TriggerSource "feature-off opposite close regression gate" `
    -Synthetic $true `
    -BaselineCompare "_coord/artifacts/step20_live_opposite_regression"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_close_vs_modify_precedence.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_close_vs_modify_precedence") `
    -Title "STEP21 Close Vs Modify Precedence Artifact" `
    -Summary "_coord/logs/smoke/step21_close_vs_modify_precedence_summary.md" `
    -ValidationClass "close-vs-modify-precedence" `
    -TriggerSource "synthetic close trigger + synthetic BE trigger + precedence gate" `
    -Synthetic $true

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_live_trailing_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_live_trailing_probe") `
    -Title "STEP21 Live Trailing Probe Artifact" `
    -Summary "_coord/logs/smoke/step21_live_trailing_probe_summary.md" `
    -ValidationClass "live-trailing-probe" `
    -TriggerSource "actual trailing modify path"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_live_tp_reshape_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_live_tp_reshape_probe") `
    -Title "STEP21 Live TP Reshape Probe Artifact" `
    -Summary "_coord/logs/smoke/step21_live_tp_reshape_probe_summary.md" `
    -ValidationClass "live-tp-reshape-probe" `
    -TriggerSource "actual TP reshape modify path"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_live_time_policy_probe.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_live_time_policy_probe") `
    -Title "STEP21 Live Time Policy Probe Artifact" `
    -Summary "_coord/logs/smoke/step21_live_time_policy_probe_summary.md" `
    -ValidationClass "live-time-policy-probe" `
    -TriggerSource "actual time-policy modify path"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_recovery_pending_modify_tx.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_recovery_pending_modify_tx") `
    -Title "STEP21 Recovery Pending Modify Tx Artifact" `
    -Summary "_coord/logs/smoke/step21_recovery_pending_modify_tx_summary.md" `
    -ValidationClass "recovery-pending-modify-tx" `
    -TriggerSource "synthetic BE trigger + recovery reload + tx authority" `
    -Synthetic $true

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_runtime_reload_success.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_runtime_reload_success") `
    -Title "STEP21 Runtime Reload Success Artifact" `
    -Summary "_coord/logs/smoke/step21_runtime_reload_success_summary.md" `
    -ValidationClass "runtime-reload-success" `
    -TriggerSource "runtime patch success path + broker audit"

Invoke-Step21Run `
    -Preset (Join-Path $project "_coord\tester\step21\step21_tester_runtime_reload_rollback.ini") `
    -ArtifactDir (Join-Path $project "_coord\artifacts\step21_runtime_reload_rollback") `
    -Title "STEP21 Runtime Reload Rollback Artifact" `
    -Summary "_coord/logs/smoke/step21_runtime_reload_rollback_summary.md" `
    -ValidationClass "runtime-reload-rollback" `
    -TriggerSource "runtime patch forced failure + rollback + broker audit"

Write-Output "step21 runs complete"
