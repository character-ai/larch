# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false
"""Tests for inactive vendor descriptors, argv builders, and launch lifecycle."""

from __future__ import annotations

import ast
import json
import os
from collections.abc import Iterable
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from larch.agents import _vendor
from larch.agents._run_external import _codex_auth_args, _trust_config_arg
from larch.agents._types import _PY_CLI, VendorSessionHandle
from larch.agents._vendor import (
    CAP_HIT_PAYLOAD,
    CLAUDE_DESCRIPTOR,
    CLAUDE_ENVELOPE_EMPTY_RESULT,
    CLAUDE_ENVELOPE_IS_ERROR,
    CLAUDE_ENVELOPE_MALFORMED_JSON,
    CLAUDE_ENVELOPE_MISSING_RESULT,
    CLAUDE_ENVELOPE_NON_OBJECT,
    CLAUDE_ENVELOPE_NON_STRING_RESULT,
    CLAUDE_ENVELOPE_OK,
    CODEX_DESCRIPTOR,
    CURSOR_DESCRIPTOR,
    REQUIRED_CAPABILITIES,
    VENDOR_DESCRIPTORS,
    VendorCapCheckResult,
    VendorDescriptor,
    VendorFamilyHooks,
    VendorLaunchRequest,
    VendorParsedResult,
    VendorProcessResult,
    VendorRetryPolicy,
    build_check_budget_argv,
    build_claude_argv,
    build_codex_argv,
    build_codex_resume_argv,
    build_codex_session_argv,
    build_cursor_argv,
    build_cursor_create_chat_argv,
    build_cursor_resume_argv,
    build_vendor_registry,
    check_token_budget_cap,
    cursor_config_context,
    extract_model_from_argv,
    parse_claude_envelope,
    run_vendor_launch,
    run_with_vendor_retries,
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
        "larch.agents._ci_launcher",
        "larch.agents.agent_voters",
        "larch.agents.collect_results",
    }
)

_PRODUCTION_LAUNCHERS = (
    "agents.py",
    "_claude_runner.py",
    "agent_voters.py",
    "collect_results.py",
)

# Launchers migrated to the shared vendor descriptor table and run_vendor_launch.
_MIGRATED_LAUNCHERS: frozenset[str] = frozenset()


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
            {
                "review-ask",
                "ci-write",
                "implement-write",
                "negotiation-write",
                "lint-fix-write",
            }
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
            if name in _MIGRATED_LAUNCHERS:
                assert "larch.agents._vendor" in imports, f"{name} must import _vendor as a migrated launcher"
            else:
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
        assert not _codex_auth_args()

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

    def test_lint_fix_write_uses_only_the_lint_fix_flags(self) -> None:
        argv = build_cursor_argv("lint-fix-write", self._request())
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--trust",
            "--model",
            "cursor-model",
            "--workspace",
            "/ws",
            "review please",
        ]
        assert "--force" not in argv
        assert "--output-format" not in argv
        assert "--mode" not in argv

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


def test_module_exports_lifecycle_surface() -> None:
    assert hasattr(_vendor, "run_vendor_launch")
    assert hasattr(_vendor, "check_token_budget_cap")
    assert hasattr(_vendor, "cursor_config_context")
    assert hasattr(_vendor, "parse_claude_envelope")
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


# ---------------------------------------------------------------------------
# Piece 2 lifecycle coverage
# ---------------------------------------------------------------------------


class _BudgetResult:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def _base_request(**kwargs: Any) -> VendorLaunchRequest:
    defaults: dict[str, Any] = {
        "workdir": "/repo",
        "output": "/tmp/out.txt",
        "prompt": "do the thing",
        "timing_task_kind": "codex-review",
    }
    defaults.update(kwargs)
    return VendorLaunchRequest(**defaults)


class TestTokenCapCheck:
    def test_positive_cap_builds_argv_and_preserves_payload(self) -> None:
        seen: list[tuple[str, ...]] = []

        def runner(argv: Any) -> _BudgetResult:
            seen.append(tuple(argv))
            return _BudgetResult("STATUS=cap_hit TOTAL=99 CAP=10\n")

        result = check_token_budget_cap(cap="10", step="codex-review", runner=runner)
        assert result.hit is True
        assert result.payload == CAP_HIT_PAYLOAD
        assert result.payload == "STATUS=cap_hit\n"
        expected = tuple(build_check_budget_argv(cap="10", step="codex-review"))
        assert result.argv == expected
        assert seen == [expected]
        assert expected[:4] == (sys_executable := __import__("sys").executable, str(_PY_CLI), "token", "check-budget")
        assert expected[4:] == ("--cap", "10", "--step", "codex-review")
        assert sys_executable  # pin presence

    def test_under_cap_is_not_a_hit(self) -> None:
        result = check_token_budget_cap(
            cap="10",
            step="step",
            runner=lambda _argv: _BudgetResult("STATUS=under_cap TOTAL=1 CAP=10\n"),
        )
        assert result.hit is False
        assert result.payload == ""

    @pytest.mark.parametrize("cap", ["", "0", "-1", "abc", "1.5"])
    def test_invalid_caps_skip_command(self, cap: str) -> None:
        calls: list[object] = []

        def runner(argv: object) -> _BudgetResult:
            calls.append(argv)
            return _BudgetResult("STATUS=cap_hit\n")

        result = check_token_budget_cap(cap=cap, step="step", runner=runner)
        assert result.hit is False
        assert not calls


class TestCursorConfigContext:
    @staticmethod
    def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
        def _home(_cls: type[Path] = Path) -> Path:
            return home

        monkeypatch.setattr(Path, "home", classmethod(_home))

    def test_copies_config_sets_and_restores_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        cursor_dir = home / ".cursor"
        cursor_dir.mkdir(parents=True)
        (cursor_dir / "cli-config.json").write_text('{"approvalMode":"allow"}\n', encoding="utf-8")
        monkeypatch.setenv("HOME", str(home))
        self._patch_home(monkeypatch, home)
        monkeypatch.delenv("CURSOR_CONFIG_DIR", raising=False)

        with cursor_config_context() as cfg_tmp:
            assert os.environ["CURSOR_CONFIG_DIR"] == str(cfg_tmp)
            copied = cfg_tmp / "cli-config.json"
            assert copied.is_file()
            assert copied.read_text(encoding="utf-8") == '{"approvalMode":"allow"}\n'
            assert cfg_tmp.is_dir()
        assert "CURSOR_CONFIG_DIR" not in os.environ
        assert not cfg_tmp.exists()

    def test_missing_source_config_still_isolates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        self._patch_home(monkeypatch, home)
        monkeypatch.setenv("CURSOR_CONFIG_DIR", "/preexisting")
        with cursor_config_context() as cfg_tmp:
            assert os.environ["CURSOR_CONFIG_DIR"] == str(cfg_tmp)
            assert not (cfg_tmp / "cli-config.json").exists()
        assert os.environ["CURSOR_CONFIG_DIR"] == "/preexisting"

    def test_copy_failure_is_suppressed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        cursor_dir = home / ".cursor"
        cursor_dir.mkdir(parents=True)
        src = cursor_dir / "cli-config.json"
        src.write_text("{}\n", encoding="utf-8")
        self._patch_home(monkeypatch, home)
        monkeypatch.delenv("CURSOR_CONFIG_DIR", raising=False)

        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("copy failed")

        monkeypatch.setattr(_vendor.shutil, "copyfile", boom)
        with cursor_config_context() as cfg_tmp:
            assert os.environ["CURSOR_CONFIG_DIR"] == str(cfg_tmp)
            assert not (cfg_tmp / "cli-config.json").exists()
        assert "CURSOR_CONFIG_DIR" not in os.environ

    def test_cleanup_after_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        self._patch_home(monkeypatch, home)
        monkeypatch.delenv("CURSOR_CONFIG_DIR", raising=False)
        cfg_holder: dict[str, Path] = {}

        def _raise_inside() -> None:
            with cursor_config_context() as cfg:
                cfg_holder["cfg"] = cfg
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            _raise_inside()
        cfg_tmp = cfg_holder["cfg"]
        assert not cfg_tmp.exists()
        assert "CURSOR_CONFIG_DIR" not in os.environ


class TestClaudeEnvelope:
    def test_valid_result(self) -> None:
        raw = json.dumps({"result": "hello", "is_error": False})
        parsed = parse_claude_envelope(raw)
        assert parsed == VendorParsedResult(status=CLAUDE_ENVELOPE_OK, text="hello", raw=raw)

    def test_explicit_error(self) -> None:
        raw = json.dumps({"result": "x", "is_error": True})
        parsed = parse_claude_envelope(raw)
        assert parsed.status == CLAUDE_ENVELOPE_IS_ERROR
        assert parsed.is_error is True
        assert parsed.text == ""

    def test_empty_result(self) -> None:
        raw = json.dumps({"result": ""})
        assert parse_claude_envelope(raw).status == CLAUDE_ENVELOPE_EMPTY_RESULT

    def test_missing_result(self) -> None:
        raw = json.dumps({"is_error": False})
        assert parse_claude_envelope(raw).status == CLAUDE_ENVELOPE_MISSING_RESULT

    def test_non_string_result(self) -> None:
        raw = json.dumps({"result": 42})
        assert parse_claude_envelope(raw).status == CLAUDE_ENVELOPE_NON_STRING_RESULT

    def test_malformed_json(self) -> None:
        raw = "{not-json"
        assert parse_claude_envelope(raw).status == CLAUDE_ENVELOPE_MALFORMED_JSON

    def test_non_object_json(self) -> None:
        raw = json.dumps(["result"])
        assert parse_claude_envelope(raw).status == CLAUDE_ENVELOPE_NON_OBJECT


class TestVendorRetries:
    def test_auth_retry_success(self) -> None:
        attempts = {"n": 0}

        def execute() -> VendorProcessResult:
            attempts["n"] += 1
            if attempts["n"] == 1:
                return VendorProcessResult(exit_code=1, stderr="auth")
            return VendorProcessResult(exit_code=0, stdout="ok")

        result = run_with_vendor_retries(
            execute,
            policy=VendorRetryPolicy(
                is_auth_failure=lambda r: r.exit_code != 0 and "auth" in r.stderr,
                max_auth_retries=2,
            ),
        )
        assert result.exit_code == 0
        assert attempts["n"] == 2

    def test_auth_retry_exhaustion(self) -> None:
        attempts = {"n": 0}

        def execute() -> VendorProcessResult:
            attempts["n"] += 1
            return VendorProcessResult(exit_code=1, stderr="auth")

        result = run_with_vendor_retries(
            execute,
            policy=VendorRetryPolicy(
                is_auth_failure=lambda _r: True,
                max_auth_retries=1,
            ),
        )
        assert result.exit_code == 1
        assert attempts["n"] == 2  # initial + 1 retry

    def test_transient_retry_success(self) -> None:
        attempts = {"n": 0}

        def execute() -> VendorProcessResult:
            attempts["n"] += 1
            if attempts["n"] < 3:
                return VendorProcessResult(exit_code=1, stderr="transient")
            return VendorProcessResult(exit_code=0)

        result = run_with_vendor_retries(
            execute,
            policy=VendorRetryPolicy(
                is_transient_failure=lambda r: r.exit_code != 0,
                max_transient_retries=5,
            ),
        )
        assert result.exit_code == 0
        assert attempts["n"] == 3

    def test_empty_response_retry_and_exhaustion(self) -> None:
        attempts = {"n": 0}

        def execute() -> VendorProcessResult:
            attempts["n"] += 1
            return VendorProcessResult(exit_code=0, stdout="")

        result = run_with_vendor_retries(
            execute,
            policy=VendorRetryPolicy(
                is_empty_response=lambda r: r.exit_code == 0 and not r.stdout,
                max_empty_retries=2,
            ),
        )
        assert result.stdout == ""
        assert attempts["n"] == 3  # initial + 2 retries


class TestRunVendorLaunchOrdering:
    def _ordered_hooks(self, events: list[str], *, exit_code: int = 0) -> VendorFamilyHooks:
        def preflight(**_kwargs: object) -> bool:
            events.append("preflight")
            return True

        def execute(**_kwargs: object) -> VendorProcessResult:
            events.append("execute")
            return VendorProcessResult(exit_code=exit_code, stdout="out")

        def mirror_quota(**_kwargs: object) -> None:
            events.append("quota")

        def record_timing(**_kwargs: object) -> None:
            events.append("timing")

        def postprocess(**_kwargs: object) -> None:
            events.append("postprocess")

        def record_usage(**_kwargs: object) -> None:
            events.append("usage")

        def promote_completion(**_kwargs: object) -> None:
            events.append("promote")

        return VendorFamilyHooks(
            preflight=preflight,
            execute=execute,
            mirror_quota=mirror_quota,
            record_timing=record_timing,
            postprocess=postprocess,
            record_usage=record_usage,
            promote_completion=promote_completion,
        )

    def test_cap_precedes_preflight_and_full_order_zero_exit(self) -> None:
        events: list[str] = []
        budget_calls: list[tuple[str, ...]] = []

        def budget_runner(argv: Any) -> _BudgetResult:
            events.append("cap")
            budget_calls.append(tuple(argv))
            return _BudgetResult("STATUS=under_cap TOTAL=1\n")

        def resolve_model(req: VendorLaunchRequest) -> VendorLaunchRequest:
            events.append("resolve_model")
            return req

        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(token_cap="10"),  # noqa: S106  # token budget cap, not a password
            hooks=self._ordered_hooks(events, exit_code=0),
            resolve_model=resolve_model,
            budget_runner=budget_runner,
            use_config_context=False,
        )
        assert outcome.status == "completed"
        assert outcome.process_result is not None
        assert outcome.process_result.exit_code == 0
        assert events == [
            "cap",
            "preflight",
            "resolve_model",
            "execute",
            "quota",
            "timing",
            "postprocess",
            "usage",
            "promote",
        ]
        assert budget_calls[0][4:] == ("--cap", "10", "--step", "codex-review")

    def test_nonzero_exit_still_mirrors_quota_and_promotes(self) -> None:
        events: list[str] = []
        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(),
            hooks=self._ordered_hooks(events, exit_code=7),
            use_config_context=False,
        )
        assert outcome.status == "completed"
        assert outcome.process_result is not None
        assert outcome.process_result.exit_code == 7
        assert events == [
            "preflight",
            "execute",
            "quota",
            "timing",
            "postprocess",
            "usage",
            "promote",
        ]

    def test_cap_hit_skips_preflight_and_launch(self) -> None:
        events: list[str] = []
        artifacts: list[str] = []

        def budget_runner(_argv: Any) -> _BudgetResult:
            events.append("cap")
            return _BudgetResult("STATUS=cap_hit TOTAL=50 CAP=10\n")

        def emit_cap(**kwargs: object) -> None:
            events.append("cap_artifact")
            artifacts.append(str(kwargs.get("payload", "")))

        def preflight(**_kwargs: object) -> bool:
            events.append("preflight")
            return True

        def execute(**_kwargs: object) -> VendorProcessResult:
            events.append("execute")
            return VendorProcessResult(exit_code=0)

        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(token_cap="10"),  # noqa: S106  # token budget cap, not a password
            hooks=VendorFamilyHooks(
                preflight=preflight,
                execute=execute,
                emit_cap_hit_artifact=emit_cap,
                promote_completion=lambda **_k: events.append("promote"),
            ),
            budget_runner=budget_runner,
            use_config_context=False,
        )
        assert outcome.status == "cap_hit"
        assert outcome.cap_check is not None
        assert outcome.cap_check.payload == CAP_HIT_PAYLOAD
        assert artifacts == [CAP_HIT_PAYLOAD]
        assert events == ["cap", "cap_artifact"]

    @pytest.mark.parametrize("cap", ["", "0", "-3", "nope"])
    def test_invalid_cap_skips_command_but_runs_lifecycle(self, cap: str) -> None:
        events: list[str] = []
        calls: list[object] = []

        def budget_runner(argv: object) -> _BudgetResult:
            calls.append(argv)
            return _BudgetResult("STATUS=cap_hit\n")

        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(token_cap=cap),
            hooks=self._ordered_hooks(events),
            budget_runner=budget_runner,
            use_config_context=False,
        )
        assert outcome.status == "completed"
        assert not calls
        assert events[0] == "preflight"
        assert "execute" in events
        assert "promote" in events

    def test_preflight_refusal_skips_execution(self) -> None:
        events: list[str] = []

        def preflight(**_kwargs: object) -> bool:
            events.append("preflight")
            return False

        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(),
            hooks=VendorFamilyHooks(
                preflight=preflight,
                execute=lambda **_k: events.append("execute") or VendorProcessResult(exit_code=0),
                promote_completion=lambda **_k: events.append("promote"),
            ),
            use_config_context=False,
        )
        assert outcome.status == "preflight_refused"
        assert events == ["preflight"]

    @pytest.mark.parametrize(
        "fail_hook",
        ["timing", "postprocess", "usage"],
    )
    @pytest.mark.parametrize("exit_code", [0, 3])
    def test_lifecycle_failure_blocks_promotion(self, fail_hook: str, exit_code: int) -> None:
        events: list[str] = []

        def maybe_fail(name: str) -> None:
            events.append(name)
            if name == fail_hook:
                raise RuntimeError(f"{name} failed")

        hooks = VendorFamilyHooks(
            preflight=lambda **_k: True,
            execute=lambda **_k: VendorProcessResult(exit_code=exit_code),
            mirror_quota=lambda **_k: events.append("quota"),
            record_timing=lambda **_k: maybe_fail("timing"),
            postprocess=lambda **_k: maybe_fail("postprocess"),
            record_usage=lambda **_k: maybe_fail("usage"),
            promote_completion=lambda **_k: events.append("promote"),
        )
        with pytest.raises(RuntimeError, match=fail_hook):
            run_vendor_launch(
                CODEX_DESCRIPTOR,
                "read-only",
                _base_request(),
                hooks=hooks,
                use_config_context=False,
            )
        assert "promote" not in events
        assert fail_hook in events

    def test_cursor_postprocess_precedes_usage(self) -> None:
        events: list[str] = []
        hooks = VendorFamilyHooks(
            execute=lambda **_k: VendorProcessResult(exit_code=0, stdout='{"result":null}'),
            postprocess=lambda **_k: events.append("postprocess"),
            record_usage=lambda **_k: events.append("usage"),
            promote_completion=lambda **_k: events.append("promote"),
            record_timing=lambda **_k: events.append("timing"),
            mirror_quota=lambda **_k: events.append("quota"),
        )
        run_vendor_launch(
            CURSOR_DESCRIPTOR,
            "review-ask",
            _base_request(model_args=("--model", "m"), timing_task_kind="cursor-review"),
            hooks=hooks,
            use_config_context=False,
        )
        assert events.index("postprocess") < events.index("usage")
        assert events.index("usage") < events.index("promote")

    def test_config_context_exits_after_lifecycle_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        TestCursorConfigContext._patch_home(monkeypatch, home)
        monkeypatch.delenv("CURSOR_CONFIG_DIR", raising=False)
        seen_cfg: list[str] = []

        def execute(**_kwargs: object) -> VendorProcessResult:
            seen_cfg.append(os.environ.get("CURSOR_CONFIG_DIR", ""))
            return VendorProcessResult(exit_code=0)

        def boom(**_kwargs: object) -> None:
            raise RuntimeError("postprocess failed")

        with pytest.raises(RuntimeError, match="postprocess failed"):
            run_vendor_launch(
                CURSOR_DESCRIPTOR,
                "review-ask",
                _base_request(model_args=("--model", "m"), timing_task_kind="cursor-review"),
                hooks=VendorFamilyHooks(execute=execute, postprocess=boom),
                use_config_context=True,
            )
        assert seen_cfg
        assert seen_cfg[0]
        assert Path(seen_cfg[0]).exists() is False
        assert "CURSOR_CONFIG_DIR" not in os.environ

    def test_retry_hook_exhaustion_still_promotes(self) -> None:
        events: list[str] = []
        attempts = {"n": 0}

        def execute(**_kwargs: object) -> VendorProcessResult:
            attempts["n"] += 1
            events.append(f"execute-{attempts['n']}")
            return VendorProcessResult(exit_code=1, stderr="auth")

        def retry(run_once: Any, **_kwargs: object) -> VendorProcessResult:
            events.append("retry")
            return run_with_vendor_retries(
                run_once,
                policy=VendorRetryPolicy(
                    is_auth_failure=lambda r: r.exit_code != 0,
                    max_auth_retries=1,
                ),
            )

        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            "read-only",
            _base_request(),
            hooks=VendorFamilyHooks(
                execute=execute,
                retry=retry,
                mirror_quota=lambda **_k: events.append("quota"),
                record_timing=lambda **_k: events.append("timing"),
                postprocess=lambda **_k: events.append("postprocess"),
                record_usage=lambda **_k: events.append("usage"),
                promote_completion=lambda **_k: events.append("promote"),
            ),
            use_config_context=False,
        )
        assert outcome.status == "completed"
        assert outcome.process_result is not None
        assert outcome.process_result.exit_code == 1
        assert attempts["n"] == 2
        assert events[-5:] == ["quota", "timing", "postprocess", "usage", "promote"]


def test_cap_check_result_frozen() -> None:
    result = VendorCapCheckResult(hit=False)
    with pytest.raises(FrozenInstanceError):
        result.hit = True  # type: ignore[misc]


class TestSessionArgvBuilders:
    def _request(self, **overrides: object) -> VendorLaunchRequest:
        base: dict[str, object] = {
            "workdir": "/repo",
            "output": "/tmp/out.txt",
            "prompt": "continue the debate",
            "model_args": ("--model", "cursor-grok-4.5-high"),
        }
        base.update(overrides)
        return VendorLaunchRequest(**base)  # type: ignore[arg-type]

    def test_cursor_create_chat_is_option_free(self) -> None:
        assert build_cursor_create_chat_argv() == ["cursor", "agent", "create-chat"]

    def test_cursor_resume_plan_mode_trust_json_workspace(self) -> None:
        handle = VendorSessionHandle.create(vendor="cursor", session_id="chat-abc123")
        argv = build_cursor_resume_argv(handle, self._request())
        assert argv == [
            "cursor",
            "agent",
            "-p",
            "--resume",
            "chat-abc123",
            "--mode",
            "plan",
            "--trust",
            "--output-format",
            "json",
            "--model",
            "cursor-grok-4.5-high",
            "--workspace",
            "/repo",
            "continue the debate",
        ]
        assert "--last" not in argv

    def test_codex_session_reuses_read_only_builder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        req = VendorLaunchRequest(workdir="/repo", output="/tmp/out.txt", prompt="start")
        assert build_codex_session_argv(req) == build_codex_argv("read-only", req)
        assert "--sandbox" in build_codex_session_argv(req)
        assert "read-only" in build_codex_session_argv(req)

    def test_codex_resume_omits_unsupported_flags_keeps_uuid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        handle = VendorSessionHandle.create(
            vendor="codex",
            session_id="019fc6b3-e6c4-7892-a97a-c80b30a7f5b0",
        )
        req = VendorLaunchRequest(
            workdir="/repo",
            output="/tmp/out.txt",
            prompt="resume please",
            model_args=("-m", "gpt-5.6-sol"),
        )
        argv = build_codex_resume_argv(handle, req)
        assert argv[:4] == [
            "codex",
            "exec",
            "resume",
            "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0",
        ]
        assert "--sandbox" not in argv
        assert "-C" not in argv
        assert "--add-dir" not in argv
        assert "--last" not in argv
        assert 'sandbox_mode="read-only"' in argv
        assert "--json" in argv
        assert "--output-last-message" in argv
        assert argv[-1] == "resume please"
        assert _trust_config_arg("/repo") in argv

    def test_wrong_vendor_and_unsafe_handles_rejected(self) -> None:
        cursor = VendorSessionHandle.create(vendor="cursor", session_id="chat1")
        codex = VendorSessionHandle.create(
            vendor="codex",
            session_id="019fc6b3-e6c4-7892-a97a-c80b30a7f5b0",
        )
        req = self._request(model_args=())
        with pytest.raises(ValueError, match="wrong vendor"):
            build_cursor_resume_argv(codex, req)
        with pytest.raises(ValueError, match="wrong vendor"):
            build_codex_resume_argv(cursor, req)
        with pytest.raises(ValueError, match="must be non-empty"):
            VendorSessionHandle.create(vendor="cursor", session_id="")
        with pytest.raises(ValueError, match="without surrounding or embedded whitespace"):
            VendorSessionHandle.create(vendor="cursor", session_id="  spaced  ")
        with pytest.raises(ValueError, match="must not be flag-like"):
            VendorSessionHandle.create(vendor="cursor", session_id="-flaglike")
        with pytest.raises(ValueError, match="codex session id must be a UUID"):
            VendorSessionHandle.create(vendor="codex", session_id="not-a-uuid")
        with pytest.raises(ValueError, match="unsupported vendor session handle vendor"):
            VendorSessionHandle.create(vendor="claude", session_id="x")

    def test_handle_is_frozen_and_module_has_no_last(self) -> None:
        handle = VendorSessionHandle.create(vendor="cursor", session_id="chat1")
        with pytest.raises(FrozenInstanceError):
            handle.session_id = "other"  # type: ignore[misc]
        source = VENDOR_PATH.read_text(encoding="utf-8")
        assert "--last" not in source
        for builder in (
            build_cursor_create_chat_argv,
            build_cursor_resume_argv,
            build_codex_session_argv,
            build_codex_resume_argv,
        ):
            assert builder.__name__ in source
