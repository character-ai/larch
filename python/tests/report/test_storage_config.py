"""Repository config, Git identity, and derived storage contract tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import subprocess
import tomllib
from typing import cast

import pytest

from larch.core import config, proc
from larch.report import storage_config


def _write_config(
    repo_root: Path,
    uri: str = "s3://zhupanov",
    *,
    extra: str = "",
) -> None:
    _ = (repo_root / "tools-config.toml").write_text(
        f'[larch]\nstorage_base_uri = "{uri}"\n{extra}',
        encoding="utf-8",
    )


def _result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> proc.CommandResult:
    return proc.CommandResult(
        argv=(),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration=0.0,
    )


class FakeRunner:
    """Return queued command results and retain credential-free argv."""

    def __init__(self, *results: proc.CommandResult) -> None:
        self.results: list[proc.CommandResult] = list(results)
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
    ) -> proc.CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        self.calls.append(tuple(argv))
        return self.results.pop(0)


def test_gcs_checkout_build_failure_has_actionable_preflight_guidance(
) -> None:
    storage = storage_config.ToolRepositoryStorage(
        storage_config.StorageBase("gs", "bucket"),
        "larch",
    )
    runner = FakeRunner(_result(returncode=1))

    with pytest.raises(
        storage_config.StoragePreflightError,
        match="verify Cargo is installed",
    ):
        storage_config.preflight_tool_repository(
            storage=storage,
            environ={},
            runner=runner,
        )

    assert runner.calls[0][0] == config.CARGO_CLI


def _load(
    repo_root: Path,
    *,
    uri: str = "s3://zhupanov",
    origin: str = "git@github.com:character-ai/larch.git",
    environ: Mapping[str, str] | None = None,
) -> storage_config.ToolRepositoryStorage:
    _write_config(repo_root, uri)
    return storage_config.load_tool_repository_storage(
        repo_root=repo_root,
        environ={} if environ is None else environ,
        runner=FakeRunner(_result(stdout=f"{origin}\n")),
    )


@pytest.mark.parametrize(
    ("base_uri", "expected"),
    [
        ("s3://zhupanov", "s3://zhupanov/larch/larch"),
        (
            "s3://company-data/prod/tools",
            "s3://company-data/prod/tools/larch/larch",
        ),
        ("gs://character-tool-logs", "gs://character-tool-logs/larch/larch"),
        ("r2://archive-bucket/base", "r2://archive-bucket/base/larch/larch"),
    ],
)
def test_load_derives_tool_repository_and_run_logs_uri(
    tmp_path: Path, base_uri: str, expected: str
) -> None:
    storage = _load(tmp_path, uri=base_uri)

    assert storage.base.uri == base_uri
    assert storage.client_repo == "larch"
    assert storage.uri == expected
    assert storage.run_logs_uri == f"{expected}/run-logs/"
    assert len(storage.storage_origin_id) == 64


def test_base_override_requires_config_and_changes_only_base(tmp_path: Path) -> None:
    storage = _load(
        tmp_path,
        uri="s3://file-root/base",
        environ={config.ENV_LARCH_STORAGE_BASE_URI: "gs://override"},
    )
    assert storage.uri == "gs://override/larch/larch"

    missing = tmp_path / "missing"
    missing.mkdir()
    with pytest.raises(
        storage_config.StorageConfigurationError, match="missing required file"
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=missing,
            environ={config.ENV_LARCH_STORAGE_BASE_URI: "gs://override"},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )


def test_legacy_environment_override_is_rejected_with_guidance(tmp_path: Path) -> None:
    _write_config(tmp_path)
    with pytest.raises(
        storage_config.StorageConfigurationError,
        match=r"LARCH_LOGS_URI.*LARCH_STORAGE_BASE_URI",
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={config.ENV_LARCH_LOGS_URI: "s3://old/root"},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )


@pytest.mark.parametrize("former", ["config.toml", "tool-config.toml"])
def test_former_or_singular_config_names_are_not_probed(
    tmp_path: Path, former: str
) -> None:
    _ = (tmp_path / former).write_text(
        '[larch]\nstorage_base_uri = "s3://ignored"\n', encoding="utf-8"
    )
    with pytest.raises(
        storage_config.StorageConfigurationError, match=r"tools-config\.toml"
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )


def test_dot_larch_config_is_not_probed(tmp_path: Path) -> None:
    legacy_directory = tmp_path / ".larch"
    legacy_directory.mkdir()
    _ = (legacy_directory / "config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://ignored"\n', encoding="utf-8"
    )
    with pytest.raises(
        storage_config.StorageConfigurationError, match=r"tools-config\.toml"
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )


def test_config_is_strict_for_larch_and_ignores_other_tools(tmp_path: Path) -> None:
    _ = (tmp_path / "tools-config.toml").write_text(
        '[sre]\nanything = true\n\n[larch]\nstorage_base_uri = "s3://zhupanov"\n',
        encoding="utf-8",
    )
    storage = storage_config.load_tool_repository_storage(
        repo_root=tmp_path,
        environ={},
        runner=FakeRunner(_result(stdout="git@github.com:character-ai/larch.git\n")),
    )
    assert storage.client_repo == "larch"

    _write_config(tmp_path, extra='client_repo = "wrong"\n')
    with pytest.raises(
        storage_config.StorageConfigurationError, match="must contain only"
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )


def test_missing_larch_table_error_is_actionable(tmp_path: Path) -> None:
    _ = (tmp_path / "tools-config.toml").write_text(
        "[sre]\nvalue = 1\n", encoding="utf-8"
    )
    with pytest.raises(storage_config.StorageConfigurationError) as failure:
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(
                _result(stdout="git@github.com:character-ai/larch.git\n")
            ),
        )
    message = str(failure.value)
    assert all(
        token in message
        for token in (
            "Git repository",
            "tools-config.toml",
            "[larch]",
            "storage_base_uri",
        )
    )


def test_symlinked_config_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "actual.toml"
    _ = target.write_text(
        '[larch]\nstorage_base_uri = "s3://bucket"\n', encoding="utf-8"
    )
    (tmp_path / "tools-config.toml").symlink_to(target)
    with pytest.raises(
        storage_config.StorageConfigurationError, match="refusing symlink"
    ):
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(_result(stdout="git@github.com:org/repo.git\n")),
        )


@pytest.mark.parametrize(
    ("uri", "message"),
    [
        ("https://bucket", "must use one of"),
        ("S3://bucket", "must use one of"),
        ("s3://key:secret@bucket", "must not contain credentials"),
        ("s3://bucket:443", "without a port"),
        ("s3://bucket/a/../prefix", r"must not contain empty, '\.' or '\.\.'"),
        ("s3://bucket/a//prefix", r"must not contain empty, '\.' or '\.\.'"),
        ("s3://bucket/prefix/", "trailing slash"),
        ("s3://bucket/prefix?query=1", "query or fragment"),
        ("s3://bucket/prefix#fragment", "query or fragment"),
        (r"s3://bucket\\other/prefix", "plain bucket name"),
        (r"s3://bucket/base\\prefix", "whitespace or control characters"),
        (" s3://bucket", "surrounding whitespace"),
    ],
)
def test_storage_base_rejects_unsafe_shapes(uri: str, message: str) -> None:
    with pytest.raises(storage_config.StorageConfigurationError, match=message):
        _ = storage_config.parse_storage_base_uri(uri)


@pytest.mark.parametrize(
    ("origin", "client_repo"),
    [
        ("https://github.com/character-ai/Agent-Lint.git", "agent-lint"),
        ("ssh://git@github.com/character-ai/larch.git", "larch"),
        ("git@github.com:character-ai/larch.git", "larch"),
        ("github.com:character-ai/service_a", "service_a"),
    ],
)
def test_git_origin_derivation_supports_standard_syntax(
    tmp_path: Path, origin: str, client_repo: str
) -> None:
    _write_config(tmp_path)
    storage = storage_config.load_tool_repository_storage(
        repo_root=tmp_path,
        environ={},
        runner=FakeRunner(_result(stdout=f"{origin}\n")),
    )
    assert storage.client_repo == client_repo


@pytest.mark.parametrize(
    "origin",
    [
        "https://user:secret@example.com/org/repo.git",
        "https://example.com:443/org/repo.git",
        "ssh://example.com:notaport/org/repo.git",
        "file:///tmp/repo.git",
        "git@github.com:org/../repo.git",
        "git@github.com:org/-repo.git",
        "git@github.com:org/repo-.git",
        "ambiguous",
        "",
    ],
)
def test_git_origin_derivation_rejects_unsafe_or_ambiguous_values(
    tmp_path: Path, origin: str
) -> None:
    _write_config(tmp_path)
    with pytest.raises(storage_config.StorageConfigurationError) as failure:
        _ = storage_config.load_tool_repository_storage(
            repo_root=tmp_path,
            environ={},
            runner=FakeRunner(_result(stdout=f"{origin}\n")),
        )
    assert "secret" not in str(failure.value)


def test_discovery_uses_git_toplevel_from_nested_startup_cwd(tmp_path: Path) -> None:
    _write_config(tmp_path)

    def fake_consumer_repo_root(start: Path | None = None) -> Path:
        assert start == tmp_path / "nested"
        return tmp_path

    storage = storage_config.discover_tool_repository_storage(
        start=tmp_path / "nested",
        environ={},
        root_resolver=fake_consumer_repo_root,
        runner=FakeRunner(_result(stdout="git@github.com:character-ai/larch.git\n")),
    )
    assert storage.uri == "s3://zhupanov/larch/larch"


def test_discovery_uses_linked_worktree_git_identity(tmp_path: Path) -> None:
    checkout = tmp_path / "larch2"
    checkout.mkdir()
    _ = subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    _ = subprocess.run(
        ["git", "config", "user.email", "fixture@example.com"],
        cwd=checkout,
        check=True,
    )
    _ = subprocess.run(
        ["git", "config", "user.name", "Fixture"],
        cwd=checkout,
        check=True,
    )
    _ = subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "git@github.com:character-ai/Agent-Lint.git",
        ],
        cwd=checkout,
        check=True,
    )
    _write_config(checkout)
    _ = subprocess.run(["git", "add", "tools-config.toml"], cwd=checkout, check=True)
    _ = subprocess.run(
        ["git", "commit", "-q", "-m", "fixture"],
        cwd=checkout,
        check=True,
    )
    worktree = tmp_path / "agent-lint-worktree"
    _ = subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "fixture-worktree", str(worktree)],
        cwd=checkout,
        check=True,
    )
    nested = worktree / "nested"
    nested.mkdir()

    storage = storage_config.discover_tool_repository_storage(
        start=nested,
        environ={},
    )

    assert storage.client_repo == "agent-lint"
    assert storage.uri == "s3://zhupanov/larch/agent-lint"


def test_preflight_machine_envelope_names_derived_namespaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = storage_config.ToolRepositoryStorage(
        storage_config.StorageBase("s3", "company-data", "prod/tools"),
        "service-a",
    )
    preflighted: list[storage_config.ToolRepositoryStorage] = []

    def discover_storage(**_kwargs: object) -> storage_config.ToolRepositoryStorage:
        return storage

    def preflight_storage(**kwargs: object) -> None:
        preflighted.append(
            cast(
                "storage_config.ToolRepositoryStorage",
                kwargs["storage"],
            )
        )

    monkeypatch.setattr(
        storage_config,
        "discover_tool_repository_storage",
        discover_storage,
    )
    monkeypatch.setattr(
        storage_config,
        "preflight_tool_repository",
        preflight_storage,
    )

    assert storage_config.storage_preflight_main(["--repo-root", str(tmp_path)]) == 0

    assert preflighted == [storage]
    assert capsys.readouterr().out.splitlines() == [
        "STORAGE_BASE_URI=s3://company-data/prod/tools",
        "CLIENT_REPO=service-a",
        "TOOL_REPO_URI=s3://company-data/prod/tools/larch/service-a",
        "RUN_LOGS_URI=s3://company-data/prod/tools/larch/service-a/run-logs/",
        "PREFLIGHT_OK=true",
    ]


def test_checked_config_and_published_examples_match_executable_contract() -> None:
    repo_root = Path(__file__).parents[3]
    config_text = (repo_root / "tools-config.toml").read_text(encoding="utf-8")
    assert config_text == '[larch]\nstorage_base_uri = "s3://zhupanov"\n'
    assert tomllib.loads(config_text) == {
        "larch": {"storage_base_uri": "s3://zhupanov"}
    }

    storage = storage_config.ToolRepositoryStorage(
        storage_config.parse_storage_base_uri("s3://company-data/prod/tools"),
        "service-a",
    )
    archive_doc = (repo_root / "docs/run-log-archive.md").read_text(encoding="utf-8")
    analysis_doc = (repo_root / "docs/analysis-state.md").read_text(encoding="utf-8")
    assert f"{storage.run_logs_uri}review/<run-id>.tar.gz" in archive_doc
    assert "tools-config.toml" in archive_doc
    assert "run-logs/v2/" in archive_doc
    assert "analysis-state/v2/" in analysis_doc


def test_legacy_descriptor_parser_is_explicit_and_config_independent() -> None:
    storage = storage_config.ToolRepositoryStorage(
        storage_config.StorageBase("s3", "zhupanov"), "larch"
    )
    descriptor = storage_config.parse_legacy_migration_descriptor(
        {
            "schema": "larch-run-log-migration-inventory-v1",
            "source_commit": "a" * 40,
            "storage_root": storage.base.uri,
            "inventory_key": "migration/inventory.json",
            "inventory_sha256": "b" * 64,
        },
        storage_root=storage.base,
    )
    assert descriptor.inventory_key == "migration/inventory.json"
