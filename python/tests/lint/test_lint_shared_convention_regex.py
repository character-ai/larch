from __future__ import annotations

from pathlib import Path
from typing import Protocol

from larch.lint import lint_shared_convention_regex as lscr
from tests.lint.conftest import write_project as _write_project


class CaptureResult(Protocol):
    err: str
    out: str


class CaptureFixture(Protocol):
    def readouterr(self) -> CaptureResult: ...


def _module(body: str) -> str:
    return "from __future__ import annotations\n\nimport re\n\n" + body


def test_duplicate_guideline_heading_regex_is_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module('GUIDELINE_RE = re.compile(r"^###\\s+(G-[A-Za-z0-9-]+-\\d+):\\s*(.+?)\\s*$")\n')},
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "use architectural_guidelines.GUIDELINE_HEADING_RE" in capsys.readouterr().err


def test_duplicate_invariant_heading_regex_constant_is_detected(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module('INVARIANT_RE = r"^#{2,4}\\s+(I-[A-Za-z0-9-]+-\\d+):\\s*(.+?)\\s*$"\n')},
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "use architectural_guidelines.INVARIANT_HEADING_RE" in capsys.readouterr().err


def test_module_level_assign_and_annassign_bug_selectors_are_detected(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/assign.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/annassign.py": _module('DEFAULT_SEARCH: str = "[BUG] in:title"\n'),
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    stderr = capsys.readouterr().err
    assert stderr.count("use title_match.bug_title_match or title_match.BUG_PREFIX") == 2


def test_shared_constant_imports_are_clean(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "from larch.core.architectural_guidelines import GUIDELINE_HEADING_RE\n"
                "from larch.issue.title_match import BUG_PREFIX, bug_title_match\n"
                "DEFAULT_SEARCH = f'{BUG_PREFIX} in:title'\n"
                "def run(title: str) -> bool:\n"
                "    return bug_title_match(title) or GUIDELINE_HEADING_RE.match(title) is not None\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_same_line_suppression_requires_reason(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/ok.py": _module(
                'DEFAULT_SEARCH = "[BUG] in:title"  # lint-shared-convention-regex: ok fixture\n'
            ),
            "larch/bad.py": _module(
                'DEFAULT_SEARCH = "[BUG] in:title"  # lint-shared-convention-regex: ok\n'
            ),
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1


def test_owner_modules_are_skipped(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/core/architectural_guidelines.py": _module(
                'GUIDELINE_HEADING_RE = re.compile(r"^###\\s+(G-[A-Za-z0-9-]+-\\d+):\\s*(.+?)\\s*$")\n'
            ),
            "larch/issue/title_match.py": _module('BUG_PREFIX = "[BUG]"\nDEFAULT_SEARCH = "[BUG] in:title"\n'),
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_lint_implementation_module_is_excluded_from_scan_scope(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/lint/lint_shared_convention_regex.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/prod.py": _module("VALUE = 'clean'\n"),
        },
    )
    larch_dir = tmp_path / "python" / "larch"

    assert [path.relative_to(larch_dir.parent).as_posix() for path in lscr.iter_source_files(larch_dir)] == [
        "larch/pkg/prod.py"
    ]
    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_lifecycle_prefix_call_compare_and_regex_contexts_are_not_double_reported(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "def run(title: str) -> bool:\n"
                "    bug_re = re.compile(r'\\[BUG\\]')\n"
                "    return title.startswith('[BUG]') or title != '[BUG]' or bug_re.match(title) is not None\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_lifecycle_prefix_strip_loop_is_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "LIFECYCLE_PREFIXES = ('[DONE] ',)\n"
                "def strip(title: str) -> str:\n"
                "    for prefix in LIFECYCLE_PREFIXES:\n"
                "        if title.startswith(prefix):\n"
                "            return title[len(prefix):]\n"
                "    return title\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "use title_match.strip_lifecycle_prefix or title_match.detect_lifecycle_prefix" in capsys.readouterr().err


def test_lifecycle_prefix_slice_loop_is_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "LIFECYCLE_PREFIXES = ('[DONE] ',)\n"
                "def trim(title: str) -> str:\n"
                "    for prefix in LIFECYCLE_PREFIXES:\n"
                "        return title[len(prefix):]\n"
                "    return title\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "lifecycle-prefix-strip-loop" in capsys.readouterr().err


def test_lifecycle_prefix_strip_loop_owner_is_allowlisted(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/issue/title_match.py": _module(
                "LIFECYCLE_PREFIXES = ('[DONE] ',)\n"
                "def strip(title: str) -> str:\n"
                "    for prefix in LIFECYCLE_PREFIXES:\n"
                "        if title.startswith(prefix):\n"
                "            return title[len(prefix):]\n"
                "    return title\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_lifecycle_prefix_strip_loop_suppression_is_honored(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "LIFECYCLE_PREFIXES = ('[DONE] ',)\n"
                "def strip(title: str) -> str:\n"
                "    for prefix in LIFECYCLE_PREFIXES:  # lint-shared-convention-regex: ok fixture\n"
                "        if title.startswith(prefix):\n"
                "            return title[len(prefix):]\n"
                "    return title\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_scope_excludes_tests_helpers_and_vendor_dirs(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/test_mod.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/test_nested.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/conftest.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/test_support.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/review_test_support.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/tests/helper.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/__pycache__/generated.py": _module('DEFAULT_SEARCH = "[BUG] in:title"\n'),
            "larch/pkg/prod.py": _module("VALUE = 'clean'\n"),
        },
    )
    larch_dir = tmp_path / "python" / "larch"

    assert [path.relative_to(larch_dir.parent).as_posix() for path in lscr.iter_source_files(larch_dir)] == [
        "larch/pkg/prod.py"
    ]
    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_reviewer_item_heading_regex_calls_and_assignments_are_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/compiled.py": _module('ITEM_RE = re.compile(r"(?ms)^### (?:FINDING|OOS)_[0-9]+:.*?(?=^### |\\Z)")\n'),
            "larch/direct.py": _module('def run(text: str) -> object:\n    return re.search(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\\Z)", text)\n'),
            "larch/assigned.py": _module('ITEM_PATTERN = r"(?ms)^### OOS_[0-9]+:.*?(?=^### OOS_|\\Z)"\n'),
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert capsys.readouterr().err.count("use review_types.parse_blocks or review_types.parse_canonical_heading") == 3


def test_review_types_owner_is_exempt(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/review/review_types.py": _module('ITEM_RE = re.compile(r"^### FINDING_[0-9]+:")\n')},
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_inline_multiline_block_sentinel_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/seg.py": _module(
                'HEADING_RE = re.compile(r"(?m)^### (?:FINDING|OOS)_[0-9]+(?:\\b|:).*$")\n'
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "use review_types.parse_blocks or review_types.parse_canonical_heading" in capsys.readouterr().err


def test_canonical_id_capture_group_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/hdr.py": _module(
                r'OOS_RE = re.compile(r"^###\s+OOS_(\d+):[^\n]*\n", re.MULTILINE)' + "\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 1
    assert "use review_types.parse_blocks or review_types.parse_canonical_heading" in capsys.readouterr().err


def test_vote_line_and_field_regex_non_matches(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/voter.py": _module(
                'VOTE_ROW_RE = re.compile(r"^\\| (FINDING_[0-9]+) \\| (YES|NO) \\|")\n'
                'FIELD_RE = re.compile(r"(?i)focus-area\\s*[:=]\\s*security")\n'
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0


def test_suppression_on_retained_line_scan(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/retained.py": _module(
                'BALLOT_RE = re.compile(r"(?m)^### (?:FINDING|OOS)_[0-9]+(?:\\b|:).*$")  '
                "# lint-shared-convention-regex: ok distinct historical ballot grammar\n"
            )
        },
    )

    assert lscr.main(["--root", str(tmp_path)]) == 0
