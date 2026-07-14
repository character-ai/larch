# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for inactive vendor descriptors, argv builders, and model extraction."""

from __future__ import annotations

import ast
import os
from collections.abc import Iterable
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from larch.agents import _vendor
from larch.agents._run_external import _codex_auth_args, _trust_config_arg
from larch.agents._vendor import (
    CLAUDE_DESCRIPTOR,
    CODEX_DESCRIPTOR,
    CURSOR_DESCRIPTOR,
    REQUIRED_CAPABILITIES,
    VENDOR_DESCRIPTORS,
    VendorDescriptor,
    VendorFamilyHooks,
    VendorLaunchRequest,
    VendorParsedResult,
    VendorProcessResult,
    build_claude_argv,
    build_codex_argv,
    build_cursor_argv,
    build_vendor_registry,
    extract_model_from_argv,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / "python" / "larch" / "agents"
VENDOR_PATH = AGENTS_DIR / "_vendor.py"

_LOWER_LEVEL_ALLOWLIST = frozenset(
    {
        "larch.agents._types",
        "larch.agents._launch_failure",
        "larch.agents._failure_diag",
        "larch.agents._run_external",
        "larch.agents._auth",
    }
)

_FORBIDDEN_MODULES = frozenset(
    {
        "larch.agents.agents",
        "larch.agents._claude_runner",
        "larch.agents._drafter",
        "larch.agents._review_launcher",
        "larch.agents._ci_launcher",
        "larch.agents.agent_voters",
        "larch.agents.agent_waterfall",
        "larch.agents.collect_results",
        "larch.agents.review_dispatch",
    }
)

_PRODUCTION_LAUNCHERS = (
    "agents.py",
    "_claude_runner.py",
    "_drafter.py",
    "_review_launcher.py",
    "_ci_launcher.py",
    "agent_voters.py",
    "agent_waterfall.py",
    "collect_results.py",
    "review_dispatch.py",
)


def _agent_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("larch.agents"):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("larch.agents"):
                    found.add(alias.name)
    return found


def _transitive_agent_imports(roots: Iterable[str]) -> set[str]:
    """BFS over local larch.agents imports reachable from ``roots``."""
    seen: set[str] = set()
    queue = list(roots)
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        seen.add(module)
        if not module.startswith("larch.agents."):
            continue
        short = module.removeprefix("larch.agents.")
        path = AGENTS_DIR / f"{short}.py"
        if not path.is_file():
            continue
        for child in _agent_imports(path):
            if child not in seen:
                queue.append(child)
    return seen


class TestDescriptorRegistry:
    def test_keys_are_unique_and_complete(self) -> None:
        assert set(VENDOR_DESCRIPTORS) == {"codex", "cursor", "claude"}
        assert len(VENDOR_DESCRIPTORS) == 3

    def test_every_vendor_exposes_required_capabilities(self) -> None:
        for key, descriptor in VENDOR_DESCRIPTORS.items():
            assert descriptor.capabilities >= REQUIRED_CAPABILITIES, key

    def test_argv_profiles_registered(self) -> None:
        assert CODEX_DESCRIPTOR.argv_profiles == frozenset({"read-only", "workspace-write"})
        assert CURSOR_DESCRIPTOR.argv_profiles == frozenset(
            {"review-ask", "ci-write", "implement-write", "negotiation-write"}
        )
        assert CLAUDE_DESCRIPTOR.argv_profiles == frozenset(
            {
                "review-subprocess",
                "review-subprocess-base",
                "drafter-read",
                "workspace-write",
            }
        )

    def test_dataclasses_are_frozen(self) -> None:
        with pytest.raises(FrozenInstanceError):
            CODEX_DESCRIPTOR.key = "other"  # type: ignore[misc]
        request = VendorLaunchRequest(workdir="/w", output="/o", prompt="p")
        with pytest.raises(FrozenInstanceError):
            request.prompt = "x"  # type: ignore[misc]
        result = VendorProcessResult(exit_code=0)
        with pytest.raises(FrozenInstanceError):
            result.exit_code = 1  # type: ignore[misc]
        parsed = VendorParsedResult(status="ok")
        with pytest.raises(FrozenInstanceError):
            parsed.status = "bad"  # type: ignore[misc]
        hooks = VendorFamilyHooks()
        with pytest.raises(FrozenInstanceError):
            hooks.execute = None  # type: ignore[misc]

    def test_duplicate_key_fails_loudly(self) -> None:
        with pytest.raises(ValueError, match="duplicate vendor key"):
            build_vendor_registry((CODEX_DESCRIPTOR, CODEX_DESCRIPTOR))

    def test_missing_capability_fails_loudly(self) -> None:
        bad = VendorDescriptor(
            key="bad",
            capabilities=frozenset({"argv"}),
            argv_profiles=frozenset({"x"}),
            build_argv=lambda _profile, _request: [],
            extract_model=extract_model_from_argv,
        )
        with pytest.raises(ValueError, match="missing capabilities"):
            build_vendor_registry((bad,))


class TestImportIsolation:
    def test_vendor_direct_imports_are_allowlisted(self) -> None:
        imports = _agent_imports(VENDOR_PATH)
        assert imports <= _LOWER_LEVEL_ALLOWLIST

    def test_vendor_transitive_graph_avoids_launcher_families(self) -> None:
        reachable = _transitive_agent_imports(_agent_imports(VENDOR_PATH))
        for module in _FORBIDDEN_MODULES:
            assert module not in reachable

    def test_production_launchers_do_not_import_vendor(self) -> None:
        for name in _PRODUCTION_LAUNCHERS:
            imports = _agent_imports(AGENTS_DIR / name)
            assert "larch.agents._vendor" not in imports, name


class TestCodexArgv:
    def _request(
        self,
        *,
        add_dirs: tuple[str, ...] = (),
        model_args: tuple[str, ...] = (),
        prompt_via_stdin: bool = False,
        workdir: str = "/repo",
        output: str = "/tmp/out.txt",
        prompt: str = "do the thing",
    ) -> VendorLaunchRequest:
        return VendorLaunchRequest(
            workdir=workdir,
            output=output,
            prompt=prompt,
            add_dirs=add_dirs,
            model_args=model_args,
            prompt_via_stdin=prompt_via_stdin,
            timing_task_kind="codex-review",
        )

    def test_read_only_zero_add_dirs_argv_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = self._request()
        argv = build_codex_argv("read-only", req)
        assert argv[:4] == ["codex", "exec", "--sandbox", "read-only"]
        assert argv == [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "-C",
            "/repo",
            "-c",
            _trust_config_arg("/repo"),
            "--output-last-message",
            "/tmp/out.txt",
            "--json",
            "--",
            "do the thing",
        ]

    def test_workspace_write_one_add_dir_with_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        model_args = ("-m", "gpt-test", "-c", 'model_reasoning_effort="high"')
        req = self._request(add_dirs=("/repo",), model_args=model_args)
        argv = build_codex_argv("workspace-write", req)
        assert argv[:4] == ["codex", "exec", "--sandbox", "workspace-write"]
        assert argv == [
            "codex",
            "exec",
            "--sandbox",
            "workspace-write",
            "-C",
            "/repo",
            "--add-dir",
            "/repo",
            "-m",
            "gpt-test",
            "-c",
            'model_reasoning_effort="high"',
            "-c",
            _trust_config_arg("/repo"),
            "--output-last-message",
            "/tmp/out.txt",
            "--json",
            "--",
            "do the thing",
        ]

    def test_multiple_add_dirs_preserve_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = self._request(add_dirs=("/tmp/session", "/repo", "/extra"))
        argv = build_codex_argv("workspace-write", req)
        assert argv[6:12] == [
            "--add-dir",
            "/tmp/session",
            "--add-dir",
            "/repo",
            "--add-dir",
            "/extra",
        ]

    def test_stdin_prompt_form(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = self._request(prompt_via_stdin=True)
        argv = build_codex_argv("workspace-write", req)
        assert argv[-2:] == ["--", "-"]

    def test_populated_openai_api_key_auth_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        req = self._request()
        argv = build_codex_argv("read-only", req)
        auth = _codex_auth_args()
        assert auth
        trust_idx = argv.index("-c")
        # First -c is trust; auth -c pairs follow immediately.
        after_trust = argv[trust_idx + 2 :]
        for token in auth:
            assert token in after_trust
        assert after_trust[: len(auth)] == auth

    def test_empty_openai_api_key_no_auth_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = self._request()
        argv = build_codex_argv("read-only", req)
        assert 'model_provider="openai-larch-env"' not in argv
        assert _codex_auth_args() == []

    def test_descriptor_dispatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = self._request()
        assert CODEX_DESCRIPTOR.build_argv("read-only", req) == build_codex_argv("read-only", req)

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown Codex"):
            build_codex_argv("nope", self._request())


class TestCursorArgv:
    def _request(self, *, model_args: tuple[str, ...] = ("--model", "cursor-model")) -> VendorLaunchRequest:
        return VendorLaunchRequest(
            workdir="/ws",
            output="/tmp/out",
            prompt="review please",
            model_args=model_args,
            timing_task_kind="cursor-review",
        )

    def test_review_ask(self) -> None:
        argv = build_cursor_argv("review-ask", self._request())
        assert argv[:3] == ["cursor", "agent", "-p"]
        assert "--force" not in argv
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--trust",
            "--mode",
            "ask",
            "--output-format",
            "json",
            "--model",
            "cursor-model",
            "--workspace",
            "/ws",
            "review please",
        ]

    def test_ci_write_model_before_output_format(self) -> None:
        argv = build_cursor_argv("ci-write", self._request())
        assert argv[:3] == ["cursor", "agent", "-p"]
        assert "--mode" not in argv
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            "--model",
            "cursor-model",
            "--output-format",
            "json",
            "--workspace",
            "/ws",
            "review please",
        ]

    def test_implement_write_model_after_output_format(self) -> None:
        argv = build_cursor_argv("implement-write", self._request())
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            "--output-format",
            "json",
            "--model",
            "cursor-model",
            "--workspace",
            "/ws",
            "review please",
        ]

    def test_negotiation_write_omits_output_format(self) -> None:
        argv = build_cursor_argv("negotiation-write", self._request())
        assert "--output-format" not in argv
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            "--model",
            "cursor-model",
            "--workspace",
            "/ws",
            "review please",
        ]

    def test_all_profiles_via_descriptor(self) -> None:
        req = self._request()
        for profile in sorted(CURSOR_DESCRIPTOR.argv_profiles):
            argv = CURSOR_DESCRIPTOR.build_argv(profile, req)
            assert argv[:3] == ["cursor", "agent", "-p"]
            assert argv[-1] == "review please"

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown Cursor"):
            build_cursor_argv("nope", self._request())


class TestClaudeArgv:
    def _request(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        workdir: str = "/repo",
        read_tools_add_dir: str = "",
    ) -> VendorLaunchRequest:
        return VendorLaunchRequest(
            workdir=workdir,
            output="/tmp/out",
            prompt="prompt on stdin",
            model=model,
            read_tools_add_dir=read_tools_add_dir,
            timing_task_kind="claude-review",
        )

    def test_review_subprocess(self) -> None:
        argv = build_claude_argv(
            "review-subprocess",
            self._request(read_tools_add_dir="/sandbox"),
        )
        assert argv == [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--model",
            "claude-sonnet-4-6",
            "--add-dir",
            "/sandbox",
            "--allowedTools",
            "Read",
            "--permission-mode",
            "plan",
        ]
        assert "prompt on stdin" not in argv  # stdin transport

    def test_review_subprocess_base(self) -> None:
        argv = build_claude_argv("review-subprocess-base", self._request())
        assert argv == [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--model",
            "claude-sonnet-4-6",
        ]
        assert "--add-dir" not in argv
        assert "--allowedTools" not in argv
        assert "--permission-mode" not in argv

    def test_drafter_read_model_before_print(self) -> None:
        argv = build_claude_argv("drafter-read", self._request())
        assert argv == [
            "claude",
            "--model",
            "claude-sonnet-4-6",
            "--print",
            "--output-format",
            "json",
            "--add-dir",
            "/repo",
            "--allowedTools",
            "Read,Glob,Grep,LS",
            "--permission-mode",
            "plan",
        ]

    def test_workspace_write(self) -> None:
        argv = build_claude_argv("workspace-write", self._request())
        assert argv == [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            "claude-sonnet-4-6",
            "--add-dir",
            "/repo",
            "--allowedTools",
            "Read,Edit,Write",
        ]
        assert "--permission-mode" not in argv
        assert "--print" not in argv

    def test_review_subprocess_requires_add_dir(self) -> None:
        with pytest.raises(ValueError, match="read_tools_add_dir"):
            build_claude_argv("review-subprocess", self._request())

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown Claude"):
            build_claude_argv("nope", self._request())


class TestModelExtraction:
    def test_codex_dash_m(self) -> None:
        assert extract_model_from_argv(["codex", "exec", "-m", "gpt-x", "--json"]) == "gpt-x"

    def test_cursor_model(self) -> None:
        assert extract_model_from_argv(["cursor", "agent", "--model", "c-model", "-p"]) == "c-model"

    def test_claude_model(self) -> None:
        assert extract_model_from_argv(["claude", "--print", "--model", "claude-x"]) == "claude-x"

    def test_missing_flag(self) -> None:
        assert extract_model_from_argv(["codex", "exec", "--json"]) == ""

    def test_dangling_model_flag(self) -> None:
        assert extract_model_from_argv(["cursor", "agent", "--model"]) == ""
        assert extract_model_from_argv(["codex", "exec", "-m"]) == ""

    def test_prefers_model_over_dash_m(self) -> None:
        assert extract_model_from_argv(["-m", "a", "--model", "b"]) == "b"

    def test_descriptor_extract_model(self) -> None:
        argv = ["claude", "--model", "m1"]
        assert CLAUDE_DESCRIPTOR.extract_model(argv) == "m1"
        assert CURSOR_DESCRIPTOR.extract_model(["--model", "m2"]) == "m2"
        assert CODEX_DESCRIPTOR.extract_model(["-m", "m3"]) == "m3"


def test_module_exports_inactive_surface() -> None:
    # Lifecycle helpers must not exist yet (piece 2).
    assert not hasattr(_vendor, "run_vendor_launch")
    assert "VENDOR_DESCRIPTORS" in dir(_vendor)
    # Pure argv builders must not mutate environment.
    before = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ.pop("OPENAI_API_KEY", None)
        build_codex_argv(
            "read-only",
            VendorLaunchRequest(workdir="/w", output="/o", prompt="p"),
        )
        assert "OPENAI_API_KEY" not in os.environ
    finally:
        if before is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = before
