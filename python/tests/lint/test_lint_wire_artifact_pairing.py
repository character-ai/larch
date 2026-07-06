from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_wire_artifact_pairing as lwa


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _project(root: Path, *, manifest: object, baseline: object | None = None) -> None:
    (root / "python" / "larch").mkdir(parents=True, exist_ok=True)
    _write(root / "python" / lwa.MANIFEST_FILENAME, json.dumps(manifest))
    _write(root / "python" / lwa.BASELINE_FILENAME, json.dumps(baseline if baseline is not None else []))


def _row(artifact: str = "artifact.env", kind: str = "basename") -> dict[str, str]:
    return {"kind": kind, "artifact": artifact}


def test_reader_plus_python_writer_passes(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')
    _write(tmp_path / "python/larch/writer.py", 'from pathlib import Path\nPath("artifact.env").write_text("x")\n')

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_reader_with_no_writer_fails(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')

    assert lwa.main(["--root", str(tmp_path)]) == 1


def test_reader_with_sibling_manifest_name_does_not_count(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row("manifest.json")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "scout-coder-manifest.json"\n')

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_skill_md_prose_writer_does_not_count(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')
    _write(tmp_path / "skills/demo/SKILL.md", "Write artifact.env before reading it.\n")

    assert lwa.main(["--root", str(tmp_path)]) == 1


def test_test_only_writers_do_not_count(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')
    _write(tmp_path / "python/tests/test_writer.py", 'from pathlib import Path\nPath("artifact.env").write_text("x")\n')
    _write(tmp_path / "scripts/test-writer.sh", "touch artifact.env\n")

    assert lwa.main(["--root", str(tmp_path)]) == 1


@pytest.mark.parametrize("line", ["touch artifact.env\n", "printf %s x > artifact.env\n"])
def test_production_shell_writer_counts(tmp_path: Path, line: str) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')
    _write(tmp_path / "scripts/write.sh", line)

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_path_touch_counts(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row()])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')
    _write(tmp_path / "python/larch/writer.py", 'from pathlib import Path\nPath("artifact.env").touch()\n')

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_python_atomic_writer_with_split_binding_counts(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row("design-report-gate-sidecars.md")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "design-report-gate-sidecars.md"\n')
    _write(
        tmp_path / "python/larch/writer.py",
        'from pathlib import Path\n'
        'artifact = "design-report-gate-sidecars.md"\n'
        'target = Path("build") / artifact\n'
        '_write_text_atomic(\n'
        '    path=target,\n'
        '    text="x",\n'
        ')\n',
    )

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_python_writer_with_distant_split_binding_counts(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row(".completed/step-final-summary", "relative_path")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = tmpdir / ".completed/step-final-summary"\n')
    _write(
        tmp_path / "python/larch/writer.py",
        'from pathlib import Path\n'
        '\n'
        'def write_summary(tmpdir: Path) -> None:\n'
        '    completed = tmpdir / ".completed"\n'
        '    target = completed / "step-final-summary"\n'
        '    prefix = "ignored"\n'
        '    for _ in range(2):\n'
        '        prefix = prefix\n'
        '    target.write_text("x")\n'
        '\n'
        'write_summary(Path("build"))\n',
    )

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_python_writer_with_joinpath_counts(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row(".completed/step-5c-terminal", "relative_path")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = tmpdir / ".completed/step-5c-terminal"\n')
    _write(
        tmp_path / "python/larch/writer.py",
        'from pathlib import Path\n'
        '\n'
        'def write_terminal(tmpdir: Path) -> None:\n'
        '    artifact = "step-5c-terminal"\n'
        '    target = Path(tmpdir).joinpath(".completed").joinpath(artifact)\n'
        '    target.touch()\n'
        '\n'
        'write_terminal(Path("build"))\n',
    )

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_run_log_batch_name_counts_as_writer(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row("token-report.json")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "token-report.json"\n')
    _write(tmp_path / "python/larch/report/run_log_batch.py", 'BatchInfo = tuple\n_LARCH_LOG_BATCHES = {"token-report": BatchInfo(".json")}\n')

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_skills_scripts_manifest_artifact_shell_writer_counts(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row("design-report-gate-sidecars.md")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "design-report-gate-sidecars.md"\n')
    _write(
        tmp_path / "skills/demo/scripts/write.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' ok > design-report-gate-sidecars.md\n",
    )

    assert lwa.main(["--root", str(tmp_path)]) == 0


def test_shell_redirect_with_artifact_input_does_not_count(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row("design-report-gate-sidecars.md")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = "design-report-gate-sidecars.md"\n')
    _write(
        tmp_path / "skills/demo/scripts/write.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' design-report-gate-sidecars.md > output.txt\n",
    )

    assert lwa.main(["--root", str(tmp_path)]) == 1


def test_baseline_suppresses_and_warns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _project(
        tmp_path,
        manifest=[_row()],
        baseline=[{"artifact": "artifact.env", "side": "external-writer", "reason": "created by fixture"}],
    )
    _write(tmp_path / "python/larch/reader.py", 'NAME = "artifact.env"\n')

    assert lwa.main(["--root", str(tmp_path)]) == 0
    assert "baselined" in capsys.readouterr().err


@pytest.mark.parametrize(
    "manifest",
    [
        [{"artifact": "artifact.env", "reason": "wrong"}],
        [{"artifact": "artifact.env"}],
        [_row("a/b", "basename")],
    ],
)
def test_malformed_manifest_exits_2(tmp_path: Path, manifest: object) -> None:
    _project(tmp_path, manifest=manifest)

    assert lwa.main(["--root", str(tmp_path)]) == 2


@pytest.mark.parametrize(
    "baseline",
    [
        [{"artifact": "artifact.env", "side": "external-writer", "reason": ""}],
        [{"artifact": "artifact.env", "side": "bad", "reason": "x"}],
        [{"artifact": "artifact.env", "side": "external-writer", "reason": "x", "extra": "no"}],
    ],
)
def test_malformed_baseline_exits_2(tmp_path: Path, baseline: object) -> None:
    _project(tmp_path, manifest=[_row()], baseline=baseline)

    assert lwa.main(["--root", str(tmp_path)]) == 2


def test_duplicate_manifest_or_baseline_identity_exits_2(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row(), _row()])
    assert lwa.main(["--root", str(tmp_path)]) == 2

    _project(
        tmp_path,
        manifest=[_row()],
        baseline=[
            {"artifact": "artifact.env", "side": "external-writer", "reason": "x"},
            {"artifact": "artifact.env", "side": "external-reader", "reason": "y"},
        ],
    )
    assert lwa.main(["--root", str(tmp_path)]) == 2


def test_write_preserves_reasons_and_drops_obsolete_rows(tmp_path: Path) -> None:
    _project(
        tmp_path,
        manifest=[_row("live.env"), _row("gone.env")],
        baseline=[
            {"artifact": "live.env", "side": "external-writer", "reason": "kept"},
            {"artifact": "gone.env", "side": "external-writer", "reason": "dropped"},
        ],
    )
    _write(tmp_path / "python/larch/reader.py", 'NAME = "live.env"\n')

    assert lwa.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / lwa.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [{"artifact": "live.env", "side": "external-writer", "reason": "kept"}]


def test_relative_path_rows_match_anchored_suffix(tmp_path: Path) -> None:
    _project(tmp_path, manifest=[_row(".completed/step-3-terminal", "relative_path")])
    _write(tmp_path / "python/larch/reader.py", 'NAME = tmpdir / ".completed/step-3-terminal"\n')
    _write(tmp_path / "scripts/write.sh", 'touch "$DIR/.completed/step-3-terminal"\n')

    assert lwa.main([str(tmp_path)]) == 0
