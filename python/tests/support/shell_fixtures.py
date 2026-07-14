"""Hermetic fixtures for tests that invoke supported external shell tools."""

from __future__ import annotations

import json
import os
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from tests.support.repo_contract import repo_root

ExternalTool = Literal["gh", "codex", "cursor", "claude"]
PluginSource = str | Path

_SUPPORTED_TOOL_NAMES: tuple[ExternalTool, ...] = ("gh", "codex", "cursor", "claude")
_SUPPORTED_TOOLS: frozenset[str] = frozenset(_SUPPORTED_TOOL_NAMES)
_DEFAULT_FAILURE_CODE = 127


@dataclass(frozen=True)
class FakeCommand:
    """Configured response returned by a fake external command."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


@dataclass(frozen=True)
class Invocation:
    """One exact argv vector received by a fake external command."""

    tool: ExternalTool
    argv: tuple[str, ...]


@dataclass(frozen=True)
class FakeBinDir:
    """A directory of fail-closed external command fakes and their invocation log."""

    path: Path
    _config_dir: Path
    _log_path: Path

    def configure(self, tool: ExternalTool, response: FakeCommand | None = None) -> None:
        """Configure *tool* to return *response* on later invocations."""
        _validate_tool(tool)
        command = response or FakeCommand()
        payload: dict[str, str | int] = {
            "stdout": command.stdout,
            "stderr": command.stderr,
            "returncode": command.returncode,
        }
        config_path = self._config_dir / f"{tool}.json"
        _ = config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def invocations(self) -> list[Invocation]:
        """Return the exact ordered external command invocations."""
        if not self._log_path.exists():
            return []
        records: list[Invocation] = []
        for line in self._log_path.read_text(encoding="utf-8").splitlines():
            raw: object = json.loads(line)
            if not isinstance(raw, dict):
                msg = "invalid fake-command invocation record"
                raise TypeError(msg)
            record = cast("Mapping[str, object]", raw)
            tool = _parse_tool(record.get("tool"))
            argv_value = record.get("argv")
            if not isinstance(argv_value, list):
                msg = "invalid fake-command argv in invocation record"
                raise TypeError(msg)
            argv: list[str] = []
            argv_values = cast("list[object]", argv_value)
            for argument in argv_values:
                if not isinstance(argument, str):
                    msg = "invalid fake-command argv in invocation record"
                    raise TypeError(msg)
                argv.append(argument)
            records.append(Invocation(tool=tool, argv=tuple(argv)))
        return records


FakeBinDirFactory = Callable[[], FakeBinDir]
PluginTreeFactory = Callable[[Sequence[PluginSource]], Path]
SubprocessEnvFactory = Callable[[FakeBinDir, Mapping[str, str] | None], dict[str, str]]


def _validate_tool(tool: str) -> None:
    if tool not in _SUPPORTED_TOOLS:
        msg = f"unsupported fake executable: {tool!r}"
        raise ValueError(msg)


def _parse_tool(value: object) -> ExternalTool:
    if not isinstance(value, str) or value not in _SUPPORTED_TOOLS:
        msg = "invalid fake-command tool in invocation record"
        raise ValueError(msg)
    return cast("ExternalTool", value)


def _default_response(tool: ExternalTool) -> FakeCommand:
    return FakeCommand(
        stderr=f"fake {tool} is not configured; refusing to run a live executable\\n",
        returncode=_DEFAULT_FAILURE_CODE,
    )


def _fake_script(tool: ExternalTool, config_path: Path, log_path: Path) -> str:
    config_literal = json.dumps(str(config_path))
    log_literal = json.dumps(str(log_path))
    tool_literal = json.dumps(tool)
    return f"""#!{sys.executable}
import json
import sys
from pathlib import Path

config = json.loads(Path({config_literal}).read_text(encoding=\"utf-8\"))
record = {{\"tool\": {tool_literal}, \"argv\": sys.argv[1:]}}
with Path({log_literal}).open(\"a\", encoding=\"utf-8\") as stream:
    stream.write(json.dumps(record, ensure_ascii=False) + \"\\n\")
sys.stdout.write(config[\"stdout\"])
sys.stderr.write(config[\"stderr\"])
raise SystemExit(config[\"returncode\"])
"""


def make_fake_bin_dir(tmp_path: Path) -> FakeBinDir:
    """Create fakes for every supported external tool under *tmp_path*.

    All tools fail closed until configured. The generated scripts use structured
    JSONL records so argument boundaries survive spaces, empty arguments, and
    embedded newlines.
    """
    bin_dir = tmp_path / "fake-bin"
    config_dir = bin_dir / "config"
    config_dir.mkdir(parents=True)
    log_path = bin_dir / "invocations.jsonl"
    fake_bin = FakeBinDir(path=bin_dir, _config_dir=config_dir, _log_path=log_path)
    for tool in _SUPPORTED_TOOL_NAMES:
        fake_bin.configure(tool, _default_response(tool))
        script_path = bin_dir / tool
        _ = script_path.write_text(_fake_script(tool, config_dir / f"{tool}.json", log_path), encoding="utf-8")
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake_bin


def make_subprocess_env(
    fake_bin: FakeBinDir,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a fresh subprocess environment with *fake_bin* first on ``PATH``."""
    environment = dict(os.environ)
    system_path = environment.get("PATH", "")
    requested_path = ""
    if overrides is not None:
        environment.update(overrides)
        requested_path = overrides.get("PATH", "")
    path_parts = [str(fake_bin.path), requested_path, system_path]
    environment["PATH"] = os.pathsep.join(part for part in path_parts if part)
    return environment


def _checkout_source(source: PluginSource) -> tuple[Path, Path]:
    relative = Path(source)
    if relative.is_absolute() or ".." in relative.parts:
        msg = f"plugin source must be a checkout-relative path: {source!r}"
        raise ValueError(msg)
    checkout_root = repo_root()
    resolved = (checkout_root / relative).resolve()
    try:
        _ = resolved.relative_to(checkout_root)
    except ValueError as exc:
        msg = f"plugin source escapes checkout root: {source!r}"
        raise ValueError(msg) from exc
    if not resolved.exists():
        msg = f"checkout source does not exist: {source!r}"
        raise FileNotFoundError(msg)
    return relative, resolved


def make_fake_plugin_tree(tmp_path: Path, sources: Sequence[PluginSource]) -> Path:
    """Build a minimal plugin tree that symlinks the requested checkout sources."""
    plugin_root = tmp_path / "plugin"
    _ = plugin_root.mkdir(parents=True)
    for source in sources:
        relative, resolved = _checkout_source(source)
        destination = plugin_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = destination.symlink_to(resolved, target_is_directory=resolved.is_dir())
    return plugin_root
