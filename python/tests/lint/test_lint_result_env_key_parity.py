from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_result_env_key_parity as lrp


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _writer_src(basename: str, keys: list[str], *, pragma: bool = False, dynamic: bool = False) -> str:
    open_line = "    phase_driver_write_result_env("
    if pragma:
        open_line += "  # lint-result-env-key-parity: ok fixture divergence"
    if dynamic:
        kv_line = "        kvs=rows,"
    else:
        items = ", ".join(f'("{key}", "value")' for key in keys)
        kv_line = f"        kvs=[{items}],"
    return (
        "from pathlib import Path\n"
        "\n"
        "def emit(tmpdir: Path, rows: list) -> None:\n"
        f"{open_line}\n"
        f'        path=tmpdir / "{basename}",\n'
        f"{kv_line}\n"
        "    )\n"
    )


def _project(root: Path) -> None:
    (root / "python" / "larch").mkdir(parents=True, exist_ok=True)


def _writer(root: Path, name: str, basename: str, keys: list[str], *, pragma: bool = False, dynamic: bool = False) -> None:
    _write(root / "python" / "larch" / name, _writer_src(basename, keys, pragma=pragma, dynamic=dynamic))


def _seed_baseline(root: Path, rows: list[dict[str, str]]) -> None:
    _write(root / "python" / lrp.BASELINE_FILENAME, json.dumps(rows))


def test_identical_key_sets_pass(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A", "B"])

    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_missing_key_fails_and_names_basename_path_and_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])

    assert lrp.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "python/larch/writer_b.py:" in err
    assert "result-env-key-parity: slot.env writer missing key B present in sibling writers" in err


def test_optional_key_suppresses_violation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])
    monkeypatch.setitem(lrp.OPTIONAL_KEYS, "slot.env", frozenset({"B"}))

    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_pragma_on_call_line_suppresses_violation(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"], pragma=True)

    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_baseline_record_suppresses_and_shrinks(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])
    _seed_baseline(
        tmp_path,
        [{"basename": "slot.env", "path": "python/larch/writer_b.py", "key": "B", "reason": "grandfathered"}],
    )

    assert lrp.main(["--root", str(tmp_path)]) == 0

    _seed_baseline(tmp_path, [])
    assert lrp.main(["--root", str(tmp_path)]) == 1


def test_dynamic_kv_argument_is_skipped_without_violation(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", [], dynamic=True)

    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_single_writer_is_never_a_violation(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "solo.env", ["A", "B", "C"])

    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_write_seeds_reason_and_check_then_passes(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])

    assert lrp.main(["--root", str(tmp_path), "--write", "--initial-reason", "grandfathered divergent writers"]) == 0
    rows = json.loads((tmp_path / "python" / lrp.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [{"basename": "slot.env", "path": "python/larch/writer_b.py", "key": "B", "reason": "grandfathered divergent writers"}]
    assert lrp.main(["--root", str(tmp_path)]) == 0


def test_write_without_initial_reason_for_new_violation_exits_2(tmp_path: Path) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])

    assert lrp.main(["--root", str(tmp_path), "--write"]) == 2


@pytest.mark.parametrize(
    "baseline",
    [
        [{"basename": "slot.env", "path": "python/larch/w.py", "key": "B", "reason": ""}],
        [{"basename": "slot.env", "path": "python/larch/w.py", "key": "B"}],
        [{"basename": "slot.env", "path": "python/larch/w.py", "key": "B", "reason": "x", "extra": "no"}],
    ],
)
def test_malformed_baseline_exits_2(tmp_path: Path, baseline: object) -> None:
    _project(tmp_path)
    _writer(tmp_path, "writer_a.py", "slot.env", ["A", "B"])
    _writer(tmp_path, "writer_b.py", "slot.env", ["A"])
    _write(tmp_path / "python" / lrp.BASELINE_FILENAME, json.dumps(baseline))

    assert lrp.main(["--root", str(tmp_path)]) == 2
