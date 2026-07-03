"""Agent/reviewer file generators extracted from rendering.py."""
# pylint: skip-file
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedImport=false, reportUnusedFunction=false

from __future__ import annotations
import difflib
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc

# ---------------------------------------------------------------------------
# Helpers duplicated from rendering.py to avoid circular imports.

REPO_ROOT = Path(__file__).resolve().parents[3]
MIN_TOPOLOGY_VALUE_LEN = 3
TOPOLOGY_COLUMN_COUNT = 4
FRONTMATTER_FENCE_COUNT = 2
GENERATOR_COLUMN_COUNT = 2


class RenderError(RuntimeError):
    """Rendering drift or runtime error."""


def _err(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _read_text(path: Path) -> str:
    return larch_io.read_text(path)


def _write_text_atomic(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, prefix=f".{path.name}.")


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _frontmatter_body(path: Path) -> str:
    lines = _read_text(path).splitlines()
    count = 0
    for i, line in enumerate(lines):
        if re.fullmatch(r"---\s*", line):
            count += 1
            if count == FRONTMATTER_FENCE_COUNT:
                return "\n".join(lines[i + 1 :])
    return ""


def _iter_physical_lines(path: Path, *, crlf_prefix: str) -> Iterable[tuple[int, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        text = handle.read()
    for row, line in enumerate(text.split("\n"), start=1):
        if "\r" in line:
            suffix = " (use LF)" if crlf_prefix.endswith(":") else ""
            raise RenderError(f"{crlf_prefix}{row}: CRLF line endings not allowed{suffix}")
        if not line or line.startswith("#"):
            continue
        yield row, line


def _path_has_segment(*, path: str, segment: str) -> bool:
    return any(part == segment for part in Path(path).parts)


def _extract_generated_body(template: Path, *, heading: str | None = None) -> str:
    body_lines = _read_text(template).splitlines()
    in_section = heading is None
    in_body = False
    found = False
    buf: list[str] = []
    skipped_open = False
    for line in body_lines:
        if heading is not None and line == heading:
            in_section = True
            continue
        if found:
            continue
        if in_section and "<!-- BEGIN GENERATED_BODY -->" in line:
            in_body = True
            skipped_open = False
            continue
        if in_body and "<!-- END GENERATED_BODY -->" in line:
            in_body = False
            in_section = False
            found = True
            continue
        if in_body:
            if not skipped_open:
                skipped_open = True
                continue
            buf.append(line)
    if not found or not buf:
        label = heading or "GENERATED_BODY"
        raise RenderError(f"ERROR: no content found for {label} between BEGIN/END GENERATED_BODY markers")
    if buf[-1] != "```":
        raise RenderError(f"ERROR: expected outer close fence ``` as last line inside GENERATED_BODY markers; got: {buf[-1]}")
    return "\n".join(buf[:-1])


def _replace_output_instruction(body: str, *, inscope: Iterable[str], oos: Iterable[str]) -> str:
    out: list[str] = []
    section = ""
    for line in body.splitlines():
        if line == "### In-Scope Findings":
            section = "in_scope"
            out.append(line)
            continue
        if line == "### Out-of-Scope Observations":
            section = "oos"
            out.append(line)
            continue
        if line == "- {OUTPUT_INSTRUCTION}":
            if section == "in_scope":
                out.extend(f"- {item}" for item in inscope if item)
            elif section == "oos":
                out.extend(f"- {item}" for item in oos if item)
            else:
                raise RenderError("{OUTPUT_INSTRUCTION} encountered outside a known section")
            continue
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# generators


AUTO_HEADER_BY_VERB = {
    "code-reviewer-agent": "python3 python/cli.py generate code-reviewer-agent",
    "reviewer-plan-fidelity-agent": "python3 python/cli.py generate reviewer-plan-fidelity-agent",
    "reviewer-code-robustness-agent": "python3 python/cli.py generate reviewer-code-robustness-agent",
    "reviewer-security-structure-tests-agent": "python3 python/cli.py generate reviewer-security-structure-tests-agent",
    "pre-rendered-reviewer-prompts": "python3 python/cli.py generate pre-rendered-reviewer-prompts",
    "codex-implementer": "python3 python/cli.py generate codex-implementer",
    "cursor-implementer": "python3 python/cli.py generate cursor-implementer",
    "topology-docs": "python3 python/cli.py generate topology-docs",
}


REVIEWER_FRONTMATTER = {
    "code-reviewer-agent": """---
name: code-reviewer
description: Unified code reviewer combining code quality (bugs, reuse, tests, backward compat, style), risk/integration (breaking changes, thread safety, deployment, regressions, CI), correctness (logic errors, off-by-one, nil, types, races, errors, math), architecture (separation of concerns, contract boundaries, invariants, semantic boundaries), and security (injection, authn/authz, secrets, crypto, deserialization, SSRF, path traversal, dependency CVEs).
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---""",
    "reviewer-plan-fidelity-agent": """---
name: reviewer-plan-fidelity
description: "Specialist code reviewer concentrating on plan fidelity: plan-to-implementation traceability, completeness against design requirements, correctness against stated intent, stale replacement surfaces, generated artifact coverage, and explicit loud failure when the design plan is missing."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---""",
    "reviewer-code-robustness-agent": """---
name: reviewer-code-robustness
description: "Specialist code reviewer concentrating on code robustness: edge cases, boundary behavior, failure recovery, partial failure, resource cleanup, retry/idempotency, silent data corruption, and invariants at failure boundaries. Does not require or expect a design plan."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---""",
    "reviewer-security-structure-tests-agent": """---
name: reviewer-security-structure-tests
description: "Specialist code reviewer concentrating on security, structure/maintainability, and tests/CI: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs, code reuse, KISS, style consistency, backward compatibility, single-responsibility, test coverage gaps, missing assertions, CI workflow correctness, deployment risks, and regression risk."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---""",
}


REVIEWER_SECTION = {
    "code-reviewer-agent": "## Reviewer: Code Reviewer",
    "reviewer-plan-fidelity-agent": "## Reviewer: Plan Fidelity",
    "reviewer-code-robustness-agent": "## Reviewer: Code Robustness",
    "reviewer-security-structure-tests-agent": "## Reviewer: Security + Structure + Tests",
}


REVIEWER_OUTPUT = {
    "code-reviewer-agent": REPO_ROOT / "agents" / "code-reviewer.md",
    "reviewer-plan-fidelity-agent": REPO_ROOT / "agents" / "reviewer-plan-fidelity.md",
    "reviewer-code-robustness-agent": REPO_ROOT / "agents" / "reviewer-code-robustness.md",
    "reviewer-security-structure-tests-agent": REPO_ROOT / "agents" / "reviewer-security-structure-tests.md",
}


def _reviewer_agent_text(verb: str) -> str:
    body = _extract_generated_body(REPO_ROOT / "skills" / "shared" / "reviewer-templates.md", heading=REVIEWER_SECTION[verb])
    if verb == "code-reviewer-agent":
        body = body.replace("{REVIEW_TARGET}", "code, plans, or conflict resolutions")
        lines: list[str] = []
        skip_blank = False
        for line in body.splitlines():
            if line == "{CONTEXT_BLOCK}":
                skip_blank = True
                continue
            if skip_blank:
                skip_blank = False
                if line == "":
                    continue
            lines.append(line)
        body = _replace_output_instruction(
            "\n".join(lines),
            inscope=["File path and line number(s) (if reviewing code) or the specific concern (if reviewing a plan)", "What the issue is", "Suggested fix (be specific)"],
            oos=["File path and line number(s) or the specific concern (use `<expected-path>:1` for absent-artifact observations)", "What the issue is", "Suggested fix"],
        )
    return f"{REVIEWER_FRONTMATTER[verb]}\n\n<!-- AUTO-GENERATED: Derived from skills/shared/reviewer-templates.md. Do not edit. Regenerate via: {AUTO_HEADER_BY_VERB[verb]} -->\n\n{body}\n"


def _diff_or_write(*, target: Path, text: str, check: bool, label: str) -> int:
    if check:
        current = _read_text(target) if target.is_file() else ""
        if current != text:
            sys.stdout.writelines(difflib.unified_diff(current.splitlines(keepends=True), text.splitlines(keepends=True), fromfile=str(target), tofile="expected"))
            _err(f"{label} is out of sync. Run: {AUTO_HEADER_BY_VERB.get(label, 'python3 python/cli.py generate check')}")
            return 1
        return 0
    _write_text_atomic(path=target, text=text)
    logging_util.emit(f"Wrote {target}")
    return 0


def _check_arg(argv: list[str]) -> tuple[bool, int]:
    if argv == ["--check"]:
        return True, 0
    if argv:
        _err("Usage: [--check]")
        return False, 2
    return False, 0


def _reviewer_agent_main(*, verb: str, argv: list[str]) -> int:
    logging_util.quiet_init(argv0=f"generate-{verb}.sh")
    check, rc = _check_arg(argv)
    if rc:
        return rc
    try:
        return _diff_or_write(target=REVIEWER_OUTPUT[verb], text=_reviewer_agent_text(verb), check=check, label=verb)
    except RenderError as exc:
        _err(str(exc))
        return 1


def generate_code_reviewer_agent_main(argv: list[str]) -> int:
    return _reviewer_agent_main(verb="code-reviewer-agent", argv=argv)


def generate_reviewer_plan_fidelity_agent_main(argv: list[str]) -> int:
    return _reviewer_agent_main(verb="reviewer-plan-fidelity-agent", argv=argv)


def generate_reviewer_code_robustness_agent_main(argv: list[str]) -> int:
    return _reviewer_agent_main(verb="reviewer-code-robustness-agent", argv=argv)


def generate_reviewer_security_structure_tests_agent_main(argv: list[str]) -> int:
    return _reviewer_agent_main(verb="reviewer-security-structure-tests-agent", argv=argv)

def _implementer_text(kind: str) -> str:
    base = _read_text(REPO_ROOT / "agents" / "_implementer-base.md")
    if kind == "codex":
        header = f"""---
name: codex-implementer
description: Codex implementer system prompt for /implement Step 2. Produces working-tree edits plus a structured manifest; the dispatcher commits with manifest.commit_message. Loaded as --agent-prompt by python/cli.py agent launch-codex-implement; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Do not edit. Regenerate via: {AUTO_HEADER_BY_VERB['codex-implementer']} -->

# Codex implementer (system prompt)

You are the Codex implementer for `/implement` Step 2. Turn the written plan into working-tree edits plus a structured manifest, then exit cleanly. The dispatcher commits for you with `git add -A && git commit -F …` using `manifest.commit_message`; you do NOT commit.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Before exit, atomically write these orchestration files:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.
- `<SCOUT_MANIFEST_PATH>` — optional best-effort `scout-coder-manifest.json`.

The dispatcher passes the paths as arguments. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crash leaves "no file" instead of "half a JSON document."

You edit the working tree, write the manifest, and exit. The dispatcher reads `manifest.commit_message` and commits after you exit, preserving `workspace-write` sandbox semantics that forbid `.git/` writes.

"""
        rendered = base.replace("TOOL_COMMIT_STDERR", "codex-commit-stderr.txt").replace(". `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself.", ".")
        rendered = re.sub(r"^2\. \*\*NEVER `git add`.*$", "2. **NEVER `git add` or `git commit`.** Committing is the dispatcher's job. Your output is the working-tree edits plus `manifest.json`. Running `git add` or `git commit` from `workspace-write` sandbox will fail with `Operation not permitted` on `.git/index.lock` anyway, so just do not try.", rendered, flags=re.MULTILINE)
    else:
        header = f"""---
name: cursor-implementer
description: Cursor implementer system prompt for /implement Step 2. Produces working-tree edits plus a structured manifest; the dispatcher commits with manifest.commit_message. Loaded as --agent-prompt by python/cli.py agent launch-cursor-implement; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Do not edit. Regenerate via: {AUTO_HEADER_BY_VERB['cursor-implementer']} -->

# Cursor implementer (system prompt)

You are the Cursor implementer for `/implement` Step 2. Turn the written plan into working-tree edits plus a structured manifest, then exit cleanly. The dispatcher commits for you with `git add -A && git commit -F …` using `manifest.commit_message`; you do NOT commit.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Before exit, atomically write these orchestration files:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.
- `<SCOUT_MANIFEST_PATH>` — optional best-effort `scout-coder-manifest.json`.

The dispatcher passes the paths as arguments. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crash leaves "no file" instead of "half a JSON document."

You edit the working tree, write the manifest, and exit. The dispatcher reads `manifest.commit_message` and commits after you exit.

Cursor lacks Codex's `workspace-write` sandbox. The dispatcher asserts `HEAD == BASELINE_SHA` before committing for you; any `git commit` you produce triggers `cursor-modified-history` and preserves partial work for operator inspection.

## Shared guardrails

The section below, Inputs through Style, is generated from the Cursor implementer template; `scripts/test-implement-structure.sh` assertion (24) enforces the structure.

"""
        rendered = base.replace("TOOL_MODIFIED_HISTORY", "cursor-modified-history").replace("TOOL_COMMIT_STDERR", "cursor-commit-stderr.txt")
        rendered = re.sub(r"^9\. \*\*NEVER spawn or maintain persistent interactive subprocess sessions\.\*\*.*?(?=^10\.)", "", rendered, flags=re.MULTILINE | re.DOTALL)
    return header + rendered


def generate_codex_implementer_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="generate-codex-implementer.sh")
    check, rc = _check_arg(argv)
    if rc:
        return rc
    return _diff_or_write(target=REPO_ROOT / "agents" / "codex-implementer.md", text=_implementer_text("codex"), check=check, label="codex-implementer")


def generate_cursor_implementer_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="generate-cursor-implementer.sh")
    check, rc = _check_arg(argv)
    if rc:
        return rc
    return _diff_or_write(target=REPO_ROOT / "agents" / "cursor-implementer.md", text=_implementer_text("cursor"), check=check, label="cursor-implementer")


def generate_pre_rendered_reviewer_prompts_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="generate-pre-rendered-reviewer-prompts.sh")
    check, rc = _check_arg(argv)
    if rc:
        return rc
    tmpdir = Path(tempfile.mkdtemp(prefix="larch-pre-rendered-reviewers."))
    try:
        expected = tmpdir / "pre-rendered"
        expected.mkdir()
        for agent in sorted((REPO_ROOT / "agents").glob("reviewer-*.md")):
            body = _frontmatter_body(agent)
            if not body:
                _err(f"generate-pre-rendered-reviewer-prompts.sh: empty body in {agent.relative_to(REPO_ROOT)}")
                return 1
            (expected / f"{agent.stem}-body.txt").write_text(body, encoding="utf-8")
        manifest_lines = [f"# Generated by {AUTO_HEADER_BY_VERB['pre-rendered-reviewer-prompts']}. Do not edit."]
        for body_file in sorted(expected.glob("reviewer-*-body.txt")):
            rel = f"agents/pre-rendered/{body_file.name}"
            manifest_lines.append(f"{_sha256_path(body_file)}  {rel}")
        (expected / ".manifest").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        output = REPO_ROOT / "agents" / "pre-rendered"
        if check:
            result = subprocess.run(["diff", "-ru", str(output), str(expected)], check=False, text=True, capture_output=True)  # noqa: S607
            if result.returncode != 0:
                print(result.stdout, end="")
                _err("agents/pre-rendered is out of sync with agents/reviewer-*.md.")
                return 1
            return 0
        output.mkdir(exist_ok=True)
        for existing in output.glob("reviewer-*-body.txt"):
            existing.unlink()
        (output / ".manifest").unlink(missing_ok=True)
        for generated in sorted(expected.iterdir()):
            if generated.is_file():
                _write_text_atomic(path=output / generated.name, text=_read_text(generated))
        logging_util.emit(f"Wrote {output}")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _validate_topology_row(*, row: int, key: str, value: str, composition: str, runtime: str) -> None:
    if not re.fullmatch(r"[a-z0-9_.]+", key):
        raise RenderError(f"row {row}: key must match [a-z0-9_.]+: {key}")
    if not value or re.search(r"[\t\n<>\[\]`]", value) or re.search(r"[^A-Za-z0-9 ./+-]", value):
        raise RenderError(f"row {row}: invalid value: {value}")
    if composition and (re.search(r"[\t\n<>\[\]`]", composition) or re.search(r"[^A-Za-z0-9 ./+-]", composition)):
        raise RenderError(f"row {row}: invalid composition: {composition}")
    if not runtime or runtime.startswith(("/", "./", "-", ":")) or "//" in runtime or _path_has_segment(path=runtime, segment="..") or _path_has_segment(path=runtime, segment="."):
        raise RenderError(f"row {row}: invalid runtime_authority: {runtime}")
    if value.isdigit() or len(value) < MIN_TOPOLOGY_VALUE_LEN:
        raise RenderError(f"row {row}: value '{value}' is too short or purely numeric")
    path = REPO_ROOT / runtime
    if not path.is_file():
        raise RenderError(f"row {row}: runtime_authority not found: {runtime}")
    if proc.run(["git", "ls-files", "--error-unmatch", "--", runtime], cwd=str(REPO_ROOT), check=False).returncode != 0:
        raise RenderError(f"row {row}: runtime_authority is not tracked by git: {runtime}")
    if value not in _read_text(path):
        raise RenderError(f"row {row}: value '{value}' not found in runtime_authority: {runtime}")


def _topology_text() -> str:
    rows: list[tuple[str, str, str, str]] = []
    seen_keys: set[str] = set()
    seen_anchors: set[str] = set()
    topology_path = Path(os.environ.get("LARCH_TOPOLOGY_TSV", str(REPO_ROOT / "skills" / "shared" / "topology.tsv")))
    for row, line in _iter_physical_lines(topology_path, crlf_prefix="row "):
        parts = line.split("\t")
        if len(parts) != TOPOLOGY_COLUMN_COUNT or not parts[0] or not parts[1] or not parts[3]:
            raise RenderError(f"row {row}: malformed row; expected exactly four tab-separated columns with key, value, and runtime_authority non-empty")
        key, value, composition, runtime = parts
        _validate_topology_row(row=row, key=key, value=value, composition=composition, runtime=runtime)
        if key in seen_keys:
            raise RenderError(f"row {row}: duplicate key '{key}'")
        if key in seen_anchors:
            raise RenderError(f"row {row}: derived anchor '{key}' collides")
        seen_keys.add(key)
        seen_anchors.add(key)
        rows.append((key, value, composition, runtime))
    header = f"""# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: {AUTO_HEADER_BY_VERB['topology-docs']} -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

`/implement` Step 5 public phrases are pinned by `scripts/test-quick-mode-docs-sync.sh`; the review-panel shape is also projected here from `skills/shared/topology.tsv` so the topology row and public-doc harness stay aligned.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
"""
    return header + "".join(f'| <a id="{key}"></a>`{key}` | {value} | {composition or " "} | `{runtime}` |\n' for key, value, composition, runtime in rows)


def generate_topology_docs_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="generate-topology-docs.sh")
    check, rc = _check_arg(argv)
    if rc:
        return rc
    try:
        target = Path(os.environ.get("LARCH_TOPOLOGY_DOC", str(REPO_ROOT / "docs" / "topology.md")))
        return _diff_or_write(target=target, text=_topology_text(), check=check, label="topology-docs")
    except RenderError as exc:
        _err(f"generate-topology-docs: {exc}")
        return 1


_GENERATOR_VERB_TO_FUNC = {
    "code-reviewer-agent": generate_code_reviewer_agent_main,
    "reviewer-plan-fidelity-agent": generate_reviewer_plan_fidelity_agent_main,
    "reviewer-code-robustness-agent": generate_reviewer_code_robustness_agent_main,
    "reviewer-security-structure-tests-agent": generate_reviewer_security_structure_tests_agent_main,
    "pre-rendered-reviewer-prompts": generate_pre_rendered_reviewer_prompts_main,
    "codex-implementer": generate_codex_implementer_main,
    "cursor-implementer": generate_cursor_implementer_main,
    "topology-docs": generate_topology_docs_main,
}


def _validate_generator_command(*, row: int, command: str) -> str:
    parts = command.split()
    if len(parts) != GENERATOR_COLUMN_COUNT or parts[0] != "generate" or parts[1] not in _GENERATOR_VERB_TO_FUNC:
        raise RenderError(f"scripts/generators.tsv:{row}: generator command must be 'generate <registered-verb>': {command}")
    return parts[1]


def _validate_registry_path(*, row: int, label: str, path: str) -> None:
    invalid = [
        not path,
        path.startswith(("/", "./", "-", ":")),
        "//" in path,
        "\t" in path or "\n" in path,
        _path_has_segment(path=path, segment=".."),
        _path_has_segment(path=path, segment="."),
    ]
    if any(invalid):
        raise RenderError(f"scripts/generators.tsv:{row}: invalid {label} path: {path}")


def generate_check_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="check-generators.sh")
    if argv:
        _err("Usage: generate check")
        return 2
    try:
        registry = REPO_ROOT / "scripts" / "generators.tsv"
        if not registry.is_file():
            raise RenderError(f"check-generators: registry not found: {registry}")
        if proc.run(["git", "rev-parse", "--show-toplevel"], cwd=str(REPO_ROOT), check=False).returncode != 0:
            raise RenderError("check-generators: not inside a git work tree")
        commands: list[str] = []
        outputs: list[str] = []
        for row, line in _iter_physical_lines(registry, crlf_prefix="scripts/generators.tsv:"):
            parts = line.split("\t")
            if len(parts) != GENERATOR_COLUMN_COUNT or not parts[0] or not parts[1]:
                raise RenderError(f"scripts/generators.tsv:{row}: malformed row; expected exactly two non-empty tab-separated columns")
            command, output = parts
            verb = _validate_generator_command(row=row, command=command)
            _validate_registry_path(row=row, label="output", path=output)
            if command in commands:
                raise RenderError(f"scripts/generators.tsv:{row}: duplicate generator command: {command}")
            if output in outputs:
                raise RenderError(f"scripts/generators.tsv:{row}: duplicate output path: {output}")
            if not (REPO_ROOT / output).exists():
                raise RenderError(f"scripts/generators.tsv:{row}: output path not found: {output}")
            if proc.run(["git", "ls-files", "--error-unmatch", "--", output], cwd=str(REPO_ROOT), check=False).returncode != 0:
                raise RenderError(f"scripts/generators.tsv:{row}: output path is not tracked by git: {output}")
            commands.append(command)
            outputs.append(output)
            _ = verb
        if not commands:
            raise RenderError(f"{registry}: no rows registered")
        before = proc.run(["git", "diff", "HEAD", "--", *outputs], cwd=str(REPO_ROOT)).stdout
        for command, output in zip(commands, outputs, strict=True):
            verb = command.split()[1]
            rc = _GENERATOR_VERB_TO_FUNC[verb](["--check"])
            if rc != 0:
                raise RenderError(f"check-generators: drift detected by {command} (output: {output})")
        after = proc.run(["git", "diff", "HEAD", "--", *outputs], cwd=str(REPO_ROOT)).stdout
        if before != after:
            raise RenderError(f"check-generators: post-run working-tree delta detected at: {' '.join(outputs)}")
        return 0
    except RenderError as exc:
        _err(str(exc))
        return 1
