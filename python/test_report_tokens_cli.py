from __future__ import annotations

import pytest

import config
import report_tokens_cli


def test_reject_plot_from() -> None:
    with pytest.raises(SystemExit):
        _ = report_tokens_cli.parse_args(["--skill", "design", "--plot-from", "1"])


def test_env_bool_no_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_LARCH_REPORT_TOKENS_NO_ISSUE, "1")
    assert report_tokens_cli.env_flag_enabled(config.ENV_LARCH_REPORT_TOKENS_NO_ISSUE) is True
