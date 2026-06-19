# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportMissingTypeStubs=false
"""Tests for duplicate_code.py."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from types import MethodType

import pytest
from astroid import nodes
from pylint.checkers import symilar
from pylint.lint import PyLinter

import duplicate_code


def _write_rc(
    root: Path,
    *,
    min_lines: int = 4,
    ignore: str = "CVS",
    ignore_patterns: str = "^\\.#",
    ignore_paths: str = "",
    ignore_comments: str = "yes",
    ignore_docstrings: str = "yes",
    ignore_imports: str = "yes",
    ignore_signatures: str = "yes",
) -> Path:
    rcfile = root / ".pylintrc"
    rcfile.write_text(
        f"""
[MAIN]
ignore={ignore}
ignore-patterns={ignore_patterns}
ignore-paths={ignore_paths}

[MESSAGES CONTROL]
disable=duplicate-code

[REPORTS]
reports=no

[SIMILARITIES]
min-similarity-lines={min_lines}
ignore-comments={ignore_comments}
ignore-docstrings={ignore_docstrings}
ignore-imports={ignore_imports}
ignore-signatures={ignore_signatures}
""".lstrip(),
        encoding="utf-8",
    )
    return rcfile


def _module(lines: int, *, prefix: str = "VALUE") -> str:
    return "\n".join(f"{prefix}_{index} = {index}" for index in range(lines)) + "\n"


def _write_modules(root: Path, names: Sequence[str], source: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def _run(root: Path, *, jobs: int = 1) -> duplicate_code.DuplicateCodeResult:
    return duplicate_code.run_duplicate_code(root=root, rcfile=root / ".pylintrc", jobs=jobs)


def test_config_parsing_reads_similarity_and_ignore_values(tmp_path: Path) -> None:
    rcfile = _write_rc(
        tmp_path,
        min_lines=8,
        ignore="CVS,build",
        ignore_patterns="models.py,__pycache__.*",
        ignore_paths=".venv/,.mypy_cache/",
        ignore_comments="no",
        ignore_docstrings="yes",
        ignore_imports="no",
        ignore_signatures="yes",
    )

    config = duplicate_code.DuplicateCodeConfig.load(root=tmp_path, rcfile=rcfile)

    assert config.min_similarity_lines == 8
    assert config.ignore_comments is False
    assert config.ignore_docstrings is True
    assert config.ignore_imports is False
    assert config.ignore_signatures is True
    assert config.ignore == ("CVS", "build")
    assert config.ignore_patterns == ("models.py", "__pycache__.*")
    assert config.ignore_paths == (".venv/", ".mypy_cache/")


def test_invalid_config_values_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rcfile = _write_rc(tmp_path)
    rcfile.write_text(rcfile.read_text(encoding="utf-8").replace("ignore-comments=yes", "ignore-comments=maybe"), encoding="utf-8")

    rc = duplicate_code.duplicate_code_main(["--root", str(tmp_path), "--rcfile", str(rcfile)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid yn value" in captured.err


def test_global_duplicate_code_enablement_overrides_rcfile_disable(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert "a" in result.findings
    assert "b" in result.findings


def test_process_tokens_runs_before_process_module_with_astroid_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    original_process_tokens = PyLinter.process_tokens
    original_process_module = symilar.SimilaritiesChecker.process_module

    def process_tokens_spy(self: object, tokens: object) -> None:
        events.append("tokens")
        original_process_tokens(self, tokens)  # type: ignore[arg-type]

    def process_module_spy(self: object, node: object) -> None:
        assert isinstance(node, nodes.Module)
        events.append("module")
        original_process_module(self, node)  # type: ignore[arg-type]

    monkeypatch.setattr(PyLinter, "process_tokens", process_tokens_spy)
    monkeypatch.setattr(symilar.SimilaritiesChecker, "process_module", process_module_spy)
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert events[:2] == ["tokens", "module"]


def test_ignore_base_name_excludes_matching_file(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4, ignore="ignored.py")
    _write_modules(tmp_path, ["a.py", "ignored.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.files == ("a.py",)


def test_ignore_patterns_excludes_matching_base_name(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4, ignore_patterns="skip_.*\\.py")
    _write_modules(tmp_path, ["a.py", "skip_b.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.files == ("a.py",)


def test_ignore_paths_is_root_relative(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4, ignore_paths=".venv/")
    _write_modules(tmp_path, ["a.py", ".venv/b.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.files == ("a.py",)


def test_no_duplicates_below_threshold_passes(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=8)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(7))

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.digest == "[]"


def test_exactly_at_threshold_passes(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(4))

    result = _run(tmp_path)

    assert result.exit_code == 0


def test_above_threshold_fails_and_prints_both_modules(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    result = _run(tmp_path)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert "==a:[0:5]" in result.findings
    assert "==b:[0:5]" in result.findings


@pytest.mark.parametrize(("line_count", "expected"), [(3, 0), (4, 0), (5, duplicate_code.REFACTOR_MSG_STATUS)])
def test_threshold_guard(tmp_path: Path, line_count: int, expected: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(line_count))

    result = _run(tmp_path)

    assert result.exit_code == expected


def test_disabled_duplicate_code_lines_remain_in_file_set_but_do_not_report(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.files == ("a.py", "b.py")
    assert result.pair_count == 1


def test_disable_all_suppresses_attribution_while_pairs_are_compared(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=all\n" + _module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.digest == "[]"


def test_enabled_peers_still_fail_when_disabled_peer_is_present(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(
        tmp_path,
        ["a.py", "b.py", "c.py"],
        _module(5),
    )
    (tmp_path / "c.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert result.pair_count == 3
    assert "==a:[0:5]" in result.findings
    assert "==b:[0:5]" in result.findings
    assert "==c:" not in result.findings


def test_block_level_disable_via_file_state_suppresses_duplicate(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    disabled_block = "HEADER = 1\n# pylint: disable=duplicate-code\n" + _module(5)
    (tmp_path / "a.py").write_text(disabled_block, encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.files == ("a.py", "b.py")
    assert result.digest == "[]"


def test_close_equivalent_gating_suppresses_disabled_only_commonalities(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.pair_count == 1
    assert result.digest == "[]"


def test_close_equivalent_gating_reports_enabled_clusters(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))
    (tmp_path / "c.py").write_text("# pylint: disable=all\n" + _module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert result.digest != "[]"
    assert "==a:[0:5]" in result.findings
    assert "==b:[0:5]" in result.findings


@pytest.mark.parametrize("jobs", [2])
def test_disabled_duplicate_code_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == 0
    assert serial.digest == parallel.digest == "[]"
    assert serial.files == parallel.files == ("a.py", "b.py")


@pytest.mark.parametrize("jobs", [2])
def test_disable_all_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=all\n" + _module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == 0
    assert serial.digest == parallel.digest == "[]"


@pytest.mark.parametrize("jobs", [2])
def test_block_level_disable_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    disabled_block = "HEADER = 1\n# pylint: disable=duplicate-code\n" + _module(5)
    (tmp_path / "a.py").write_text(disabled_block, encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == 0
    assert serial.digest == parallel.digest == "[]"
    assert serial.files == parallel.files == ("a.py", "b.py")


@pytest.mark.parametrize("jobs", [2])
def test_close_equivalent_gating_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == 0
    assert serial.digest == parallel.digest == "[]"
    assert serial.pair_count == parallel.pair_count == 1


@pytest.mark.parametrize("jobs", [2])
def test_enabled_peers_with_disabled_peer_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))
    (tmp_path / "c.py").write_text("# pylint: disable=duplicate-code\n" + _module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert serial.digest == parallel.digest
    assert "==a:[0:5]" in serial.findings
    assert "==b:[0:5]" in serial.findings
    assert "==c:" not in serial.findings


@pytest.mark.parametrize("jobs", [2])
def test_close_equivalent_enabled_cluster_parallel_matches_serial(tmp_path: Path, jobs: int) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))
    (tmp_path / "c.py").write_text("# pylint: disable=all\n" + _module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=jobs)

    assert serial.exit_code == parallel.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert serial.digest == parallel.digest
    assert serial.digest != "[]"


def test_cross_file_shard_guard_detects_non_adjacent_duplicates_under_parallel_jobs(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text("UNIQUE_ONLY = 1\n" + _module(5, prefix="OTHER"), encoding="utf-8")
    (tmp_path / "c.py").write_text(_module(5), encoding="utf-8")

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=2)

    assert serial.exit_code == parallel.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert serial.digest == parallel.digest
    assert "==a:[0:5]" in serial.findings
    assert "==c:[0:5]" in serial.findings
    assert "==b:" not in serial.findings


def test_pair_enumeration_uses_instance_bound_find_common_without_iter_sims_prescan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_find_commonalities = duplicate_code._find_commonalities
    find_common_calls: list[tuple[int, object, object]] = []
    iter_sims_during_find: list[bool] = []

    def find_commonalities_spy(
        symilar: object,
        linesets: Sequence[object],
        pairs: Sequence[tuple[int, int]],
        jobs: int,
    ) -> list[object]:
        checker_id = id(symilar)
        original_find_common = symilar._find_common  # type: ignore[attr-defined]
        original_iter_sims = symilar._iter_sims  # type: ignore[attr-defined]

        def find_common_spy(_self: object, lineset1: object, lineset2: object) -> list[object]:
            find_common_calls.append((checker_id, lineset1, lineset2))
            assert id(symilar) == checker_id
            return original_find_common(lineset1, lineset2)

        def iter_sims_guard(_self: object) -> object:
            iter_sims_during_find.append(True)
            return original_iter_sims()

        symilar._find_common = MethodType(find_common_spy, symilar)  # type: ignore[attr-defined]
        symilar._iter_sims = MethodType(iter_sims_guard, symilar)  # type: ignore[attr-defined]
        try:
            return original_find_commonalities(symilar, linesets, pairs, jobs)
        finally:
            symilar._find_common = original_find_common  # type: ignore[attr-defined]
            symilar._iter_sims = original_iter_sims  # type: ignore[attr-defined]

    monkeypatch.setattr(duplicate_code, "_find_commonalities", find_commonalities_spy)
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))

    result = _run(tmp_path, jobs=1)

    assert result.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert result.pair_count == 3
    assert len(find_common_calls) == 3
    assert len({checker_id for checker_id, _, _ in find_common_calls}) == 1
    assert not iter_sims_during_find


def test_configured_threshold_lives_on_checker_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[int] = []
    original_bootstrap = duplicate_code._bootstrap_linter

    def bootstrap_spy(config: duplicate_code.DuplicateCodeConfig, backend: duplicate_code.PylintBackend) -> tuple[object, object, list[object]]:
        linter, checker, fileitems = original_bootstrap(config, backend)
        captured.append(checker.namespace.min_similarity_lines)  # type: ignore[attr-defined]
        assert not hasattr(checker, "min_similarity_lines")
        return linter, checker, fileitems

    monkeypatch.setattr(duplicate_code, "_bootstrap_linter", bootstrap_spy)
    _write_rc(tmp_path, min_lines=8)
    _write_modules(tmp_path, ["a.py"], _module(4))

    result = duplicate_code.run_duplicate_code(root=tmp_path, rcfile=tmp_path / ".pylintrc", jobs=1)

    assert captured == [8]
    assert result.exit_code == 0


def test_cluster_digest_is_stable_between_serial_and_parallel_paths(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))

    serial = _run(tmp_path, jobs=1)
    parallel = _run(tmp_path, jobs=2)

    assert serial.exit_code == parallel.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert serial.digest == parallel.digest
    assert serial.pair_count == parallel.pair_count == 3


def test_digest_changes_when_cluster_is_added(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))
    before = _run(tmp_path).digest
    (tmp_path / "c.py").write_text(_module(5, prefix="OTHER"), encoding="utf-8")
    (tmp_path / "d.py").write_text(_module(5, prefix="OTHER"), encoding="utf-8")

    after = _run(tmp_path).digest

    assert before != after


def test_empty_python_tree_passes(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.digest == "[]"
    assert not result.files
    assert result.pair_count == 0


def test_single_file_passes(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.pair_count == 0
    assert result.digest == "[]"


def test_astroid_parse_failure_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_rc(tmp_path, min_lines=4)
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")

    rc = duplicate_code.duplicate_code_main(
        ["--root", str(tmp_path), "--rcfile", str(tmp_path / ".pylintrc")]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "astroid parse failed" in captured.err


def test_jobs_zero_auto_matches_serial(tmp_path: Path) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    serial = _run(tmp_path, jobs=1)
    auto = duplicate_code.run_duplicate_code(root=tmp_path, rcfile=tmp_path / ".pylintrc", jobs=0)

    assert serial.exit_code == auto.exit_code == duplicate_code.REFACTOR_MSG_STATUS
    assert serial.digest == auto.digest


def test_invalid_jobs_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    rc = duplicate_code.duplicate_code_main(
        [
            "--root",
            str(tmp_path),
            "--rcfile",
            str(tmp_path / ".pylintrc"),
            "--jobs",
            "-1",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid --jobs" in captured.err


def test_worker_failure_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py", "c.py"], _module(5))

    def fail_collect(_futures: object) -> list[object]:
        raise duplicate_code.DuplicateCodeError("duplicate-code worker failed: simulated")

    monkeypatch.setattr(duplicate_code, "_collect_worker_results", fail_collect)

    rc = duplicate_code.duplicate_code_main(
        [
            "--root",
            str(tmp_path),
            "--rcfile",
            str(tmp_path / ".pylintrc"),
            "--jobs",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "worker failed" in captured.err


def test_import_failure_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_rc(tmp_path, min_lines=4)
    _write_modules(tmp_path, ["a.py", "b.py"], _module(5))

    def fail_import() -> duplicate_code.PylintBackend:
        raise duplicate_code.DuplicateCodeError("pylint symilar API drift: missing _find_common")

    monkeypatch.setattr(duplicate_code, "_import_pylint_backend", fail_import)

    rc = duplicate_code.duplicate_code_main(["--root", str(tmp_path), "--rcfile", str(tmp_path / ".pylintrc")])

    captured = capsys.readouterr()
    assert rc == 2
    assert "API drift" in captured.err
