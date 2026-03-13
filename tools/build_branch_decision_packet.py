"""
build_branch_decision_packet.py - WF4 routing packet builder.

Reads a campaign-native run and its KPI summary, then emits a deterministic
branch recommendation in 60_decision/branch_decision_packet.json plus a
human-readable memo.

Usage:
    python tools/build_branch_decision_packet.py <run_dir>
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _validate_against_schema(data: dict, schema_path: Path) -> list[str]:
    import jsonschema

    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda err: list(err.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def _determine_project_root(path: Path) -> Path:
    root = path.resolve()
    while root.name != "PROJECT_triple_sigma" and root.parent != root:
        root = root.parent
    return root


def _confidence_from_gap(score_gap: int) -> str:
    if score_gap >= 4:
        return "high"
    if score_gap >= 2:
        return "medium"
    return "low"


def _append_rule(rules: list[dict], branch: str, rule_id: str, observed, threshold, rationale: str):
    rules.append({
        "branch": branch,
        "rule_id": rule_id,
        "observed": observed,
        "threshold": threshold,
        "rationale": rationale,
    })


def build_packet(run_dir: Path) -> dict:
    parser_dir = run_dir / "30_parsed"
    decision_dir = run_dir / "60_decision"
    decision_dir.mkdir(parents=True, exist_ok=True)

    run_manifest = _load_json(run_dir / "run_manifest.json")
    parse_manifest = _load_json(parser_dir / "parse_manifest.json")
    kpi_summary = _load_json(run_dir / "40_kpi" / "kpi_summary.json")
    validator_path = run_dir / "50_validator" / "validator_report.json"
    validator_report = _load_json(validator_path) if validator_path.exists() else {}

    campaign_manifest = {}
    manifest_ref = run_manifest.get("manifest_ref")
    if manifest_ref:
        manifest_path = Path(manifest_ref)
        if not manifest_path.exists():
            manifest_path = _determine_project_root(run_dir) / manifest_ref
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as handle:
                campaign_manifest = yaml.safe_load(handle) or {}

    runtime_blockers = []
    if validator_report.get("verdict") != "PASS":
        runtime_blockers.append("validator_verdict_not_pass")
    if not parse_manifest.get("pass", False):
        runtime_blockers.append("parse_manifest_pass_false")
    if not parse_manifest.get("invariants_pass", False):
        runtime_blockers.append("parse_manifest_invariants_false")
    if "master_tables_pass" in parse_manifest and not parse_manifest.get("master_tables_pass", False):
        runtime_blockers.append("master_tables_pass_false")

    rules = []
    portfolio = kpi_summary["portfolio"]
    risk = kpi_summary["risk"]
    signal = kpi_summary["signal"]
    counterfactual = kpi_summary["counterfactual"]

    if runtime_blockers:
        for blocker in runtime_blockers:
            _append_rule(
                rules,
                "runtime-fix-first",
                blocker,
                True,
                True,
                "Admissibility or parser integrity failed. Optimization must stop before WF4 routing.",
            )

        primary_branch = "runtime-fix-first"
        ml_score = 0
        ea_score = 0
        confidence = "high"
        rationale = "Admissibility blockers exist, so branch work is deferred until runtime integrity is restored."
    else:
        ml_score = 0
        ea_score = 0

        global_pf = portfolio.get("global_profit_factor") or 0.0
        total_pnl = portfolio.get("total_pnl") or 0.0
        long_pf = (portfolio.get("direction_breakdown") or {}).get("LONG", {}).get("profit_factor") or 0.0
        short_pf = (portfolio.get("direction_breakdown") or {}).get("SHORT", {}).get("profit_factor") or 0.0
        gate_block_rate = counterfactual.get("gate_block_rate_candidate_bars") or 0.0
        gate_regret_mean = counterfactual.get("gate_regret_mean") or 0.0
        exit_cost_to_risk_ratio = counterfactual.get("exit_cost_to_risk_ratio")
        early_exit_share = (
            ((portfolio.get("exit_reason_counts") or {}).get("EARLY_EXIT", 0)) / portfolio["total_trades"]
            if portfolio.get("total_trades", 0) > 0 else 0.0
        )
        force_exit_share = (
            ((portfolio.get("exit_reason_counts") or {}).get("FORCE_EXIT", 0)) / portfolio["total_trades"]
            if portfolio.get("total_trades", 0) > 0 else 0.0
        )
        stage1_margin_p10 = signal.get("candidate_margin_p10") or 0.0
        modify_count = counterfactual.get("modify_count") or 0
        modify_save_ratio = counterfactual.get("modify_save_ratio_mean")

        if global_pf < 1.0:
            ml_score += 2
            _append_rule(rules, "ML-first", "pf_below_one", global_pf, "< 1.0", "Portfolio PF is below break-even.")
        if total_pnl < 0:
            ml_score += 1
            _append_rule(rules, "ML-first", "negative_total_pnl", total_pnl, "< 0", "Benchmark baseline is losing money.")
        if long_pf < 0.9 and short_pf < 0.9:
            ml_score += 2
            _append_rule(
                rules,
                "ML-first",
                "both_directions_weak",
                {"LONG": long_pf, "SHORT": short_pf},
                "both < 0.9",
                "Both directional books are weak, pointing upstream to model quality rather than a single EA layer.",
            )
        if gate_block_rate < 0.02:
            ml_score += 1
            _append_rule(
                rules,
                "ML-first",
                "gate_block_rate_low",
                gate_block_rate,
                "< 0.02",
                "Gate rejection rate is too low to explain the benchmark loss by itself.",
            )
        if exit_cost_to_risk_ratio is not None and exit_cost_to_risk_ratio <= 1.0:
            ml_score += 1
            _append_rule(
                rules,
                "ML-first",
                "exit_cost_not_dominant",
                exit_cost_to_risk_ratio,
                "<= 1.0",
                "Exit opportunity cost does not exceed risk saved, so EA exits are not the primary deficit.",
            )
        if stage1_margin_p10 < 0.10:
            ml_score += 1
            _append_rule(
                rules,
                "ML-first",
                "candidate_margin_tail_thin",
                stage1_margin_p10,
                "< 0.10",
                "Low tail margin suggests weak classifier separation on the weakest candidate decile.",
            )

        if gate_block_rate >= 0.02 and gate_regret_mean >= 10.0:
            ea_score += 2
            _append_rule(
                rules,
                "EA-first",
                "gate_regret_material",
                {"gate_block_rate": gate_block_rate, "gate_regret_mean": gate_regret_mean},
                "rate >= 0.02 and regret >= 10",
                "Blocked setups are both frequent enough and costly enough to justify EA gate review.",
            )
        if exit_cost_to_risk_ratio is not None and exit_cost_to_risk_ratio > 1.0 and early_exit_share >= 0.20:
            ea_score += 2
            _append_rule(
                rules,
                "EA-first",
                "early_exit_cost_exceeds_saved_risk",
                {"ratio": exit_cost_to_risk_ratio, "share": early_exit_share},
                "ratio > 1.0 and share >= 0.20",
                "Exit policy is costing more forward opportunity than risk it saves.",
            )
        if modify_count > 0 and modify_save_ratio is not None and modify_save_ratio < 1.0:
            ea_score += 1
            _append_rule(
                rules,
                "EA-first",
                "modify_alpha_loss",
                modify_save_ratio,
                "< 1.0",
                "Protective modify logic is destroying more alpha than it saves.",
            )
        if force_exit_share >= 0.01:
            ea_score += 1
            _append_rule(
                rules,
                "EA-first",
                "force_exit_share_high",
                force_exit_share,
                ">= 0.01",
                "Hold-boundary pressure is high enough to justify EA exit review.",
            )

        if ml_score > ea_score:
            primary_branch = "ML-first"
            confidence = _confidence_from_gap(ml_score - ea_score)
            rationale = (
                "Losses are broad across both directional books while gate/exit pressure is not dominant. "
                "The benchmark points upstream to Stage1/Stage2 quality before EA relaxation."
            )
        elif ea_score > ml_score:
            primary_branch = "EA-first"
            confidence = _confidence_from_gap(ea_score - ml_score)
            rationale = (
                "Counterfactual evidence points to gate or exit policy as the dominant source of lost opportunity. "
                "EA policy should move before another ML cycle."
            )
        else:
            pending_layers = [
                item.get("layer")
                for item in (campaign_manifest.get("optimization_order") or [])
                if item.get("status") == "pending"
            ]
            if pending_layers and pending_layers[0] in ("Stage1", "Stage2"):
                primary_branch = "ML-first"
                confidence = "low"
                rationale = (
                    "Scores are tied, so the campaign's declared primary bottleneck takes precedence. "
                    "Stage1/Stage2 is the first pending branch in manifest governance."
                )
            else:
                primary_branch = "EA-first"
                confidence = "low"
                rationale = (
                    "Scores are tied and the campaign manifest does not present an earlier ML blocker. "
                    "Defaulting to the first reversible EA policy branch."
                )

    if primary_branch == "runtime-fix-first":
        next_actions = [
            "Resolve validator or parser blockers before any WF4 routing.",
            "Re-run strict validation with `python tools/validate_campaign_run.py <run_dir> --require-parse`.",
            "Do not open ML or EA optimization sweeps until admissibility is restored.",
        ]
    elif primary_branch == "ML-first":
        next_actions = [
            "Prioritize Stage1 refresh on the frozen optimization folds before changing EA thresholds.",
            "Keep Stage2 retune secondary unless post-refresh branch metrics still show weak exit/gate attribution.",
            "Re-stage the benchmark run after ML refresh and compare PF, drawdown, and directional PF symmetry.",
        ]
    else:
        next_actions = [
            "Open EA gate and early-exit tuning before retraining models.",
            "Keep runtime and pack fixed while sweeping gate thresholds to isolate policy attribution.",
            "Re-stage the benchmark run and verify gate regret or exit-cost compression without worsening drawdown.",
        ]

    packet = {
        "schema_version": "1.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": run_manifest.get("campaign_id", ""),
        "run_id": run_manifest.get("run_id", ""),
        "window_alias": run_manifest.get("window_alias", ""),
        "pack_id": run_manifest.get("pack_id", ""),
        "primary_branch": primary_branch,
        "confidence": confidence,
        "rationale": rationale,
        "admissibility": {
            "validator_verdict": validator_report.get("verdict", "UNKNOWN"),
            "parse_pass": bool(parse_manifest.get("pass", False)),
            "invariants_pass": bool(parse_manifest.get("invariants_pass", False)),
            "master_tables_pass": bool(parse_manifest.get("master_tables_pass", False)),
            "runtime_blockers": runtime_blockers,
        },
        "scores": {
            "ml_score": ml_score,
            "ea_score": ea_score,
        },
        "headline_metrics": {
            "total_pnl": portfolio.get("total_pnl", 0.0),
            "global_profit_factor": portfolio.get("global_profit_factor"),
            "global_win_rate": portfolio.get("global_win_rate", 0.0),
            "max_equity_dd_pct": risk.get("max_equity_dd_pct", 0.0),
            "gate_regret_mean": counterfactual.get("gate_regret_mean", 0.0),
            "gate_block_rate_candidate_bars": counterfactual.get("gate_block_rate_candidate_bars", 0.0),
            "exit_cost_to_risk_ratio": counterfactual.get("exit_cost_to_risk_ratio"),
        },
        "triggered_rules": rules,
        "next_actions": next_actions,
        "source_artifacts": {
            "kpi_summary": str(run_dir / "40_kpi" / "kpi_summary.json"),
            "validator_report": str(validator_path) if validator_path.exists() else "",
            "parse_manifest": str(parser_dir / "parse_manifest.json"),
            "campaign_manifest": manifest_ref or "",
        },
    }

    project_root = _determine_project_root(run_dir)
    schema_path = project_root / "_coord" / "ops" / "schemas" / "branch_decision_packet.schema.json"
    schema_errors = _validate_against_schema(packet, schema_path)
    if schema_errors:
        raise ValueError("branch_decision_packet schema validation failed: " + "; ".join(schema_errors))

    json_path = decision_dir / "branch_decision_packet.json"
    json_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    md_lines = [
        f"# Branch Decision Packet - {packet['run_id']}",
        "",
        f"- Primary branch: `{primary_branch}`",
        f"- Confidence: `{confidence}`",
        f"- Rationale: {rationale}",
        "",
        "## Headline Metrics",
        f"- Total PnL: {packet['headline_metrics']['total_pnl']:.2f}",
        f"- Global PF: {(packet['headline_metrics']['global_profit_factor'] or 0.0):.4f}",
        f"- Global WR: {packet['headline_metrics']['global_win_rate']:.2%}",
        f"- Max equity DD: {packet['headline_metrics']['max_equity_dd_pct']:.2f}%",
        f"- Gate regret mean: {packet['headline_metrics']['gate_regret_mean']:.2f}",
        f"- Gate block rate: {packet['headline_metrics']['gate_block_rate_candidate_bars']:.4f}",
        f"- Exit cost/risk ratio: {(packet['headline_metrics']['exit_cost_to_risk_ratio'] or 0.0):.4f}",
        "",
        "## Triggered Rules",
    ]
    if rules:
        for rule in rules:
            md_lines.append(
                f"- `{rule['branch']}` / `{rule['rule_id']}`: observed={rule['observed']} threshold={rule['threshold']} :: {rule['rationale']}"
            )
    else:
        md_lines.append("- None")
    md_lines.extend(["", "## Next Actions"])
    for action in next_actions:
        md_lines.append(f"- {action}")
    (decision_dir / "branch_decision_packet.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return packet


def main():
    parser = argparse.ArgumentParser(description="Build WF4 branch decision packet.")
    parser.add_argument("run_dir", type=Path, help="Path to runs/RUN_<ts>/")
    args = parser.parse_args()

    packet = build_packet(args.run_dir)
    print(f"Branch decision: {args.run_dir / '60_decision' / 'branch_decision_packet.json'}")
    print(f"  Primary branch: {packet['primary_branch']}")
    print(f"  Confidence:     {packet['confidence']}")


if __name__ == "__main__":
    main()
