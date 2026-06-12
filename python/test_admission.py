# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false
from __future__ import annotations

import admission


def test_single_line_flattens_newlines() -> None:
    assert admission._single_line(" a\n b\r\n c ") == "a b c"  # pyright: ignore[reportPrivateUsage]


def test_normal_issue_rejects_zero() -> None:
    assert admission._normal_issue("0") is None  # pyright: ignore[reportPrivateUsage]
    assert admission._normal_issue("042") == 42  # pyright: ignore[reportPrivateUsage]


def test_prefix_helpers() -> None:
    assert admission._has_managed_prefix("[IMPLEMENTING] Thing")  # pyright: ignore[reportPrivateUsage]
    assert admission._has_designed_prefix("[DESIGNED] Thing")  # pyright: ignore[reportPrivateUsage]
    assert admission._has_report_prefix("[Audit Report] Thing")  # pyright: ignore[reportPrivateUsage]


def test_preflight_unknown_arg_exits_3(capsys) -> None:
    assert admission.preflight_main(["--bogus"]) == 3
    assert "Unknown option" in capsys.readouterr().err
