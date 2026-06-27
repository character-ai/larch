from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_env_via_config_constant as levcc
def _record(
    *,
    file: str = "mod.py",
    qualified_symbol: str = "run",
    env_name: str = "LARCH_TOKEN_SESSION_ID",
    constant: str = "ENV_LARCH_TOKEN_SESSION_ID",
    access: str = "get",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "env_name": env_name,
        "constant": constant,
        "access": access,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(
    root: Path,
    *,
    files: dict[str, str],
    baseline: object,
    exemptions: object | None = None,
    config: str | None = None,
) -> None:
    python_dir = root / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    config_path = python_dir / "larch" / "core" / "config.py"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _ = config_path.write_text(
        config
        or (
            "from typing import Final\n"
            "ENV_LARCH_TOKEN_SESSION_ID: Final = 'LARCH_TOKEN_SESSION_ID'\n"
            "ENV_LARCH_QUIET_DISABLE = 'LARCH_QUIET_DISABLE'\n"
            "ENV_TMPDIR = 'TMPDIR'\n"
            "ENV_SCRIPT_SH = 'SCRIPT_SH'\n"
        ),
        encoding="utf-8",
    )
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    _ = (python_dir / levcc.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")
    if exemptions is not None:
        _ = (python_dir / levcc.EXEMPTIONS_FILENAME).write_text(
            json.dumps(exemptions), encoding="utf-8"
        )


def _source(body: str) -> str:
    return "import os\nimport config\n\ndef run():\n" + body


def test_config_parser_reads_final_and_plain_assignments(tmp_path: Path) -> None:
    config = tmp_path / "config.py"
    _ = config.write_text(
        "from typing import Final\nENV_ALPHA: Final = 'ALPHA'\nENV_BETA = 'BETA'\n",
        encoding="utf-8",
    )

    assert levcc.parse_config_constants(config, allow_duplicate_values=False) == {
        "ALPHA": "ENV_ALPHA",
        "BETA": "ENV_BETA",
    }


@pytest.mark.parametrize(
    ("body", "access"),
    [
        ("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n", "get"),
        ("    os.environ.get('LARCH_TOKEN_SESSION_ID', '')\n", "get"),
        ("    value = os.environ['LARCH_TOKEN_SESSION_ID']\n", "subscript_load"),
        ("    os.environ['LARCH_TOKEN_SESSION_ID'] = 'x'\n", "subscript_store"),
    ],
)
def test_bare_literal_env_accesses_are_detected(tmp_path: Path, body: str, access: str) -> None:
    _write_project(tmp_path, files={"mod.py": _source(body)}, baseline=[])
    python_dir = tmp_path / "python"
    constants = levcc.parse_config_constants(
        python_dir / "larch" / "core" / "config.py", allow_duplicate_values=False
    )

    findings = levcc.scan_file(python_dir / "mod.py", python_dir=python_dir, env_constants=constants)
    assert [(finding.env_name, finding.constant, finding.access) for finding in findings] == [
        ("LARCH_TOKEN_SESSION_ID", "ENV_LARCH_TOKEN_SESSION_ID", access)
    ]


def test_config_constant_accesses_are_allowed_in_get_and_subscript(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": _source(
                "    os.environ.get(config.ENV_LARCH_TOKEN_SESSION_ID)\n"
                "    os.environ.get(config.ENV_LARCH_TOKEN_SESSION_ID, '')\n"
                "    value = os.environ[config.ENV_LARCH_TOKEN_SESSION_ID]\n"
                "    os.environ[config.ENV_LARCH_TOKEN_SESSION_ID] = value\n"
            )
        },
        baseline=[],
    )

    assert levcc.main(["--root", str(tmp_path)]) == 0


def test_scope_excludes_config_tests_helpers_and_scans_nested_modules(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "test_mod.py": "",
            "pkg/test_nested.py": "",
            "conftest.py": "",
            "pkg/test_support.py": "",
            "pkg/review_test_support.py": "",
            "analysis/nested.py": "",
            "pkg/config.py": "",
            ".venv/lib/vendor.py": "",
            "node_modules/tool/vendor.py": "",
            "__pycache__/generated.py": "",
        },
        baseline=[],
    )
    python_dir = tmp_path / "python"

    assert [path.relative_to(python_dir).as_posix() for path in levcc.iter_source_files(python_dir)] == [
        "analysis/nested.py",
        "pkg/config.py",
    ]


def test_sh_suffix_and_unknown_literals_are_skipped(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"mod.py": _source("    os.environ.get('SCRIPT_SH')\n    os.environ.get('UNKNOWN')\n")},
        baseline=[],
    )

    assert levcc.main(["--root", str(tmp_path)]) == 0


def test_occurrences_are_distinct_and_canonical_on_write(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": _source(
                "    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
                "    os.environ.get('LARCH_QUIET_DISABLE')\n"
            )
        },
        baseline=[],
    )

    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [
        _record(
            env_name="LARCH_QUIET_DISABLE",
            constant="ENV_LARCH_QUIET_DISABLE",
            occurrence=2,
            reason="bootstrap",
        ),
        _record(reason="bootstrap"),
    ]


def test_occurrence_is_assigned_before_pragma_suppression(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": _source(
                "    os.environ.get('LARCH_TOKEN_SESSION_ID')  # lint-env-via-config-constant: ok fixture\n"
                "    os.environ.get('LARCH_QUIET_DISABLE')\n"
            )
        },
        baseline=[],
    )

    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [
        _record(
            env_name="LARCH_QUIET_DISABLE",
            constant="ENV_LARCH_QUIET_DISABLE",
            occurrence=2,
            reason="bootstrap",
        )
    ]


def test_same_env_in_different_symbols_has_distinct_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": (
                "import os\n"
                "def one():\n    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
                "def two():\n    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
            )
        },
        baseline=[],
    )

    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert [row["qualified_symbol"] for row in rows] == ["one", "two"]


@pytest.mark.parametrize(
    "payload",
    [
        [_record(reason="")],
        [
            {
                "file": "mod.py",
                "qualified_symbol": "run",
                "env_name": "LARCH_TOKEN_SESSION_ID",
                "constant": "ENV_LARCH_TOKEN_SESSION_ID",
                "access": "get",
                "occurrence": 1,
            }
        ],
        [_record(extra="nope")],
    ],
)
def test_baseline_shape_or_reason_errors_exit_2(tmp_path: Path, payload: object) -> None:
    _write_project(tmp_path, files={"mod.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n")}, baseline=payload)

    assert levcc.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_and_live_identity_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = _record()
    _write_project(tmp_path, files={"mod.py": ""}, baseline=[row, row])
    assert levcc.main(["--root", str(tmp_path)]) == 2

    _write_project(tmp_path / "live", files={"mod.py": ""}, baseline=[])
    finding = levcc.Finding("mod.py", "run", "LARCH_TOKEN_SESSION_ID", "ENV_LARCH_TOKEN_SESSION_ID", "get", 1, 1)

    def fake_collect_all(
        _python_dir: Path, *, env_constants: dict[str, str]
    ) -> tuple[list[levcc.Finding], dict[str, tuple[str, ...]]]:
        _ = env_constants
        return [finding, finding], {"mod.py": ()}

    monkeypatch.setattr(levcc, "_collect_all", fake_collect_all)
    assert levcc.main(["--root", str(tmp_path / "live")]) == 2


def test_initial_reason_bootstrap_succeeds_when_baseline_absent(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    config_path = python_dir / "larch" / "core" / "config.py"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _ = config_path.write_text(
        "ENV_LARCH_TOKEN_SESSION_ID = 'LARCH_TOKEN_SESSION_ID'\n", encoding="utf-8"
    )
    _ = (python_dir / "mod.py").write_text(
        _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"), encoding="utf-8"
    )

    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0


def test_write_preserves_distinct_env_reasons_after_package_move(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/agents/agents.py": (
                "import os\n"
                "def one():\n    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
                "def two():\n    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
            )
        },
        baseline=[
            _record(file="agents.py", qualified_symbol="one", reason="reason one"),
            _record(file="agents.py", qualified_symbol="two", reason="reason two"),
        ],
    )

    assert levcc.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert {row["qualified_symbol"]: row["reason"] for row in rows} == {
        "one": "reason one",
        "two": "reason two",
    }
    assert {row["file"] for row in rows} == {"larch/agents/agents.py"}


def test_write_fails_on_unmatched_env_finding_without_initial_reason(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/agents/agents.py": (
                "import os\n"
                "def run():\n    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"
                "def extra():\n    os.environ.get('LARCH_QUIET_DISABLE')\n"
            )
        },
        baseline=[_record(file="agents.py", qualified_symbol="run", reason="kept")],
    )

    assert levcc.main(["--root", str(tmp_path), "--write"]) == 2
    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "new reason",
    ]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    reasons = {row["qualified_symbol"]: row["reason"] for row in rows}
    assert reasons == {"extra": "new reason", "run": "kept"}


def test_write_fails_on_duplicate_old_env_rows_sharing_relocation_key(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/agents/agents.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n")},
        baseline=[
            _record(file="flat/agents.py", reason="old one"),
            _record(file="other/agents.py", reason="old two"),
        ],
    )

    assert levcc.main(["--root", str(tmp_path), "--write"]) == 2
    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "new reason",
    ]) == 2


def test_write_fails_on_duplicate_live_env_findings_sharing_relocation_key(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "pkg1/agents.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"),
            "pkg2/agents.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"),
        },
        baseline=[_record(file="agents.py", reason="old")],
    )

    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "new reason",
    ]) == 2


def test_file_and_scoped_exemptions_suppress_only_intended_findings(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "file.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"),
            "env.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n    os.environ.get('LARCH_QUIET_DISABLE')\n"),
            "const.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n"),
            "both.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')\n    os.environ.get('LARCH_QUIET_DISABLE')\n"),
        },
        baseline=[],
        exemptions=[
            {"file": "file.py", "reason": "file"},
            {"file": "env.py", "reason": "env", "env_name": "LARCH_TOKEN_SESSION_ID"},
            {"file": "const.py", "reason": "const", "constant": "ENV_LARCH_TOKEN_SESSION_ID"},
            {
                "file": "both.py",
                "reason": "both",
                "env_name": "LARCH_TOKEN_SESSION_ID",
                "constant": "ENV_LARCH_TOKEN_SESSION_ID",
            },
        ],
    )

    assert levcc.main(["--root", str(tmp_path)]) == 1
    assert levcc.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / levcc.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert [row["file"] for row in rows] == ["both.py", "env.py"]


@pytest.mark.parametrize(
    "exemptions",
    [
        [{"file": "", "reason": "x"}],
        [{"file": "mod.py"}],
        [{"file": "mod.py", "reason": ""}],
        [{"file": "mod.py", "reason": "x", "extra": "bad"}],
        [{"file": "mod.py", "reason": "x", "constant": "NOT_ENV"}],
    ],
)
def test_exemption_shape_errors_exit_2(tmp_path: Path, exemptions: object) -> None:
    _write_project(tmp_path, files={"mod.py": ""}, baseline=[], exemptions=exemptions)

    assert levcc.main(["--root", str(tmp_path)]) == 2


def test_inline_pragma_requires_reason_and_suppresses_only_intended_access(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "ok.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')  # lint-env-via-config-constant: ok fixture\n"),
            "bad.py": _source("    os.environ.get('LARCH_TOKEN_SESSION_ID')  # lint-env-via-config-constant: ok\n"),
        },
        baseline=[],
    )

    assert levcc.main(["--root", str(tmp_path)]) == 1


def test_duplicate_config_values_fail_for_fixtures_but_first_sorted_can_be_used(tmp_path: Path) -> None:
    config = tmp_path / "config.py"
    _ = config.write_text("ENV_B = 'DUP'\nENV_A = 'DUP'\n", encoding="utf-8")

    with pytest.raises(levcc.BaselineError):
        _ = levcc.parse_config_constants(config, allow_duplicate_values=False)
    constants = levcc.parse_config_constants(config, allow_duplicate_values=True)
    assert constants == {"DUP": "ENV_A"}
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    module = python_dir / "mod.py"
    _ = module.write_text(_source("    os.environ.get('DUP')\n"), encoding="utf-8")
    assert levcc.scan_file(module, python_dir=python_dir, env_constants=constants) == [
        levcc.Finding("mod.py", "run", "DUP", "ENV_A", "get", 1, 5)
    ]


def test_malformed_json_and_duplicate_config_main_exit_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"mod.py": ""}, baseline=[])
    python_dir = tmp_path / "python"
    _ = (python_dir / levcc.BASELINE_FILENAME).write_text("{", encoding="utf-8")
    assert levcc.main(["--root", str(tmp_path)]) == 2
    _ = (python_dir / levcc.BASELINE_FILENAME).write_text("[]", encoding="utf-8")
    _ = (python_dir / levcc.EXEMPTIONS_FILENAME).write_text("{", encoding="utf-8")
    assert levcc.main(["--root", str(tmp_path)]) == 2

    _write_project(
        tmp_path / "dup",
        files={"mod.py": ""},
        baseline=[],
        config="ENV_A = 'DUP'\nENV_B = 'DUP'\n",
    )
    assert levcc.main(["--root", str(tmp_path / "dup")]) == 2
