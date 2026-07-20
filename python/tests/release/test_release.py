"""Regression tests for remaining release-adjacent Python helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from larch.core import verify_main
from larch.core.proc import CommandResult

if TYPE_CHECKING:
    import pytest


def cr(argv: tuple[str, ...], stdout: str = "") -> CommandResult:
    return CommandResult(tuple(argv), 0, stdout, "", 0.01)


def result_runner(stdout: str) -> Callable[..., CommandResult]:
    def run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return cr(tuple(argv), stdout=stdout)

    return run


def test_verify_main_direct_title_and_suffix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Feature title (#42)\n"),
    )
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"
    assert out["COMMIT_HASH"] == "abc123"


def test_verify_main_direct_mismatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Other title\n"),
    )
    assert verify_main.main(["--expected-title", "Feature title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "false"


def test_verify_main_unnumbered_expected_prefix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Feature follow-up\n"),
    )
    assert verify_main.main(["--expected-title", "Feature"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_numbered_expected_exact(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Title (#7)\n"),
    )
    assert verify_main.main(["--expected-title", "Title (#7)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_numbered_expected_suffix_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Feature title (#42)\n"),
    )
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_rejects_mid_string_suffix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 (#42) Feature title\n"),
    )
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "false"


def test_verify_main_rejects_numbered_expected_stripped_prefix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        verify_main.proc,
        "run",
        result_runner("abc123 Title follow-up\n"),
    )
    assert verify_main.main(["--expected-title", "Title (#7)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "false"
