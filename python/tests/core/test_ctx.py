from __future__ import annotations

from typing import TYPE_CHECKING

from larch.core import config
from larch.core.ctx import Ctx

if TYPE_CHECKING:
    import pytest


def test_ctx_defaults_empty_env() -> None:
    ctx = Ctx.from_mapping({})
    assert ctx.design_tmpdir == ""
    assert ctx.implement_tmpdir == ""
    assert ctx.tmpdir == ""
    assert ctx.str_value(key="MISSING", default="fallback") == "fallback"


def test_bool_value_parsing() -> None:
    ctx = Ctx.from_mapping({"A": "1", "B": "true", "C": "yes", "D": "on", "E": "", "F": "nope"})
    assert ctx.bool_value(key="A") is True
    assert ctx.bool_value(key="B") is True
    assert ctx.bool_value(key="C") is True
    assert ctx.bool_value(key="D") is True
    assert ctx.bool_value(key="E", default=True) is False
    assert ctx.bool_value(key="F", default=True) is True
    assert ctx.bool_value(key="MISSING", default=True) is True


def test_numeric_invalid_values_use_defaults() -> None:
    ctx = Ctx.from_mapping({"I": "abc", "F": "abc", "I2": "7", "F2": "1.5"})
    assert ctx.int_value(key="I", default=2) == 2
    assert ctx.float_value(key="F", default=2.5) == 2.5
    assert ctx.int_value(key="I2") == 7
    assert ctx.float_value(key="F2") == 1.5


def test_contains_and_str_value_preserve_empty_membership() -> None:
    ctx = Ctx.from_mapping({"EMPTY": ""})
    assert ctx.contains("EMPTY") is True
    assert ctx.contains("MISSING") is False
    assert ctx.str_value(key="EMPTY", default="fallback") == ""


def test_config_constant_backed_fields_and_empty_presence() -> None:
    ctx = Ctx.from_mapping({
        config.ENV_DESIGN_TMPDIR: "/tmp/design",
        config.ENV_CLAUDE_PLUGIN_ROOT: "/repo",
        config.ENV_REPO: "owner/repo",
        config.ENV_CODEX_PRESENT: "",
        config.ENV_CURSOR_PRESENT: "false",
    })
    assert ctx.design_tmpdir == "/tmp/design"
    assert ctx.claude_plugin_root == "/repo"
    assert ctx.repo == "owner/repo"
    assert ctx.codex_present == ""
    assert ctx.cursor_present == "false"


def test_subprocess_env_override_and_removal() -> None:
    ctx = Ctx.from_mapping({"A": "1", "B": "2"})
    assert ctx.subprocess_env(overrides={"C": "3"}, remove=("B",)) == {"A": "1", "C": "3"}


def test_snapshot_immutable_after_os_environ_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, "/before")
    ctx = Ctx.from_env()
    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, "/after")
    assert ctx.design_tmpdir == "/before"


def test_from_mapping_copies_input_mapping() -> None:
    env = {config.ENV_DESIGN_TMPDIR: "/before"}
    ctx = Ctx.from_mapping(env)
    env[config.ENV_DESIGN_TMPDIR] = "/after"
    assert ctx.design_tmpdir == "/before"
    assert ctx.raw_env[config.ENV_DESIGN_TMPDIR] == "/before"


def test_repr_does_not_expose_secret_values() -> None:
    ctx = Ctx.from_mapping({"OPENAI_API_KEY": "sk-secret-value"})
    assert "sk-secret-value" not in repr(ctx)


def test_no_quiet_typed_fields() -> None:
    ctx = Ctx.from_mapping({})
    assert not hasattr(ctx, "quiet_disable")
    assert not hasattr(ctx, "quiet_active")
    assert not hasattr(ctx, "quiet_pid")
