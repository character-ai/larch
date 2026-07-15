"""Unit tests for /status vendor model-pin resolution (no live vendor calls)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from larch.agents import _model_pins
from larch.core import config
from larch.core.proc import CommandResult


class _ScriptedRunner:
    def __init__(self, result: CommandResult) -> None:
        self._result = result
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        self.calls.append(tuple(argv))
        return self._result


def _models_stdout(*ids: str) -> str:
    body = "\n".join(f"{mid} - Display {mid}" for mid in ids)
    return f"Available models\n\n{body}\n"


def test_parse_cursor_model_list_known_grammar() -> None:
    parsed = _model_pins.parse_cursor_model_list(
        _models_stdout("composer-2.5", "cursor-grok-4.5-high", "auto")
    )
    assert parsed == frozenset({"composer-2.5", "cursor-grok-4.5-high", "auto"})


def test_parse_cursor_model_list_fail_closed_on_junk() -> None:
    assert _model_pins.parse_cursor_model_list("Available models\nnot a model line\n") is None
    assert _model_pins.parse_cursor_model_list("Available models\n\n") is None
    assert _model_pins.parse_cursor_model_list("") is None


def test_resolve_cursor_model_pins_known_id_pass() -> None:
    pins = _model_pins.cursor_pinned_models()
    runner = _ScriptedRunner(
        CommandResult(
            config.CURSOR_MODEL_LIST_ARGV,
            0,
            _models_stdout(*(pin.model_id for pin in pins), "extra-ok"),
            "",
            0.01,
        )
    )
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_OK
    assert result.detail == ""
    assert runner.calls == [config.CURSOR_MODEL_LIST_ARGV]


def test_resolve_cursor_model_pins_unknown_id_fail() -> None:
    runner = _ScriptedRunner(
        CommandResult(config.CURSOR_MODEL_LIST_ARGV, 0, _models_stdout("other-only"), "", 0.01)
    )
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_UNKNOWN_ID
    assert "CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY=" in result.detail
    for pin in _model_pins.cursor_pinned_models():
        assert f"{pin.constant_name}={pin.model_id}" in result.detail


def test_resolve_cursor_model_pins_list_command_failure() -> None:
    runner = _ScriptedRunner(
        CommandResult(config.CURSOR_MODEL_LIST_ARGV, 2, "", "list blew up\n", 0.01)
    )
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_LIST_FAILED
    assert result.detail == "cursor agent models exited 2: list blew up"


def test_resolve_cursor_model_pins_unparseable() -> None:
    runner = _ScriptedRunner(
        CommandResult(config.CURSOR_MODEL_LIST_ARGV, 0, "totally broken\n", "", 0.01)
    )
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_UNPARSEABLE


def test_resolve_cursor_model_pins_skipped_when_vendor_not_ok() -> None:
    runner = _ScriptedRunner(CommandResult(config.CURSOR_MODEL_LIST_ARGV, 0, "", "", 0.01))
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="binary-missing")
    assert result.status == config.MODEL_PINS_STATUS_SKIPPED
    assert runner.calls == []


def test_resolve_codex_model_pins_unverifiable_when_ok() -> None:
    result = _model_pins.resolve_codex_model_pins(vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_UNVERIFIABLE
    assert "no model-list surface" in result.detail
    assert "CODEX_DEFAULT_MODEL=" in result.detail


def test_resolve_model_pins_combined_report() -> None:
    pins = _model_pins.cursor_pinned_models()
    runner = _ScriptedRunner(
        CommandResult(
            config.CURSOR_MODEL_LIST_ARGV,
            0,
            _models_stdout(*(pin.model_id for pin in pins)),
            "",
            0.01,
        )
    )
    report = _model_pins.resolve_model_pins(runner=runner, codex_state="ok", cursor_state="ok")
    assert report.cursor.status == config.MODEL_PINS_STATUS_OK
    assert report.codex.status == config.MODEL_PINS_STATUS_UNVERIFIABLE
