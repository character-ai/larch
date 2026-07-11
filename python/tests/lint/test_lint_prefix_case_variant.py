from __future__ import annotations

from pathlib import Path

from larch.lint import lint_prefix_case_variant as lpcv


def _write_fixture(
    root: Path,
    *,
    markdown: dict[str, str] | None = None,
    bash: dict[str, str] | None = None,
    residual_paths: list[str] | None = None,
) -> None:
    for relpath, source in (markdown or {}).items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    bash_files = bash or {}
    for relpath, source in bash_files.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    manifest = root / "scripts" / "residual-bash-paths.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    rows = residual_paths if residual_paths is not None else sorted(bash_files)
    _ = manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def test_flags_case_variant_in_markdown_and_bash(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={"skills/example/SKILL.md": "File a `[Bug]` issue.\n"},
        bash={"scripts/example.sh": 'echo "[bug] title"\n'},
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 1


def test_allows_exact_case_canonical_tokens(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={
            "skills/a.md": "Use `[BUG]` and `[DONE]` prefixes.\n",
            ".claude/skills/b.md": "Rename to `[STALLED]` when needed.\n",
            "agents/c.md": "Keep `[IMPLEMENTING]` exact.\n",
        },
        bash={"scripts/ok.sh": 'printf "%s\\n" "[BUG] title"\n'},
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 0


def test_markdown_and_bash_suppressions_require_reasons(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={
            "skills/ok.md": (
                "Legacy `[Bug]` heading. "
                "<!-- lint-prefix-case-variant: ok fixture -->\n"
            ),
            "skills/bad.md": (
                "Legacy `[Bug]` heading. <!-- lint-prefix-case-variant: ok -->\n"
            ),
        },
        bash={
            "scripts/ok.sh": (
                'printf "%s\\n" "[bug]"  # lint-prefix-case-variant: ok fixture\n'
            ),
            "scripts/bad.sh": (
                'printf "%s\\n" "[bug]"  # lint-prefix-case-variant: ok\n'
            ),
        },
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 1


def test_unrelated_brackets_and_canonical_prose_remain_allowed(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={
            "skills/a.md": "See `[BUGFIX]` and `[feature]` notes plus exact `[BUG]`.\n"
        },
        bash={"scripts/a.sh": 'echo "[ok]" "[BUG]"\n'},
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 0


def test_scans_all_markdown_roots_and_residual_bash(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={
            "skills/one.md": "x\n",
            ".claude/skills/two.md": "y\n",
            "agents/three.md": "z\n",
        },
        bash={
            "scripts/a.sh": "true\n",
            "scripts/b.sh": "true\n",
        },
    )
    root = tmp_path
    markdown_files = [
        path.relative_to(root).as_posix() for path in lpcv.iter_markdown_files(root)
    ]
    bash_files = [
        path.relative_to(root).as_posix() for path in lpcv.iter_residual_bash_files(root)
    ]

    assert markdown_files == [
        ".claude/skills/two.md",
        "agents/three.md",
        "skills/one.md",
    ]
    assert bash_files == ["scripts/a.sh", "scripts/b.sh"]


def test_multi_finding_output_is_deterministic(tmp_path: Path, capsys: object) -> None:
    _write_fixture(
        tmp_path,
        markdown={
            "skills/z.md": "`[Done]` then `[Bug]`\n",
            "skills/a.md": "`[bug]`\n",
        },
        bash={},
        residual_paths=[],
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if "matched" in line]
    assert lines == [
        "skills/a.md: line 1 matched [bug]; use exact-case [BUG]",
        "skills/z.md: line 1 matched [Bug]; use exact-case [BUG]",
        "skills/z.md: line 1 matched [Done]; use exact-case [DONE]",
    ]


def test_missing_residual_manifest_exits_2(tmp_path: Path) -> None:
    _ = (tmp_path / "skills").mkdir()
    _ = (tmp_path / "skills" / "a.md").write_text("[BUG]\n", encoding="utf-8")

    assert lpcv.main(["--root", str(tmp_path)]) == 2


def test_missing_residual_path_exits_2(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={"skills/a.md": "[BUG]\n"},
        bash={},
        residual_paths=["scripts/missing.sh"],
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 2


def test_symlinked_markdown_exits_2(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    real = tmp_path / "real.md"
    _ = real.write_text("`[Bug]`\n", encoding="utf-8")
    link = skills / "linked.md"
    link.symlink_to(real)
    _write_fixture(tmp_path, markdown={}, bash={}, residual_paths=[])

    assert lpcv.main(["--root", str(tmp_path)]) == 2


def test_symlinked_residual_bash_exits_2(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    real = tmp_path / "real.sh"
    _ = real.write_text('echo "[bug]"\n', encoding="utf-8")
    link = scripts / "linked.sh"
    link.symlink_to(real)
    _write_fixture(
        tmp_path,
        markdown={"skills/a.md": "[BUG]\n"},
        bash={},
        residual_paths=["scripts/linked.sh"],
    )

    assert lpcv.main(["--root", str(tmp_path)]) == 2


def test_non_utf8_markdown_exits_2(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        markdown={"skills/a.md": "`[Bug]`\n"},
        bash={},
        residual_paths=[],
    )
    _ = (tmp_path / "skills" / "a.md").write_bytes(b"\xff\xfe")

    assert lpcv.main(["--root", str(tmp_path)]) == 2
