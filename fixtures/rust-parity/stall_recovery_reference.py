#!/usr/bin/env python3
"""Frozen Python reference for the six issue-8064 stall-recovery commands."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def options(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    index = 0
    while index < len(values):
        arg = values[index]
        if arg.startswith("--") and "=" in arg:
            key, value = arg.split("=", 1)
            parsed[key] = value
            index += 1
        elif arg.startswith("--") and index + 1 < len(values):
            parsed[arg] = values[index + 1]
            index += 2
        else:
            index += 1
    return parsed


def emit(key: str, valid: bool) -> int:
    print(f"{key}={'true' if valid else 'false'}")
    return 0 if valid else 1


def read_last(path: Path, key: str) -> str:
    if not path.is_file() or path.is_symlink():
        return ""
    prefix = f"{key}="
    found = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            found = line[len(prefix) :].strip("\r")
    return found


def safe_step(value: str, generic: bool) -> bool:
    if generic and value in {"validator", "postplan", "publish", "clarify", "panel", "judge-panel", "step2b", "step3", "step5c"}:
        return True
    return bool(re.fullmatch(r"[2-9]|1[0-5]|(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", value))


def token_valid(value: str, kind: str, generic: bool) -> bool:
    if not value or any(char in value for char in "\n\r {}()[]<>|&;`$"):
        return False
    if not kind:
        return True
    if kind == "outcome":
        return value in {"approved", "approved-partition", "failed-publish"}
    if kind == "step":
        return safe_step(value, generic)
    if kind == "phase":
        return value in {"ship-pr", "ci-initial"} or (generic and value == "publish")
    if kind == "site":
        return value == "ship-pr" or (generic and value == "gate-b")
    if kind == "trigger":
        return value == "main-agent-required" or (generic and value == "failed")
    if kind == "bail":
        return value == "review-required" or (generic and value == "operator-action")
    if kind == "source-script":
        return value == "ship-pr" or (generic and value == "split-path")
    if kind == "root-cause":
        return value in {"larch-defect", "environment", "operator-action"}
    return False


def rewrite(path: Path, updates: dict[str, str]) -> bool:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return False
        key, value = line.split("=", 1)
        rows[key] = value.rstrip("\r")
    rows.update(updates)
    path.write_text("".join(f"{key}={value}\n" for key, value in rows.items()), encoding="utf-8")
    return True


def clear(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    for name in ("stall-recovery-classification.env", "stall-recovery-issue.env"):
        try:
            (tmpdir / name).unlink()
        except OSError:
            pass
    paths = [tmpdir / name for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh")]
    for path in paths:
        if path.exists() and (path.is_symlink() or not path.is_file() or not rewrite(path, {})):
            print("CLEARED=false")
            return 3
    for path in paths:
        if path.is_file() and not rewrite(path, {
            "STALL_TRACKING": "false", "STALL_STEP": "", "BAIL_REASON": "",
            "IMPLEMENT_BAIL_REASON": "", "EXIT_CODE": "unknown",
        }):
            return emit("CLEARED", False)
    return emit("CLEARED", True)


def seed(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    state = tmpdir / "ship-pr-state.sh"
    if state.is_symlink():
        print("SEEDED=false")
        return 3
    if state.is_file() and any(line and not line.startswith("#") and "=" not in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        print("SEEDED=false")
        return 3
    step = opts.get("--stall-step") or read_last(state, "STALL_STEP") or "8"
    phase = opts.get("--phase") or read_last(state, "PHASE") or "ci-initial"
    step = step if safe_step(step, True) else "unknown"
    phase = phase if phase in {"ci-initial", "publish", "ship-pr"} else "unknown"
    if state.is_file() and state.stat().st_size and any("=" in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        rewrite(state, {"STALL_TRACKING": "true", "STALL_STEP": step, "PHASE": phase})
        mode = "rewrite"
    else:
        tmpdir.mkdir(parents=True, exist_ok=True)
        state.write_text(
            f"PHASE={phase}\nSTALL_TRACKING=true\nSTALL_STEP={step}\nBAIL_REASON=\nBAIL_FAILURE_DETAIL_LOG=\nEXIT_CODE=4\n",
            encoding="utf-8",
        )
        mode = "seed"
    print("SEEDED=true")
    print(f"SEED_MODE={mode}")
    return 0


def terminal(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    state = Path(opts.get("--primary-state-file", str(tmpdir / "design-failure-terminal-state.env")))
    if not state.is_absolute() or state.is_symlink() or not state.is_file():
        return emit("VALID", False)
    try:
        state.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return emit("VALID", False)
    rows: dict[str, str] = {}
    for raw in state.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return emit("VALID", False)
        key, value = line.split("=", 1)
        if key in rows:
            return emit("VALID", False)
        rows[key] = value
    required = {"DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME", "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE", "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT"}
    valid = required <= rows.keys() and all(rows[key] for key in required - {"FAILURE_DETAIL_LOG"})
    valid = valid and rows.get("DESIGN_FAILURE_VERSION") == "1" and rows.get("DESIGN_FAILURE_KIND") == "terminal"
    valid = valid and token_valid(rows.get("STALL_STEP", ""), "step", opts.get("--profile") == "generic")
    return emit("VALID", valid)


def public(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--tmpdir") or opts.get("--implement-tmpdir", "."))
    candidate = Path(opts.get("--public-file", ""))
    corpus = Path(opts.get("--sensitive-corpus-file", ""))
    prefix = opts.get("--artifact-prefix") or "stall-recovery"
    effective = tmpdir / f"{prefix}-sensitive-corpus.public.effective"
    if not candidate.is_absolute() or not candidate.is_file() or candidate.is_symlink() or not corpus.is_absolute() or not corpus.is_file() or corpus.is_symlink():
        return emit("PUBLIC_FILE_VALID", False)
    text = corpus.read_text(encoding="utf-8", errors="replace")
    effective.write_text(text, encoding="utf-8")
    body = candidate.read_text(encoding="utf-8", errors="replace")
    sensitive = any(token.strip() and token.strip() in body for token in text.splitlines())
    if sensitive:
        return emit("PUBLIC_FILE_VALID", False)
    effective.unlink()
    return emit("PUBLIC_FILE_VALID", True)


def dev_clone(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    forked = read_last(tmpdir / "ship-pr-state.sh", "FORKED_TARGET") or read_last(tmpdir / "session-env.sh", "FORKED_TARGET")
    root = Path(opts.get("--working-tree-root", ""))
    valid = forked.lower() not in {"1", "true", "yes", "on"} and (root / "skills/implement/SKILL.md").is_file()
    print(f"LARCH_DEV_CLONE={'true' if valid else 'false'}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    verb = sys.argv[1]
    opts = options(sys.argv[2:])
    if verb == "validate-token":
        token = opts.get("--token") or opts.get("--value", "")
        return emit("TOKEN_VALID", token_valid(token, opts.get("--token-kind", ""), opts.get("--profile") == "generic"))
    if verb == "validate-terminal-state":
        return terminal(opts)
    if verb == "validate-tier-b-public-file":
        return public(opts)
    if verb == "clear-stall":
        return clear(opts)
    if verb == "seed-terminal-state":
        return seed(opts)
    if verb == "is-larch-dev-clone":
        return dev_clone(opts)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
