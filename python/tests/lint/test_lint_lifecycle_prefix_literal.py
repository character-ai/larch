from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_lifecycle_prefix_literal as llpll


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "run",
    token: str = "[DONE]",  # noqa: S107 - fixture token literal for lint row
    constant: str = 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]',
    context: str = "startswith",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "token": token,
        "constant": constant,
        "context": context,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        _ = (python_dir / llpll.BASELINE_FILENAME).write_text(
            json.dumps(baseline), encoding="utf-8"
        )


def _source(body: str) -> str:
    return "import re\n\ndef run(title):\n" + body


def _scan_body(tmp_path: Path, body: str) -> list[llpll.Finding]:
    larch_dir = tmp_path / "python" / "larch"
    larch_dir.mkdir(parents=True)
    path = larch_dir / "mod.py"
    _ = path.write_text(_source(body), encoding="utf-8")
    return llpll.scan_file(path, larch_dir=larch_dir, token_infos=llpll.build_token_map())


@pytest.mark.parametrize(
    ("body", "context", "token", "constant"),
    [
        ('    title.startswith("[DONE]")\n', "startswith", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title.startswith(("[DONE]", "safe"))\n', "startswith", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title.startswith("[done] ")\n', "startswith", "[done]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title == "[DONE]"\n', "compare_eq", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title != "[BUG]"\n', "compare_ne", "[BUG]", "title_match.BUG_PREFIX"),
        ('    "[DONE]" in title\n', "membership_in", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title not in {"[DONE]"}\n', "membership_not_in", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title.endswith("[DONE] ")\n', "endswith", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title.removeprefix("[done] ")\n', "removeprefix", "[done]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ('    title.lstrip("[Bug]")\n', "lstrip", "[Bug]", "title_match.BUG_PREFIX"),
    ],
)
def test_comparison_and_match_positions_are_detected(
    tmp_path: Path, body: str, context: str, token: str, constant: str
) -> None:
    findings = _scan_body(tmp_path, body)

    assert [(finding.context, finding.token, finding.constant) for finding in findings] == [
        (context, token, constant)
    ]


def test_chained_comparison_flags_each_comparator_pair(tmp_path: Path) -> None:
    findings = _scan_body(tmp_path, '    "[DONE]" == title != "[BUG]"\n')

    assert [(finding.context, finding.token) for finding in findings] == [
        ("compare_eq", "[DONE]"),
        ("compare_ne", "[BUG]"),
    ]


def test_regex_calls_detect_raw_and_escaped_bracket_tokens(tmp_path: Path) -> None:
    findings = _scan_body(
        tmp_path,
        '    re.compile(r"\\[DONE\\]")\n'
        '    re.search(r"^\\[done\\]\\s*$", title)\n'
        '    re.match("[BUG]", title)\n'
        '    re.fullmatch(r"\\[STALLED\\]", title)\n',
    )

    assert [(finding.context, finding.token, finding.constant) for finding in findings] == [
        ("regex_pattern", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ("regex_pattern", "[DONE]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]'),
        ("regex_pattern", "[BUG]", "title_match.BUG_PREFIX"),
        ("regex_pattern", "[STALLED]", 'config.TRACKING_ISSUE_PREFIX_BY_STATE["stalled"]'),
    ]


def test_scope_excludes_config_title_match_tests_helpers_and_vendor_dirs(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/core/config.py": _source('    title.startswith("[DONE]")\n'),
            "larch/issue/title_match.py": _source('    title.startswith("[DONE]")\n'),
            "larch/test_mod.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/test_support.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/review_test_support.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/conftest.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/tests/helper.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/__pycache__/generated.py": _source('    title.startswith("[DONE]")\n'),
            "larch/pkg/prod.py": _source("    pass\n"),
        },
        baseline=[],
    )
    larch_dir = tmp_path / "python" / "larch"

    assert [path.relative_to(larch_dir.parent).as_posix() for path in llpll.iter_source_files(larch_dir)] == [
        "larch/pkg/prod.py"
    ]
    assert llpll.main(["--root", str(tmp_path)]) == 0


def test_display_strings_docstrings_comments_and_fstrings_are_not_flagged(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": (
                'def run(title):\n'
                '    """[DONE] is displayed in docs."""\n'
                '    message = "[DONE]"\n'
                '    print(f"[DONE] {title}")\n'
                '    # title.startswith("[DONE]")\n'
            )
        },
        baseline=[],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 0


def test_pragma_like_string_literals_do_not_suppress_findings(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _source(
                '    message = "# lint-lifecycle-prefix: ok fixture"\n'
                '    title.startswith("[DONE]")\n'
            )
        },
        baseline=[],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 1


def test_inline_and_standalone_suppressions_require_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/inline_ok.py": _source(
                '    title.startswith("[DONE]")  # lint-lifecycle-prefix: ok fixture\n'
            ),
            "larch/standalone_ok.py": _source(
                '    # lint-lifecycle-prefix: ok fixture\n'
                '    title.startswith("[DONE]")\n'
            ),
            "larch/bad.py": _source(
                '    title.startswith("[DONE]")  # lint-lifecycle-prefix: ok\n'
            ),
        },
        baseline=[],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 1


def test_occurrence_is_assigned_before_suppression(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _source(
                '    title.startswith("[DONE]")  # lint-lifecycle-prefix: ok fixture\n'
                '    title.startswith("[DONE]")\n'
            )
        },
        baseline=[],
    )

    assert llpll.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / llpll.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(occurrence=2, reason="bootstrap")]


@pytest.mark.parametrize(
    "body",
    [
        '    title.startswith("[done]\\t")\n',
        '    title.startswith("[done]\\n")\n',
    ],
)
def test_non_space_trailing_whitespace_is_not_normalized(tmp_path: Path, body: str) -> None:
    findings = _scan_body(tmp_path, body)

    assert findings == []


def test_baseline_suppresses_existing_findings_and_reports_concrete_constant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=[_record(reason="kept")],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 0
    assert 'use config.TRACKING_ISSUE_PREFIX_BY_STATE["done"] instead' in capsys.readouterr().err


def test_new_finding_exits_1_and_names_bug_prefix_constant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[Bug]")\n')},
        baseline=[],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 1
    assert "matched [Bug] in startswith; use title_match.BUG_PREFIX instead" in capsys.readouterr().err


def test_distinct_contexts_on_same_line_have_separate_identities(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _source(
                '    if title == "[DONE]" or title.startswith("[DONE]"): pass\n'
            )
        },
        baseline=[],
    )

    assert llpll.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / llpll.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert [(row["context"], row["occurrence"]) for row in rows] == [
        ("compare_eq", 1),
        ("startswith", 1),
    ]


@pytest.mark.parametrize(
    "payload",
    [
        [_record(reason="")],
        [
            {
                "file": "larch/mod.py",
                "qualified_symbol": "run",
                "token": "[DONE]",
                "constant": 'config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]',
                "context": "startswith",
                "occurrence": 1,
            }
        ],
        [_record(extra="nope")],
        [_record(file="python/larch/mod.py")],
        [_record(file="mod.py")],
        [_record(context="bad")],
    ],
)
def test_malformed_rows_exit_2(tmp_path: Path, payload: object) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=payload,
    )

    assert llpll.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    row = _record()
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=[row, row],
    )

    assert llpll.main(["--root", str(tmp_path)]) == 2


def test_malformed_json_exits_2(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=[],
    )
    _ = (tmp_path / "python" / llpll.BASELINE_FILENAME).write_text("{", encoding="utf-8")

    assert llpll.main(["--root", str(tmp_path)]) == 2


def test_write_preserves_reasons_and_shrinks_obsolete_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=[_record(reason="kept"), _record(context="compare_eq", reason="obsolete")],
    )

    assert llpll.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / llpll.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="kept")]


def test_write_fails_when_new_rows_lack_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _source(
                '    title.startswith("[DONE]")\n'
                '    title.endswith("[DONE]")\n'
            )
        },
        baseline=[_record()],
    )

    assert llpll.main(["--root", str(tmp_path), "--write"]) == 2


def test_missing_baseline_exits_2_in_check_mode(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=None,
    )

    assert llpll.main(["--root", str(tmp_path)]) == 2


def test_absent_baseline_bootstrap_succeeds(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source('    title.startswith("[DONE]")\n')},
        baseline=None,
    )

    assert llpll.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / llpll.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="bootstrap")]
