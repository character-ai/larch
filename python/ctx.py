"""Read-once typed environment snapshots for Python CLI boundaries."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import config


@dataclass(frozen=True)
class Ctx:
    """Frozen snapshot of process configuration at one CLI ownership boundary."""

    raw_env: Mapping[str, str] = field(repr=False)
    design_tmpdir: str = ""
    implement_tmpdir: str = ""
    claude_plugin_root: str = ""
    repo: str = ""
    issue_number: str = ""
    session_id: str = ""
    session_tmpdir: str = ""
    larch_run_id: str = ""
    summary_outcome: str = ""
    final_summary_path: str = ""
    claude_pid: str = ""
    codex_binary_found: str = ""
    cursor_binary_found: str = ""
    codex_present: str = ""
    cursor_present: str = ""
    tmpdir: str = ""
    home: str = ""
    path: str = ""
    user: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Ctx:
        return cls.from_mapping(os.environ if env is None else env)

    @classmethod
    def from_mapping(cls, env: Mapping[str, str]) -> Ctx:
        snapshot = dict(env)
        return cls(
            raw_env=MappingProxyType(snapshot),
            design_tmpdir=snapshot.get(config.ENV_DESIGN_TMPDIR, ""),
            implement_tmpdir=snapshot.get(config.ENV_IMPLEMENT_TMPDIR, ""),
            claude_plugin_root=snapshot.get(config.ENV_CLAUDE_PLUGIN_ROOT, ""),
            repo=snapshot.get(config.ENV_REPO, ""),
            issue_number=snapshot.get(config.ENV_ISSUE_NUMBER, ""),
            session_id=snapshot.get(config.ENV_SESSION_ID, ""),
            session_tmpdir=snapshot.get(config.ENV_SESSION_TMPDIR, ""),
            larch_run_id=snapshot.get(config.ENV_LARCH_RUN_ID, ""),
            summary_outcome=snapshot.get(config.ENV_SUMMARY_OUTCOME, ""),
            final_summary_path=snapshot.get(config.ENV_FINAL_SUMMARY_PATH, ""),
            claude_pid=snapshot.get(config.ENV_CLAUDE_PID, ""),
            codex_binary_found=snapshot.get(config.ENV_CODEX_BINARY_FOUND, ""),
            cursor_binary_found=snapshot.get(config.ENV_CURSOR_BINARY_FOUND, ""),
            codex_present=snapshot.get(config.ENV_CODEX_PRESENT, ""),
            cursor_present=snapshot.get(config.ENV_CURSOR_PRESENT, ""),
            tmpdir=snapshot.get(config.ENV_TMPDIR, ""),
            home=snapshot.get(config.ENV_HOME, ""),
            path=snapshot.get(config.ENV_PATH, ""),
            user=snapshot.get(config.ENV_USER, ""),
        )

    def contains(self, key: str) -> bool:
        return key in self.raw_env

    def str_value(self, *, key: str, default: str = "") -> str:
        return self.raw_env.get(key, default)

    def bool_value(self, *, key: str, default: bool = False) -> bool:
        if key not in self.raw_env:
            return default
        value = self.raw_env.get(key, "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"", "0", "false", "no", "off"}:
            return False
        return default

    def int_value(self, *, key: str, default: int | None = None) -> int | None:
        try:
            return int(self.raw_env[key])
        except (KeyError, TypeError, ValueError):
            return default

    def float_value(self, *, key: str, default: float | None = None) -> float | None:
        try:
            return float(self.raw_env[key])
        except (KeyError, TypeError, ValueError):
            return default

    def subprocess_env(
        self,
        *, overrides: Mapping[str, str] | None = None,
        remove: Iterable[str] = (),
    ) -> dict[str, str]:
        env = dict(self.raw_env)
        for key in remove:
            _ = env.pop(key, None)
        if overrides:
            env.update(overrides)
        return env
