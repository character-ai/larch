"""Tests for the shared report Markdown block upsert helper."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from larch.report import markdown_block, timing, tokens


def _run_tokens(target: Path, block: str) -> None:
    tokens._replace_block(  # pyright: ignore[reportPrivateUsage]  # calling the private _replace_block wrapper to exercise the public delegation contract
        target=target, block=block, begin="token-report-begin", end="token-report-end"
    )


def _run_timing(target: Path, block: str) -> None:
    timing._replace_block(target=target, block=block)  # pyright: ignore[reportPrivateUsage]  # calling the private _replace_block wrapper to exercise the public delegation contract


# Each caller's private _replace_block wrapper, the diagnostic label it passes,
# and its marker pair. The table cases below use {B}/{E} placeholders that are
# rendered with each caller's marker comment so the same input shape runs through
# both public caller paths.
CALLERS: dict[str, tuple[object, str, str, str]] = {
    "tokens": (_run_tokens, "token report", "token-report-begin", "token-report-end"),
    "timing": (_run_timing, "timing report", "timing-report-begin", "timing-report-end"),
}


def _render(tpl: str, begin: str, end: str) -> str:
    return tpl.replace("{B}", f"<!-- {begin} -->").replace("{E}", f"<!-- {end} -->")


def _expected_warning(kind: str, label: str, begin: str, end: str, target: Path) -> str:
    if kind == "begin":
        return (
            f"{label}: warning: {target} has lone <!-- {begin} --> marker; "
            "truncating from marker and rewriting block"
        )
    if kind == "end":
        return (
            f"{label}: warning: {target} has lone <!-- {end} --> marker; "
            "dropping head through marker and rewriting block"
        )
    msg = f"unknown warning kind: {kind}"
    raise AssertionError(msg)


CASES = [
    pytest.param(
        "header\n{B}\nold\n{E}\nfooter\n",
        "NEW\n",
        "header\nNEW\nfooter\n",
        "",
        id="valid-pair",
    ),
    pytest.param(
        "just prose\nhere\n",
        "NEW\n",
        "just prose\nhere\n\nNEW\n",
        "",
        id="no-markers",
    ),
    pytest.param(
        "header\n{B}\nold\nfooter\n",
        "NEW\n",
        "header\nNEW\n",
        "begin",
        id="lone-begin",
    ),
    pytest.param(
        "header\nold\n{E}\nfooter\n",
        "NEW\n",
        "footer\nNEW\n",
        "end",
        id="lone-end",
    ),
    pytest.param(
        "header\n{E}\nmiddle\n{B}\nfooter\n",
        "NEW\n",
        "header\n{E}\nmiddle\n{B}\nfooter\n\nNEW\n",
        "",
        id="end-before-begin",
    ),
    pytest.param(
        "header\n{B}\nold1\n{E}\nmid\n{B}\nold2\n{E}\nfooter\n",
        "NEW\n",
        "header\nNEW\nmid\n{B}\nold2\n{E}\nfooter\n",
        "",
        id="multiple-pairs",
    ),
    pytest.param(
        "",
        "NEW\n",
        "NEW\n",
        "",
        id="empty-file",
    ),
    pytest.param(
        "header\n{B}\nold\n{E}\nfooter",
        "NEW\n",
        "header\nNEW\nfooter",
        "",
        id="missing-final-newline",
    ),
    pytest.param(
        "header\r\n{B}\r\nold\r\n{E}\r\nfooter\r\n",
        "NEW\n",
        # read_text opens in universal-newline mode, so CRLF is normalized to LF
        # on read exactly as the pre-refactor callers did; the block is inserted
        # against the LF-normalized text.
        "header\nNEW\nfooter\n",
        "",
        id="crlf-input",
    ),
]


@pytest.mark.parametrize("caller_id", list(CALLERS))
@pytest.mark.parametrize(("before_tpl", "block", "expected_tpl", "warning_kind"), CASES)
def test_replace_block_runs_same_table_through_both_callers(
    tmp_path: Path,
    caller_id: str,
    before_tpl: str,
    block: str,
    expected_tpl: str,
    warning_kind: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_fn, label, begin, end = CALLERS[caller_id]
    target = tmp_path / "body.md"
    _ = target.write_text(_render(before_tpl, begin, end), encoding="utf-8")

    run_fn(target, block)  # type: ignore[operator]  # run_fn is an object-typed callable from the CALLERS table

    assert target.read_text(encoding="utf-8") == _render(expected_tpl, begin, end)
    captured = capsys.readouterr()
    if warning_kind:
        assert captured.err.strip() == _expected_warning(warning_kind, label, begin, end, target)
    else:
        assert captured.err == ""


def test_block_markers_reject_empty_and_equal() -> None:
    with pytest.raises(ValueError, match="block markers must be non-empty"):
        _ = markdown_block.BlockMarkers(begin="", end="end")
    with pytest.raises(ValueError, match="block markers must be non-empty"):
        _ = markdown_block.BlockMarkers(begin="begin", end="")
    with pytest.raises(ValueError, match="block markers must be distinct"):
        _ = markdown_block.BlockMarkers(begin="same", end="same")


def test_validation_runs_before_target_is_read(tmp_path: Path) -> None:
    # Constructing BlockMarkers with invalid markers raises without touching the
    # filesystem, so replace_markdown_block can never reach a target read.
    target = tmp_path / "absent.md"
    assert not target.exists()
    with pytest.raises(ValueError, match="block markers must be non-empty"):
        _ = markdown_block.BlockMarkers(begin="", end="end")


def test_replace_block_preserves_existing_file_mode(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    _ = target.write_text(
        "<!-- token-report-begin -->\nold\n<!-- token-report-end -->\n", encoding="utf-8"
    )
    target.chmod(0o600)
    _run_tokens(target, "NEW\n")
    assert target.read_text(encoding="utf-8") == "NEW\n"
    assert (target.stat().st_mode & 0o777) == 0o600


def test_replace_block_direct_helper_warn_callback(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    _ = target.write_text(
        "<!-- timing-report-begin -->\nold\n<!-- timing-report-end -->\n", encoding="utf-8"
    )
    warnings: list[str] = []
    markdown_block.replace_markdown_block(
        target=target,
        block="NEW\n",
        markers=markdown_block.BlockMarkers(begin="timing-report-begin", end="timing-report-end"),
        label="timing report",
        warn=warnings.append,
    )
    assert target.read_text(encoding="utf-8") == "NEW\n"
    assert warnings == []


@pytest.mark.skipif(getattr(os, "geteuid", lambda: 0)() == 0, reason="root bypasses file permissions")
def test_replace_block_leaves_original_intact_on_write_failure(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    original = "header\n<!-- token-report-begin -->\nold\n<!-- token-report-end -->\nfooter\n"
    _ = target.write_text(original, encoding="utf-8")
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(PermissionError):
            _run_tokens(target, "NEW\n")
        assert target.read_text(encoding="utf-8") == original
        assert not (tmp_path / "body.md.tmp").exists()
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.skipif(getattr(os, "geteuid", lambda: 0)() == 0, reason="root bypasses file permissions")
def test_replace_block_unreadable_target_propagates_and_keeps_file(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    original = "header\n<!-- token-report-begin -->\nold\n<!-- token-report-end -->\nfooter\n"
    _ = target.write_text(original, encoding="utf-8")
    target.chmod(0o000)
    try:
        with pytest.raises(PermissionError):
            _run_tokens(target, "NEW\n")
    finally:
        target.chmod(0o600)
    # The helper must propagate the read failure before any write, so the
    # original bytes survive unchanged once read permission is restored.
    assert target.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("caller_id", list(CALLERS))
def test_callers_delegate_without_local_marker_or_temp_logic(
    tmp_path: Path, caller_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Neither tokens._replace_block nor timing._replace_block may retain the
    # marker-index or temporary-replace logic: each wrapper must only forward to
    # the shared helper. Install a spy that records the call and writes nothing;
    # the target must stay untouched and no temp file may appear.
    target = tmp_path / "body.md"
    _ = target.write_text("unchanged\n", encoding="utf-8")
    run_fn, _label, begin, end = CALLERS[caller_id]
    recorded: list[markdown_block.BlockMarkers] = []

    def _spy(**kwargs: object) -> None:
        recorded.append(kwargs["markers"])  # type: ignore[index]  # kwargs is object-typed in the spy signature

    monkeypatch.setattr(markdown_block, "replace_markdown_block", _spy)
    run_fn(target, "NEW\n")  # type: ignore[operator]  # run_fn is an object-typed callable from the CALLERS table
    assert len(recorded) == 1
    assert recorded[0] == markdown_block.BlockMarkers(begin=begin, end=end)
    assert target.read_text(encoding="utf-8") == "unchanged\n"
    assert not (tmp_path / "body.md.tmp").exists()


def test_callers_drop_inlined_state_machine() -> None:
    # Ratchet: the marker-index state machine and the bare temp-write/replace
    # must live only in the shared helper, never in the two caller modules.
    assert tokens.__file__ is not None
    assert timing.__file__ is not None
    for source_path in (Path(tokens.__file__), Path(timing.__file__)):
        source = source_path.read_text(encoding="utf-8")
        assert "begin_idx" not in source, f"caller {source_path} retained marker-index logic"
        assert "splitlines(keepends=True)" not in source, (
            f"caller {source_path} retained the block state machine"
        )
