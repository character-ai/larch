#!/usr/bin/env python3
"""Verified-bootstrap test double for Rust-owned reviewer agent commands.

Python review integration tests exercise callers through ``scripts/larch.sh``.
This executable supplies only the narrow command behavior those caller tests
need; the real command contracts live in Rust integration tests.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ARG_PAIR_SIZE = 2
ENV_CLAUDE_PLUGIN_ROOT = "CLAUDE_PLUGIN_ROOT"
GENERATORS_TSV_COLUMNS = 2
GIT = shutil.which("git") or "git"


def _plugin_root() -> Path:
    return Path(os.environ[ENV_CLAUDE_PLUGIN_ROOT])


def _version() -> str:
    manifest = _plugin_root() / ".claude-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return str(payload["version"])


def _target() -> str:
    targets = {
        ("Darwin", "arm64"): "aarch64-apple-darwin",
        ("Darwin", "aarch64"): "aarch64-apple-darwin",
        ("Darwin", "x86_64"): "x86_64-apple-darwin",
        ("Darwin", "amd64"): "x86_64-apple-darwin",
        ("Linux", "arm64"): "aarch64-unknown-linux-gnu",
        ("Linux", "aarch64"): "aarch64-unknown-linux-gnu",
        ("Linux", "x86_64"): "x86_64-unknown-linux-gnu",
        ("Linux", "amd64"): "x86_64-unknown-linux-gnu",
    }
    return targets[(platform.system(), platform.machine())]


def _classify_path(path: str, generated: set[str]) -> str:
    if not path or path.startswith("/") or ".." in path:
        return "generic"
    if path in generated:
        return "generated-only"
    base = Path(path).name
    if (
        re.fullmatch(r"scripts/test-.*\.(?:sh|py)", path)
        or re.fullmatch(r"skills/[^/]+/scripts/test-.*\.sh", path)
        or re.fullmatch(r"[^/]+/(?:tests|test)/[^/]+\.(?:sh|py|go|bats)", path)
        or re.fullmatch(r"(?:test_.*|.*_test|.*\.test)\.(?:sh|py|go)", base)
        or base.endswith(".bats")
    ):
        return "test-only"
    if (
        re.fullmatch(r"docs/[^/]+\.(?:md|txt|rst|adoc)", path)
        or re.fullmatch(r"scripts/[^/]+\.md", path)
        or path in {"README.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md", "KARPATHY_CLAUDE.md"}
    ):
        return "docs-only"
    return "generic"


def _classify(arguments: list[str]) -> int:
    if len(arguments) != 1:
        return 2
    diff = Path(arguments[0])
    if not diff.is_file():
        return 2
    manifest = _plugin_root() / "scripts" / "generators.tsv"
    generated = {
        columns[1]
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        if len(columns := line.split("\t")) == GENERATORS_TSV_COLUMNS and columns[1]
    }
    mode = ""
    for line in diff.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"diff --git a/([^\s]+) b/([^\s]+)", line)
        if line.startswith("diff --git ") and match is None:
            print("DIFF_MODE=generic")
            return 0
        if match is None:
            continue
        old_mode = _classify_path(match.group(1), generated)
        new_mode = _classify_path(match.group(2), generated)
        if old_mode != new_mode or old_mode == "generic" or (mode and mode != old_mode):
            print("DIFF_MODE=generic")
            return 0
        mode = old_mode
    print(f"DIFF_MODE={mode or 'generic'}")
    return 0


def _wait(arguments: list[str]) -> int:
    timeout = 1_860
    sentinels = arguments[:]
    if len(sentinels) >= ARG_PAIR_SIZE and sentinels[0] == "--timeout":
        timeout = int(sentinels[1])
        sentinels = sentinels[2:]
    interval = float(os.environ.get("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "5"))
    deadline = time.monotonic() + timeout
    while any(not Path(raw_path).is_file() for raw_path in sentinels) and time.monotonic() < deadline:
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
    for index, raw_path in enumerate(sentinels, start=1):
        path = Path(raw_path)
        name = path.name.removesuffix(".done")
        if not path.is_file():
            print(f"TIMEOUT {index} {name}")
            continue
        code = "".join(path.read_text(encoding="utf-8", errors="replace").split())
        print(f"DONE {index} {name}: exit={code if code.isdigit() and code else 'unknown'}")
    return 0


def _git(arguments: list[str]) -> str:
    result = subprocess.run(  # lint-subprocess-via-runner: ok standalone bootstrap test double must not import the runtime package
        [GIT, *arguments], check=False, text=True, capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "git command failed")
    return result.stdout


def _gather(arguments: list[str]) -> int:
    if len(arguments) != ARG_PAIR_SIZE or arguments[0] != "--output-dir":
        return 1
    output = Path(arguments[1])
    if not output.is_dir():
        return 1
    try:
        origin_main = subprocess.run(  # lint-subprocess-via-runner: ok standalone bootstrap test double must not import the runtime package
            [GIT, "rev-parse", "--verify", "--quiet", "origin/main"],
            check=False,
            text=True,
            capture_output=True,
        )
        base = "origin/main" if origin_main.returncode == 0 and origin_main.stdout.strip() else "main"
        merge_base = _git(["merge-base", "HEAD", base]).strip()
        paths = ["--", ".", ":(exclude)larch-logs/**"]
        diff = _git(["diff", "-U20", f"{merge_base}...HEAD", *paths])
        file_list = _git(["diff", f"{merge_base}...HEAD", "--name-only", *paths])
        commit_log = _git(["log", f"{merge_base}..HEAD", "--oneline", *paths])
    except RuntimeError as error:
        print(f"gather-branch-context.sh: {error}", file=sys.stderr)
        return 1
    diff_file = output / "diff.txt"
    file_list_file = output / "file-list.txt"
    commit_log_file = output / "commit-log.txt"
    _ = diff_file.write_text(diff, encoding="utf-8")
    _ = file_list_file.write_text(file_list, encoding="utf-8")
    _ = commit_log_file.write_text(commit_log, encoding="utf-8")
    print(f"DIFF_FILE={diff_file}")
    print(f"FILE_LIST_FILE={file_list_file}")
    print(f"COMMIT_LOG_FILE={commit_log_file}")
    print(f"COMMIT_COUNT={len(commit_log.splitlines())}")
    return 0


def _compose(arguments: list[str]) -> int:
    values = dict(zip(arguments[::2], arguments[1::2], strict=False))
    record = values.get("--structured-record", "")
    output = values.get("--output", "")
    if not record or not output:
        return 2
    target = Path(output)
    _ = target.write_text(f"## Structured collector record\n\n{record}\n", encoding="utf-8")
    target.chmod(0o600)
    return 0


def main(arguments: list[str]) -> int:
    result = 2
    if arguments == ["--version"]:
        print(f"larch {_version()}")
        result = 0
    elif arguments == ["bootstrap", "self-check"]:
        print(json.dumps({"schema_version": 1, "version": _version(), "target": _target()}, separators=(",", ":")))
        result = 0
    else:
        handlers = {
            ("agent", "classify-diff"): _classify,
            ("agent", "wait-reviewers"): _wait,
            ("agent", "gather-branch-context"): _gather,
            ("agent", "compose-collector-failure-log"): _compose,
        }
        handler = handlers.get((arguments[0], arguments[1])) if len(arguments) >= ARG_PAIR_SIZE else None
        if handler is not None:
            result = handler(arguments[2:])
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
