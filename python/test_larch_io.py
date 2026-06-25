from __future__ import annotations

from pathlib import Path

import pytest

import larch_io


def test_parse_kv_last_wins_by_default() -> None:
    assert larch_io.parse_kv("A=1\nA=2\nB=3\n") == {"A": "2", "B": "3"}


def test_parse_kv_first_wins() -> None:
    assert larch_io.parse_kv("A=1\nA=2\n", first_wins=True) == {"A": "1"}


def test_parse_kv_empty_key_policy() -> None:
    assert larch_io.parse_kv("=value\n") == {"": "value"}
    assert not larch_io.parse_kv("=value\n", skip_empty_key=True)


def test_parse_kv_comments_and_strip_value() -> None:
    text = "# ignored\nA= value \n"
    assert larch_io.parse_kv(text, skip_comments=True, strip_value=True) == {"A": "value"}


def test_parse_kv_cr_strip_modes() -> None:
    text = "A=\rvalue\r\n"
    assert larch_io.parse_kv(text, cr_strip="none")["A"] == "\rvalue"
    assert larch_io.parse_kv(text, cr_strip="suffix")["A"] == "\rvalue"
    assert larch_io.parse_kv(text, cr_strip="rstrip")["A"] == "\rvalue"
    assert larch_io.parse_kv(text, cr_strip="strip")["A"] == "value"


def test_kv_value_first_and_last() -> None:
    text = "A=1\nA=2\n"
    assert larch_io.kv_value(text=text, key="A") == "1"
    assert larch_io.kv_value(text=text, key="A", first_match=False) == "2"


def test_read_kv_modes(tmp_path: Path) -> None:
    path = tmp_path / "env"
    _ = path.write_text("A=\nA=2\r\n", encoding="utf-8")
    assert larch_io.read_kv(path=path, key="A", default="x", empty_value_means_default=True) == "x"
    assert larch_io.read_kv(path=path, key="A", first_match=False, cr_strip="suffix") == "2"


def test_reject_symlink_on_read_kvs_and_read_kv(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    link = tmp_path / "link.env"
    _ = target.write_text("A=1\n", encoding="utf-8")
    link.symlink_to(target)
    assert not larch_io.read_kvs(link, reject_symlink=True)
    assert larch_io.read_kv(path=link, key="A", default="x", reject_symlink=True) == "x"


def test_reject_cr_raises(tmp_path: Path) -> None:
    path = tmp_path / "env"
    _ = path.write_bytes(b"A=1\r\n")
    with pytest.raises(ValueError, match="carriage return"):
        _ = larch_io.read_kvs(path, reject_cr=True)


def test_missing_and_error_defaults(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert not larch_io.read_kvs(missing)
    assert larch_io.read_kv(path=missing, key="A", default="x") == "x"
    bad = tmp_path / "bad"
    _ = bad.write_bytes(b"\xff")
    assert larch_io.read_kv(path=bad, key="A", default="x", errors="strict", on_error_default=True) == "x"
    with pytest.raises(UnicodeDecodeError):
        _ = larch_io.read_kv(path=bad, key="A", errors="strict")


def test_format_kvs_ordering() -> None:
    assert larch_io.format_kvs({"B": 2, "A": 1}) == "B=2\nA=1\n"
    assert larch_io.format_kvs([("B", 2), ("A", 1)], sort_keys=True) == "A=1\nB=2\n"


def test_write_kvs_and_non_atomic_error(tmp_path: Path) -> None:
    path = tmp_path / "out.env"
    larch_io.write_kvs(path=path, values={"B": 2, "A": 1})
    assert path.read_text(encoding="utf-8") == "B=2\nA=1\n"
    with pytest.raises(FileNotFoundError):
        larch_io.write_kvs(path=tmp_path / "missing" / "out.env", values={"A": 1}, atomic=False, create_parent=False)


def test_atomic_write_parent_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "a" / "out.txt"
    larch_io.atomic_write(path=path, text="ok", mode=0o600)
    assert path.read_text(encoding="utf-8") == "ok"
    assert (path.stat().st_mode & 0o777) == 0o600


def test_atomic_write_exclusive_nofollow_rejects_symlink_temp(tmp_path: Path) -> None:
    path = tmp_path / "out"
    temp = tmp_path / "out.tmp"
    target = tmp_path / "target"
    _ = target.write_text("target", encoding="utf-8")
    temp.symlink_to(target)
    with pytest.raises(OSError, match="refusing symlink temp"):
        larch_io.atomic_write(path=path, text="x", exclusive=True, nofollow=True, temp_name="out.tmp")
    assert temp.is_symlink()
    assert target.read_text(encoding="utf-8") == "target"


def test_parse_kv_crlf_parity(tmp_path: Path) -> None:
    text = "TOOL=codex\r\nCODEX_BINARY_FOUND=true\r\n"
    assert larch_io.parse_kv(text) == {"TOOL": "codex", "CODEX_BINARY_FOUND": "true"}
    assert larch_io.kv_value(text=text, key="TOOL") == "codex"
    path = tmp_path / "env"
    _ = path.write_bytes(text.encode("utf-8"))
    assert larch_io.read_kv(path=path, key="TOOL") == "codex"
    assert larch_io.read_kvs(path) == {"TOOL": "codex", "CODEX_BINARY_FOUND": "true"}


def test_atomic_write_exclusive_fixed_temp_unlinks_stale(tmp_path: Path) -> None:
    path = tmp_path / "out"
    temp = tmp_path / "out.tmp"
    _ = temp.write_text("stale", encoding="utf-8")
    larch_io.atomic_write(path=path, text="new", exclusive=True, nofollow=True, temp_name="out.tmp")
    assert path.read_text(encoding="utf-8") == "new"
    assert not temp.exists()


def test_text_helpers(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "file.txt"
    assert larch_io.read_text(path, default="") == ""
    larch_io.write_text(path=path, text="a")
    larch_io.append_text(path=path, text="b")
    assert larch_io.read_text(path) == "ab"
