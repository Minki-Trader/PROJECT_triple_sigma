# STEP18 Execution Observability Hardening

Purpose:
- Improve failure-mode diagnostics without widening trade semantics.
- Keep `OnTradeTransaction()` observer-only.
- Make direct `CTrade.Result*` observations and transaction-level
  request/result observations visible in the runtime summary.

In scope:
- Pass `request` and `result` through `OnTradeTransaction()`.
- Record the latest direct trade result observed after `CTrade` entry/exit
  calls.
- Record the latest `TRADE_TRANSACTION_REQUEST` result observed from MT5.
- Distinguish synthetic tester-only rejects from actual server-result paths.
- Preserve current trade-log schema and current reconciliation behavior.

Out of scope:
- New live exit reasons
- BE / MODIFY
- Core `bar_log` / `trade_log` schema expansion
- Turning transaction callbacks into the authoritative state machine
- Broker/live-account testing requirements

Authoritative source-of-truth rule:
- Immediate call-site diagnostics:
  - direct `CTrade.Result*`
- Persisted intent:
  - `pending_exit_*`
- Final live state reconciliation:
  - `TS_SyncPositionState()`
- Transaction callback:
  - observer only

Actual-path validation for this step:
- Keep the retained control/live/reject tester presets.
- Treat normal tester entry/exit runs as the actual request/result path for this
  step.
- Use reject-once only as a synthetic negative-path probe and label it as
  synthetic in logs/summary.
- Close acceptance only if direct-result and transaction-request diagnostics are
  both present while trade semantics stay unchanged.

Practical validation matrix:
- Control trade:
  - `InpEarlyExitEnabled=false`
  - proves the added diagnostics do not widen baseline trade semantics
- Live early-exit:
  - `InpEarlyExitEnabled=true`
  - `InpEarlyExitLive=true`
  - `InpTestEarlyExitRejectOnce=false`
  - this is the primary actual-path validation run for STEP18
- Pending EARLY_EXIT recovery:
  - keeps the same live path as above
  - adds tester-only recovery probe coverage while keeping final artifacts
    stable
- Reject-once:
  - `InpTestEarlyExitRejectOnce=true`
  - remains intentionally synthetic and is used only to probe the negative
    branch and its diagnostics
