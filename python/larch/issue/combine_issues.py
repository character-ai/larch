# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: SIM115, TRY004, PLR2004, PERF401
# pylint: skip-file
"""Combine-issues helper CLI verbs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from larch.issue import blocker
from larch.git import gh
from larch.core import proc
from larch.core import redact

_BUSY_RE = re.compile(r"^(?:\[(?:DESIGNING|IMPLEMENTING|STALLED|DONE|PLANNED|IN PROGRESS)\]\s|\[LOCKED\])")
_OOS_RE = re.compile(r"^\[OOS\]\s")
_BLOCKS_LINE_RE = re.compile(r"^(?:Blocks|Blocking)[ \t]+#([0-9]+)(?:[^0-9]|$)", re.IGNORECASE)
_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?")
_EXAMPLE_PREFIX_RE = re.compile(r"^(?:example|examples|e\.g\.|eg\.|for example|sample)\b", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_NEGATION_RE = re.compile(r"\b(?:does\s+not|do\s+not|did\s+not|not|no|never|without)\b", re.IGNORECASE)
_NEGATION_SCOPE_BOUNDARY_RE = re.compile(r"(?:[.;:!?]|\b(?:and|but|however|then|yet)\b)", re.IGNORECASE)
_WRITE_SUCCESS = {"written", "already_present"}
_INHERITED_SAFE_PHASES = {"inherited_safe", "inherited_reclassified_safe"}
_INHERITED_EXCEPTION_PHASES = {"inherited_exception", "inherited_reclassified_exception"}
_INHERITED_WRITE_PHASES = _INHERITED_SAFE_PHASES | _INHERITED_EXCEPTION_PHASES


def _repo() -> str | None:
    res = proc.run(["gh", "repo", "view", "--json", "nameWithOwner"])
    if res.returncode != 0:
        return None
    try:
        data: object = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    val: object | None = data.get("nameWithOwner") if isinstance(data, dict) else None
    return str(val) if val else None


def _resolve_repo(explicit: str = "") -> str | None:
    if explicit:
        return explicit
    return gh.resolve_repo(proc)


def _emit_json(payload: dict[str, Any]) -> int:
    json.dump(payload, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _load_json_file(path: str, *, desc: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{desc}: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{desc}: invalid JSON: {exc}") from exc


def _fail_json_error(message: str) -> int:
    print(f"ERROR={message}", file=sys.stderr)
    return 1


def _positive_int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    return None


def _parse_issue_csv(raw: str, *, arg_name: str = "--issues") -> list[int]:
    if not raw.strip():
        raise ValueError(f"{arg_name} must contain at least one positive integer")
    values: list[int] = []
    seen: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        value = _positive_int_value(token)
        if value is None:
            raise ValueError(f"{arg_name} values must be positive integers: {token!r}")
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _parse_source_to_combined(data: Any) -> dict[int, list[int]]:
    if not isinstance(data, dict):
        raise ValueError("source-to-combined JSON must be an object")
    out: dict[int, list[int]] = {}
    for raw_source, raw_combined in data.items():
        source = _positive_int_value(raw_source)
        if source is None:
            raise ValueError("source-to-combined keys must be positive integers")
        raw_values = raw_combined if isinstance(raw_combined, list) else [raw_combined]
        combined_values: list[int] = []
        seen: set[int] = set()
        for raw_value in raw_values:
            combined = _positive_int_value(raw_value)
            if combined is None:
                raise ValueError("source-to-combined values must be positive integers or lists of positive integers")
            if combined not in seen:
                seen.add(combined)
                combined_values.append(combined)
        if not combined_values:
            raise ValueError("source-to-combined values must not be empty")
        out[source] = combined_values
    return out


def _source_mapping_wire_value(values: list[int]) -> int | list[int]:
    return values[0] if len(values) == 1 else values


def _merge_source_to_combined_fragment(*, accumulated: Any, fragment: Any) -> dict[str, int | list[int]]:
    merged = _parse_source_to_combined(accumulated)
    incoming = _parse_source_to_combined(fragment)
    for source, combined_values in incoming.items():
        merged[source] = sorted(set(merged.get(source, []) + combined_values))
    return {
        str(source): _source_mapping_wire_value(values)
        for source, values in sorted(merged.items())
    }


def _remap_issue_hosts(*, issue: int, source_to_combined: dict[int, list[int]]) -> list[int]:
    return source_to_combined.get(issue, [issue])


def _edge_key(edge: tuple[int, int] | list[int]) -> str:
    return f"{int(edge[0])}:{int(edge[1])}"


def _edge_list(edge: tuple[int, int]) -> list[int]:
    return [edge[0], edge[1]]


def _has_scoped_negation(prefix: str) -> bool:
    clause = _NEGATION_SCOPE_BOUNDARY_RE.split(prefix)[-1]
    return _NEGATION_RE.search(clause) is not None


def _edge_record(edge: tuple[int, int], source_issues: list[int], reason: str, *, meta: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    client, blocker_issue = edge
    record: dict[str, Any] = {
        "edge": [client, blocker_issue],
        "client_issue": client,
        "blocker_issue": blocker_issue,
        "source_issues": source_issues,
        "reason": reason,
    }
    if meta is not None:
        client_meta = meta.get(client, {})
        blocker_meta = meta.get(blocker_issue, {})
        record["client_title"] = str(client_meta.get("title") or "")
        record["blocker_title"] = str(blocker_meta.get("title") or "")
    return record


def _normal_edge(value: Any, *, desc: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{desc}: edge must be [client_issue, blocker_issue]")
    client = _positive_int_value(value[0])
    blocker_issue = _positive_int_value(value[1])
    if client is None or blocker_issue is None:
        raise ValueError(f"{desc}: edge values must be positive integers")
    return client, blocker_issue


def _load_edge_pair_list(path: str, *, desc: str) -> set[tuple[int, int]]:
    data = _load_json_file(path, desc=desc)
    if not isinstance(data, list):
        raise ValueError(f"{desc}: expected a JSON list")
    return {_normal_edge(item, desc=desc) for item in data}


def _warning(*, issue: int, direction: str, result: proc.CommandResult) -> dict[str, Any]:
    err = redact.redact((result.stderr or result.stdout or "dependency read failed")[:500]).strip()
    code = "dependency_read_failed"
    if direction == "blocking" and re.search(r"404|not found|unavailable|preview", err, re.IGNORECASE):
        code = "blocking_endpoint_unavailable"
    return {"source_issue": issue, "direction": direction, "code": code, "message": err}


def _dep_numbers(text: str) -> list[int]:
    rows = gh.loads_json_paginated_list(text or "[]")
    nums: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = _positive_int_value(row.get("number"))
        if number is not None:
            nums.add(number)
    return sorted(nums)


def _parse_prose_blocks(text: str) -> list[int]:
    refs: set[int] = set()
    in_fence = False
    for raw_line in (text or "").splitlines():
        if _CODE_FENCE_RE.match(raw_line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`\n]*`", "", raw_line).replace("*", "").replace("_", "")
        line = _MARKDOWN_PREFIX_RE.sub("", line).strip()
        if not line or line.startswith("<!--") or _EXAMPLE_PREFIX_RE.match(line):
            continue
        match = _BLOCKS_LINE_RE.match(line)
        if match and _has_scoped_negation(line[: match.start()]):
            continue
        if match:
            refs.add(int(match.group(1)))
    return sorted(refs)


def _require_status_ok(data: Any, *, desc: str) -> None:
    if isinstance(data, dict) and "status" in data and str(data.get("status") or "") != "ok":
        raise ValueError(f"{desc}: status is {data.get('status')!r}")


def _read_deps_for_issue(*, repo: str, issue: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    entry: dict[str, Any] = {"blocked_by": [], "blocking": [], "read_ok": True}
    for direction, reader in (("blocked_by", gh.issue_blocked_by_read), ("blocking", gh.issue_blocking_read)):
        result = reader(proc, str(issue), repo=repo)
        if result.returncode != 0:
            entry["read_ok"] = False
            warn = _warning(issue=issue, direction=direction, result=result)
            warnings.append(warn)
            failed.append({"source_issue": issue, "direction": direction, "error": warn["message"]})
            continue
        try:
            entry[direction] = _dep_numbers(result.stdout)
        except Exception as exc:
            entry["read_ok"] = False
            message = redact.redact(str(exc)).strip()
            warnings.append({"source_issue": issue, "direction": direction, "code": "dependency_json_invalid", "message": message})
            failed.append({"source_issue": issue, "direction": direction, "error": message})
    return entry, failed, warnings


def fetch_deps_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues fetch-deps")
    p.add_argument("--repo", default="")
    p.add_argument("--issues", required=True)
    args = p.parse_args(argv)
    try:
        issues = _parse_issue_csv(args.issues)
    except ValueError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    out: dict[str, Any] = {"status": "ok", "issues": {}, "failed_issue_reads": [], "warnings": []}
    for issue in issues:
        entry, failed, warnings = _read_deps_for_issue(repo=repo, issue=issue)
        out["issues"][str(issue)] = entry
        out["failed_issue_reads"].extend(failed)
        out["warnings"].extend(warnings)
    return _emit_json(out)


def _combined_issue_rows(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("combined-issues JSON must be a list")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("combined-issues entries must be objects")
        number = _positive_int_value(item.get("number"))
        if number is None:
            raise ValueError("combined-issues entries require positive integer number")
        source_issues = item.get("source_issues", [])
        if not isinstance(source_issues, list):
            raise ValueError("combined-issues source_issues must be a list")
        rows.append({
            "number": number,
            "title": str(item.get("title") or ""),
            "state": "open",
            "labels": item.get("labels", []),
            "body": str(item.get("body") or ""),
            "source_issues": sorted(n for n in (_positive_int_value(v) for v in source_issues) if n is not None),
        })
    return rows


def _open_issue_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("issues", [])
    if not isinstance(data, list):
        raise ValueError("open-issues JSON must contain an issues list")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        number = _positive_int_value(item.get("number"))
        if number is None:
            continue
        rows.append({
            "number": number,
            "title": str(item.get("title") or ""),
            "state": str(item.get("state") or ""),
            "labels": item.get("labels", []),
            "body": str(item.get("body") or ""),
        })
    return rows


def _metadata(*, open_rows: list[dict[str, Any]], combined_rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    meta: dict[int, dict[str, Any]] = {}
    for row in combined_rows + open_rows:
        number = _positive_int_value(row.get("number"))
        if number is not None:
            meta[number] = row
    return meta


def _blocker_state_warning(*, issue: int, message: str) -> dict[str, Any]:
    redacted = redact.redact((message or "blocker state read failed")[:500]).strip()
    return {"issue": issue, "code": "blocker_state_read_failed", "message": redacted}


def _enrich_missing_blockers(*, meta: dict[int, dict[str, Any]], edges: Any, repo: str, warnings: list[Any]) -> None:
    missing_blockers = sorted({edge[1] for edge in edges if edge[1] not in meta})
    for blocker_issue_number in missing_blockers:
        result = gh.issue_view_field_read(proc, str(blocker_issue_number), "number,state,title", repo=repo)
        if result.returncode != 0:
            warnings.append(_blocker_state_warning(issue=blocker_issue_number, message=result.stderr or result.stdout))
            continue
        try:
            data: object = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            warnings.append(_blocker_state_warning(issue=blocker_issue_number, message=str(exc)))
            continue
        if not isinstance(data, dict):
            warnings.append(_blocker_state_warning(issue=blocker_issue_number, message="blocker state response was not an object"))
            continue
        number = _positive_int_value(data.get("number"))
        if number is None:
            warnings.append(_blocker_state_warning(issue=blocker_issue_number, message="blocker state response missing positive number"))
            continue
        meta[blocker_issue_number] = {
            "number": number,
            "title": str(data.get("title") or ""),
            "state": str(data.get("state") or ""),
            "labels": [],
            "body": "",
        }


def _combined_oos_numbers(*, combined_rows: list[dict[str, Any]], meta: dict[int, dict[str, Any]]) -> set[int]:
    out: set[int] = set()
    for row in combined_rows:
        number = _positive_int_value(row.get("number"))
        if number is None:
            continue
        live_title = str(meta.get(number, row).get("title") or "")
        if _is_oos_title(live_title):
            out.add(number)
    return out


def _is_oos_title(title: str) -> bool:
    return _OOS_RE.match(title or "") is not None


def _classify_edge(*, edge: tuple[int, int], meta: dict[int, dict[str, Any]], combined_oos: set[int]) -> tuple[str, str]:
    client, blocker_issue = edge
    client_meta = meta.get(client)
    blocker_meta = meta.get(blocker_issue)
    if client_meta is None or blocker_meta is None:
        return "unknown", "missing issue metadata"
    if str(client_meta.get("state") or "").lower() != "open":
        return "unknown", "client issue is not known open"
    blocker_state = str(blocker_meta.get("state") or "").lower()
    if blocker_state == "closed":
        return "satisfied", "blocker issue already closed (dependency satisfied)"
    if blocker_state != "open":
        return "unknown", "blocker issue is not known open"
    client_title = str(client_meta.get("title") or "")
    if blocker_issue in combined_oos and not _is_oos_title(client_title):
        return "exception", "non-OOS open issue would be blocked by a newly combined [OOS] issue"
    return "safe", "edge does not block a non-OOS issue on newly combined [OOS] work"


def _dep_entry(*, source: int, data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        issues = data.get("issues", {})
        if isinstance(issues, dict) and isinstance(issues.get(str(source)), dict):
            return cast("dict[str, Any]", issues[str(source)])
        if isinstance(issues, list):
            for row in issues:
                if isinstance(row, dict) and _positive_int_value(row.get("source_issue") or row.get("number")) == source:
                    return row
    return {"blocked_by": [], "blocking": [], "read_ok": False}


def plan_inherited_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues plan-inherited")
    p.add_argument("--deps-file", required=True)
    p.add_argument("--source-to-combined-file", required=True)
    p.add_argument("--open-issues-file", required=True)
    p.add_argument("--combined-issues-file", required=True)
    p.add_argument("--repo", default="")
    args = p.parse_args(argv)
    try:
        deps = _load_json_file(args.deps_file, desc="deps-file")
        source_to_combined = _parse_source_to_combined(_load_json_file(args.source_to_combined_file, desc="source-to-combined-file"))
        open_data = _load_json_file(args.open_issues_file, desc="open-issues-file")
        _require_status_ok(deps, desc="deps-file")
        _require_status_ok(open_data, desc="open-issues-file")
        open_rows = _open_issue_rows(open_data)
        combined_rows = _combined_issue_rows(_load_json_file(args.combined_issues_file, desc="combined-issues-file"))
    except ValueError as exc:
        return _fail_json_error(str(exc))

    meta = _metadata(open_rows=open_rows, combined_rows=combined_rows)
    combined_oos = _combined_oos_numbers(combined_rows=combined_rows, meta=meta)
    edge_sources: dict[tuple[int, int], set[int]] = defaultdict(set)
    self_edges_skipped = 0
    duplicate_edges_skipped = 0
    per_source: dict[str, dict[str, Any]] = {}
    warnings: list[Any] = []
    if isinstance(deps, dict) and isinstance(deps.get("warnings"), list):
        warnings.extend(deps["warnings"])

    for source, combined_hosts in sorted(source_to_combined.items()):
        entry = _dep_entry(source=source, data=deps)
        reasons: list[str] = []
        if not bool(entry.get("read_ok")):
            reasons.append("dependency_read_failed")
        per_source[str(source)] = {"eligible": not reasons, "reasons": reasons}
        for blocker_issue in sorted(n for n in (_positive_int_value(v) for v in entry.get("blocked_by", [])) if n is not None):
            for combined in combined_hosts:
                for blocker_host in _remap_issue_hosts(issue=blocker_issue, source_to_combined=source_to_combined):
                    edge = (combined, blocker_host)
                    if edge[0] == edge[1]:
                        self_edges_skipped += 1
                        continue
                    if source in edge_sources[edge] or edge_sources[edge]:
                        duplicate_edges_skipped += 1
                    edge_sources[edge].add(source)
        for client in sorted(n for n in (_positive_int_value(v) for v in entry.get("blocking", [])) if n is not None):
            for client_host in _remap_issue_hosts(issue=client, source_to_combined=source_to_combined):
                for combined in combined_hosts:
                    edge = (client_host, combined)
                    if edge[0] == edge[1]:
                        self_edges_skipped += 1
                        continue
                    if source in edge_sources[edge] or edge_sources[edge]:
                        duplicate_edges_skipped += 1
                    edge_sources[edge].add(source)

    if args.repo:
        repo = _resolve_repo(args.repo)
        if repo:
            _enrich_missing_blockers(meta=meta, edges=edge_sources, repo=repo, warnings=warnings)
        else:
            warnings.append({"code": "repo_resolve_failed", "message": "Could not determine repository for blocker enrichment"})

    safe: list[dict[str, Any]] = []
    exception: list[dict[str, Any]] = []
    satisfied: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    edge_provenance: dict[str, list[int]] = {}
    for edge in sorted(edge_sources):
        sources = sorted(edge_sources[edge])
        edge_provenance[_edge_key(edge)] = sources
        bucket, reason = _classify_edge(edge=edge, meta=meta, combined_oos=combined_oos)
        record = _edge_record(edge, sources, reason, meta=meta)
        if bucket == "safe":
            safe.append(record)
        elif bucket == "exception":
            exception.append(record)
        elif bucket == "satisfied":
            satisfied.append(record)
        else:
            unknown.append(record)
            for source in sources:
                state = per_source.setdefault(str(source), {"eligible": True, "reasons": []})
                state["eligible"] = False
                if "unknown_inherited_classification" not in state["reasons"]:
                    state["reasons"].append("unknown_inherited_classification")
    for state in per_source.values():
        if state.get("reasons"):
            state["eligible"] = False
    return _emit_json({
        "status": "ok",
        "safe_edges": safe,
        "exception_edges": exception,
        "satisfied_edges": satisfied,
        "unknown_edges": unknown,
        "edge_provenance": edge_provenance,
        "per_source_initial_eligibility": per_source,
        "self_edges_skipped": self_edges_skipped,
        "duplicate_edges_skipped": duplicate_edges_skipped,
        "warnings": warnings,
    })


def _records_by_edge(*, data: Any, key: str) -> dict[tuple[int, int], list[dict[str, Any]]]:
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise ValueError(f"{key} JSON must be an object with {key} list")
    out: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for item in data[key]:
        if not isinstance(item, dict):
            raise ValueError(f"{key} entries must be objects")
        edge = _normal_edge(item.get("edge"), desc=key)
        out[edge].append(item)
    return out


def _successful_write_edges(data: Any, *, phases: set[str] | None = None) -> set[tuple[int, int]]:
    records = _records_by_edge(data=data, key="write_results")
    out: set[tuple[int, int]] = set()
    for edge, items in records.items():
        if any(str(item.get("status")) in _WRITE_SUCCESS and (phases is None or str(item.get("phase")) in phases) for item in items):
            out.add(edge)
    return out


def _decision_for_edge(*, decisions: dict[tuple[int, int], list[dict[str, Any]]], edge: tuple[int, int]) -> str:
    items = decisions.get(edge, [])
    if any(str(item.get("decision")) == "unresolved" for item in items):
        return "unresolved"
    if any(str(item.get("decision")) == "approved" for item in items):
        return "approved"
    if any(str(item.get("decision")) == "rejected" for item in items):
        return "rejected"
    return "missing"


def _source_issues_from_record(record: dict[str, Any]) -> list[int]:
    source_issues = record.get("source_issues", [])
    return sorted(n for n in (_positive_int_value(v) for v in source_issues if not isinstance(v, dict)) if n is not None)


def _write_outcome(*, rows: list[dict[str, Any]], phases: set[str]) -> str:
    has_failed = False
    for row in rows:
        phase = str(row.get("phase") or "")
        if phase in phases:
            status = str(row.get("status") or "")
            if status in _WRITE_SUCCESS:
                return "success"
            if status in {"failed", "unresolved"}:
                has_failed = True
    if has_failed:
        return "failed"
    return "missing"


def close_eligible_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues close-eligible")
    p.add_argument("--inherited-plan-file", required=True)
    p.add_argument("--write-results-file", required=True)
    p.add_argument("--exception-decisions-file", required=True)
    p.add_argument("--source-to-combined-file", required=True)
    p.add_argument("--blocked-sources-file", required=True)
    args = p.parse_args(argv)
    try:
        plan = _load_json_file(args.inherited_plan_file, desc="inherited-plan-file")
        write_results = _load_json_file(args.write_results_file, desc="write-results-file")
        exception_decisions = _load_json_file(args.exception_decisions_file, desc="exception-decisions-file")
        source_to_combined = _parse_source_to_combined(_load_json_file(args.source_to_combined_file, desc="source-to-combined-file"))
        blocked_data = _load_json_file(args.blocked_sources_file, desc="blocked-sources-file")
        writes_by_edge = _records_by_edge(data=write_results, key="write_results")
        decisions_by_edge = _records_by_edge(data=exception_decisions, key="decisions")
    except ValueError as exc:
        return _fail_json_error(str(exc))
    if not isinstance(plan, dict):
        return _fail_json_error("inherited plan must be an object")
    if str(plan.get("status") or "") != "ok":
        return _fail_json_error("inherited-plan-file: status must be 'ok'")
    per_source_raw = plan.get("per_source_initial_eligibility")
    if not isinstance(per_source_raw, dict):
        return _fail_json_error("inherited-plan-file: per_source_initial_eligibility must be an object")
    missing_initial_eligibility = [
        source
        for source in sorted(source_to_combined)
        if not isinstance(per_source_raw.get(str(source)), dict)
    ]
    if missing_initial_eligibility:
        return _fail_json_error(
            "inherited-plan-file: missing per_source_initial_eligibility for source issues: "
            + ",".join(str(source) for source in missing_initial_eligibility)
        )
    if not isinstance(blocked_data, dict) or not isinstance(blocked_data.get("blocked_sources", []), list):
        return _fail_json_error("blocked-sources JSON must be an object with blocked_sources list")

    reasons: dict[str, list[str]] = {str(source): [] for source in source_to_combined}
    blocked_sources: set[int] = set()
    for item in blocked_data.get("blocked_sources", []):
        if isinstance(item, dict):
            source = _positive_int_value(item.get("source_issue"))
            if source is not None:
                blocked_sources.add(source)
                reasons.setdefault(str(source), []).append(str(item.get("reason") or "blocked_source"))

    per_source = per_source_raw
    for raw_source, state in per_source.items():
        source = _positive_int_value(raw_source)
        if source is None or not isinstance(state, dict):
            continue
        if not bool(state.get("eligible", True)):
            for reason in state.get("reasons", []) if isinstance(state.get("reasons", []), list) else ["initially_ineligible"]:
                reasons.setdefault(str(source), []).append(str(reason))

    safe_edges = plan.get("safe_edges", []) if isinstance(plan.get("safe_edges", []), list) else []
    exception_edges = plan.get("exception_edges", []) if isinstance(plan.get("exception_edges", []), list) else []
    unknown_edges = plan.get("unknown_edges", []) if isinstance(plan.get("unknown_edges", []), list) else []
    for item in unknown_edges:
        if not isinstance(item, dict):
            continue
        edge = _normal_edge(item.get("edge"), desc="unknown_edges")
        for source in _source_issues_from_record(item):
            reasons.setdefault(str(source), []).append(f"unknown_inherited_classification:{_edge_key(edge)}")
    for item in safe_edges:
        if not isinstance(item, dict):
            continue
        edge = _normal_edge(item.get("edge"), desc="safe_edges")
        if _write_outcome(rows=writes_by_edge.get(edge, []), phases=_INHERITED_SAFE_PHASES) != "success":
            for source in _source_issues_from_record(item):
                reasons.setdefault(str(source), []).append(f"inherited_safe_write_missing_or_failed:{_edge_key(edge)}")
    for item in exception_edges:
        if not isinstance(item, dict):
            continue
        edge = _normal_edge(item.get("edge"), desc="exception_edges")
        decision = _decision_for_edge(decisions=decisions_by_edge, edge=edge)
        write_outcome = _write_outcome(rows=writes_by_edge.get(edge, []), phases=_INHERITED_EXCEPTION_PHASES)
        for source in _source_issues_from_record(item):
            if write_outcome == "failed":
                reasons.setdefault(str(source), []).append(f"inherited_exception_write_failed:{_edge_key(edge)}")
            elif decision == "rejected":
                reasons.setdefault(str(source), []).append(f"inherited_exception_rejected:{_edge_key(edge)}")
            elif decision == "approved" and write_outcome == "success":
                continue
            elif decision == "approved":
                reasons.setdefault(str(source), []).append(f"approved_exception_write_missing_or_failed:{_edge_key(edge)}")
            elif decision == "unresolved":
                reasons.setdefault(str(source), []).append(f"inherited_exception_unresolved:{_edge_key(edge)}")
            else:
                reasons.setdefault(str(source), []).append(f"inherited_exception_decision_missing:{_edge_key(edge)}")

    eligible_by_combined: dict[str, list[int]] = defaultdict(list)
    ineligible_sources: list[int] = []
    for source, combined_hosts in sorted(source_to_combined.items()):
        source_reasons = [r for r in reasons.get(str(source), []) if not r.startswith("inherited_exception_rejected:")]
        if len(combined_hosts) != 1:
            source_reasons.append("multi_combined_host_closure_unsupported")
            reasons.setdefault(str(source), []).append("multi_combined_host_closure_unsupported")
        if source in blocked_sources or source_reasons:
            ineligible_sources.append(source)
        else:
            eligible_by_combined[str(combined_hosts[0])].append(source)
    return _emit_json({
        "eligible_by_combined": dict(sorted(eligible_by_combined.items(), key=lambda kv: int(kv[0]))),
        "ineligible_sources": ineligible_sources,
        "reasons": reasons,
        "counts": {
            "eligible_sources": sum(len(v) for v in eligible_by_combined.values()),
            "ineligible_sources": len(ineligible_sources),
            "blocked_sources": len(blocked_sources),
        },
    })


def list_open_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues list-open")
    p.add_argument("--repo", default="")
    args = p.parse_args(argv)
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    result = proc.run(["gh", "api", "--paginate", f"repos/{repo}/issues?state=open&per_page=100"])
    warnings: list[dict[str, str]] = []
    if result.returncode != 0:
        _emit_json({"status": "failed", "issues": [], "warnings": [{"code": "gh_api_failed", "message": "failed to list open issues"}]})
        return 1
    try:
        rows = gh.loads_json_paginated_list(result.stdout)
    except Exception as exc:
        _emit_json({"status": "failed", "issues": [], "warnings": [{"code": "json_invalid", "message": str(exc)}]})
        return 1
    issues: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("pull_request") is not None:
            continue
        number = _positive_int_value(row.get("number"))
        if number is None or str(row.get("state") or "").lower() != "open":
            continue
        issues.append({
            "number": number,
            "title": str(row.get("title") or ""),
            "state": "open",
            "labels": row.get("labels", []),
            "body": str(row.get("body") or ""),
        })
    return _emit_json({"status": "ok", "issues": sorted(issues, key=lambda item: item["number"]), "warnings": warnings})


def _parse_issue_number(text: str) -> str:
    nums = re.findall(r"/issues/([0-9]+)", text)
    return nums[-1] if nums else ""


def _combined_away_close_comment(*, issue: str, combined: str) -> str:
    return (
        f"Combined into #{combined}\n\n"
        f"<!-- larch:combined-away source=#{issue} target=#{combined} -->"
    )


def _close_issue_with_retry(issue: str, repo: str, combined: str, *, attempts: int = 3) -> proc.CommandResult:
    result: proc.CommandResult | None = None
    comment = _combined_away_close_comment(issue=issue, combined=combined)
    for attempt in range(attempts):
        result = proc.run(["gh", "issue", "close", issue, "--repo", repo, "--comment", comment])
        if result.returncode == 0:
            return result
        if attempt + 1 < attempts:
            time.sleep(1)
    assert result is not None
    return result


def _close_stale_issue(*, issue: str, repo: str, reason: str, comment: str | None) -> proc.CommandResult:
    argv = ["gh", "issue", "close", issue, "--repo", repo, "--reason", reason]
    if comment is not None:
        argv.extend(["--comment", comment])
    return proc.run(argv)


def apply_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues apply")
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--source-issues", required=True)
    p.add_argument("--repo", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--defer-close", action="store_true")
    args = p.parse_args(argv)
    body = Path(args.body_file)
    if not body.is_file():
        print(f"ERROR=Missing or unreadable --body-file: {args.body_file}", file=sys.stderr)
        return 1
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    issue_tokens = [x.strip() for x in args.source_issues.split(",") if x.strip()]
    if not issue_tokens:
        print("ERROR=No source issues provided", file=sys.stderr)
        return 1
    try:
        issues = [str(issue) for issue in _parse_issue_csv(args.source_issues, arg_name="--source-issues")]
    except ValueError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        print("DRY_RUN=true")
        print(f"WOULD_CREATE={args.title}")
        print(f"WOULD_CLOSE={len(issues)} issues: {','.join(issues)}")
        if args.defer_close:
            print("CLOSING_DEFERRED=true")
        return 0
    red_title = redact.redact(args.title).rstrip("\n")
    red_body = tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="combine-redacted-", dir="/tmp", delete=False)
    red_body.write(redact.redact(body.read_text(encoding="utf-8")))
    red_body.close()
    try:
        create = proc.run(["gh", "issue", "create", "--repo", repo, "--title", red_title, "--body-file", red_body.name])
        if create.returncode != 0:
            print("ERROR=Failed to create combined issue (gh output withheld)", file=sys.stderr)
            return 1
        combined = _parse_issue_number(create.stdout + create.stderr)
        if not combined:
            print("ERROR=Could not parse issue number from gh issue create output (output withheld)", file=sys.stderr)
            return 1
        if args.defer_close:
            combined_issue = _positive_int_value(combined)
            if combined_issue is None:
                print("ERROR=Could not parse issue number from gh issue create output (output withheld)", file=sys.stderr)
                return 1
            source_to_combined_fragment: dict[str, int] = dict.fromkeys(issues, combined_issue)
            print("DRY_RUN=false")
            print(f"COMBINED_ISSUE={combined}")
            print(f"SOURCE_ISSUES={','.join(issues)}")
            print("SOURCE_TO_COMBINED_JSON_FRAGMENT=" + json.dumps(source_to_combined_fragment, sort_keys=True, separators=(",", ":")))
            print("CLOSING_DEFERRED=true")
            print("CLOSED_ISSUES=0")
            return 0
        closed = 0
        warnings: list[str] = []
        for issue in issues:
            res = _close_issue_with_retry(issue, repo, combined)
            if res.returncode == 0:
                closed += 1
            else:
                warnings.append(f"Failed to close #{issue}: {redact.redact((res.stderr or res.stdout)[:500]).strip()}")
        if warnings:
            print(f"WARNING={'; '.join(warnings)}", file=sys.stderr)
        print("DRY_RUN=false")
        print(f"COMBINED_ISSUE={combined}")
        print(f"CLOSED_ISSUES={closed}")
        return 0
    finally:
        Path(red_body.name).unlink(missing_ok=True)


def close_sources_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues close-sources")
    p.add_argument("--repo", default="")
    p.add_argument("--combined-issue", required=True)
    p.add_argument("--source-issues", required=True)
    args = p.parse_args(argv)
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    try:
        sources = _parse_issue_csv(args.source_issues, arg_name="--source-issues")
    except ValueError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    combined = _positive_int_value(args.combined_issue)
    if combined is None:
        print("ERROR=--combined-issue must be a positive integer", file=sys.stderr)
        return 1
    closed = 0
    warnings: list[str] = []
    for source in sources:
        skip_reason = _source_close_skip_reason(repo=repo, source=source)
        if skip_reason is not None:
            warnings.append(f"Skipped #{source}: {skip_reason}")
            continue
        res = _close_issue_with_retry(str(source), repo, str(combined))
        if res.returncode == 0:
            closed += 1
        else:
            warnings.append(f"Failed to close #{source}: {redact.redact((res.stderr or res.stdout)[:500]).strip()}")
    if warnings:
        print(f"WARNING={'; '.join(warnings)}", file=sys.stderr)
    print(f"CLOSED_ISSUES={closed}")
    print(f"PARTIAL={str(bool(warnings)).lower()}")
    return 0


def close_stale_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues close-stale")
    p.add_argument("--issues", required=True)
    p.add_argument("--repo", default="")
    p.add_argument("--reason", required=True)
    p.add_argument("--comment-file", default="")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.reason not in {"completed", "not planned"}:
        print("ERROR=--reason must be one of: completed, not planned", file=sys.stderr)
        return 1
    try:
        sources = _parse_issue_csv(args.issues)
    except ValueError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    comment: str | None = None
    if args.comment_file:
        comment_path = Path(args.comment_file)
        if not comment_path.is_file():
            print(f"ERROR=Missing or unreadable --comment-file: {args.comment_file}", file=sys.stderr)
            return 1
        try:
            comment = comment_path.read_text(encoding="utf-8")
        except OSError:
            print(f"ERROR=Missing or unreadable --comment-file: {args.comment_file}", file=sys.stderr)
            return 1
    if args.dry_run:
        print("DRY_RUN=true")
        print("WOULD_CLOSE=" + ",".join(str(source) for source in sources))
        print("CLOSED_ISSUES=0")
        print("PARTIAL=false")
        return 0
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    closed = 0
    warnings: list[str] = []
    for source in sources:
        skip_reason = _source_close_skip_reason(repo=repo, source=source)
        if skip_reason is not None:
            warnings.append(f"Skipped #{source}: {redact.redact(skip_reason).strip()}")
            continue
        res = _close_stale_issue(issue=str(source), repo=repo, reason=args.reason, comment=comment)
        if res.returncode == 0:
            closed += 1
        else:
            warnings.append(f"Failed to close #{source}: {redact.redact((res.stderr or res.stdout)[:500]).strip()}")
    if warnings:
        print(f"WARNING={'; '.join(warnings)}", file=sys.stderr)
    print(f"CLOSED_ISSUES={closed}")
    print(f"PARTIAL={str(bool(warnings)).lower()}")
    return 0


def _source_close_skip_reason(*, repo: str, source: int) -> str | None:
    result = gh.issue_view_field_read(proc, str(source), "title,state", repo=repo)
    if result.returncode != 0:
        return "could not refresh source issue state"
    try:
        data: object = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return "could not parse source issue state"
    if not isinstance(data, dict):
        return "could not parse source issue state"
    state = str(data.get("state") or "")
    if state.lower() != "open":
        return f"source issue is not open ({state or 'unknown'})"
    title = str(data.get("title") or "")
    if _BUSY_RE.match(title):
        return "source issue has busy title prefix"
    return None


def _issue_content_from_view(*, result: proc.CommandResult, fallback: dict[str, Any]) -> tuple[str, str, str]:
    if result.returncode != 0:
        raise ValueError("issue view failed")
    try:
        data: object = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"issue view JSON invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("issue view JSON must be an object")
    return (
        str(data.get("title") or fallback.get("title") or ""),
        str(data.get("body") or fallback.get("body") or ""),
        str(data.get("state") or fallback.get("state") or ""),
    )


def _comment_rows(result: proc.CommandResult) -> list[dict[str, Any]]:
    if result.returncode != 0:
        raise ValueError("issue comments read failed")
    rows = gh.loads_json_paginated_list(result.stdout or "[]")
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def _candidate_reason(*, kind: str, current: int, ref: int) -> str:
    if kind == "blocked_by":
        return f"issue #{current} prose says it is blocked by #{ref}"
    return f"issue #{current} prose says it blocks #{ref}"


def prose_audit_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues prose-audit")
    p.add_argument("--repo", required=True)
    p.add_argument("--combined-issues", required=True)
    p.add_argument("--open-issues-file", required=True)
    p.add_argument("--existing-edges-file", required=True)
    p.add_argument("--source-to-combined-file", required=True)
    args = p.parse_args(argv)
    try:
        combined_issue_numbers = set(_parse_issue_csv(args.combined_issues, arg_name="--combined-issues"))
        open_data = _load_json_file(args.open_issues_file, desc="open-issues-file")
        _require_status_ok(open_data, desc="open-issues-file")
        open_rows = _open_issue_rows(open_data)
        existing_edges = _load_edge_pair_list(args.existing_edges_file, desc="existing-edges-file")
        source_to_combined = _parse_source_to_combined(_load_json_file(args.source_to_combined_file, desc="source-to-combined-file"))
    except ValueError as exc:
        return _fail_json_error(str(exc))
    meta = _metadata(open_rows=open_rows, combined_rows=[])
    for combined_issue in combined_issue_numbers:
        meta.setdefault(combined_issue, {"number": combined_issue, "title": "", "state": "", "labels": [], "body": ""})
    open_numbers = {row["number"] for row in open_rows}
    all_to_scan = sorted(open_numbers | combined_issue_numbers)
    candidates_by_edge: dict[tuple[int, int], dict[str, Any]] = {}
    warnings: list[dict[str, Any]] = []

    def add_candidate(*, raw_current: int, ref: int, kind: str, evidence_kind: str, comment_id: int | None = None) -> None:
        for current in _remap_issue_hosts(issue=raw_current, source_to_combined=source_to_combined):
            for mapped_ref in _remap_issue_hosts(issue=ref, source_to_combined=source_to_combined):
                edge = (current, mapped_ref) if kind == "blocked_by" else (mapped_ref, current)
                if edge[0] == edge[1] or edge in existing_edges:
                    continue
                if edge[0] not in meta or edge[1] not in meta:
                    continue
                if str(meta[edge[0]].get("state") or "").lower() != "open" or str(meta[edge[1]].get("state") or "").lower() != "open":
                    continue
                if edge[0] not in combined_issue_numbers and edge[1] not in combined_issue_numbers:
                    continue
                if edge in candidates_by_edge:
                    continue
                record: dict[str, Any] = {
                    "edge": [edge[0], edge[1]],
                    "source_kind": "tier1_prose",
                    "confidence": "explicit",
                    "evidence_kind": evidence_kind,
                    "evidence_issue": raw_current,
                    "reason": _candidate_reason(kind=kind, current=current, ref=mapped_ref),
                }
                if comment_id is not None:
                    record["evidence_comment_id"] = comment_id
                candidates_by_edge[edge] = record

    for issue in all_to_scan:
        fallback = meta.get(issue, {"number": issue, "title": "", "body": "", "state": "open"})
        view = gh.issue_view_field_read(proc, str(issue), "title,body,state", repo=args.repo)
        try:
            title, body_text, state = _issue_content_from_view(result=view, fallback=fallback)
        except ValueError as exc:
            warnings.append({"issue": issue, "code": "issue_view_failed", "message": str(exc)})
            return _emit_json({"status": "failed", "candidates": [], "warnings": warnings}) or 1
        meta[issue] = {
            "number": issue,
            "title": title,
            "state": state,
            "labels": fallback.get("labels", []),
            "body": body_text,
        }

    issues_to_scan = [issue for issue in all_to_scan if str(meta.get(issue, {}).get("state") or "").lower() == "open"]
    for issue in issues_to_scan:
        body_text = str(meta.get(issue, {}).get("body") or "")
        for ref in blocker.parse_prose_blockers(body_text):
            add_candidate(raw_current=issue, ref=ref, kind="blocked_by", evidence_kind="body")
        for ref in _parse_prose_blocks(body_text):
            add_candidate(raw_current=issue, ref=ref, kind="blocks", evidence_kind="body")
        comments = gh.issue_comments_list_read(proc, str(issue), repo=args.repo)
        try:
            rows = _comment_rows(comments)
        except Exception as exc:
            warnings.append({"issue": issue, "code": "comments_read_failed", "message": str(exc)})
            return _emit_json({"status": "failed", "candidates": [], "warnings": warnings}) or 1
        for row in rows:
            text = str(row.get("body") or "")
            comment_id = _positive_int_value(row.get("id"))
            for ref in blocker.parse_prose_blockers(text):
                add_candidate(raw_current=issue, ref=ref, kind="blocked_by", evidence_kind="comment", comment_id=comment_id)
            for ref in _parse_prose_blocks(text):
                add_candidate(raw_current=issue, ref=ref, kind="blocks", evidence_kind="comment", comment_id=comment_id)
    return _emit_json({"status": "ok", "candidates": list(candidates_by_edge.values()), "warnings": warnings})


def _candidate_rows(data: Any, *, desc: str) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("candidates", [])
    if not isinstance(data, list):
        raise ValueError(f"{desc}: expected candidate list")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{desc}: candidate entries must be objects")
        _normal_edge(item.get("edge"), desc=desc)
        rows.append(item)
    return rows


def _decisions_by_edge_value(data: Any) -> dict[tuple[int, int], set[str]]:
    if not isinstance(data, dict) or not isinstance(data.get("decisions", []), list):
        raise ValueError("decided-edges JSON must be an object with decisions list")
    out: dict[tuple[int, int], set[str]] = defaultdict(set)
    for item in data.get("decisions", []):
        if isinstance(item, dict):
            out[_normal_edge(item.get("edge"), desc="decided-edges")].add(str(item.get("decision") or ""))
    return out


def plan_audit_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues plan-audit")
    p.add_argument("--prose-candidates-file", required=True)
    p.add_argument("--tier2-candidates-file", required=True)
    p.add_argument("--existing-edges-file", required=True)
    p.add_argument("--decided-edges-file", required=True)
    p.add_argument("--open-issues-file", required=True)
    p.add_argument("--combined-issues-file", required=True)
    args = p.parse_args(argv)
    try:
        prose = _candidate_rows(_load_json_file(args.prose_candidates_file, desc="prose-candidates-file"), desc="prose-candidates-file")
        tier2: list[dict[str, Any]] = []
        for row in _candidate_rows(_load_json_file(args.tier2_candidates_file, desc="tier2-candidates-file"), desc="tier2-candidates-file"):
            tagged = dict(row)
            tagged["_candidate_origin"] = "tier2"
            tier2.append(tagged)
        existing = _load_edge_pair_list(args.existing_edges_file, desc="existing-edges-file")
        decided = _decisions_by_edge_value(_load_json_file(args.decided_edges_file, desc="decided-edges-file"))
        open_data = _load_json_file(args.open_issues_file, desc="open-issues-file")
        _require_status_ok(open_data, desc="open-issues-file")
        open_rows = _open_issue_rows(open_data)
        combined_rows = _combined_issue_rows(_load_json_file(args.combined_issues_file, desc="combined-issues-file"))
    except ValueError as exc:
        return _fail_json_error(str(exc))
    meta = _metadata(open_rows=open_rows, combined_rows=combined_rows)
    combined_oos = _combined_oos_numbers(combined_rows=combined_rows, meta=meta)
    merged: dict[tuple[int, int], dict[str, Any]] = {}
    duplicate = 0
    for row in prose + tier2:
        edge = _normal_edge(row.get("edge"), desc="candidate")
        edge_decisions = decided.get(edge, set())
        if edge in existing or "rejected" in edge_decisions or "unresolved" in edge_decisions:
            duplicate += 1
            continue
        if edge in merged:
            duplicate += 1
            if str(row.get("source_kind")) == "tier2_semantic" and str(merged[edge].get("source_kind")) != "tier2_semantic":
                merged[edge] = row
            continue
        merged[edge] = row
    auto: list[dict[str, Any]] = []
    approval: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for edge, row in sorted(merged.items()):
        bucket, reason = _classify_edge(edge=edge, meta=meta, combined_oos=combined_oos)
        enriched = {key: value for key, value in row.items() if key != "_candidate_origin"}
        enriched["client_issue"] = edge[0]
        enriched["blocker_issue"] = edge[1]
        enriched["reason"] = str(row.get("reason") or reason)
        source_kind = str(row.get("source_kind") or "")
        if row.get("_candidate_origin") == "tier2" and source_kind != "tier2_semantic":
            enriched["policy_reason"] = "tier2 candidate must declare source_kind=tier2_semantic"
            rejected.append(enriched)
        elif source_kind == "tier2_semantic" and str(row.get("confidence") or "") not in {"low", "medium", "high"}:
            enriched["policy_reason"] = "tier2 candidate missing low, medium, or high confidence"
            rejected.append(enriched)
        elif bucket == "unknown":
            enriched["policy_reason"] = reason
            rejected.append(enriched)
        elif source_kind == "tier2_semantic" or bucket == "exception":
            enriched["approval_reason"] = "Tier-2 semantic edge requires approval" if source_kind == "tier2_semantic" else reason
            approval.append(enriched)
        else:
            auto.append(enriched)
    return _emit_json({
        "auto_write_edges": auto,
        "approval_required_edges": approval,
        "policy_rejected_edges": rejected,
        "duplicate_edges_skipped": duplicate,
        "warnings": warnings,
    })


def fetch_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues fetch")
    p.add_argument("--repo", default="")
    p.add_argument("--oos", action="store_true")
    args = p.parse_args(argv)
    repo = _resolve_repo(args.repo)
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    res = proc.run(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "200", "--json", "number,title,body,labels"])
    if res.returncode != 0:
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    try:
        raw: object = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    if not isinstance(raw, list):
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    out: list[dict[str, Any]] = []
    for issue in raw:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title") or "")
        if args.oos:
            if _OOS_RE.match(title):
                out.append(issue)
        elif not _BUSY_RE.match(title):
            out.append(issue)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="combine-issues-", dir="/tmp", delete=False)
    Path(handle.name).chmod(0o600)
    json.dump(out, handle)
    handle.write("\n")
    handle.close()
    print(f"ISSUES_FILE={handle.name}")
    print(f"COUNT={len(out)}")
    return 0
