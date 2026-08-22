"""Frozen Python owner for the token command cutover in #8797.

This is the retired production implementation trimmed only to its three command
entries and their direct dependencies. The parity suite blocks live service
credentials and exercises it in an isolated sandbox.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from larch.core import proc
from larch.git import gh

_UINT_RE = re.compile(r"^[0-9]+$")


@dataclass(frozen=True)
class BudgetCheckResult:
    status: Literal["cap_hit", "under_cap"]
    total: int
    cap: int
    step: str


@dataclass(frozen=True)
class PrLineCountResult:
    status: Literal["ok", "skipped", "unavailable"]
    code_added: int | None = None
    code_deleted: int | None = None
    logs_added: int | None = None
    logs_deleted: int | None = None
    reason: str = ""

    def kv_items(self) -> tuple[tuple[str, str], ...]:
        items: list[tuple[str, str]] = [("LINES_STATUS", self.status)]
        if self.status == "ok":
            items.extend(
                (
                    ("CODE_ADDED", str(self.code_added)),
                    ("CODE_DELETED", str(self.code_deleted)),
                    ("LOGS_ADDED", str(self.logs_added)),
                    ("LOGS_DELETED", str(self.logs_deleted)),
                )
            )
        else:
            items.append(("REASON", self.reason))
        return tuple(items)


def _int_field(*, data: Mapping[str, Any], key: str) -> int:
    value = data.get(key, 0)
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _tmp_root(env: Mapping[str, str] | None = None) -> Path | None:
    raw = (env or os.environ).get("TMPDIR") or "/tmp"
    try:
        return Path(raw).resolve(strict=True)
    except OSError:
        return None


def _canonical_dir(path: str | Path) -> Path | None:
    try:
        candidate = Path(path)
        if not candidate.parts:
            return None
        if candidate.is_dir():
            return candidate.resolve(strict=True)
    except OSError:
        return None
    return None


def _validate_under_tmp(raw: str, *, env: Mapping[str, str] | None = None) -> Path:
    env_map: Mapping[str, str] = os.environ if env is None else env
    root = _tmp_root(env_map)
    if root is None:
        raise ValueError("cannot canonicalize TMPDIR")
    if not raw or ".." in Path(raw).parts:
        raise ValueError(f"ledger must not be empty or contain '..': {raw}")
    candidate = Path(raw) if Path(raw).is_absolute() else root / raw
    candidate.parent.mkdir(parents=True, exist_ok=True)
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    allowed = [root]
    private = _canonical_dir("/private/tmp")
    if private is not None:
        allowed.append(private)
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        workflow_root = _canonical_dir(env_map.get(key, ""))
        if workflow_root is not None:
            allowed.append(workflow_root)
    if not any(resolved == base or base in resolved.parents for base in allowed):
        raise ValueError(f"ledger must resolve under TMPDIR: {raw}")
    return resolved


def resolve_session_id(*, env: Mapping[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    if env_map.get("LARCH_TOKEN_SESSION_ID"):
        return str(env_map["LARCH_TOKEN_SESSION_ID"])
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        root = env_map.get(key, "")
        candidate = Path(root) / "session-id" if root else None
        if candidate and candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace").strip()
    return _sha256_hex(str(Path.cwd().resolve()))


def resolve_token_ledger_path(
    *, ledger: str | None = None, env: Mapping[str, str] | None = None
) -> Path | None:
    env_map = os.environ if env is None else env
    if ledger:
        return _validate_under_tmp(ledger, env=env_map)
    if env_map.get("LARCH_TOKEN_LEDGER"):
        try:
            return _validate_under_tmp(str(env_map["LARCH_TOKEN_LEDGER"]), env=env_map)
        except ValueError:
            pass
    slug = _sha256_hex(resolve_session_id(env=env_map))
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"):
        root = _canonical_dir(env_map.get(key, ""))
        if root is not None:
            return root / f"larch-tokens-{slug}.jsonl"
    session_env = env_map.get("SESSION_ENV_PATH", "")
    if session_env:
        root = _canonical_dir(Path(session_env).parent)
        if root is not None:
            return root / f"larch-tokens-{slug}.jsonl"
    return None


def _parse_ledger(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(cast("dict[str, Any]", obj))
    return rows


def check_step_token_budget(
    *, cap: int, step: str = "unknown", env: Mapping[str, str] | None = None
) -> BudgetCheckResult:
    total = 0
    try:
        ledger = resolve_token_ledger_path(env=env)
        for row in _parse_ledger(ledger):
            if row.get("type") == "mark":
                total = 0
            elif row.get("type") == "vendor":
                total += _int_field(data=row, key="total")
    except (OSError, ValueError):
        total = 0
    return BudgetCheckResult(
        status="cap_hit" if total >= cap else "under_cap",
        total=total,
        cap=cap,
        step=step,
    )


def compute_pr_line_counts(*, pr_number: int, repo: str | None = None) -> PrLineCountResult:
    if pr_number < 1:
        return PrLineCountResult(status="skipped", reason="no-pr")
    if repo is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return PrLineCountResult(status="skipped", reason="invalid-repo")
    endpoint = (
        f"repos/{repo}/pulls/{pr_number}/files"
        if repo
        else f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files"
    )
    try:
        result = gh.command(
            proc,
            [
                "api",
                "--paginate",
                endpoint,
                "--jq",
                ".[] | [.filename, .additions, .deletions] | @tsv",
            ],
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.argv,
                output=result.stdout,
                stderr=result.stderr,
            )
        out = result.stdout
    except (OSError, subprocess.CalledProcessError):
        return PrLineCountResult(status="unavailable", reason="gh-failed")
    code_added = code_deleted = logs_added = logs_deleted = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = int(parts[1] or 0)
        deleted = int(parts[2] or 0)
        if parts[0].startswith("larch-logs/"):
            logs_added += added
            logs_deleted += deleted
        else:
            code_added += added
            code_deleted += deleted
    return PrLineCountResult(
        status="ok",
        code_added=code_added,
        code_deleted=code_deleted,
        logs_added=logs_added,
        logs_deleted=logs_deleted,
    )


def token_check_budget_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cap: int | None = None
    step = "unknown"
    idx = 0
    while idx < len(args):
        if args[idx] == "--cap":
            cap = int(args[idx + 1])
            idx += 2
        elif args[idx] == "--step":
            step = args[idx + 1]
            idx += 2
        else:
            print(f"token check-budget: unknown flag: {args[idx]}", file=sys.stderr)
            return 1
    if cap is None or cap < 1:
        print("token check-budget: --cap must be >= 1", file=sys.stderr)
        return 1
    result = check_step_token_budget(cap=cap, step=step)
    print(f"STATUS={result.status} TOTAL={result.total} CAP={result.cap} STEP={result.step}")
    return 0


def compute_pr_lines_main(argv: list[str] | None = None) -> int:
    return compute_pr_line_counts_main(argv)


def compute_pr_line_counts_main(argv: list[str] | None = None) -> int:
    opts = _flag_map(list(argv if argv is not None else sys.argv[1:]))
    pr_raw = opts.get("--pr-number", "")
    if not _UINT_RE.fullmatch(pr_raw or "") or int(pr_raw) == 0:
        print("LINES_STATUS=skipped\nREASON=no-pr")
        return 0
    result = compute_pr_line_counts(pr_number=int(pr_raw), repo=opts.get("--repo") or None)
    for key, value in result.kv_items():
        print(f"{key}={value}")
    return 0


def _flag_map(args: list[str]) -> dict[str, str]:
    opts: dict[str, str] = {}
    idx = 0
    while idx < len(args):
        if not args[idx].startswith("--"):
            idx += 1
            continue
        if idx + 1 >= len(args) or args[idx + 1].startswith("--"):
            opts[args[idx]] = ""
            idx += 1
        else:
            opts[args[idx]] = args[idx + 1]
            idx += 2
    return opts


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print("token_cutover_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = arguments[0], arguments[1:]
    handlers = {
        "check-budget": token_check_budget_main,
        "compute-pr-line-counts": compute_pr_line_counts_main,
        "compute-pr-lines": compute_pr_lines_main,
    }
    handler = handlers.get(verb)
    if handler is None:
        print(f"token_cutover_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
