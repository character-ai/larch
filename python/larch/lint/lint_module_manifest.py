"""Host-or-justify backstop for ``python/larch/lint/lint_*.py`` modules.

Every lint module must own a record in ``python/lint-module-manifest.json``.
``host_decision`` is ``legacy`` (seeded once for the modules that existed when
this feature was commissioned) or ``new-module-justified`` (a non-empty
justification plus a positive ``source_issue``). The lint compares the manifest
with the live ``lint_*.py`` inventory through the shared lint engine and fails
on a missing entry, a stale entry, a ``legacy`` row outside the frozen seed, or
an incomplete ``new-module-justified`` row, so every new lint module forces one
reviewable JSON diff stating why it exists and which issue commissioned it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core import proc
from larch.lint.engine import EXIT_ERROR, Finding, LintRule, ScanError, SourceFile, parse_argparse_args, run_rule

RULE_ID = "module-manifest"
SUPPRESSION_TOKEN = "lint-module-manifest"
MANIFEST_PATH = "python/lint-module-manifest.json"
LINT_SUBDIR = ("python", "larch", "lint")
LINT_GLOB = "lint_*.py"
SCHEMA_VERSION = 1
LEGACY = "legacy"
NEW_MODULE_JUSTIFIED = "new-module-justified"
HOST_DECISIONS = frozenset({LEGACY, NEW_MODULE_JUSTIFIED})
TOP_LEVEL_KEYS = frozenset({"schema_version", "modules"})
RECORD_KEYS = frozenset({"module", "host_decision", "justification", "source_issue"})

# Frozen at commissioning: the exact lint-module basenames that predate this
# feature. New modules may not claim the legacy exemption, so this set is a
# code-level constant, never derived from the manifest or the filesystem.
LEGACY_SEED_MODULES = frozenset(
    {
        "lint_codex_exec_auth.py",
        "lint_common.py",
        "lint_complexity_baseline.py",
        "lint_complexity_debt.py",
        "lint_em_dash_output.py",
        "lint_env_via_config_constant.py",
        "lint_flat_tests.py",
        "lint_gh_argv_literal.py",
        "lint_guidelines_note_wrapper_bypass.py",
        "lint_keyword_only.py",
        "lint_kv_codec.py",
        "lint_layering.py",
        "lint_lifecycle_prefix_literal.py",
        "lint_markdown_heading_fence_state.py",
        "lint_monkeypatch_facade_binding.py",
        "lint_no_raw_stderr_after_quiet_init.py",
        "lint_prefix_case_variant.py",
        "lint_pylint_skip_file.py",
        "lint_renderer_golden_tests.py",
        "lint_run_log_walkers.py",
        "lint_self_disarmable_gate.py",
        "lint_shared_convention_regex.py",
        "lint_subprocess_via_runner.py",
        "lint_suppression_reason.py",
        "lint_tempfile_dir.py",
        "lint_unreachable_branch.py",
        "lint_wire_artifact_pairing.py",
    }
)


@dataclass(frozen=True)
class ManifestRecord:
    """A validated manifest row for one lint module."""

    module: str
    host_decision: str
    justification: str
    source_issue: int


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_safe_module_name(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    if not value.startswith("lint_") or not value.endswith(".py"):
        return False
    if "/" in value or "\\" in value:
        return False
    return value == Path(value).name


def _parse_record(raw: object, *, index: int, source_label: str) -> ManifestRecord:
    if not isinstance(raw, dict):
        raise ScanError(f"{source_label}: module record {index} must be a JSON object")
    record = cast("dict[str, object]", raw)
    if frozenset(record) != RECORD_KEYS:
        raise ScanError(
            f"{source_label}: module record {index} must have exactly keys {sorted(RECORD_KEYS)}"
        )
    module = record["module"]
    host_decision = record["host_decision"]
    justification = record["justification"]
    source_issue = record["source_issue"]
    if not _is_safe_module_name(module):
        raise ScanError(f"{source_label}: module record {index} has an unsafe module name")
    if host_decision not in HOST_DECISIONS:
        raise ScanError(
            f"{source_label}: module record {index} has an unsupported host_decision"
        )
    if not isinstance(justification, str):
        raise ScanError(f"{source_label}: module record {index} justification must be a string")
    if not _is_int(source_issue):
        raise ScanError(f"{source_label}: module record {index} source_issue must be an integer")
    return ManifestRecord(
        module=cast("str", module),
        host_decision=cast("str", host_decision),
        justification=justification,
        source_issue=cast("int", source_issue),
    )


def parse_manifest(text: str, *, source_label: str) -> list[ManifestRecord]:
    """Validate the manifest schema and return its records, or raise ScanError."""
    try:
        decoded: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source_label}: invalid JSON: {exc.msg}") from exc
    if not isinstance(decoded, dict):
        raise ScanError(f"{source_label}: manifest must be a top-level JSON object")
    manifest = cast("dict[str, object]", decoded)
    if frozenset(manifest) != TOP_LEVEL_KEYS:
        raise ScanError(f"{source_label}: manifest must have exactly keys {sorted(TOP_LEVEL_KEYS)}")
    schema_version = manifest["schema_version"]
    if not _is_int(schema_version) or schema_version != SCHEMA_VERSION:
        raise ScanError(f"{source_label}: manifest schema_version must be {SCHEMA_VERSION}")
    modules = manifest["modules"]
    if not isinstance(modules, list):
        raise ScanError(f"{source_label}: manifest modules must be a JSON array")
    records = [
        _parse_record(item, index=index, source_label=source_label)
        for index, item in enumerate(cast("list[object]", modules))
    ]
    seen: set[str] = set()
    for record in records:
        if record.module in seen:
            raise ScanError(f"{source_label}: duplicate manifest record for {record.module}")
        seen.add(record.module)
    return records


def inventory_modules(root: Path) -> frozenset[str]:
    """Return the live ``lint_*.py`` basenames, rejecting unsafe entries."""
    lint_dir = root.joinpath(*LINT_SUBDIR)
    if not lint_dir.is_dir():
        raise ScanError(f"lint module directory not found: {lint_dir}")
    modules: set[str] = set()
    for entry in sorted(lint_dir.glob(LINT_GLOB)):
        if entry.is_symlink():
            raise ScanError(f"lint module is a symlink: {entry.name}")
        if not entry.is_file():
            raise ScanError(f"lint module is not a regular file: {entry.name}")
        modules.add(entry.name)
    return frozenset(modules)


def _finding(path: str, message: str) -> Finding:
    return Finding(path=path, line=1, rule_id=RULE_ID, message=message)


def _record_findings(record: ManifestRecord, *, path: str) -> list[Finding]:
    if record.host_decision == LEGACY:
        if record.module not in LEGACY_SEED_MODULES:
            return [
                _finding(
                    path,
                    f"legacy record {record.module} is not in the frozen legacy seed; "
                    "a new lint module must be new-module-justified",
                )
            ]
        return []
    findings: list[Finding] = []
    if not record.justification.strip():
        findings.append(
            _finding(path, f"new-module-justified record {record.module} has an empty justification")
        )
    if record.source_issue <= 0:
        findings.append(
            _finding(
                path,
                f"new-module-justified record {record.module} has a non-positive source_issue",
            )
        )
    return findings


def policy_findings(
    records: list[ManifestRecord], inventory: frozenset[str], *, path: str
) -> list[Finding]:
    """Return manifest/inventory parity and per-record host-or-justify findings."""
    recorded = {record.module for record in records}
    findings: list[Finding] = [
        _finding(path, f"lint module {module} has no manifest record; add a host-or-justify entry")
        for module in sorted(inventory - recorded)
    ]
    findings.extend(
        _finding(path, f"manifest record {module} has no matching lint module; remove the stale entry")
        for module in sorted(recorded - inventory)
    )
    for record in records:
        findings.extend(_record_findings(record, path=path))
    return findings


def _build_rule(root: Path) -> LintRule:
    def detect(source: SourceFile) -> list[Finding]:
        records = parse_manifest(source.text, source_label=source.path)
        inventory = inventory_modules(root)
        return policy_findings(records, inventory, path=source.path)

    return LintRule(
        rule_id=RULE_ID,
        description="Every lint module owns a host-or-justify manifest record",
        detect=detect,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        allow_inline_suppression=False,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint module-manifest", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    return parse_argparse_args(parser, argv)


def main(argv: list[str] | None = None, *, runner: proc.Runner | None = None) -> int:
    """Run the module-manifest lint; 0 clean, 1 findings, 2 malformed/unsafe input."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    active_runner = runner if runner is not None else proc.ProcRunner()
    return run_rule(_build_rule(root), root, active_runner, paths=[MANIFEST_PATH])


if __name__ == "__main__":
    raise SystemExit(main())
