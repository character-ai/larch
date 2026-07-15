"""Coverage for the host-or-justify lint-module manifest ratchet."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.lint import lint_module_manifest
from larch.lint.engine import ScanError

MANIFEST_REL = lint_module_manifest.MANIFEST_PATH
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _manifest_text(records: list[object], *, schema_version: object = 1) -> str:
    return json.dumps({"schema_version": schema_version, "modules": records})


def _record(
    module: str,
    host_decision: str,
    justification: str = "",
    source_issue: object = 0,
) -> dict[str, object]:
    return {
        "module": module,
        "host_decision": host_decision,
        "justification": justification,
        "source_issue": source_issue,
    }


def _parse(records: list[object]) -> list[lint_module_manifest.ManifestRecord]:
    return lint_module_manifest.parse_manifest(_manifest_text(records), source_label="m")


class _FakeGit:
    """Offline Runner: answers only rev-parse and ls-files with canned output."""

    def __init__(self, *, toplevel: Path, tracked: Sequence[str]) -> None:
        self._toplevel = str(toplevel)
        self._tracked = tuple(tracked)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        args = list(argv)
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return CommandResult(tuple(args), 0, f"{self._toplevel}\n", "", 0.0)
        if args[:4] == ["git", "ls-files", "--cached", "-z"]:
            payload = "".join(f"{rel}\0" for rel in self._tracked)
            return CommandResult(tuple(args), 0, payload, "", 0.0)
        raise AssertionError(f"unexpected git argv: {args}")


def _make_repo(tmp_path: Path, *, manifest_text: str, inventory: Sequence[str]) -> Path:
    lint_dir = tmp_path.joinpath("python", "larch", "lint")
    lint_dir.mkdir(parents=True)
    for name in inventory:
        _ = (lint_dir / name).write_text("", encoding="utf-8")
    _ = (tmp_path / "python" / "lint-module-manifest.json").write_text(
        manifest_text, encoding="utf-8"
    )
    return tmp_path


# --- schema validation (tool-error exit) --------------------------------------


def test_parse_rejects_malformed_json() -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest("{not json", source_label="m")


def test_parse_rejects_non_object_top_level() -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest("[]", source_label="m")


def test_parse_rejects_wrong_top_level_keys() -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest(
            json.dumps({"schema_version": 1}), source_label="m"
        )


def test_parse_rejects_bad_schema_version() -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest(
            json.dumps({"schema_version": 2, "modules": []}), source_label="m"
        )
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest(
            json.dumps({"schema_version": True, "modules": []}), source_label="m"
        )


def test_parse_rejects_non_list_modules() -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.parse_manifest(
            json.dumps({"schema_version": 1, "modules": {}}), source_label="m"
        )


def test_parse_rejects_non_object_record() -> None:
    with pytest.raises(ScanError):
        _ = _parse(["nope"])


def test_parse_rejects_wrong_record_keys() -> None:
    with pytest.raises(ScanError):
        _ = _parse([{"module": "lint_x.py", "host_decision": "legacy"}])


def test_parse_rejects_unsupported_host_decision() -> None:
    with pytest.raises(ScanError):
        _ = _parse([_record("lint_x.py", "invented")])


def test_parse_rejects_unsafe_module_names() -> None:
    for name in ("../lint_x.py", "sub/lint_x.py", "lint_x", "notlint.py", "", "lint_x.py\x00"):
        with pytest.raises(ScanError):
            _ = _parse([_record(name, "legacy")])


def test_parse_rejects_non_string_justification() -> None:
    bad = {
        "module": "lint_x.py",
        "host_decision": "legacy",
        "justification": 5,
        "source_issue": 0,
    }
    with pytest.raises(ScanError):
        _ = _parse([bad])


def test_parse_rejects_non_integer_source_issue() -> None:
    # Strings, floats, null, and booleans are all bad field types, including the
    # booleans-are-not-integers edge for a new-module-justified row.
    for value in ("7", 1.5, None, True):
        bad = _record("lint_x.py", "new-module-justified", "why", value)
        with pytest.raises(ScanError):
            _ = _parse([bad])


def test_parse_rejects_duplicate_modules() -> None:
    with pytest.raises(ScanError):
        _ = _parse([_record("lint_x.py", "legacy"), _record("lint_x.py", "legacy")])


# --- inventory enumeration ----------------------------------------------------


def test_inventory_lists_regular_lint_modules(tmp_path: Path) -> None:
    lint_dir = tmp_path.joinpath("python", "larch", "lint")
    lint_dir.mkdir(parents=True)
    for name in ("lint_a.py", "lint_b.py", "helper.py"):
        _ = (lint_dir / name).write_text("", encoding="utf-8")
    assert lint_module_manifest.inventory_modules(tmp_path) == frozenset(
        {"lint_a.py", "lint_b.py"}
    )


def test_inventory_rejects_symlinked_module(tmp_path: Path) -> None:
    lint_dir = tmp_path.joinpath("python", "larch", "lint")
    lint_dir.mkdir(parents=True)
    target = lint_dir / "real.py"
    _ = target.write_text("", encoding="utf-8")
    (lint_dir / "lint_link.py").symlink_to(target)
    with pytest.raises(ScanError):
        _ = lint_module_manifest.inventory_modules(tmp_path)


def test_inventory_missing_dir_is_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ScanError):
        _ = lint_module_manifest.inventory_modules(tmp_path)


# --- policy findings ----------------------------------------------------------


def _seed_module() -> str:
    return sorted(lint_module_manifest.LEGACY_SEED_MODULES)[0]


def test_policy_clean_for_seed_legacy_and_new_module() -> None:
    seed = _seed_module()
    parsed = _parse(
        [_record(seed, "legacy"), _record("lint_new.py", "new-module-justified", "why", 42)]
    )
    inventory = frozenset({seed, "lint_new.py"})
    assert lint_module_manifest.policy_findings(parsed, inventory, path=MANIFEST_REL) == []


def test_policy_reports_missing_entry() -> None:
    findings = lint_module_manifest.policy_findings(
        [], frozenset({"lint_ghost.py"}), path=MANIFEST_REL
    )
    assert [item.message for item in findings] == [
        "lint module lint_ghost.py has no manifest record; add a host-or-justify entry"
    ]


def test_policy_reports_stale_entry() -> None:
    seed = _seed_module()
    parsed = _parse([_record(seed, "legacy")])
    findings = lint_module_manifest.policy_findings(parsed, frozenset(), path=MANIFEST_REL)
    assert [item.message for item in findings] == [
        f"manifest record {seed} has no matching lint module; remove the stale entry"
    ]


def test_policy_rejects_non_seed_legacy() -> None:
    parsed = _parse([_record("lint_brand_new.py", "legacy")])
    findings = lint_module_manifest.policy_findings(
        parsed, frozenset({"lint_brand_new.py"}), path=MANIFEST_REL
    )
    assert any("is not in the frozen legacy seed" in item.message for item in findings)


def test_policy_rejects_empty_justification() -> None:
    parsed = _parse([_record("lint_new.py", "new-module-justified", "   ", 5)])
    findings = lint_module_manifest.policy_findings(
        parsed, frozenset({"lint_new.py"}), path=MANIFEST_REL
    )
    assert any("empty justification" in item.message for item in findings)


def test_policy_rejects_non_positive_source_issue() -> None:
    for value in (0, -3):
        parsed = _parse([_record("lint_new.py", "new-module-justified", "why", value)])
        findings = lint_module_manifest.policy_findings(
            parsed, frozenset({"lint_new.py"}), path=MANIFEST_REL
        )
        assert any("non-positive source_issue" in item.message for item in findings)


def test_policy_findings_are_sorted_and_deterministic() -> None:
    findings = lint_module_manifest.policy_findings(
        [], frozenset({"lint_b.py", "lint_a.py"}), path=MANIFEST_REL
    )
    messages = [item.message for item in findings]
    assert messages == sorted(messages)
    assert "lint_a.py" in messages[0]


# --- main() through an injected offline runner --------------------------------


def test_main_clean_manifest(tmp_path: Path) -> None:
    text = _manifest_text([_record("lint_demo.py", "new-module-justified", "why", 5)])
    root = _make_repo(tmp_path, manifest_text=text, inventory=["lint_demo.py"])
    runner = _FakeGit(toplevel=root.resolve(), tracked=[MANIFEST_REL])
    assert lint_module_manifest.main(["--root", str(root)], runner=runner) == 0


def test_main_reports_missing_entry(tmp_path: Path) -> None:
    text = _manifest_text([_record("lint_demo.py", "new-module-justified", "why", 5)])
    root = _make_repo(tmp_path, manifest_text=text, inventory=["lint_demo.py", "lint_extra.py"])
    runner = _FakeGit(toplevel=root.resolve(), tracked=[MANIFEST_REL])
    assert lint_module_manifest.main(["--root", str(root)], runner=runner) == 1


def test_main_missing_manifest_is_tool_error(tmp_path: Path) -> None:
    tmp_path.joinpath("python", "larch", "lint").mkdir(parents=True)
    runner = _FakeGit(toplevel=tmp_path.resolve(), tracked=[])
    assert lint_module_manifest.main(["--root", str(tmp_path)], runner=runner) == 2


def test_main_symlink_manifest_is_tool_error(tmp_path: Path) -> None:
    text = _manifest_text([_record("lint_demo.py", "new-module-justified", "why", 5)])
    root = _make_repo(tmp_path, manifest_text=text, inventory=["lint_demo.py"])
    manifest = root / "python" / "lint-module-manifest.json"
    real = root / "python" / "lint-module-manifest-real.json"
    _ = manifest.rename(real)
    manifest.symlink_to(real)
    runner = _FakeGit(toplevel=root.resolve(), tracked=[MANIFEST_REL])
    assert lint_module_manifest.main(["--root", str(root)], runner=runner) == 2


def test_main_non_utf8_manifest_is_tool_error(tmp_path: Path) -> None:
    tmp_path.joinpath("python", "larch", "lint").mkdir(parents=True)
    manifest = tmp_path / "python" / "lint-module-manifest.json"
    _ = manifest.write_bytes(b"\xff\xfe not utf8")
    runner = _FakeGit(toplevel=tmp_path.resolve(), tracked=[MANIFEST_REL])
    assert lint_module_manifest.main(["--root", str(tmp_path)], runner=runner) == 2


def test_main_rejects_unknown_flag() -> None:
    assert lint_module_manifest.main(["--nope"]) == 2


# --- parity with the committed manifest ---------------------------------------


def test_committed_manifest_is_clean_against_live_inventory() -> None:
    manifest_text = (_REPO_ROOT / "python" / "lint-module-manifest.json").read_text(
        encoding="utf-8"
    )
    records = lint_module_manifest.parse_manifest(manifest_text, source_label=MANIFEST_REL)
    inventory = lint_module_manifest.inventory_modules(_REPO_ROOT)
    assert lint_module_manifest.policy_findings(records, inventory, path=MANIFEST_REL) == []


def test_legacy_seed_matches_committed_legacy_rows() -> None:
    manifest_text = (_REPO_ROOT / "python" / "lint-module-manifest.json").read_text(
        encoding="utf-8"
    )
    records = lint_module_manifest.parse_manifest(manifest_text, source_label=MANIFEST_REL)
    legacy = {record.module for record in records if record.host_decision == "legacy"}
    assert legacy == set(lint_module_manifest.LEGACY_SEED_MODULES)


def test_manifest_records_this_module_as_new_module_justified() -> None:
    manifest_text = (_REPO_ROOT / "python" / "lint-module-manifest.json").read_text(
        encoding="utf-8"
    )
    records = lint_module_manifest.parse_manifest(manifest_text, source_label=MANIFEST_REL)
    record = {record.module: record for record in records}["lint_module_manifest.py"]
    assert record.host_decision == "new-module-justified"
    assert record.justification.strip()
    assert record.source_issue > 0
