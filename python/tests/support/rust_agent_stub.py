#!/usr/bin/env python3
# pyright: reportPrivateUsage=false, reportArgumentType=false
# The entry-write run-log verbs deliberately reuse the shared private batch
# helpers rather than restating their behavior. The manifest fixture is local
# so test plumbing does not retain the retired Python manifest writer.
"""Verified-bootstrap test double for Rust-owned agent, run-log, and review commands.

Python integration tests exercise their callers through ``scripts/larch.sh``,
which needs a version-matching executable that a Python-only test run does not
build. This executable supplies the narrow command behavior those caller tests
need; the real command contracts live in Rust integration tests
(``crates/larch-cli/tests/``).

The entry-write ``run-log`` verbs delegate to the surviving
`larch.report.run_log_batch` helpers. ``implement scope-disposition`` loads the
frozen pre-cutover owner at
``fixtures/rust-parity/implement_scope_disposition_reference.py``. The archive
fixture and empty review composer below are test-only plumbing for Python
callers; the production contracts and hostile-input coverage live in Rust
integration tests.
"""

from __future__ import annotations

import csv
import functools
import gzip
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal, cast

ARG_PAIR_SIZE = 2
DEGRADED_REASON_ARGUMENT_COUNT = 3
VOTER_STATUS_POSITIONAL_COUNT = 13
CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR = 1_000
CURSOR_DEGRADED_RESULT_BYTES_CEILING = 500
ENV_CLAUDE_PLUGIN_ROOT = "CLAUDE_PLUGIN_ROOT"
GENERATORS_TSV_COLUMNS = 2
GIT = shutil.which("git") or "git"
ARCHIVE_FORMAT = "larch-run-archive"
ARCHIVE_MANIFEST_NAME = "archive-manifest.json"
ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_SHA256_HEX_LENGTH = 64
PRUNE_MIN_ACCEPTED = 2
PRUNE_WEIGHT_MAJOR = 2
PRUNE_LEGACY_COLUMNS = 7
PRUNE_WEIGHTED_COLUMNS = 8
PRUNE_CURRENT_COLUMNS = 9
PRUNE_WINDOW_START_ROUND = 2
_PRUNE_LEDGER_HEADER = (
    "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count"
    "\trejected_count\ttotal_count\tobserved"
)


@dataclass(frozen=True)
class _ArchiveRecord:
    """One tiny in-memory record used only by the Python bootstrap double."""

    path: str
    kind: Literal["directory", "file"]
    size: int
    sha256: str | None
    mode: int
    content: bytes | None


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


def _collect_result_files(arguments: list[str]) -> tuple[set[str], dict[str, str], list[str]]:
    switches: set[str] = set()
    values: dict[str, str] = {}
    files: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in {
            "--summary-only",
            "--substantive-validation",
            "--validation-mode",
            "--structured-reviewer-validation",
        }:
            switches.add(argument)
            index += 1
        elif argument in {"--timeout", "--paths-file"} and index + 1 < len(arguments):
            values[argument] = arguments[index + 1]
            index += 2
        else:
            files.append(argument)
            index += 1
    paths_file = values.get("--paths-file")
    if paths_file:
        try:
            files.extend(
                line.strip()
                for line in Path(paths_file).read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip()
            )
        except OSError:
            return switches, values, []
    return switches, values, files


def _collector_status(path: Path, *, substantive_validation: bool) -> tuple[str, str]:  # noqa: PLR0911 - status cases mirror collector terminal outcomes.
    done = path.with_name(path.name + ".done")
    if not done.is_file():
        return "TIMEOUT", "124"
    code = "".join(done.read_text(encoding="utf-8", errors="replace").split()) or "unknown"
    if code not in {"0", "00"}:
        return "ERROR", code
    if not path.is_file() or path.stat().st_size == 0:
        return "EMPTY_OUTPUT", code
    if substantive_validation:
        for sidecar in (
            path.with_name(path.name + ".structured.tsv"),
            path.with_name(path.name + ".sidecar.tsv"),
        ):
            if sidecar.is_file() and sidecar.stat().st_size > 0:
                return "OK", code
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(line.strip() == "NO_ISSUES_FOUND" for line in text.splitlines()):
            return "OK", code
        return "NOT_SUBSTANTIVE", code
    return "OK", code


def _collect_results(arguments: list[str]) -> int:
    switches, _values, files = _collect_result_files(arguments)
    if not files:
        return 2
    substantive_validation = "--substantive-validation" in switches
    rc = 0
    for raw_file in files:
        reviewer = Path(raw_file)
        status, exit_code = _collector_status(
            reviewer, substantive_validation=substantive_validation
        )
        tool = "codex" if "codex" in reviewer.name else "cursor" if "cursor" in reviewer.name else "claude"
        print(f"REVIEWER_FILE={reviewer}")
        print(f"TOOL={tool}")
        print(f"STATUS={status}")
        print(f"EXIT_CODE={exit_code}")
        for sidecar in (
            reviewer.with_name(reviewer.name + ".structured.tsv"),
            reviewer.with_name(reviewer.name + ".sidecar.tsv"),
        ):
            if sidecar.is_file() and sidecar.stat().st_size > 0:
                print(f"STRUCTURED_SIDECAR={sidecar}")
                break
        print()
        if status in {"TIMEOUT", "ERROR"}:
            rc = 1
    return rc


def _run_external_agent(arguments: list[str]) -> int:
    """Minimal Rust-command double for Python callers that retry an artifact."""
    output = ""
    capture_stdout = False
    capture_stdout_only = False
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            index += 1
            break
        if argument == "--output" and index + 1 < len(arguments):
            output = arguments[index + 1]
            index += 2
        elif argument in {"--tool", "--timeout", "--stderr-sink"} and index + 1 < len(arguments):
            index += 2
        elif argument == "--capture-stdout":
            capture_stdout = True
            index += 1
        elif argument == "--capture-stdout-only":
            capture_stdout_only = True
            index += 1
        else:
            return 1
    command = arguments[index:]
    if not output or not command or Path(command[0]).name not in {"claude", "codex", "cursor"}:
        return 1
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = target.open("wb") if capture_stdout or capture_stdout_only else None
    stderr_handle = target.with_suffix(target.suffix + ".diag").open("wb") if capture_stdout_only else None
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=stdout_handle,
            stderr=subprocess.STDOUT if capture_stdout else stderr_handle,
        )
    finally:
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()
    _ = target.with_suffix(target.suffix + ".done").write_text(
        f"{result.returncode}\n", encoding="utf-8"
    )
    return result.returncode


def _option_values(arguments: list[str]) -> tuple[dict[str, str], set[str]]:
    """Parse the small launch-review surface needed by Python caller tests."""
    values: dict[str, str] = {}
    switches: set[str] = set()
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--competition-notice":
            switches.add(argument)
            index += 1
            continue
        if not argument.startswith("--") or index + 1 >= len(arguments):
            return {}, set()
        values[argument] = arguments[index + 1]
        index += 2
    return values, switches


def _review_prompt(values: dict[str, str], switches: set[str]) -> str:
    prompt_file = values.get("--prompt-file", "")
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8", errors="replace")
    agent_file = values.get("--agent-file", "")
    if not agent_file:
        return ""
    prompt = Path(agent_file).read_text(encoding="utf-8", errors="replace")
    if values.get("--description-text"):
        prompt += f"\n{values['--description-text']}\n"
    if "--competition-notice" in switches:
        prompt += "\nCompetition notice\n"
    notice = values.get("--competition-notice-file", "")
    if notice:
        prompt += Path(notice).read_text(encoding="utf-8", errors="replace")
    return prompt


def _append_panel_row(*, tool: str, output: Path, prompt: str) -> None:
    artifact_dir = os.environ.get("LARCH_PANEL_ARTIFACT_DIR", "")
    slot = os.environ.get("LARCH_PANEL_SLOT", "")
    if not artifact_dir or not slot:
        return
    phase = os.environ.get("LARCH_PANEL_PHASE", "")
    slot_kind = "voter" if "voter" in slot.lower() else "specialist"
    artifact = Path(artifact_dir) / "panel-prompt-sizes.tsv"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "site\tphase\tround_num\tslot\tslot_kind\ttool\toutput\tprompt_bytes\tprompt_tokens"
        "\tscaffold_bytes\tscaffold_tokens\tpayload_bytes\tpayload_tokens\tagent_file\tagent_bytes\tagent_tokens"
    )
    prompt_bytes = len(prompt.encode())
    payload_bytes = int(os.environ.get("LARCH_PANEL_PAYLOAD_BYTES", "0") or "0")
    row = [
        os.environ.get("LARCH_PANEL_SITE", ""),
        phase,
        os.environ.get("LARCH_PANEL_ROUND_NUM", ""),
        slot,
        slot_kind,
        tool,
        output.name,
        str(prompt_bytes),
        str((prompt_bytes + 3) // 4),
        str(max(prompt_bytes - payload_bytes, 0)),
        str((max(prompt_bytes - payload_bytes, 0) + 3) // 4),
        str(payload_bytes),
        str((payload_bytes + 3) // 4),
        "",
        "0",
        "0",
    ]
    with artifact.open("a+", encoding="utf-8") as handle:
        _ = handle.seek(0)
        if not handle.read():
            _ = handle.write(f"{header}\n")
        _ = handle.write("\t".join(row) + "\n")


def _write_review_meta(*, tool: str, output: Path, timeout: str, values: dict[str, str]) -> None:
    prompt_sidecar = output.with_suffix(output.suffix + ".prompt")
    lines = [
        f"TOOL={tool}",
        f"TIMEOUT={timeout}",
        "CAPTURE_STDOUT=false",
        f"CAPTURE_STDOUT_ONLY={'true' if tool == 'cursor' else 'false'}",
        f"OUTPUT_FILE={output}",
        "CMD_JSON=[]",
        "OUTER_LAUNCHER=agent launch-review",
        f"OUTER_LAUNCHER_PROMPT_FILE={prompt_sidecar}",
        f"OUTER_LAUNCHER_WORKDIR={Path.cwd()}",
        f"OUTER_LAUNCHER_SITE={values.get('--site', 'review Step 2')}",
        f"OUTER_LAUNCHER_MODEL_ROLE={values.get('--model-role', 'default') or 'default'}",
    ]
    timing = values.get("--timing-task-kind", "")
    if timing:
        lines.append(f"OUTER_LAUNCHER_TIMING_KIND={timing}")
    cursor_model = values.get("--cursor-model", "")
    if cursor_model:
        lines.append(f"OUTER_LAUNCHER_CURSOR_MODEL={cursor_model}")
    _ = output.with_suffix(output.suffix + ".meta").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _launch_review(arguments: list[str]) -> int:
    """Test-double implementation of the Rust review launcher contract.

    Caller integration tests run through the verified bootstrap and only need
    fake-vendor artifacts. Native Rust tests cover the real command itself, so
    this double must never execute ambient vendor binaries from the operator's
    machine.
    """
    values, switches = _option_values(arguments)
    tool = values.get("--tool", "")
    output_text = values.get("--output", "")
    timeout = values.get("--timeout", "")
    if tool not in {"codex", "cursor"} or not output_text or not timeout:
        return 2
    try:
        prompt = _review_prompt(values, switches)
    except OSError:
        return 1
    output = Path(output_text)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.with_suffix(output.suffix + ".prompt").write_text(prompt, encoding="utf-8")
    _append_panel_row(tool=tool, output=output, prompt=prompt)
    if tool == "codex":
        _ = output.write_text(os.environ.get("LARCH_TEST_CODEX_REVIEW_RESULT", "codex review\n"), encoding="utf-8")
        _ = output.with_suffix(output.suffix + ".events.jsonl").write_text("{}\n", encoding="utf-8")
        result = subprocess.CompletedProcess(["codex", "exec"], 0, b"", b"")  # lint-codex-exec-auth: ok fixture records synthetic argv only
    else:
        result_text = os.environ.get("LARCH_TEST_CURSOR_REVIEW_RESULT", "cursor review")
        output_tokens = int(os.environ.get("LARCH_TEST_CURSOR_REVIEW_OUTPUT_TOKENS", "1"))
        if (
            output_tokens > CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR
            and len(result_text.encode()) < CURSOR_DEGRADED_RESULT_BYTES_CEILING
        ):
            _ = output.write_text("CURSOR_DEGRADED_RESPONSE\n", encoding="utf-8")
        else:
            _ = output.write_text(result_text + ("\n" if not result_text.endswith("\n") else ""), encoding="utf-8")
        result = subprocess.CompletedProcess(["cursor"], 0, b"", b"")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    if result.returncode == 0:
        _ = sidecar.write_text(
            f"{tool}-status: ok (no stderr emitted during agent run)\n", encoding="utf-8"
        )
    else:
        _ = output.with_suffix(output.suffix + ".diag").write_bytes(result.stderr)
        _ = sidecar.write_bytes(
            result.stderr or f"STATUS=FAILED\nLAUNCHER_EXIT={result.returncode}\n".encode()
        )
    _write_review_meta(tool=tool, output=output, timeout=timeout, values=values)
    _ = output.with_suffix(output.suffix + ".done").write_text(
        f"{result.returncode}\n", encoding="utf-8"
    )
    return result.returncode


def _flag(arguments: list[str], name: str, default: str = "") -> str:
    """Read one long option, accepting both the split and inline `=` spellings."""
    for index, token in enumerate(arguments):
        if token == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if token.startswith(f"{name}="):
            return token[len(name) + 1 :]
    return default


def _prune_rows(path: Path) -> list[dict[str, object]]:
    return [
        value
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
        if isinstance(value := json.loads(line), dict)
    ]


def _prune_label(value: str) -> str:
    label = re.sub(r"\s*\([^()]*\)\s*$", "", value.strip()).strip()
    base = Path(label).name
    stem, extension = (base[:-4], ".txt") if base.endswith(".txt") else (base, "")
    if "-output" in stem:
        return stem.rpartition("-output")[0]
    while True:
        trimmed = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if trimmed == stem:
            return stem + extension
        stem = trimmed


def _prune_plan_tokens(cell: str, labels: list[str]) -> set[str]:
    tokens: set[str] = set()
    ordered = sorted((label for label in labels if label), key=lambda label: (-len(label), label))
    for segment in cell.split(","):
        position = 0
        while position < len(segment):
            if segment[position].isspace():
                position += 1
                continue
            label = next(
                (
                    candidate
                    for candidate in ordered
                    if segment.startswith(candidate, position)
                    and (position + len(candidate) == len(segment) or segment[position + len(candidate)].isspace())
                ),
                "",
            )
            if not label:
                break
            tokens.add(label)
            position += len(label)
    return tokens


def _prune_points(row: dict[str, str], header: list[str]) -> int:
    if row.get("voting_result", "").strip() != "accepted":
        return 0
    if "scope" not in header or row.get("scope", "").strip() == "oos":
        return 1
    major_yes = sum(
        row.get(f"v{index}_vote", "") == "YES" and row.get(f"v{index}_severity", "") == "major"
        for index in range(1, 4)
    )
    return PRUNE_WEIGHT_MAJOR if major_yes >= PRUNE_MIN_ACCEPTED else 1


def _normalized_prune_ledger_row(row: list[str]) -> list[str] | None:
    if len(row) == PRUNE_LEGACY_COLUMNS:
        normalized = [*row[:5], row[4], *row[5:], "true"]
    elif len(row) == PRUNE_WEIGHTED_COLUMNS:
        normalized = [*row, "true"]
    elif len(row) == PRUNE_CURRENT_COLUMNS:
        normalized = row
    else:
        return None
    try:
        _ = [int(normalized[index]) for index in (0, 4, 5, 6, 7)]
    except ValueError:
        return None
    return normalized if normalized[8] in {"true", "false"} else None


def _reviewer_prune_record(arguments: list[str]) -> int:  # noqa: C901, PLR0912, PLR0915 - narrow test-double compatibility surface.
    ledger_raw = _flag(arguments, "--ledger")
    manifest_raw = _flag(arguments, "--manifest")
    classification_raw = _flag(arguments, "--classification")
    label_map_raw = _flag(arguments, "--label-map")
    ledger = Path(ledger_raw)
    manifest = Path(manifest_raw)
    classification = Path(classification_raw)
    try:
        round_num = int(_flag(arguments, "--round"))
        if not ledger_raw or not manifest_raw or not classification_raw or round_num <= 0 or not manifest.is_file() or not classification.is_file():
            return 2
        label_map = {}
        if label_map_raw and Path(label_map_raw).is_file():
            label_map = {
                slot: label
                for line in Path(label_map_raw).read_text(encoding="utf-8", errors="replace").splitlines()
                if "\t" in line
                if (slot := line.split("\t", 1)[0])
                if (label := line.split("\t", 1)[1])
            }
    except (OSError, ValueError):
        return 2
    rows = _prune_rows(manifest)
    slots = [
        (row, label_map.get(str(row.get("slot") or ""), Path(str(row.get("output") or row.get("slot") or "")).name))
        for row in rows
    ]
    labels = [label for _, label in slots]
    counts = {label: [0, 0, 0, 0] for label in labels}
    try:
        with classification.open(encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            header = list(reader.fieldnames or [])
            attribute = "finding_reviewers" if "finding_reviewers" in header else "reviewer_slots"
            keys = {label: label if label_map else _prune_label(label) for label in labels}
            for row in reader:
                result = (row.get("voting_result") or "").strip()
                if result not in {"accepted", "rejected", "neutral"}:
                    continue
                cell = row.get(attribute) or ""
                tokens = _prune_plan_tokens(cell, labels) if label_map else {_prune_label(token) for token in cell.split("|") if token.strip()}
                for label, key in keys.items():
                    if key not in tokens:
                        continue
                    values = counts[label]
                    values[3] += 1
                    if result == "accepted":
                        values[0] += 1
                        values[1] += _prune_points(row, header)
                    elif result == "rejected":
                        values[2] += 1
    except OSError:
        return 1
    skipped: set[str] = set()
    status = _flag(arguments, "--reviewer-status")
    try:
        if status and not Path(status).is_symlink() and Path(status).is_file():
            with Path(status).open(encoding="utf-8", errors="replace", newline="") as handle:
                skipped = {
                    row.get("slot", "")
                    for row in csv.DictReader(handle, delimiter="\t")
                    if row.get("status") == "skipped" and row.get("slot")
                }
    except OSError:
        pass
    existing: list[list[str]] = []
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            normalized = _normalized_prune_ledger_row(line.split("\t"))
            if normalized is not None and int(normalized[0]) != round_num:
                existing.append(normalized)
    recorded = [
        [
            str(round_num), str(row.get("tool") or ""), str(row.get("slot") or ""), label,
            *(str(value) for value in counts[label]), str(label not in skipped).lower(),
        ]
        for row, label in slots
    ]
    ledger.parent.mkdir(parents=True, exist_ok=True)
    _ = ledger.write_text("\n".join([_PRUNE_LEDGER_HEADER, *("\t".join(row) for row in [*existing, *recorded])]) + "\n", encoding="utf-8")
    return 0


def _reviewer_prune_filter(arguments: list[str]) -> int:  # noqa: C901, PLR0912, PLR0915 - narrow test-double compatibility surface.
    ledger_raw = _flag(arguments, "--ledger")
    manifest_raw = _flag(arguments, "--manifest")
    out_raw = _flag(arguments, "--out")
    ledger = Path(ledger_raw)
    manifest = Path(manifest_raw)
    out = Path(out_raw)
    try:
        round_num = int(_flag(arguments, "--round"))
        if not ledger_raw or not manifest_raw or not out_raw or round_num <= 0 or not manifest.is_file():
            return 2
        rows = _prune_rows(manifest)
        original = manifest.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return 2
    override = os.environ.get("LARCH_REVIEWER_PRUNE", "")
    warn = "" if not override or override == "off" else "reviewer-prune: ignoring LARCH_REVIEWER_PRUNE value; set it exactly to off to disable"
    if override == "off" or round_num < PRUNE_WINDOW_START_ROUND:
        out.parent.mkdir(parents=True, exist_ok=True)
        _ = out.write_text(original, encoding="utf-8")
        if warn:
            print(f"WARN={warn}")
        print(f"PRUNE_ACTIVE={'false' if override == 'off' else 'true'}")
        print(f"ELIGIBLE_COUNT={len(rows)}\nPRUNED_COUNT=0\nPRUNED_COMBOS=\nPANEL_PRUNED_EMPTY=false")
        return 0
    history: dict[str, dict[int, list[int | bool]]] = {}
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
        valid_headers = {
            _PRUNE_LEDGER_HEADER,
            _PRUNE_LEDGER_HEADER.rsplit("\tobserved", 1)[0],
            "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count",
        }
        if not lines or lines[0] not in valid_headers:
            raise ValueError("missing ledger columns")
        for line in lines[1:]:
            normalized = _normalized_prune_ledger_row(line.split("\t"))
            if normalized is None:
                raise ValueError("malformed ledger row")
            row_round = int(normalized[0])
            if row_round >= round_num:
                continue
            key = f"{normalized[1]}:{normalized[2]}"
            values = [int(normalized[index]) for index in range(4, 8)] + [normalized[8] == "true"]
            prior = history.setdefault(key, {}).get(row_round)
            if prior is None:
                history[key][row_round] = values
            else:
                history[key][row_round] = [max(int(prior[index]), int(values[index])) for index in range(4)] + [bool(prior[4]) or bool(values[4])]
    except (OSError, ValueError):
        out.parent.mkdir(parents=True, exist_ok=True)
        _ = out.write_text(original, encoding="utf-8")
        print("WARN=reviewer-prune: fail-open ledger read failed")
        print(f"PRUNE_ACTIVE=false\nELIGIBLE_COUNT={len(rows)}\nPRUNED_COUNT=0\nPRUNED_COMBOS=\nPANEL_PRUNED_EMPTY=false\nPRUNE_FAIL_OPEN=true")
        return 0
    eligible: list[dict[str, object]] = []
    pruned: list[str] = []
    for row in rows:
        combo = f"{row.get('tool') or ''}:{row.get('slot') or ''}"
        history_rows = list(history.get(combo, {}).values())
        if row.get("prune_exempt") is True:
            eligible.append(row)
            continue
        if not history_rows:
            pruned.append(combo)
            continue
        prior = [values for values in history_rows if values[4]]
        if not prior:
            eligible.append(row)
            continue
        accepted, weighted, rejected, total = (sum(int(values[index]) for values in prior) for index in range(4))
        if total == 0 or weighted <= rejected or (accepted < PRUNE_MIN_ACCEPTED and accepted * PRUNE_MIN_ACCEPTED < total):
            pruned.append(combo)
        else:
            eligible.append(row)
    out.parent.mkdir(parents=True, exist_ok=True)
    _ = out.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in eligible), encoding="utf-8")
    if warn:
        print(f"WARN={warn}")
    print(f"PRUNE_ACTIVE=true\nELIGIBLE_COUNT={len(eligible)}\nPRUNED_COUNT={len(pruned)}\nPRUNED_COMBOS={','.join(pruned)}\nPANEL_PRUNED_EMPTY={str(not eligible).lower()}")
    return 0


def _reviewer_prune(arguments: list[str]) -> int:
    if not arguments:
        return 2
    if arguments[0] == "record":
        return _reviewer_prune_record(arguments[1:])
    if arguments[0] == "filter":
        return _reviewer_prune_filter(arguments[1:])
    return 2


def _review_compose_findings(arguments: list[str]) -> int:
    """Write the empty composition required by Python caller-only tests.

    Detailed artifact precedence, parsing, and redaction parity are owned by
    the Rust command tests. The callers covered by this double already stub
    their review core and require only the durable empty JSONL envelope.
    """
    output = _flag(arguments, "--output")
    issue = _flag(arguments, "--issue")
    if not output or not issue.isdecimal():
        return 2
    target = Path(output)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text("", encoding="utf-8")
    except OSError:
        return 1
    print("COMPOSED=true")
    print(f"OUTPUT={target}")
    print("FINDINGS_TOTAL=0")
    print("MODE=jsonl")
    return 0


def _safe_archive_path(raw: str, *, allow_manifest: bool = False) -> str:
    if not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        raise ValueError(f"unsafe archive member path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {raw!r}")
    canonical = str(path)
    if canonical != raw:
        raise ValueError(f"unsafe archive member path: {raw!r}")
    if canonical == ARCHIVE_MANIFEST_NAME and not allow_manifest:
        raise ValueError(f"archive member path is reserved: {canonical}")
    return canonical


def _tree_records(root: Path, *, allow_manifest: bool = False) -> tuple[_ArchiveRecord, ...]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"archive staging root is not a directory: {root}")
    records: list[_ArchiveRecord] = []

    def visit(directory: Path, relative: PurePosixPath) -> None:
        for child in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
            child_relative = relative / child.name
            path = _safe_archive_path(str(child_relative), allow_manifest=allow_manifest)
            entry = child.lstat()
            if stat.S_ISLNK(entry.st_mode):
                raise ValueError(f"unsupported archive member type: {path}")
            if path == ARCHIVE_MANIFEST_NAME:
                if not stat.S_ISREG(entry.st_mode):
                    raise ValueError(f"unsupported archive member type: {path}")
                continue
            if stat.S_ISDIR(entry.st_mode):
                records.append(_ArchiveRecord(path, "directory", 0, None, 0o755, None))
                visit(child, child_relative)
                continue
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError(f"unsupported archive member type: {path}")
            content = child.read_bytes()
            records.append(
                _ArchiveRecord(
                    path,
                    "file",
                    len(content),
                    hashlib.sha256(content).hexdigest(),
                    0o755 if entry.st_mode & 0o111 else 0o644,
                    content,
                )
            )

    visit(root, PurePosixPath())
    return tuple(records)


def _manifest_bytes(
    records: tuple[_ArchiveRecord, ...], *, skill: str, run_id: str
) -> bytes:
    members: list[dict[str, int | str | None]] = [
        {
            "kind": record.kind,
            "path": record.path,
            "sha256": record.sha256,
            "size": record.size,
        }
        for record in records
    ]
    payload: dict[str, object] = {
        "archive_format": ARCHIVE_FORMAT,
        "member_count": len(records),
        "members": members,
        "run_id": run_id,
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "skill": skill,
    }
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _manifest_payload(encoded: bytes) -> dict[str, object]:
    try:
        raw_payload: object = json.loads(encoded.decode("utf-8", "strict"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("archive manifest is not valid canonical UTF-8 JSON") from error
    if not isinstance(raw_payload, dict):
        raise TypeError("archive manifest has invalid fields")
    payload = cast("dict[str, object]", raw_payload)
    if frozenset(payload) != frozenset({
        "archive_format",
        "member_count",
        "members",
        "run_id",
        "schema_version",
        "skill",
    }):
        raise ValueError("archive manifest has invalid fields")
    return payload


def _manifest_record(member: object) -> _ArchiveRecord:
    if not isinstance(member, dict):
        raise TypeError("archive manifest member has invalid fields")
    record = cast("dict[str, object]", member)
    if frozenset(record) != frozenset({"kind", "path", "sha256", "size"}):
        raise ValueError("archive manifest member has invalid fields")
    raw_path = record["path"]
    raw_kind = record["kind"]
    raw_size = record["size"]
    raw_digest = record["sha256"]
    if not isinstance(raw_path, str) or raw_kind not in {"directory", "file"}:
        raise ValueError("archive manifest member has invalid fields")
    path = _safe_archive_path(raw_path)
    if not isinstance(raw_size, int) or isinstance(raw_size, bool) or raw_size < 0:
        raise ValueError(f"archive manifest member has invalid size: {path}")
    if raw_kind == "directory":
        if raw_size != 0 or raw_digest is not None:
            raise ValueError(f"archive directory manifest record is invalid: {path}")
        return _ArchiveRecord(path, "directory", 0, None, 0o755, None)
    if not isinstance(raw_digest, str) or len(raw_digest) != ARCHIVE_SHA256_HEX_LENGTH:
        raise ValueError(f"archive file manifest digest is invalid: {path}")
    if any(character not in "0123456789abcdef" for character in raw_digest):
        raise ValueError(f"archive file manifest digest is invalid: {path}")
    return _ArchiveRecord(path, "file", raw_size, raw_digest, 0o644, None)


def _validate_manifest_records(records: tuple[_ArchiveRecord, ...]) -> None:
    if [record.path for record in records] != sorted(record.path for record in records):
        raise ValueError("archive manifest members are not in canonical order")
    kinds: dict[str, Literal["directory", "file"]] = {
        record.path: record.kind for record in records
    }
    if len(kinds) != len(records):
        raise ValueError("archive manifest members are not unique")
    for record in records:
        parent = PurePosixPath(record.path).parent
        while str(parent) != ".":
            if kinds.get(str(parent)) != "directory":
                raise ValueError(
                    f"archive member path collision or missing directory: {record.path}"
                )
            parent = parent.parent


def _parsed_manifest(
    encoded: bytes, *, expected_skill: str, expected_run_id: str
) -> tuple[_ArchiveRecord, ...]:
    payload = _manifest_payload(encoded)
    if (
        payload["archive_format"] != ARCHIVE_FORMAT
        or payload["schema_version"] != ARCHIVE_SCHEMA_VERSION
    ):
        raise ValueError("unsupported archive manifest format or schema version")
    if payload["skill"] != expected_skill or payload["run_id"] != expected_run_id:
        raise ValueError("archive manifest identity does not match the requested run")
    members = payload["members"]
    if not isinstance(members, list):
        raise TypeError("archive manifest member count is invalid")
    member_values = cast("list[object]", members)
    if payload["member_count"] != len(member_values):
        raise ValueError("archive manifest member count is invalid")
    records = tuple(_manifest_record(member) for member in member_values)
    _validate_manifest_records(records)
    canonical = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if encoded != canonical:
        raise ValueError("archive manifest is not canonical JSON")
    return records


def _read_archive_manifest(
    archive: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    *,
    expected_skill: str,
    expected_run_id: str,
) -> tuple[bytes, tuple[_ArchiveRecord, ...]]:
    manifests = [member for member in members if member.name == ARCHIVE_MANIFEST_NAME]
    if len(manifests) != 1 or not manifests[0].isreg():
        raise ValueError("archive must contain exactly one root archive manifest")
    source = archive.extractfile(manifests[0])
    if source is None:
        raise ValueError("archive manifest cannot be read")
    with source:
        manifest = source.read()
    return manifest, _parsed_manifest(
        manifest,
        expected_skill=expected_skill,
        expected_run_id=expected_run_id,
    )


def _archive_member_records(
    archive: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    expected: tuple[_ArchiveRecord, ...],
) -> tuple[_ArchiveRecord, ...]:
    expected_by_path = {record.path: record for record in expected}
    actual: list[_ArchiveRecord] = []
    for member in members:
        name = _safe_archive_path(
            member.name, allow_manifest=member.name == ARCHIVE_MANIFEST_NAME
        )
        if name == ARCHIVE_MANIFEST_NAME:
            continue
        expected_record = expected_by_path.get(name)
        if expected_record is None:
            raise ValueError("archive members do not match archive manifest")
        if member.isdir():
            if expected_record.kind != "directory" or member.size != 0:
                raise ValueError("archive members do not match archive manifest")
            actual.append(_ArchiveRecord(name, "directory", 0, None, 0o755, None))
            continue
        if not member.isreg() or expected_record.kind != "file":
            raise ValueError(f"unsupported archive member type: {name}")
        source = archive.extractfile(member)
        if source is None:
            raise ValueError(f"archive regular member cannot be read: {name}")
        with source:
            content = source.read()
        if (
            len(content) != expected_record.size
            or hashlib.sha256(content).hexdigest() != expected_record.sha256
        ):
            raise ValueError(f"archive member digest mismatch: {name}")
        actual.append(
            _ArchiveRecord(
                name,
                "file",
                len(content),
                expected_record.sha256,
                member.mode & 0o777,
                content,
            )
        )
    return tuple(actual)


def _read_archive(
    archive_path: Path, *, expected_skill: str, expected_run_id: str
) -> tuple[bytes, tuple[_ArchiveRecord, ...]]:
    entry = archive_path.lstat()
    if not stat.S_ISREG(entry.st_mode):
        raise ValueError(f"run archive is not a regular file: {archive_path}")
    with archive_path.open("rb") as probe:
        if probe.read(2) != b"\x1f\x8b":
            raise ValueError("invalid gzip header")
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            manifest, expected = _read_archive_manifest(
                archive,
                members,
                expected_skill=expected_skill,
                expected_run_id=expected_run_id,
            )
            actual = _archive_member_records(archive, members, expected)
    except (EOFError, gzip.BadGzipFile, tarfile.ReadError) as error:
        raise ValueError("invalid gzip header") from error
    if [record.path for record in actual] != [record.path for record in expected]:
        raise ValueError("archive members do not match archive manifest")
    return manifest, tuple(actual)


def _verify_materialized_tree(
    run_dir: Path, *, expected_skill: str, expected_run_id: str
) -> tuple[str, int, int]:
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise ValueError(f"materialized run directory is not a directory: {run_dir}")
    manifest_path = run_dir / ARCHIVE_MANIFEST_NAME
    manifest_entry = manifest_path.lstat()
    if not stat.S_ISREG(manifest_entry.st_mode):
        raise ValueError("archive manifest is not a regular file")
    manifest = manifest_path.read_bytes()
    expected = _parsed_manifest(
        manifest,
        expected_skill=expected_skill,
        expected_run_id=expected_run_id,
    )
    actual = _tree_records(run_dir, allow_manifest=True)
    actual_shape = [
        (record.path, record.kind, record.size, record.sha256) for record in actual
    ]
    expected_shape = [
        (record.path, record.kind, record.size, record.sha256) for record in expected
    ]
    if actual_shape != expected_shape:
        raise ValueError("materialized run directory does not match archive manifest")
    expanded_size = len(manifest) + sum(record.size for record in actual)
    return hashlib.sha256(manifest).hexdigest(), len(actual), expanded_size


def _materialize_records(
    *,
    records: tuple[_ArchiveRecord, ...],
    manifest: bytes,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
) -> tuple[str, int, int]:
    if run_dir.exists() or run_dir.is_symlink():
        raise FileExistsError(
            f"refusing to merge archive into existing run directory: {run_dir}"
        )
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".materialize-", dir=run_dir.parent))
    try:
        for record in records:
            if record.kind == "directory":
                destination = temporary.joinpath(*PurePosixPath(record.path).parts)
                destination.mkdir(mode=0o755)
                destination.chmod(0o755)
        manifest_path = temporary / ARCHIVE_MANIFEST_NAME
        _ = manifest_path.write_bytes(manifest)
        _ = manifest_path.chmod(0o644)
        for record in records:
            if record.kind != "file" or record.content is None:
                continue
            destination = temporary.joinpath(*PurePosixPath(record.path).parts)
            _ = destination.write_bytes(record.content)
            _ = destination.chmod(record.mode)
        _ = _verify_materialized_tree(
            temporary,
            expected_skill=expected_skill,
            expected_run_id=expected_run_id,
        )
        _ = temporary.replace(run_dir)
        try:
            return _verify_materialized_tree(
                run_dir,
                expected_skill=expected_skill,
                expected_run_id=expected_run_id,
            )
        except (OSError, ValueError):
            shutil.rmtree(run_dir)
            raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _archive_error(error: Exception) -> int:
    print(f"ERROR={error}")
    return 1


def _append_archive_manifest(archive: tarfile.TarFile, manifest: bytes) -> None:
    manifest_info = tarfile.TarInfo(ARCHIVE_MANIFEST_NAME)
    manifest_info.mode = 0o644
    manifest_info.size = len(manifest)
    manifest_info.mtime = manifest_info.uid = manifest_info.gid = 0
    manifest_info.uname = manifest_info.gname = ""
    archive.addfile(manifest_info, io.BytesIO(manifest))


def _run_log_archive(arguments: list[str]) -> int:
    staging_root = Path(_flag(arguments, "--staging-root"))
    output_dir = Path(_flag(arguments, "--output-dir"))
    skill = _flag(arguments, "--skill")
    run_id = _flag(arguments, "--run-id")
    if not staging_root.name or not output_dir.name or not skill or not run_id:
        return 2
    archive_path = output_dir / f"{run_id}.tar.gz"
    temporary = archive_path.with_name(f".{archive_path.name}.tmp-{os.getpid()}")
    try:
        records = _tree_records(staging_root)
        manifest = _manifest_bytes(records, skill=skill, run_id=run_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        if archive_path.is_symlink():
            raise OSError(f"refusing symlinked archive destination: {archive_path}")
        if archive_path.exists() and not archive_path.is_file():
            raise OSError(f"archive destination is not a regular file: {archive_path}")
        with temporary.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    manifest_written = False
                    for record in records:
                        if not manifest_written and record.path > ARCHIVE_MANIFEST_NAME:
                            _append_archive_manifest(archive, manifest)
                            manifest_written = True
                        info = tarfile.TarInfo(record.path)
                        info.mode = record.mode
                        info.mtime = info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        if record.kind == "directory":
                            info.type = tarfile.DIRTYPE
                            archive.addfile(info)
                        else:
                            info.type = tarfile.REGTYPE
                            info.size = record.size
                            archive.addfile(info, io.BytesIO(record.content or b""))
                    if not manifest_written:
                        _append_archive_manifest(archive, manifest)
        _ = temporary.replace(archive_path)
    except (OSError, ValueError) as error:
        temporary.unlink(missing_ok=True)
        return _archive_error(error)
    print(f"ARCHIVE_PATH={archive_path}")
    print(f"ARCHIVE_SHA256={hashlib.sha256(archive_path.read_bytes()).hexdigest()}")
    print(f"MANIFEST_SHA256={hashlib.sha256(manifest).hexdigest()}")
    print(f"MEMBER_COUNT={len(records)}")
    return 0


def _run_log_materialize(arguments: list[str]) -> int:
    run_dir = Path(_flag(arguments, "--run-dir"))
    skill = _flag(arguments, "--skill")
    run_id = _flag(arguments, "--run-id")
    if not run_dir.name or not skill or not run_id:
        return 2
    try:
        if "--verify-existing" in arguments:
            manifest_sha256, member_count, expanded_size = _verify_materialized_tree(
                run_dir,
                expected_skill=skill,
                expected_run_id=run_id,
            )
        elif staging_root := _flag(arguments, "--staging-root"):
            records = _tree_records(Path(staging_root))
            manifest = _manifest_bytes(records, skill=skill, run_id=run_id)
            expected_manifest = _flag(arguments, "--expected-manifest-sha256")
            if expected_manifest != hashlib.sha256(manifest).hexdigest():
                raise ValueError("staging tree no longer matches the pending archive manifest")
            manifest_sha256, member_count, expanded_size = _materialize_records(
                records=records,
                manifest=manifest,
                run_dir=run_dir,
                expected_skill=skill,
                expected_run_id=run_id,
            )
        else:
            archive_path = _flag(arguments, "--archive-path")
            if not archive_path:
                return 2
            manifest, records = _read_archive(
                Path(archive_path),
                expected_skill=skill,
                expected_run_id=run_id,
            )
            manifest_sha256, member_count, expanded_size = _materialize_records(
                records=records,
                manifest=manifest,
                run_dir=run_dir,
                expected_skill=skill,
                expected_run_id=run_id,
            )
    except (OSError, ValueError) as error:
        return _archive_error(error)
    print(f"RUN_DIR={run_dir}")
    print(f"MANIFEST_SHA256={manifest_sha256}")
    print(f"MEMBER_COUNT={member_count}")
    print(f"EXPANDED_SIZE={expanded_size}")
    return 0


def _append_execution_issue(*, log: Path, category: str, entry: str) -> None:
    """Append `entry` under `### category`, matching the Rust composer."""
    log.parent.mkdir(parents=True, exist_ok=True)
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    header = f"### {category}"
    lines = text.splitlines()
    if header in lines:
        out: list[str] = []
        inserted = False
        in_target = False
        for line in lines:
            if line == header:
                in_target = True
                out.append(line)
                continue
            if in_target and line.startswith("### "):
                if not inserted:
                    out.extend(["", entry.rstrip("\n")])
                    inserted = True
                in_target = False
            out.append(line)
        if in_target and not inserted:
            out.extend(["", entry.rstrip("\n")])
        rendered = "\n".join(out) + "\n"
    else:
        prefix = "\n" if text else ""
        rendered = text.rstrip("\n") + prefix + header + "\n\n" + entry.rstrip("\n") + "\n"
    _ = log.write_text(rendered, encoding="utf-8")


def _execution_issue_chunks(body: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_fence = False
    pending_break = False
    for line in body.splitlines():
        if not in_fence and not line.strip():
            pending_break = bool(current)
            continue
        candidate = line.lstrip()
        if candidate.startswith("- "):
            candidate = candidate[2:].lstrip()
        fence = candidate.startswith("```")
        if not in_fence and line.startswith("- ") and current and not fence:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
            pending_break = False
        if pending_break and current:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
        pending_break = False
        current.append(line)
        if fence:
            in_fence = not in_fence
    if current:
        chunks.append("\n".join(current).strip() + "\n")
    return chunks


def _execution_issue_keys(markdown: str) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    category = "Warnings"
    body: list[str] = []
    for line in [*markdown.splitlines(), "### __END__"]:
        if line.startswith("### "):
            for chunk in _execution_issue_chunks("\n".join(body)):
                keys.add((category, chunk.strip()))
            category = line[4:].strip()
            body = []
        else:
            body.append(line)
    return keys


def _execution_issue_batch_keys(path: Path) -> set[tuple[str, str]]:
    """Return valid category/body identities from one durable batch double."""
    keys: set[tuple[str, str]] = set()
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            decoded = cast("object", json.loads(raw))
        except json.JSONDecodeError:
            continue
        if not isinstance(decoded, dict):
            continue
        row = cast("dict[str, object]", decoded)
        durable_category = row.get("category")
        durable_body = row.get("body")
        if isinstance(durable_category, str) and isinstance(durable_body, str):
            keys.update(
                (durable_category, chunk.strip())
                for chunk in _execution_issue_chunks(durable_body)
            )
    return keys


def _execution_issues_append(arguments: list[str]) -> int:
    log = Path(_flag(arguments, "--log"))
    category = _flag(arguments, "--category") or "Tool Failures"
    entry = _flag(arguments, "--entry")
    existing = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    known = _execution_issue_keys(existing)
    batch = _flag(arguments, "--existing-batch")
    if batch and Path(batch).is_file():
        known.update(_execution_issue_batch_keys(Path(batch)))
    kept: list[str] = []
    for chunk in _execution_issue_chunks(entry):
        key = (category, chunk.strip())
        if key in known:
            continue
        known.add(key)
        kept.append(chunk)
    status = "duplicate"
    if kept:
        _append_execution_issue(log=log, category=category, entry="\n".join(kept))
        status = "appended"
    if "--report-status" in arguments:
        print(f"APPEND_STATUS={status}")
    return 0


def _execution_issues_flush_common(arguments: list[str], *, clear: bool) -> int:
    issue_log = Path(_flag(arguments, "--issue-log"))
    if not issue_log.is_file() or not issue_log.read_text(encoding="utf-8", errors="replace"):
        print("FLUSH_STATUS=skip")
        print("RECORDS=0")
        return 0
    records = sum(
        1
        for line in issue_log.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("- ")
    )
    print("FLUSH_STATUS=ok")
    print(f"RECORDS={records}")
    if records and clear:
        _ = issue_log.write_text("", encoding="utf-8")
    return 0


def _execution_issues_flush(arguments: list[str]) -> int:
    return _execution_issues_flush_common(arguments, clear=True)


def _execution_issues_flush_safety_net(arguments: list[str]) -> int:
    return _execution_issues_flush_common(arguments, clear=False)


def _execution_issues_refresh(arguments: list[str]) -> int:
    tmpdir = Path(_flag(arguments, "--implement-tmpdir"))
    if not tmpdir.is_dir():
        print("REFRESHED=false")
        print("ERROR=--implement-tmpdir not found")
        return 0 if "--best-effort" in arguments else 2
    print("REFRESHED=true")
    print("REASON=issue-not-set")
    return 0


def _bind_larch_package() -> None:
    """Make `larch.*` importable in this detached bootstrap process.

    The double is executed by `scripts/larch.sh`, which exports the plugin root
    but no `PYTHONPATH`, so the shared run-log helpers need an explicit path.
    """
    package_root = str(_plugin_root() / "python")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)


def _log_envelope(*, path: Path | None, written: bool, unchanged: bool, error: str = "") -> None:
    size = path.stat().st_size if path is not None and path.is_file() else 0
    digest = ""
    if path is not None and path.is_file():
        import hashlib  # noqa: PLC0415 - deferred so the module imports without the runtime package

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"LOG_WRITTEN={'true' if written else 'false'}")
    print(f"LOG_PATH={path if path is not None else ''}")
    print(f"BYTES={size}")
    print(f"SHA256={digest}")
    print("COMMIT_SHA=")
    print(f"UNCHANGED={'true' if unchanged else 'false'}")
    if error:
        print(f"ERROR={error}")


def _identity(arguments: list[str]) -> tuple[Path, str, str]:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root = run_log_batch._resolve_log_root(_flag(arguments, "--log-root"))  # noqa: SLF001 - test double reuses the shared resolver
    return log_root, _flag(arguments, "--skill"), _flag(arguments, "--run-id")


def _run_log_init(arguments: list[str]) -> int:
    log_root, skill, run_id = _identity(arguments)
    path = log_root / skill / run_id / "manifest.json"
    if path.is_file():
        _log_envelope(path=path, written=False, unchanged=True)
        return 0
    issue = _flag(arguments, "--issue")
    if issue and not issue.isdigit():
        _log_envelope(path=None, written=False, unchanged=False, error=f"invalid issue: {issue}")
        return 1
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "skill": skill,
                "run_id": run_id,
                "operator_cwd": "<OPERATOR_CWD>",
                "operator_repo_root": "<REPO_ROOT>",
                "parent_skill": _flag(arguments, "--parent-skill") or None,
                "parent_run_id": _flag(arguments, "--parent-run-id") or None,
                "issue_number": int(issue) if issue else None,
                "larch_version": _version(),
                "model_roster": {"main": "unknown"},
                "effort": "unknown",
                "started_at": timestamp,
                "updated_at": timestamp,
                "attempt": 1,
                "superseded_by": None,
                "stalled_at_step": None,
                "steps_ran": {},
                "flags": {},
                "status": "partial",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _log_envelope(path=path, written=True, unchanged=False)
    return 0


def _manifest_scalar(raw: str) -> object:
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


def _manifest_updates(arguments: list[str]) -> dict[str, object]:
    updates: dict[str, object] = {}
    for index, token in enumerate(arguments):
        if token != "--field" or index + 1 >= len(arguments):
            continue
        key, separator, raw = arguments[index + 1].partition("=")
        if not separator or not key:
            raise ValueError(f"invalid field assignment: {arguments[index + 1]}")
        updates[key] = _manifest_scalar(raw)
    return updates


def _apply_manifest_updates(*, payload: dict[str, object], updates: dict[str, object]) -> None:
    for key, value in updates.items():
        if not key.startswith("steps_ran."):
            payload[key] = value
            continue
        steps = payload.setdefault("steps_ran", {})
        if not isinstance(steps, dict):
            raise TypeError("steps_ran must be an object")
        steps[key.split(".", 1)[1]] = value


def _run_log_manifest(arguments: list[str]) -> int:
    """Apply a test-fixture manifest patch for the Rust-owned selector."""
    log_root, skill, run_id = _identity(arguments)
    path = log_root / skill / run_id / "manifest.json"
    if not path.is_file():
        _log_envelope(path=None, written=False, unchanged=False, error=f"manifest not found: {path}")
        return 1
    try:
        payload_raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload_raw, dict):
            raise TypeError("manifest root must be an object")
        payload = cast("dict[str, object]", payload_raw)
        _apply_manifest_updates(payload=payload, updates=_manifest_updates(arguments))
        payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _ = path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        _log_envelope(path=None, written=False, unchanged=False, error=str(error))
        return 1
    _log_envelope(path=path, written=True, unchanged=False)
    return 0


def _run_log_batch_command(arguments: list[str], *, append: bool) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    batch = _flag(arguments, "--batch")
    source = _flag(arguments, "--record-file" if append else "--input-file")
    writer = run_log_batch._append_batch if append else run_log_batch._write_batch  # noqa: SLF001 - test double reuses the shared batch writers
    key = "record_file" if append else "input_file"
    try:
        path, written, unchanged = writer(
            log_root=log_root, skill=skill, run_id=run_id, batch=batch, **{key: source}
        )
    except ValueError as error:
        _log_envelope(path=None, written=False, unchanged=False, error=str(error))
        return 1
    except OSError as error:
        _log_envelope(path=None, written=False, unchanged=False, error=str(error))
        return 2
    _log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def _run_log_write(arguments: list[str]) -> int:
    return _run_log_batch_command(arguments, append=False)


def _run_log_append(arguments: list[str]) -> int:
    return _run_log_batch_command(arguments, append=True)


def _run_log_exists(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    batch = _flag(arguments, "--batch")
    if batch not in run_log_batch._LARCH_LOG_BATCHES:  # noqa: SLF001 - test double reuses the shared registry
        _log_envelope(path=None, written=False, unchanged=False, error=f"unknown batch: {batch}")
        return 1
    path = run_log_batch._batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)  # noqa: SLF001 - test double reuses the shared path owner
    _log_envelope(path=path, written=False, unchanged=path.exists())
    return 0


def _run_log_write_round(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    round_number = _flag(arguments, "--round")
    source = Path(_flag(arguments, "--source-dir"))
    if not round_number.isdigit() or int(round_number) <= 0:
        _log_envelope(path=None, written=False, unchanged=False, error="--round must be a positive integer")
        return 1
    if not source.is_dir():
        _log_envelope(path=None, written=False, unchanged=False, error=f"source directory not found: {source}")
        return 1
    dest = run_log_batch._run_dir(log_root=log_root, skill=skill, run_id=run_id) / f"round-{round_number}"  # noqa: SLF001 - test double reuses the shared path owner
    dest.mkdir(parents=True, exist_ok=True)
    written = False
    for item in sorted(source.iterdir()):
        if not item.is_file() or item.is_symlink():
            continue
        name = item.name
        if run_log_batch._is_round_sidecar_file(name) or not run_log_batch._round_artifact_included(name):  # noqa: SLF001 - test double reuses the shared filters
            continue
        content = run_log_batch._stage_round_artifact(src=item, name=name)  # noqa: SLF001 - test double reuses the shared staging transform
        out = dest / name
        if not out.exists() or out.read_text(encoding="utf-8", errors="replace") != content:
            run_log_batch._atomic_write(path=out, content=content)  # noqa: SLF001 - test double reuses the shared writer
            written = True
    _log_envelope(path=dest, written=written, unchanged=not written)
    return 0


def _missing_required_files(*, run_dir: Path, manifest_tsv: Path, manifest: object) -> list[str]:
    """Return the reachable required-file rows that are absent from `run_dir`."""
    from larch.report import run_log_manifest  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    missing: list[str] = []
    for line in manifest_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not parts or parts[0] == "relative_path":
            continue
        relative_path = parts[0]
        if not run_log_manifest._verify_condition_reached(  # noqa: SLF001 - test double reuses the shared reachability chain
            condition=parts[1] if len(parts) > 1 else "always",
            run_dir=run_dir,
            manifest_data=manifest,
            manifest_status=run_log_manifest._manifest_field(manifest=manifest, key="status"),  # noqa: SLF001 - test double reuses the shared field reader
            manifest_pr_number=run_log_manifest._manifest_field(manifest=manifest, key="pr_number"),  # noqa: SLF001 - test double reuses the shared field reader
        ):
            continue
        if "*" in relative_path:
            if not any(hit.is_file() for hit in run_dir.glob(relative_path)):
                missing.append(relative_path)
        elif not (run_dir / relative_path).is_file():
            missing.append(relative_path)
    return missing


def _run_log_verify_completeness(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_manifest  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    if not arguments:
        print("MISSING=manifest", file=sys.stderr)
        return 1
    run_dir = Path(arguments[0])
    if not run_dir.is_dir():
        print(f"verify-completeness: run dir not found: {run_dir}", file=sys.stderr)
        return 1
    manifest_tsv = Path(
        os.environ.get("LARCH_VERIFY_MANIFEST")
        or _plugin_root() / "docs" / "run-logs-required-files.tsv"
    )
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file() or not manifest_tsv.is_file():
        print("MISSING=manifest")
        return 1
    try:
        manifest = run_log_manifest.Manifest.from_json(run_log_manifest._read_manifest_v2(manifest_path))  # noqa: SLF001 - test double reuses the shared reader
    except (OSError, json.JSONDecodeError, TypeError):
        print("MISSING=manifest")
        return 1
    missing = _missing_required_files(run_dir=run_dir, manifest_tsv=manifest_tsv, manifest=manifest)
    if missing:
        print("MISSING=" + ",".join(missing))
        return 1
    print("OK")
    return 0


def _retry_suffix(retry_count: str, transient_retry_count: str) -> str:
    """Mirror the Rust owner's retry annotation; both counters include attempt 1."""
    if retry_count and transient_retry_count:
        parts = [
            f"{label}={value}"
            for label, value in (
                ("auth-retries", int(retry_count) - 1),
                ("transient-retries", int(transient_retry_count) - 1),
            )
            if value > 0
        ]
        return ", " + ", ".join(parts) if parts else ""
    return f", retries={retry_count}" if retry_count else ""


def _append_failure(arguments: list[str]) -> int:
    log = Path(_flag(arguments, "--log"))
    category = _flag(arguments, "--category")
    if not log.name or not category:
        print("FAILED=true")
        return 1
    exit_code = _flag(arguments, "--exit-code")
    output_file = Path(_flag(arguments, "--output-file"))
    body = (
        output_file.read_text(encoding="utf-8", errors="replace")
        if output_file.is_file() and output_file.stat().st_size
        else f"no diagnostics captured (exit {exit_code})\n"
    )
    verdict = _flag(arguments, "--verdict")
    suffix = f", {verdict}" if verdict else ""
    suffix += _retry_suffix(
        _flag(arguments, "--retry-count"), _flag(arguments, "--transient-retry-count")
    )
    entry = (
        f"- **Step {_flag(arguments, '--site')}: {_flag(arguments, '--tool')} "
        f"{_flag(arguments, '--status-label', 'failed')} (exit {exit_code}{suffix})**:\n"
        "  ```\n"
        f"{body.rstrip()}\n"
        "  ```\n"
    )
    _append_execution_issue(log=log, category=category, entry=entry)
    print("APPENDED=true")
    print(f"LOG={log}")
    return 0


def _append_entry(arguments: list[str]) -> int:
    log = Path(_flag(arguments, "--log"))
    category = _flag(arguments, "--category")
    entry_file = _flag(arguments, "--entry-file")
    entry = (
        Path(entry_file).read_text(encoding="utf-8", errors="replace")
        if entry_file
        else _flag(arguments, "--entry")
    )
    if not log.name or not category or not entry:
        print("FAILED=true")
        return 1
    _append_execution_issue(log=log, category=category, entry=entry)
    print("APPENDED=true")
    print(f"LOG={log}")
    return 0


def _launch_claude_subprocess(arguments: list[str]) -> int:
    output = _flag(arguments, "--output-file")
    prompt_file = _flag(arguments, "--prompt-file")
    if not output or not prompt_file:
        return 2
    try:
        prompt = Path(prompt_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 2
    model = _flag(arguments, "--model", "claude-sonnet-4-6")
    command = ["claude", "--print", "--output-format", "json", "--model", model]
    result = subprocess.run(
        command,
        check=False,
        input=prompt,
        text=True,
        capture_output=True,
    )
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    exit_code = result.returncode
    text = result.stdout
    if exit_code == 0:
        try:
            parsed = json.loads(result.stdout)
            if not isinstance(parsed, dict):
                raise TypeError("invalid Claude envelope")
            envelope = cast("dict[str, object]", parsed)
            value = envelope.get("result") if not envelope.get("is_error") else None
            if not isinstance(value, str) or not value:
                raise ValueError("invalid Claude envelope")
            text = value
        except (TypeError, ValueError, json.JSONDecodeError):
            text = "CLAUDE_JSON_RESULT_INVALID"
            exit_code = 99
    _ = target.write_text(text, encoding="utf-8")
    if result.stderr:
        _ = Path(f"{target}.stderr").write_text(result.stderr, encoding="utf-8")
    _ = Path(f"{target}.done").write_text(f"{exit_code}\n", encoding="utf-8")
    return exit_code


def _launch_claude_review(arguments: list[str]) -> int:
    output = _flag(arguments, "--output") or _flag(arguments, "--output-file")
    forced_result = os.environ.get("LARCH_TEST_CLAUDE_REVIEW_RESULT", "")
    if output and forced_result:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(forced_result, encoding="utf-8")
        _ = Path(f"{target}.done").write_text("0\n", encoding="utf-8")
        return 0
    prompt_file = _flag(arguments, "--prompt-file")
    if not output or not prompt_file:
        return 2
    forwarded = [
        "--prompt-file",
        prompt_file,
        "--output-file",
        output,
        "--model",
        _flag(arguments, "--model", "claude-sonnet-4-6"),
    ]
    return _launch_claude_subprocess(forwarded)


WATERFALL_SWITCHES = frozenset({"--competition-notice", "--no-fallback", "--straggler-cutoff", "--skip-invalid-slots"})


def _waterfall_rows(slots_file: str) -> list[dict[str, object]]:
    text: str = Path(slots_file).read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        if not line:
            continue
        parsed: object = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(line)
        rows.append(cast("dict[str, object]", parsed))
    return rows


def _waterfall_prompt(row: dict[str, object], tool: str) -> str:
    per_tool: object = row.get("prompt_files")
    if isinstance(per_tool, dict):
        return str(cast("dict[str, object]", per_tool).get(tool, ""))
    return str(row.get("prompt_file", ""))


def _waterfall_output(base: str, phase: str) -> str:
    if phase == "phase1":
        return base
    if base.endswith(".txt"):
        return f"{base[:-4]}-{phase}.txt"
    return f"{base}-{phase}"


def _waterfall_panel_env(*, row: dict[str, object], tool: str, phase: str, values: dict[str, str]) -> dict[str, str]:
    """Publish the panel-context keys the real dispatcher gives its children."""
    artifact_dir = values.get("--panel-artifact-dir", "") or os.environ.get("LARCH_PANEL_ARTIFACT_DIR", "")
    if not artifact_dir:
        return {}
    per_tool: object = row.get("payload_files")
    payload = cast("dict[str, object]", per_tool).get(tool, 0) if isinstance(per_tool, dict) else row.get("payload_bytes", 0)
    published = {
        "LARCH_PANEL_ARTIFACT_DIR": artifact_dir,
        "LARCH_PANEL_SITE": values.get("--site", "review Step 2"),
        "LARCH_PANEL_SLOT": str(row.get("slot", "")),
        "LARCH_PANEL_PHASE": phase,
        "LARCH_PANEL_PRIMARY_TOOL": tool,
        "LARCH_PANEL_SOURCE_AGENT_FILE": str(row.get("agent", "")),
        "LARCH_PANEL_PAYLOAD_BYTES": str(payload),
    }
    name = Path(artifact_dir).name
    if name.startswith("round-") and name[len("round-") :].isdigit():
        published["LARCH_PANEL_ROUND_DIR"] = artifact_dir
        published["LARCH_PANEL_ROUND_NUM"] = name[len("round-") :]
    return published


def _waterfall_context(values: dict[str, str]) -> list[str]:
    context: list[str] = []
    for flag in ("--diff-file", "--commit-count", "--plan-file", "--feature-file", "--scope-files", "--description-text", "--difficulty", "--session-env-path"):
        if values.get(flag):
            context.extend([flag, values[flag]])
    return context


def _waterfall_vendor_extras(*, row: dict[str, object], tool: str, values: dict[str, str], switches: set[str]) -> list[str]:
    extras: list[str] = ["--site", values.get("--site", "review Step 2")]
    if "--competition-notice" in switches:
        extras.append("--competition-notice")
    if values.get("--competition-notice-file"):
        extras.extend(["--competition-notice-file", values["--competition-notice-file"]])
    if tool == "codex":
        role = str(row.get("model_role", "")) or values.get("--model-role", "")
        if role:
            extras.extend(["--model-role", role])
        if values.get("--default-model"):
            extras.extend(["--default-model", values["--default-model"]])
    elif tool == "cursor" and row.get("cursor_model"):
        extras.extend(["--cursor-model", str(row["cursor_model"])])
    return extras


def _waterfall_launch(*, row: dict[str, object], tool: str, output: str, values: dict[str, str], switches: set[str]) -> int:
    prompt = _waterfall_prompt(row, tool)
    source = ["--prompt-file", prompt] if prompt else ["--agent-file", str(row.get("agent", ""))]
    shared = ["--output", output, *source, "--mode", values.get("--mode", "description"), "--timeout", values.get("--timeout", "1800"), *_waterfall_context(values)]
    if tool == "claude":
        forwarded = list(shared)
        if values.get("--claude-read-tools-add-dir"):
            forwarded.extend(["--read-tools-add-dir", values["--claude-read-tools-add-dir"]])
        return _launch_claude_review(forwarded)
    extras = _waterfall_vendor_extras(row=row, tool=tool, values=values, switches=switches)
    return _launch_review(["--tool", tool, *shared, *extras])


def _waterfall_accepted(output: str, timeout: str, pattern: str) -> tuple[bool, str]:
    root = os.environ.get(ENV_CLAUDE_PLUGIN_ROOT, "")
    command = [sys.executable, str(Path(root) / "python" / "cli.py"), "agent", "collect-results", "--timeout", timeout, "--summary-only", output]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return False, ""
    status = ""
    reviewer = ""
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key == "STATUS":
            status = value
        elif separator and key == "REVIEWER_FILE":
            reviewer = value
    if status not in {"OK", "cap_hit"}:
        return False, ""
    final = reviewer or output
    if status == "OK" and pattern:
        try:
            body = Path(final).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False, ""
        if not re.search(pattern, body, re.MULTILINE):
            return False, ""
    return True, final


@dataclass(frozen=True)
class _WaterfallOutcome:
    """One slot's ladder result inside the bootstrap test double."""

    final: str
    tool: str
    accepted: bool
    fallback: int


def _waterfall_ladder(*, row: dict[str, object], present: dict[str, bool], switches: set[str]) -> list[tuple[str, str]]:
    primary = str(row.get("tool", ""))
    other = "cursor" if primary == "codex" else "codex"
    ladder: list[tuple[str, str]] = [(primary, "phase1")] if present.get(primary, False) else []
    if "--no-fallback" not in switches:
        if present.get(other, False):
            ladder.append((other, "phase2"))
        ladder.append(("claude", "phase3"))
    return ladder


@dataclass(frozen=True)
class _WaterfallRequest:
    """Everything one slot's ladder run needs from the dispatch arguments."""

    values: dict[str, str]
    switches: set[str]
    timeout: str
    pattern: str


def _waterfall_run_ladder(
    *,
    row: dict[str, object],
    ladder: list[tuple[str, str]],
    request: _WaterfallRequest,
    phases: dict[str, list[str]],
) -> _WaterfallOutcome:
    base = str(row.get("output", ""))
    fallback = 0
    for tool, phase in ladder:
        output = _waterfall_output(base, phase)
        phases[phase].append(output)
        if phase == "phase3":
            fallback += 1
        _waterfall_launch_with_panel_env(row=row, tool=tool, phase=phase, output=output, request=request)
        accepted, final = _waterfall_accepted(output, request.timeout, request.pattern)
        if accepted:
            return _WaterfallOutcome(final=final, tool=tool, accepted=True, fallback=fallback)
        if phase == "phase3":
            return _WaterfallOutcome(final=output, tool=tool, accepted=False, fallback=fallback)
    return _WaterfallOutcome(final="", tool="", accepted=False, fallback=fallback)


def _waterfall_launch_with_panel_env(
    *, row: dict[str, object], tool: str, phase: str, output: str, request: _WaterfallRequest
) -> None:
    published = _waterfall_panel_env(row=row, tool=tool, phase=phase, values=request.values)
    saved = {key: os.environ.get(key) for key in published}
    os.environ.update(published)
    try:
        _ = _waterfall_launch(row=row, tool=tool, output=output, values=request.values, switches=request.switches)
    finally:
        for key, previous in saved.items():
            if previous is None:
                _ = os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _dispatch_waterfall(arguments: list[str]) -> int:
    """Sequential test double for the Rust three-phase waterfall dispatcher.

    Python caller tests only need the phase order, the published paths file,
    and the stdout key-values. The real contract, including concurrency, drop
    sidecars, and the straggler cutoff, is proved in
    `crates/larch-cli/tests/waterfall_commands.rs`.
    """
    switches = {argument for argument in arguments if argument in WATERFALL_SWITCHES}
    values, _unused = _option_values([argument for argument in arguments if argument not in WATERFALL_SWITCHES])
    slots_file = values.get("--slots-file", "")
    if not slots_file or values.get("--mode", "") not in {"diff", "description"}:
        return 2
    present = {"codex": values.get("--codex-present") == "true", "cursor": values.get("--cursor-present") == "true", "claude": False}
    request = _WaterfallRequest(
        values=values,
        switches=switches,
        timeout=values.get("--timeout", "1800"),
        pattern=_posix_pattern(values.get("--require-result-pattern", "")),
    )
    rows = _waterfall_rows(slots_file)
    paths_file = values.get("--paths-file", "") or f"{slots_file}.output-files"
    finals: list[str] = []
    tools: list[str] = []
    phases: dict[str, list[str]] = {"phase1": [], "phase2": [], "phase3": []}
    fallback = 0
    dispatch_ok = True
    for row in rows:
        ladder = _waterfall_ladder(row=row, present=present, switches=switches)
        outcome = _waterfall_run_ladder(row=row, ladder=ladder, request=request, phases=phases)
        fallback += outcome.fallback
        if outcome.final:
            finals.append(outcome.final)
            tools.append(outcome.tool)
        if not outcome.accepted:
            dispatch_ok = False
    Path(paths_file).parent.mkdir(parents=True, exist_ok=True)
    _ = Path(paths_file).write_text("".join(f"{value}\n" for value in finals), encoding="utf-8")
    for key, value in (
        ("PHASE1_SLOTS", " ".join(phases["phase1"])),
        ("PHASE2_SLOTS", " ".join(phases["phase2"])),
        ("PHASE3_SLOTS", " ".join(phases["phase3"])),
        ("ALL_OUTPUT_FILES", " ".join(finals)),
        ("ALL_OUTPUT_FILES_PATH", paths_file),
        ("ALL_OUTPUT_TOOLS", " ".join(tools)),
        ("FALLBACK_COUNT", str(fallback)),
        ("COMBINED_FALLBACK_COUNT", str(fallback)),
        ("STRAGGLER_DROPPED_COUNT", "0"),
        ("DISPATCH_OK", "true" if dispatch_ok else "false"),
        ("STATIC_DISPATCH_OK", "true" if dispatch_ok else "false"),
        ("DYNAMIC_DISPATCH_OK", "true"),
    ):
        print(f"{key}={value}")
    if "--no-fallback" in switches and not finals and rows:
        print("ALL_SLOTS_DROPPED=true")
    return 0


def _posix_pattern(raw: str) -> str:
    replacements = {
        "[[:alnum:]]": "[A-Za-z0-9]",
        "[[:alpha:]]": "[A-Za-z]",
        "[[:blank:]]": "[ \t]",
        "[[:digit:]]": r"\d",
        "[[:lower:]]": "[a-z]",
        "[[:space:]]": r"\s",
        "[[:upper:]]": "[A-Z]",
    }
    translated = raw
    for needle, replacement in replacements.items():
        translated = translated.replace(needle, replacement)
    return translated



# --------------------------------------------------------- issue-body wire verbs
#
# The `/design` to `/implement` wire verbs moved to the Rust owner in #8171, so
# the Python callers that used to run them in process now spawn the bootstrap.
# These doubles answer the exact rows and exit codes those callers branch on;
# the byte-level contract itself is proven against the frozen reference in
# `crates/larch-cli/tests/parity.rs`.


def _wire_option(arguments: list[str], name: str) -> str:
    """Read one `--name value` or `--name=value` option from a wire command line."""
    prefix = f"{name}="
    for index, argument in enumerate(arguments):
        if argument == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(prefix):
            return argument[len(prefix) :]
    return ""


def _issue_title_eligibility(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.issue import issue_wire  # noqa: PLC0415 - bound above, not at module import

    title = _wire_option(arguments, "--title")
    if not title:
        print("issue title: --title is required", file=sys.stderr)
        return 2
    trimmed = title.lstrip()
    marker = issue_wire.title_lifecycle_reject_marker(title)
    print(f"LIFECYCLE_REJECT={'true' if marker else 'false'}")
    if marker:
        print(f"LIFECYCLE_MARKER={marker}")
    archival = re.match(r"^\[.*report\] ", trimmed, re.IGNORECASE) is not None
    print(f"ARCHIVAL_REPORT={'true' if archival else 'false'}")
    brainstorm = re.match(r"^brainstorm([^A-Za-z]|$)", trimmed, re.IGNORECASE) is not None
    print(f"BRAINSTORM={'true' if brainstorm else 'false'}")
    return 0


def _plan_scope_paths(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.issue import issue_wire  # noqa: PLC0415 - bound above, not at module import

    plan_file = _wire_option(arguments, "--plan-file")
    plan = Path(plan_file) if plan_file else None
    if plan is None or not plan.is_file():
        print(f"extract-plan-scope-paths.sh: plan file not found: {plan_file}", file=sys.stderr)
        return 2
    separator = "\0" if ("-z" in arguments or "--null" in arguments) else "\n"
    paths = issue_wire.extract_scope_paths(plan_text=plan.read_text(encoding="utf-8", errors="replace"))
    _ = sys.stdout.write(separator.join(paths) + separator)
    return 0


def _implement_scope_disposition(arguments: list[str]) -> int:
    """Delegate to the frozen pre-cutover Python owner for hermetic unit tests."""
    _bind_larch_package()
    import importlib.util  # noqa: PLC0415 - load only when this verb is invoked

    reference = _plugin_root() / "fixtures" / "rust-parity" / "implement_scope_disposition_reference.py"
    module_name = "implement_scope_disposition_reference"
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, "scope_disposition_main"):
        return int(existing.scope_disposition_main(arguments))
    spec = importlib.util.spec_from_file_location(module_name, reference)
    if spec is None or spec.loader is None:
        print(
            f"implement scope-disposition: frozen reference missing: {reference}",
            file=sys.stderr,
        )
        return 2
    module = importlib.util.module_from_spec(spec)
    # dataclasses look up the defining module in sys.modules during class
    # creation; register before exec_module so frozen @dataclass types load.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return int(module.scope_disposition_main(arguments))


def _plan_block_strip_body(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.issue import issue_blocks  # noqa: PLC0415 - bound above, not at module import

    source = _wire_option(arguments, "--file")
    output = _wire_option(arguments, "--output")
    body = Path(source).read_text(encoding="utf-8", errors="replace") if source else sys.stdin.read()
    stripped, malformed = issue_blocks.strip_named_block(body=body, marker="plan")
    if malformed:
        if output:
            _ = Path(output).write_text("", encoding="utf-8")
        print(f"MALFORMED={malformed}")
        return 1
    if output:
        _ = Path(output).write_text(stripped, encoding="utf-8")
    else:
        _ = sys.stdout.write(stripped)
    return 0


def _plan_review_json_get_bool(arguments: list[str]) -> int:
    path = _flag(arguments, "--path")
    key = _flag(arguments, "--key")
    default = _flag(arguments, "--default", "false")
    if not path or not key or default not in {"true", "false"}:
        return 2
    value = default == "true"
    source = Path(path)
    if source.is_file() and not source.is_symlink():
        try:
            payload: object = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            item = cast("dict[str, object]", payload).get(key)
            if isinstance(item, bool):
                value = item
    print("true" if value else "false")
    return 0


def _plan_review_drift_baseline(arguments: list[str]) -> int:
    if not arguments or arguments[0] != "write-once":
        return 2
    values, switches = _option_values(arguments[1:])
    if switches or set(values) != {"--design-tmpdir", "--plan-lines", "--diff-lines"}:
        return 2
    plan_lines = values["--plan-lines"]
    diff_lines = values["--diff-lines"]
    if not plan_lines.isdigit() or not diff_lines.isdigit():
        return 1
    root = Path(values["--design-tmpdir"])
    if not root.is_dir() or root.is_symlink():
        return 1
    baseline = root / "drift-baseline.env"
    if baseline.is_file() and not baseline.is_symlink():
        return 0
    baseline.unlink(missing_ok=True)
    try:
        _ = baseline.write_text(
            f"BASELINE_PLAN_LINES={plan_lines}\nBASELINE_DIFF_LINES={diff_lines}\n",
            encoding="utf-8",
        )
    except OSError:
        result = 1
    else:
        result = 0
    return result


def _named_block_write(arguments: list[str]) -> int:
    """Report a completed write without reaching GitHub.

    The double never mutates an issue: callers only branch on the exit code and
    the `WRITTEN=` envelope, and the real command's compare-and-swap has its own
    Rust coverage.
    """
    content_file = _wire_option(arguments, "--content-file")
    if content_file and not Path(content_file).is_file():
        print("FAILED=true")
        print(f"ERROR=content file not found: {content_file}")
        return 1
    body = Path(content_file).read_bytes() if content_file else b""
    print("WRITTEN=true")
    print("MODE=replaced" if content_file else "MODE=removed")
    print("MARKERS_PRESENT=true")
    print(f"BODY_BYTES={len(body)}")
    return 0


def _timing_ledger_path() -> Path | None:
    """Resolve the ledger the Rust `timing` owner would write."""
    declared = os.environ.get("LARCH_TIMING_LEDGER", "")
    if declared:
        return Path(declared)
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        root = os.environ.get(key, "")
        if root and Path(root).is_dir():
            return Path(root) / "timing-ledger.tsv"
    return None


def _timing_append(row: list[str]) -> int:
    ledger = _timing_ledger_path()
    if ledger is None:
        return 0
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        _ = handle.write("\t".join(row) + "\n")
    return 0


def _timing_flags(arguments: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    index = 0
    while index < len(arguments):
        if arguments[index].startswith("--") and index + 1 < len(arguments) and not arguments[index + 1].startswith("--"):
            values[arguments[index]] = arguments[index + 1]
            index += 2
        else:
            index += 1
    return values


def _timing_mark(arguments: list[str]) -> int:
    labels = [value for value in arguments if not value.startswith("--")]
    skill = os.environ.get("LARCH_TIMING_SKILL", "implement")
    return _timing_append(
        ["v1", "mark", str(int(time.time())), skill, labels[0] if labels else "", *(["-"] * 8)]
    )


def _timing_record_round(arguments: list[str]) -> int:
    values = _timing_flags(arguments)
    start = int(float(values.get("--start-s", "0")))
    end = int(float(values.get("--end-s", "0")))
    return _timing_append([
        "v1", "round", str(int(time.time())), values.get("--skill", "implement"),
        values.get("--step", ""), values.get("--round", "0"), str(start), str(end),
        str(max(0, end - start)), values.get("--accepted", "0"), values.get("--rejected", "0"),
        values.get("--oos", "-"), "1",
    ])


def _timing_record_vendor_task(arguments: list[str]) -> int:
    values = _timing_flags(arguments)
    start = int(float(values.get("--start-s", "0")))
    end = int(float(values.get("--end-s", "0")))
    return _timing_append([
        "v1", "vendor", str(int(time.time())), os.environ.get("LARCH_TIMING_SKILL", "implement"), "-",
        values.get("--vendor", ""), values.get("--task-kind", ""), str(start), str(end),
        str(max(0, end - start)), Path(values.get("--output", "")).name,
        values.get("--exit-code", "0"), values.get("--status", "complete"),
    ])


def _timing_noop(_arguments: list[str]) -> int:
    return 0


def _voting_parse_rate(arguments: list[str], *, envelope: bool) -> int:
    """Return a caller-selected parse-rate result without duplicating the Rust policy."""
    raw = os.environ.get("LARCH_TEST_VOTING_PARSE_RATE_JSON", "")
    decoded: object = json.loads(raw) if raw else {}
    if not isinstance(decoded, dict):
        return 2
    statuses = cast("dict[str, object]", decoded)
    voter = Path(_flag(arguments, "--voter-file")).name
    status = str(statuses.get(voter, statuses.get("*", "OK")))
    if status not in {"OK", "NOT_SUBSTANTIVE"}:
        return 2
    prefix = "PARSE_RATE_STATUS=" if envelope else ""
    print(f"{prefix}{status}")
    return 0


def _voting_parse_rate_check(arguments: list[str]) -> int:
    return _voting_parse_rate(arguments, envelope=True)


def _voting_parse_rate_retry(arguments: list[str]) -> int:
    return _voting_parse_rate(arguments, envelope=False)


def _voting_effective_judges(arguments: list[str]) -> int:
    records = arguments or sys.stdin.read().splitlines()
    count = 0
    for record in records:
        parts = record.split("\t")
        status, path, parse_rate = [*parts, "", "", ""][:3]
        candidate = Path(path)
        if status != "failed" and parse_rate != "NOT_SUBSTANTIVE" and candidate.is_file() and candidate.stat().st_size:
            count += 1
    print(count)
    return 0


def _voting_degraded_warning(arguments: list[str]) -> int:
    if len(arguments) not in {2, 3}:
        return 2
    effective, expected = int(arguments[0]), int(arguments[1])
    if effective < expected:
        warning = f"**⚠ Degraded plan-review panel: {effective}/{expected} effective judges produced substantive vote output.**"
        if len(arguments) == DEGRADED_REASON_ARGUMENT_COUNT and arguments[2]:
            warning += f" {arguments[2]}"
        print(warning, file=sys.stderr)
        print(f"DEGRADED_PANEL_WARNING={warning}")
    return 0


def _voting_voter_status_block(arguments: list[str]) -> int:
    row_layout = _flag(arguments, "--row-layout", "plan_review_interleaved")
    paths_policy = _flag(arguments, "--paths-file-policy", "nonempty")
    values: list[str] = []
    index = 0
    while index < len(arguments):
        if arguments[index] in {"--row-layout", "--paths-file-policy"}:
            index += 2
        else:
            values.append(arguments[index])
            index += 1
    if len(values) != VOTER_STATUS_POSITIONAL_COUNT:
        return 2
    suffixes = ("PATH", "TOOL", "STATUS", "PARSE_RATE_STATUS")
    sequential = tuple((voter, field) for voter in range(3) for field in range(4))
    interleaved = ((0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (2, 0), (1, 1), (2, 1), (1, 2), (2, 2), (1, 3), (2, 3))
    order = sequential if row_layout == "code_review_sequential" else interleaved
    for position, (voter, field) in enumerate(order):
        print(f"VOTER_{voter + 1}_{suffixes[field]}={values[voter * 4 + field]}")
        if position == (11 if row_layout == "code_review_sequential" else 5):
            paths = Path(values[12])
            if paths_policy == "always" or (paths.is_file() and paths.stat().st_size):
                print(f"VOTER_PATHS_FILE={values[12]}")
    return 0


def _voting_write_tally(arguments: list[str]) -> int:
    phase = _flag(arguments, "--phase")
    mode = _flag(arguments, "--mode")
    batch = "plan-review-tally" if phase == "plan-review" else "code-review-tally"
    record: dict[str, object] = {
        "schema_version": 2, "phase": phase, "batch": batch, "mode": mode,
        "rounds": int(_flag(arguments, "--rounds", "0")),
        "accepted_count": int(_flag(arguments, "--accepted", "0")),
        "rejected_count": int(_flag(arguments, "--rejected", "0")),
        "exonerated_count": int(_flag(arguments, "--exonerated", "0")),
    }
    body_file = _flag(arguments, "--body-file")
    if phase == "plan-review" and body_file:
        record["body"] = Path(body_file).read_text(encoding="utf-8")
    findings_file = _flag(arguments, "--self-review-findings-file")
    if findings_file:
        rows: list[str] = []
        for outcome, count, prefix in (
            ("accepted", int(record["accepted_count"]), "SELF_REVIEW_ACCEPTED"),
            ("rejected", int(record["rejected_count"]), "SELF_REVIEW_REJECTED"),
        ):
            rows.extend(json.dumps({
                    "id": f"{prefix}_{item}", "issue_number": "0", "phase": "code-review",
                    "outcome": outcome, "schema_version": "2", "reviewer_slots": ["self-review"],
                    "round_num": "1", "category": "", "body_severity": "", "focus_area": "", "prose_body": "",
                }, separators=(",", ":")) for item in range(1, count + 1))
        _ = Path(findings_file).write_text("".join(f"{row}\n" for row in rows), encoding="utf-8")
    parent = Path(_flag(arguments, "--log-root")).parent
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=parent, delete=False) as handle:
        _ = handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        source = handle.name
    try:
        return _run_log_write([
            "--log-root", _flag(arguments, "--log-root"), "--skill", _flag(arguments, "--skill"),
            "--run-id", _flag(arguments, "--run-id"), "--batch", batch, "--input-file", source,
        ])
    finally:
        Path(source).unlink(missing_ok=True)


def _voting_compose_tally_record(arguments: list[str]) -> int:
    if len(arguments) != ARG_PAIR_SIZE or arguments[0] != "--self-review-tally-file":
        return 2
    try:
        record = json.loads(Path(arguments[1]).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return 1
    if not isinstance(record, dict):
        return 0
    typed = cast("dict[str, object]", record)
    if typed.get("mode") != "self-review":
        return 0
    def count(name: str) -> int:
        try:
            return max(0, int(str(typed.get(name))))
        except (TypeError, ValueError):
            return 0
    rows: list[str] = []
    for outcome, total, prefix in (
        ("accepted", count("accepted_count"), "SELF_REVIEW_ACCEPTED"),
        ("rejected", count("rejected_count"), "SELF_REVIEW_REJECTED"),
    ):
        rows.extend(json.dumps({
                "id": f"{prefix}_{item}", "issue_number": "0", "phase": "code-review",
                "outcome": outcome, "schema_version": "2", "reviewer_slots": ["self-review"],
                "round_num": "1", "category": "", "body_severity": "", "focus_area": "", "prose_body": "",
            }, separators=(",", ":")) for item in range(1, total + 1))
    _ = sys.stdout.write("".join(f"{row}\n" for row in rows))
    return 0


def _design_terminal_verb(arguments: list[str], *, verb: str) -> int:
    """Delegate a migrated ``/design`` terminal verb to the frozen reference.

    The four terminal verbs (``read-result-env``, ``stage-terminal-state``,
    ``failure-report``, ``step-final-summary``) moved to the Rust owner in
    #8580, so a Python-only test run reaches their consumer behavior through the
    byte-frozen Python reference that the Rust parity harness also drives.
    """
    _bind_larch_package()
    reference = _plugin_root() / "fixtures" / "rust-parity" / "design_terminal_migrated_reference.py"
    spec = importlib.util.spec_from_file_location("_stub_design_terminal_reference", reference)
    if spec is None or spec.loader is None:
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main([verb, *arguments]))


def main(arguments: list[str]) -> int:
    result = 2
    if arguments == ["--version"]:
        print(f"larch {_version()}")
        result = 0
    elif arguments == ["bootstrap", "self-check"]:
        print(json.dumps({"schema_version": 1, "version": _version(), "target": _target()}, separators=(",", ":")))
        result = 0
    else:
        handlers: dict[tuple[str, str], Callable[[list[str]], int]] = {
            ("design", "read-result-env"): functools.partial(_design_terminal_verb, verb="read-result-env"),
            ("design", "stage-terminal-state"): functools.partial(_design_terminal_verb, verb="stage-terminal-state"),
            ("design", "failure-report"): functools.partial(_design_terminal_verb, verb="failure-report"),
            ("design", "step-final-summary"): functools.partial(_design_terminal_verb, verb="step-final-summary"),
            ("agent", "classify-diff"): _classify,
            ("agent", "wait-reviewers"): _wait,
            ("agent", "gather-branch-context"): _gather,
            ("agent", "compose-collector-failure-log"): _compose,
            ("agent", "collect-results"): _collect_results,
            ("agent", "run-external-agent"): _run_external_agent,
            ("agent", "launch-review"): _launch_review,
            ("agent", "dispatch-waterfall"): _dispatch_waterfall,
            ("execution-issues", "append"): _execution_issues_append,
            ("execution-issues", "flush"): _execution_issues_flush,
            ("execution-issues", "flush-safety-net"): _execution_issues_flush_safety_net,
            ("execution-issues", "refresh"): _execution_issues_refresh,
            ("run-log", "append-failure"): _append_failure,
            ("run-log", "append-entry"): _append_entry,
            ("run-log", "archive"): _run_log_archive,
            ("run-log", "init"): _run_log_init,
            ("run-log", "manifest"): _run_log_manifest,
            ("run-log", "materialize"): _run_log_materialize,
            ("run-log", "write"): _run_log_write,
            ("run-log", "append"): _run_log_append,
            ("run-log", "exists"): _run_log_exists,
            ("run-log", "write-round"): _run_log_write_round,
            ("run-log", "verify-completeness"): _run_log_verify_completeness,
            ("review", "compose-findings"): _review_compose_findings,
            ("review", "reviewer-prune"): _reviewer_prune,
            ("agent", "launch-claude-subprocess"): _launch_claude_subprocess,
            ("agent", "launch-claude-review"): _launch_claude_review,
            ("issue", "title-eligibility"): _issue_title_eligibility,
            ("named-block", "write"): _named_block_write,
            ("plan", "scope-paths"): _plan_scope_paths,
            ("implement", "scope-disposition"): _implement_scope_disposition,
            ("plan-block", "strip-body"): _plan_block_strip_body,
            ("plan-review", "drift-baseline"): _plan_review_drift_baseline,
            ("plan-review", "json-get-bool"): _plan_review_json_get_bool,
            ("timing", "mark"): _timing_mark,
            ("timing", "record-round"): _timing_record_round,
            ("timing", "record-vendor-task"): _timing_record_vendor_task,
            ("timing", "report"): _timing_noop,
            ("timing", "dump"): _timing_noop,
            ("timing", "telemetry-mark"): _timing_noop,
            ("voting", "parse-rate-check"): _voting_parse_rate_check,
            ("voting", "parse-rate-retry"): _voting_parse_rate_retry,
            ("voting", "effective-judges"): _voting_effective_judges,
            ("voting", "degraded-warning"): _voting_degraded_warning,
            ("voting", "voter-status-block"): _voting_voter_status_block,
            ("voting", "write-tally"): _voting_write_tally,
            ("voting", "compose-tally-record"): _voting_compose_tally_record,
        }
        handler = handlers.get((arguments[0], arguments[1])) if len(arguments) >= ARG_PAIR_SIZE else None
        if handler is not None:
            result = handler(arguments[2:])
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
