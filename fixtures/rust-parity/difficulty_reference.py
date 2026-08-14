#!/usr/bin/env python3
"""Frozen Python argparse oracle for the #8501 difficulty command port.

This is test-only compatibility code. Product dispatch no longer imports it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.calibration import difficulty
from larch.core import proc
from larch.errors import ShipError
from larch.git import gh
from larch.issue import issue_mutation


def validate_rating_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty validate-rating")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file")
    args = parser.parse_args(argv)
    try:
        data: object = json.loads(Path(args.input_file).read_text(encoding="utf-8", errors="replace"))
        rating = difficulty.validate_rating_object(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"STATUS=invalid\nERROR={exc}")
        return 1
    out = asdict(rating)
    if args.output_file:
        larch_io.atomic_write(Path(args.output_file), json.dumps(out, indent=2, sort_keys=True) + "\n", prefix=".difficulty-rating.")
    print("STATUS=ok")
    print(f"PREDICTED_TIER={rating.predicted_tier}")
    print(f"CONFIDENCE={rating.confidence}")
    print(f"ADJUSTED_TIER={rating.adjusted_tier}")
    return 0


def extract_plan_metadata_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty extract-plan-metadata")
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args(argv)
    try:
        text = Path(args.plan_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 2
    print("STATUS=ok")
    print(f"DESIGN_DIFFICULTY={difficulty.plan_difficulty(text)}")
    return 0


def _record_from_args(args: argparse.Namespace) -> difficulty.DifficultyRecord:
    design_rating = difficulty.read_rating_file(Path(args.design_raw_rating_file)) if args.design_raw_rating_file else None
    if design_rating is None and args.design_tier:
        design_rating = difficulty._rating_from_tier(str(args.design_tier).upper(), rationale="design wire metadata")
    implement_rating = difficulty.read_rating_file(Path(args.implement_raw_rating_file)) if args.implement_raw_rating_file else None
    raw_rating = difficulty.read_rating_file(Path(args.raw_rating_file)) if args.raw_rating_file else None
    if args.rater == "design" and design_rating is None:
        design_rating = raw_rating
    elif args.rater == "implement" and implement_rating is None:
        implement_rating = raw_rating
    elif args.rater == "review" and raw_rating is not None:
        implement_rating = raw_rating
    fallback = None
    if args.fallback_tier:
        fallback = difficulty._rating_from_tier(str(args.fallback_tier).upper(), rationale=args.fallback_rationale)
    changed_paths = difficulty._read_changed_paths(Path(args.changed_paths_file) if args.changed_paths_file else None)
    return difficulty.build_record(
        rater=args.rater,
        rater_tool=args.rater_tool,
        rater_model=args.rater_model,
        design_rating=design_rating,
        implement_rating=implement_rating,
        fallback_rating=fallback,
        changed_paths=changed_paths,
        panel_skipped=args.panel_skipped,
        audit_upgrade=args.audit_upgrade,
        escalations=tuple(args.escalation or ()),
        override_source=args.override_source,
        override_tier=args.override_tier,
        panel_tier=args.panel_tier,
        round_cap=int(args.round_cap) if str(args.round_cap).isdigit() else None,
        codex_model_role=args.codex_model_role,
        audit_evaluated=True if args.audit_evaluated == "true" else False if args.audit_evaluated == "false" else None,
        escalated_round=True if args.escalated_round == "true" else False if args.escalated_round == "false" else None,
    )


def _refreshed_existing_record(args: argparse.Namespace) -> difficulty.DifficultyRecord:
    existing: dict[str, object] = difficulty._load_record_data(Path(args.output))
    rating = difficulty.validate_rating_object({
        "predicted_tier": str(existing.get("predicted_tier") or "").upper(),
        "confidence": str(existing.get("confidence") or "").lower(),
        "rationale": str(existing.get("rationale") or ""),
    })
    rater = str(existing.get("rater") or "unknown")
    changed_paths = difficulty._read_changed_paths(Path(args.changed_paths_file) if args.changed_paths_file else None)
    if not changed_paths and args.refresh_repo_root:
        changed = proc.run(["git", "diff", "--name-only", "HEAD"], cwd=args.refresh_repo_root)
        if changed.returncode != 0:
            raise ValueError("difficulty refresh could not read changed paths")
        changed_paths = tuple(line.strip() for line in (changed.stdout or "").splitlines() if line.strip())
    raw_escalations: object | None = existing.get("escalations")
    escalations = (
        tuple(cast("list[object] | tuple[object, ...]", raw_escalations))
        if isinstance(raw_escalations, list | tuple)
        else ()
    )
    kwargs: dict[str, object] = {
        "rater": rater,
        "rater_tool": str(existing.get("rater_tool") or "unknown"),
        "rater_model": str(existing.get("rater_model") or "unknown"),
        "changed_paths": changed_paths,
        "panel_skipped": str(existing.get("panel_skipped") or ""),
        "audit_upgrade": str(existing.get("audit_upgrade") or ""),
        "escalations": escalations,
    }
    if rater == "implement":
        kwargs["implement_rating"] = rating
    elif rater == "fallback":
        kwargs["fallback_rating"] = rating
    else:
        kwargs["design_rating"] = rating
    refreshed = difficulty.build_record(**kwargs)  # type: ignore[arg-type]
    return difficulty._merge_existing_record_fields(refreshed, existing, difficulty.blank_merge_args())


def write_record_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty write-record")
    parser.add_argument("--output", required=True)
    parser.add_argument("--rater", choices=("design", "implement", "review", "fallback"), default="fallback")
    parser.add_argument("--rater-tool", default="")
    parser.add_argument("--rater-model", default="")
    parser.add_argument("--raw-rating-file", default="")
    parser.add_argument("--design-raw-rating-file", default="")
    parser.add_argument("--implement-raw-rating-file", default="")
    parser.add_argument("--design-tier", default="")
    parser.add_argument("--changed-paths-file", default="")
    parser.add_argument("--panel-skipped", default="")
    parser.add_argument("--audit-upgrade", default="")
    parser.add_argument("--escalation", action="append")
    parser.add_argument("--override-source", default="")
    parser.add_argument("--override-tier", default="")
    parser.add_argument("--panel-tier", default="")
    parser.add_argument("--round-cap", default="")
    parser.add_argument("--codex-model-role", default="")
    parser.add_argument("--audit-evaluated", choices=("", "true", "false"), default="")
    parser.add_argument("--escalated-round", choices=("", "true", "false"), default="")
    parser.add_argument("--fallback-tier", default="MODERATE")
    parser.add_argument("--fallback-rationale", default="fallback rating synthesized for recovery path")
    parser.add_argument("--refresh-existing", action="store_true")
    parser.add_argument("--refresh-repo-root", default="")
    args = parser.parse_args(argv)
    try:
        if args.refresh_existing:
            record = _refreshed_existing_record(args)
        else:
            record = _record_from_args(args)
            record = difficulty._merge_existing_record_fields(record, difficulty._load_record_data(Path(args.output)), args)
        difficulty.write_record(Path(args.output), record)
    except (OSError, ValueError) as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 1
    print("STATUS=ok")
    print(f"OUTPUT={args.output}")
    print(f"PREDICTED_TIER={record.predicted_tier}")
    print(f"APPLIED_TIER={record.applied_tier}")
    print(f"OVERRIDE_SOURCE={record.override_source}")
    return 0


def render_rubric_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty render-rubric")
    parser.parse_args(argv)
    sys.stdout.write(difficulty.render_rubric())
    return 0


def render_line_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty render-line")
    parser.add_argument("--record-file", required=True)
    args = parser.parse_args(argv)
    try:
        data: object = json.loads(Path(args.record_file).read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"STATUS=error\nERROR={exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("STATUS=error\nERROR=record must be object", file=sys.stderr)
        return 1
    print(difficulty.difficulty_line(cast("dict[str, object]", data)))
    return 0


def resolve_panel_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty resolve-panel")
    parser.add_argument("--record-file", required=True)
    parser.add_argument("--override", default="")
    parser.add_argument("--audit-roll", default="")
    parser.add_argument("--no-audit", action="store_true")
    args = parser.parse_args(argv)
    override = difficulty.normalize_tier(args.override)
    if args.override and not override:
        print("STATUS=error\nERROR=invalid-override")
        return 2
    rng: object = None
    if args.audit_roll:
        try:
            rng = int(args.audit_roll)
        except ValueError:
            print("STATUS=error\nERROR=invalid-audit-roll")
            return 2
    try:
        resolution = difficulty.resolve_panel_tier(Path(args.record_file), override=override, rng=rng, audit_enabled=not args.no_audit)
    except (OSError, ValueError) as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 1
    print("STATUS=ok")
    print(f"PANEL_TIER={resolution.panel_tier}")
    print(f"ROUND_CAP={resolution.round_cap}")
    print(f"CODEX_MODEL_ROLE={resolution.codex_model_role}")
    print(f"AUDIT_EVALUATED={'true' if resolution.audit_evaluated else 'false'}")
    print(f"AUDIT_UPGRADE={'true' if resolution.audit_upgrade else 'false'}")
    print(f"OVERRIDE_SOURCE={resolution.override_source}")
    print(f"ESCALATED_ROUND={'true' if resolution.escalated_round else 'false'}")
    return 0


def sync_labels_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty sync-labels")
    parser.add_argument("--issue", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--repo", default="")
    args = parser.parse_args(argv)
    tier = args.tier.upper()
    if not difficulty.tier_valid(tier):
        print("STATUS=error\nERROR=invalid-tier")
        return 2
    repo = args.repo or gh.resolve_repo(proc)
    if not repo:
        print("STATUS=error")
        print("ERROR=repo-unresolved")
        return 1
    label = difficulty.label_for_tier(tier)
    create_argv = ["label", "create", label]
    create_argv.extend(["--repo", repo])
    create_argv.extend(["--color", "ededed", "--description", "larch difficulty rating"])
    create = gh.command(proc, create_argv)
    if create.returncode != 0 and "already exists" not in (create.stderr + create.stdout).lower():
        print("STATUS=warning")
        print("WARNING=label-create-failed")
    try:
        snapshot = issue_mutation.read_snapshot(proc, repository=repo, issue=str(args.issue))
        _ = issue_mutation.update_labels(
            proc,
            repository=repo,
            issue=str(args.issue),
            labels=frozenset((snapshot.labels - set(difficulty.known_labels())) | {label}),
        )
    except ShipError:
        print("STATUS=error")
        print("ERROR=label-add-failed")
        return 1
    print("STATUS=ok")
    print(f"LABEL={label}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: difficulty_reference.py <verb> [...]", file=sys.stderr)
        return 2
    verb, rest = sys.argv[1], sys.argv[2:]
    handlers = {
        "validate-rating": validate_rating_main,
        "extract-plan-metadata": extract_plan_metadata_main,
        "write-record": write_record_main,
        "render-rubric": render_rubric_main,
        "render-line": render_line_main,
        "resolve-panel": resolve_panel_main,
        "sync-labels": sync_labels_main,
    }
    handler = handlers.get(verb)
    if handler is None:
        print(f"unknown verb: {verb}", file=sys.stderr)
        return 2
    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
