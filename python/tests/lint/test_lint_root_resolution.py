"""Tests for the engine-backed root-resolution adoption lint."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from larch.lint import lint_root_resolution as lint
from larch.lint.engine import SourceFile


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _repo(tmp_path: Path, *, source: str, baseline: list[dict[str, object]]) -> Path:
    root = tmp_path / "repo"
    module = root / "python" / "larch" / "demo.py"
    module.parent.mkdir(parents=True)
    _ = module.write_text(source, encoding="utf-8")
    _ = (root / "python" / lint.BASELINE_FILENAME).write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    _ = subprocess.run(["git", "init", "-q", str(root)], check=True)
    _ = subprocess.run(["git", "-C", str(root), "add", "python"], check=True)
    return root


def test_detect_rejects_private_plugin_root() -> None:
    findings = lint.detect(_source(
        "python/larch/demo.py", "def _plugin_root():\n    return None\n"
    ))

    assert len(findings) == 1
    assert findings[0].message.startswith("private-plugin-root")
    assert findings[0].occurrence_values == (("kind", "private-plugin-root"),)


def test_detect_numbers_inline_probes_in_source_order() -> None:
    source = _source(
        "python/larch/demo.py",
        "one = ['git', 'rev-parse', '--show-toplevel']\ntwo = ['git', 'rev-parse', '--show-toplevel']\n",
    )

    findings = lint.detect(source)

    assert [finding.occurrence for finding in findings] == [1, 2]


def test_detect_exempts_the_canonical_owner() -> None:
    assert not lint.detect(_source(
        "python/larch/core/repo_roots.py",
        "cmd = ['git', 'rev-parse', '--show-toplevel']\n",
    ))


def test_removed_baselined_probe_fails_strict_stale_check(tmp_path: Path) -> None:
    root = _repo(tmp_path, source="value = 1\n", baseline=[{
        "file": "larch/demo.py",
        "kind": "inline-git-toplevel",
        "occurrence": 1,
        "reason": "legacy raw diagnostic consumer",
    }])

    assert lint.main(["--root", str(root)]) == 2


def test_engine_rejects_legacy_count_schema_and_duplicate_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path, source="value = 1\n", baseline=[{
        "path": "python/larch/demo.py",
        "kind": "inline-git-toplevel",
        "count": 1,
        "reason": "legacy count schema",
    }])

    assert lint.main(["--root", str(root)]) == 2

    duplicate = [{
        "file": "larch/demo.py",
        "kind": "inline-git-toplevel",
        "occurrence": 1,
        "reason": "legacy raw diagnostic consumer",
    }]
    _ = (root / "python" / lint.BASELINE_FILENAME).write_text(
        json.dumps([*duplicate, *duplicate]), encoding="utf-8"
    )

    assert lint.main(["--root", str(root)]) == 2


def test_write_shrinks_a_removed_baseline(tmp_path: Path) -> None:
    root = _repo(tmp_path, source="value = 1\n", baseline=[{
        "file": "larch/demo.py",
        "kind": "inline-git-toplevel",
        "occurrence": 1,
        "reason": "legacy raw diagnostic consumer",
    }])

    assert lint.main(["--root", str(root), "--write"]) == 0
    assert json.loads((root / "python" / lint.BASELINE_FILENAME).read_text(encoding="utf-8")) == []
