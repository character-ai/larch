# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for forked repo helper utilities."""

from __future__ import annotations

import forked_repo


def test_normalize_github_url_shapes() -> None:
    assert forked_repo.normalize_github_url("git@github.com:Owner/Repo.git") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("https://github.com/Owner/Repo") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("not-a-url") is None


def test_parse_args_requires_owner_repo() -> None:
    try:
        forked_repo.parse_args(["--upstream", "bad", "--fork", "o/r"])
    except forked_repo.SetupError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected SetupError")
