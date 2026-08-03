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
    assert not runner.calls


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


def test_debate_pins_join_inventories_and_unknown_names_debate_constant() -> None:
    decls = _model_pins.cursor_pinned_model_declarations()
    assert any(pin.constant_name == "DEBATE_CURSOR_MODEL" for pin in decls)
    assert config.DEBATE_CURSOR_MODEL in {pin.model_id for pin in _model_pins.cursor_pinned_models()}
    assert any(pin.constant_name == "DEBATE_CODEX_MODEL" for pin in _model_pins.codex_pinned_model_declarations())
    # Unique resolution keeps one entry per model id even when debate duplicates implement.
    unique_ids = [pin.model_id for pin in _model_pins.cursor_pinned_models()]
    assert len(unique_ids) == len(set(unique_ids))


def test_missing_debate_cursor_model_reports_named_debate_pin() -> None:
    # Live list has implement HARD pin only; omit debate/TRIVIAL-MODERATE id when distinct,
    # otherwise omit both copies of the shared debate id via an unrelated-only list.
    implement_ids = set(config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY.values())
    live = implement_ids - {config.DEBATE_CURSOR_MODEL}
    if not live:
        live = {"composer-2.5-other"}
    runner = _ScriptedRunner(
        CommandResult(config.CURSOR_MODEL_LIST_ARGV, 0, _models_stdout(*sorted(live)), "", 0.01)
    )
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_UNKNOWN_ID
    assert f"DEBATE_CURSOR_MODEL={config.DEBATE_CURSOR_MODEL}" in result.detail


def test_live_cursor_list_with_debate_pin_passes_unique_resolution() -> None:
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
    result = _model_pins.resolve_cursor_model_pins(runner=runner, vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_OK


def test_debate_codex_pin_in_unverifiable_detail() -> None:
    result = _model_pins.resolve_codex_model_pins(vendor_state="ok")
    assert result.status == config.MODEL_PINS_STATUS_UNVERIFIABLE
    assert f"DEBATE_CODEX_MODEL={config.DEBATE_CODEX_MODEL}" in result.detail
