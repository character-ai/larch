"""Tests for the universal per-skill run lifecycle."""

from __future__ import annotations

import json
import shlex
import subprocess
import tarfile
import threading
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from larch.core import alias_skill
from larch.report import (
    run_lifecycle,
    run_log_manifest,
    run_log_publish,
    run_logs,
    storage_config,
)
from larch.report.object_store import (
    ObjectStoreError,
    ObjectStoreErrorKind,
    RemoteObject,
)
from larch.report.storage_config import StorageBase, ToolRepositoryStorage


class MemoryObjectStore:
    """Minimal create-only store for lifecycle publication tests."""

    def __init__(self, *, fail_uploads: int = 0) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_calls: list[str] = []
        self.fail_uploads = fail_uploads
        self._lock = threading.Lock()

    def upload_create(self, key: str, source: Path) -> RemoteObject:
        content = source.read_bytes()
        with self._lock:
            self.upload_calls.append(key)
            if self.fail_uploads:
                self.fail_uploads -= 1
                raise ObjectStoreError(ObjectStoreErrorKind.TRANSPORT, "fake", "upload")
            if key in self.objects:
                raise ObjectStoreError(
                    ObjectStoreErrorKind.ALREADY_EXISTS, "fake", "upload"
                )
            self.objects[key] = content
        return RemoteObject(key, len(content), "etag", None)

    def download(self, key: str, destination: Path) -> None:
        _ = destination.write_bytes(self.objects[key])

    def metadata(self, key: str) -> RemoteObject:
        content = self.objects[key]
        return RemoteObject(key, len(content), "etag", None)


@pytest.fixture
def lifecycle_fixture(
    tmp_path: Path,
) -> tuple[Path, dict[str, str], ToolRepositoryStorage]:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _ = subprocess.run(
        ["git", "init", "-q"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    environment = {
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    return (
        repo,
        environment,
        ToolRepositoryStorage(StorageBase("s3", "bucket"), "consumer"),
    )


def test_final_report_renderer_names_terminal_identity() -> None:
    report = run_lifecycle._render_final_report(  # pyright: ignore[reportPrivateUsage]  # Golden-test lint requires direct renderer coverage.
        skill="status", run_id="reference-success", outcome="success"
    )
    assert "Skill: `status`" in report
    assert "Run ID: `reference-success`" in report
    assert "Outcome: `success`" in report


@pytest.mark.parametrize("changed_identity", ["storage-base", "git-origin"])
def test_mid_run_repository_identity_change_fails_before_publication(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    changed_identity: str,
) -> None:
    repo, environment, _storage = lifecycle_fixture
    _ = subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:fixture/consumer.git"],
        cwd=repo,
        check=True,
    )
    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://bucket"\n',
        encoding="utf-8",
    )
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id=f"identity-change-{changed_identity}",
        environ=environment,
        preflight=lambda _storage: None,
    )
    if changed_identity == "storage-base":
        _ = (repo / "tools-config.toml").write_text(
            '[larch]\nstorage_base_uri = "gs://other-bucket"\n',
            encoding="utf-8",
        )
    else:
        _ = subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                "git@github.com:fixture/other-repository.git",
            ],
            cwd=repo,
            check=True,
        )
    store = MemoryObjectStore()

    with pytest.raises(run_lifecycle.RunLifecycleError):
        _ = run_lifecycle.finish_run(
            repo_root=repo,
            skill="status",
            run_id=started.run_id,
            outcome="failure",
            environ=environment,
            store=store,
        )

    assert not store.upload_calls


def test_manifest_storage_identity_mismatch_fails_before_terminal_writes(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id="manifest-identity-change",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _storage: None,
    )
    manifest_path = started.run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tool_repo_uri"] = "s3://other/larch/consumer"
    _ = manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(
        run_lifecycle.RunLifecycleError,
        match="publication or repository identity changed",
    ):
        _ = run_lifecycle.finish_run(
            repo_root=repo,
            skill="status",
            run_id=started.run_id,
            outcome="failure",
            environ=environment,
            storage_root=storage_root,
            store=MemoryObjectStore(),
        )

    assert not (started.run_dir / run_lifecycle.UNIVERSAL_FINAL_REPORT).exists()


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled", "early-return"])
def test_reference_skill_publishes_every_terminal_outcome(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    outcome: str,
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    preflights: list[str] = []
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id=f"reference-{outcome}",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda root: preflights.append(root.uri),
    )

    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill="status",
        run_id=started.run_id,
        outcome=outcome,
        environ=environment,
        storage_root=storage_root,
        store=MemoryObjectStore(),
    )

    assert preflights == [storage_root.uri]
    assert terminal.outcome == outcome
    assert not started.run_dir.exists()
    assert terminal.publication is not None
    cache = terminal.publication.cache_dir
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["skill"] == "status"
    assert manifest["run_id"] == started.run_id
    assert manifest["terminal_outcome"] == outcome
    assert (cache / run_lifecycle.UNIVERSAL_FINAL_REPORT).is_file()
    issues = (cache / run_lifecycle.UNIVERSAL_EXECUTION_ISSUES).read_text(
        encoding="utf-8"
    )
    assert run_lifecycle.UNIVERSAL_SESSION_TRANSCRIPT in issues


@pytest.mark.parametrize("skill", ["implement", "design", "review"])
def test_specialized_staging_has_one_identity_context_and_terminal_upload(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    skill: str,
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    run_id = f"{skill}-specialized-run"
    log_root = repo.parent / f"{skill}-session" / "larch-logs"
    _ = run_logs.log_init(log_root=log_root, skill=skill, run_id=run_id)
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill=skill,
        run_id=run_id,
        log_root=log_root,
        adopt_existing=True,
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    artifact = started.run_dir / "specialized-artifact.txt"
    _ = artifact.write_text(f"{skill} artifact\n", encoding="utf-8")
    context = json.loads(started.context_file.read_text(encoding="utf-8"))
    store = MemoryObjectStore()
    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=skill,
        run_id=run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    assert terminal.publication is not None
    assert (
        context["skill"],
        context["run_id"],
        context["log_root"],
        store.upload_calls,
        started.context_file.exists(),
        (terminal.publication.cache_dir / artifact.name).read_text(encoding="utf-8"),
    ) == (
        skill,
        run_id,
        str(log_root),
        [f"run-logs/{skill}/{run_id}.tar.gz"],
        False,
        f"{skill} artifact\n",
    )


@pytest.mark.parametrize(
    ("parent_skill", "child_skill"), [("f", "implement"), ("implement", "review")]
)
@pytest.mark.parametrize("child_outcome", ["success", "failure"])
def test_alias_target_and_nested_review_record_parent_child_ids(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    parent_skill: str,
    child_skill: str,
    child_outcome: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, environment, storage_root = lifecycle_fixture

    def preflight(_root: ToolRepositoryStorage) -> None:
        return

    start_run = run_lifecycle.start_run

    def fixture_start_run(**kwargs: Any) -> run_lifecycle.LifecycleStart:
        return start_run(
            **kwargs,
            environ=environment,
            storage_root=storage_root,
            preflight=preflight,
        )

    monkeypatch.setattr(run_lifecycle, "start_run", fixture_start_run)

    def start_from_skill_call(
        skill: str, run_id: str, parent_context: Path | None = None
    ) -> run_lifecycle.LifecycleStart:
        argv = [
            "--repo-root",
            str(repo),
            "--skill",
            skill,
            "--run-id",
            run_id,
        ]
        if parent_context:
            argv.extend(["--lifecycle-parent-context", str(parent_context)])
        assert run_lifecycle.start_main(argv) == 0
        return run_lifecycle.load_run_context(
            repo_root=repo,
            skill=skill,
            run_id=run_id,
            environ=environment,
            storage_root=storage_root,
        )

    parent = start_from_skill_call(parent_skill, f"{parent_skill}-parent-run")
    child_parent_context = parent.context_file
    if parent_skill == "f":
        generated = StringIO()
        with redirect_stdout(generated):
            assert (
                alias_skill.generate_main(
                    [
                        "--name",
                        "f",
                        "--target",
                        "implement",
                        "--target-dir",
                        "/tmp/skills/f",
                        "--flags",
                        "",
                        "--version",
                        "test",
                    ]
                )
                == 0
            )
        call_args = next(
            line.removeprefix("- args: ")
            for line in generated.getvalue().splitlines()
            if line.startswith("- args: ")
        )
        parsed_args = shlex.split(call_args)
        assert parsed_args[:2] == ["--lifecycle-parent-context", "$CONTEXT_FILE"]
        child_parent_context = Path(
            parsed_args[1].replace("$CONTEXT_FILE", str(parent.context_file))
        )
    child = start_from_skill_call(
        child_skill, f"{child_skill}-child-run", child_parent_context
    )
    store = MemoryObjectStore()

    child_terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=child.skill,
        run_id=child.run_id,
        outcome=child_outcome,
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    parent_terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=parent.skill,
        run_id=parent.run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    assert child_terminal.publication is not None
    assert parent_terminal.publication is not None

    child_manifest = json.loads(
        (child_terminal.publication.cache_dir / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    parent_manifest = json.loads(
        (parent_terminal.publication.cache_dir / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert (
        parent_manifest["skill"],
        child_manifest["skill"],
        child_manifest["terminal_outcome"],
    ) == (parent_skill, child_skill, child_outcome)
    assert child_manifest["run_id"] == child.run_id
    assert child_manifest["parent_skill"] == parent.skill
    assert child_manifest["parent_run_id"] == parent.run_id
    assert (
        child_terminal.publication.remote_key != parent_terminal.publication.remote_key
    )
    assert len(store.objects) == 2


def test_repository_config_parent_context_cli_starts_child_and_adopts(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, environment, _storage_root = lifecycle_fixture
    _ = subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:fixture/consumer.git"],
        cwd=repo,
        check=True,
    )
    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://bucket"\n',
        encoding="utf-8",
    )
    for key, value in environment.items():
        monkeypatch.setenv(key, value)

    def no_op_preflight(*, storage: ToolRepositoryStorage) -> None:
        _ = storage

    monkeypatch.setattr(storage_config, "preflight_tool_repository", no_op_preflight)

    assert (
        run_lifecycle.start_main(
            [
                "--repo-root",
                str(repo),
                "--skill",
                "bug",
                "--run-id",
                "repository-config-parent",
            ]
        )
        == 0
    )
    parent_values: dict[str, str] = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in capsys.readouterr().out.splitlines()
        if "=" in line
    }
    parent_context = Path(parent_values["CONTEXT_FILE"])
    assert parent_values["RUN_LOG_STORAGE"] == "enabled"
    assert parent_values["RUN_LOG_STORAGE_REASON"] == "repository-config"

    assert (
        run_lifecycle.start_main(
            [
                "--repo-root",
                str(repo),
                "--skill",
                "issue",
                "--run-id",
                "repository-config-child",
                "--lifecycle-parent-context",
                str(parent_context),
            ]
        )
        == 0
    )
    child_values: dict[str, str] = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in capsys.readouterr().out.splitlines()
        if "=" in line
    }
    child_context = Path(child_values["CONTEXT_FILE"])
    child_manifest = json.loads(
        (Path(child_values["RUN_DIR"]) / "manifest.json").read_text(encoding="utf-8")
    )
    assert (
        child_values["LIFECYCLE_STARTED"],
        child_values["RUN_ID"],
        child_context != parent_context,
        child_manifest["parent_skill"],
        child_manifest["parent_run_id"],
    ) == (
        "true",
        "repository-config-child",
        True,
        "bug",
        "repository-config-parent",
    )

    adopted = run_lifecycle.start_run(
        repo_root=repo,
        skill="issue",
        run_id="repository-config-child",
        adopt_existing=True,
        parent_context=parent_context,
        environ=environment,
        preflight=lambda _storage: None,
    )
    assert adopted.context_file == child_context
    assert adopted.storage_resolution.reason == "repository-config"

    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://other-bucket"\n',
        encoding="utf-8",
    )
    with pytest.raises(run_lifecycle.RunLifecycleError):
        _ = run_lifecycle.start_run(
            repo_root=repo,
            skill="review",
            run_id="repository-config-drifted-child",
            parent_context=parent_context,
            environ=environment,
            preflight=lambda _storage: None,
        )


def test_upload_failure_is_loud_and_retry_uses_durable_pending_archive(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id="upload-failure",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    store = MemoryObjectStore(fail_uploads=1)

    with pytest.raises(ObjectStoreError):
        _ = run_lifecycle.finish_run(
            repo_root=repo,
            skill=started.skill,
            run_id=started.run_id,
            outcome="failure",
            environ=environment,
            storage_root=storage_root,
            store=store,
        )

    paths = run_log_publish.publication_paths(
        request=run_log_publish.PublicationRequest(
            repo_root=repo,
            storage_root=storage_root,
            skill=started.skill,
            run_id=started.run_id,
            staging_root=None,
        ),
        environ=environment,
    )
    assert paths.pending_archive.is_file()
    assert started.run_dir.is_dir()
    manifest_before_restart = (started.run_dir / "manifest.json").read_text(
        encoding="utf-8"
    )
    _ = run_lifecycle.start_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        adopt_existing=True,
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    assert (started.run_dir / "manifest.json").read_text(
        encoding="utf-8"
    ) == manifest_before_restart

    retried = run_lifecycle.finish_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        outcome="failure",
        environ=environment,
        storage_root=storage_root,
        store=store,
    )
    assert retried.outcome == "failure"
    assert not paths.pending_dir.exists()


def test_parent_metadata_must_be_complete(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    with pytest.raises(ValueError, match="provided together"):
        _ = run_lifecycle.start_run(
            repo_root=repo,
            skill="status",
            parent_skill="cleanup",
            environ=environment,
            storage_root=storage_root,
            preflight=lambda _root: None,
        )


def test_universal_artifacts_extend_existing_skill_requirements(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="implement",
        run_id="implement-adoption",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )
    _ = (started.run_dir / "code-review-tally.json").write_text(
        "{}\n", encoding="utf-8"
    )
    manifest = run_log_manifest.Manifest.from_json(
        json.loads((started.run_dir / "manifest.json").read_text(encoding="utf-8"))
    )

    required = run_log_manifest.required_artifacts_for_run(
        run_dir=started.run_dir,
        skill="implement",
        manifest=manifest,
        repo_root=repo,
    )

    paths = {artifact.relative_path for artifact in required}
    assert run_lifecycle.UNIVERSAL_FINAL_REPORT in paths
    assert run_lifecycle.UNIVERSAL_SESSION_TRANSCRIPT in paths
    assert "review-findings-full.jsonl" in paths


def test_design_adopts_universal_ndjson_waiver_without_contract_fork(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="design",
        run_id="design-adoption",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )

    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        outcome="success",
        environ=environment,
        storage_root=storage_root,
        store=MemoryObjectStore(),
    )

    assert terminal.publication is not None
    assert (terminal.publication.cache_dir / "execution-issues.ndjson").is_file()


def test_parent_identity_is_immutable_after_start(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, storage_root = lifecycle_fixture
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="cleanup",
        run_id="immutable-parent",
        parent_skill="status",
        parent_run_id="parent-run",
        environ=environment,
        storage_root=storage_root,
        preflight=lambda _root: None,
    )

    with pytest.raises(ValueError, match="immutable-field:parent_run_id"):
        _ = run_logs.log_manifest_update(
            log_root=started.log_root,
            skill=started.skill,
            run_id=started.run_id,
            updates={"parent_run_id": "other-parent"},
        )


def test_disabled_lifecycle_skips_provider_and_stays_disabled_when_config_appears(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, environment, _storage_root = lifecycle_fixture
    _ = subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:fixture/consumer.git"],
        cwd=repo,
        check=True,
    )
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    def unexpected_preflight(**_kwargs: object) -> None:
        pytest.fail("disabled start called provider preflight")

    monkeypatch.setattr(
        storage_config,
        "preflight_tool_repository",
        unexpected_preflight,
    )
    run_id = "disabled-lifecycle"

    assert (
        run_lifecycle.start_main(
            [
                "--repo-root",
                str(repo),
                "--skill",
                "status",
                "--run-id",
                run_id,
            ]
        )
        == 0
    )
    started_output = capsys.readouterr()
    assert started_output.err == (
        "**⚠ Run-log publication is disabled (config-file-missing). This skill "
        "will run, but no remote run-log archive or synchronized cache entry "
        "will be created.**\n"
    )
    start_values = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in started_output.out.splitlines()
        if "=" in line
    }
    assert start_values["RUN_LOG_STORAGE"] == "disabled"
    assert start_values["STORAGE_PREFLIGHT"] == "skipped-disabled"
    assert start_values["PREFLIGHT_OK"] == "true"
    assert start_values["TOOL_REPO_URI"] == ""
    run_dir = Path(start_values["RUN_DIR"])
    context_file = Path(start_values["CONTEXT_FILE"])

    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://newly-configured"\n',
        encoding="utf-8",
    )

    def unexpected_publish(**_kwargs: object) -> tuple[object, int]:
        pytest.fail("disabled terminalization called archive publication")

    monkeypatch.setattr(run_log_publish, "publish_log_run", unexpected_publish)

    assert (
        run_lifecycle.finalize_main(
            [
                "--repo-root",
                str(repo),
                "--skill",
                "status",
                "--run-id",
                run_id,
            ]
        )
        == 0
    )
    terminal_output = capsys.readouterr()
    assert terminal_output.err == (
        "**⚠ Run-log publication skipped because storage was disabled at "
        "lifecycle start (config-file-missing).**\n"
    )
    terminal_lines = terminal_output.out.splitlines()
    assert "RUN_LOG_PUBLICATION=skipped-disabled" in terminal_lines
    assert "LIFECYCLE_FLUSHED=false" in terminal_lines
    assert "LIFECYCLE_TERMINALIZED=true" in terminal_lines
    assert not any(
        line.startswith(("REMOTE_KEY=", "ARCHIVE_SHA256=", "CACHE_DIR="))
        for line in terminal_lines
    )
    assert not run_dir.exists()
    assert not context_file.exists()


def test_disabled_nested_lifecycle_preserves_parent_metadata(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
) -> None:
    repo, environment, _storage_root = lifecycle_fixture
    _ = subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:fixture/consumer.git"],
        cwd=repo,
        check=True,
    )
    parent = run_lifecycle.start_run(
        repo_root=repo,
        skill="implement",
        run_id="disabled-parent",
        environ=environment,
    )
    child = run_lifecycle.start_run(
        repo_root=repo,
        skill="review",
        run_id="disabled-child",
        parent_context=parent.context_file,
        environ=environment,
    )

    child_manifest = json.loads(
        (child.run_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert parent.storage_resolution.mode == "disabled"
    assert child.storage_resolution.mode == "disabled"
    assert child.run_id != parent.run_id
    assert child_manifest["parent_skill"] == parent.skill
    assert child_manifest["parent_run_id"] == parent.run_id


@pytest.mark.parametrize(
    "outcome", ["success", "failure", "cancelled", "early-return"]
)
def test_disabled_lifecycle_terminalizes_every_outcome_without_publication(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    repo, environment, _storage_root = lifecycle_fixture
    _ = subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:fixture/consumer.git"],
        cwd=repo,
        check=True,
    )
    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="status",
        run_id=f"disabled-{outcome}",
        environ=environment,
    )

    def unexpected_publish(**_kwargs: object) -> tuple[object, int]:
        pytest.fail("disabled terminalization called publication")

    monkeypatch.setattr(run_log_publish, "publish_log_run", unexpected_publish)
    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill=started.skill,
        run_id=started.run_id,
        outcome=outcome,
        environ=environment,
    )

    assert terminal.outcome == outcome
    assert terminal.storage_mode == "disabled"
    assert terminal.publication is None
    assert not started.run_dir.exists()
    assert not started.context_file.exists()


@pytest.mark.parametrize(
    "error",
    [
        run_log_publish.PublicationError("broken publication invariant"),
        tarfile.TarError("broken archive"),
    ],
)
def test_terminal_cli_converts_publication_exceptions_to_loud_failure(
    lifecycle_fixture: tuple[Path, dict[str, str], ToolRepositoryStorage],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    repo, _environment, _storage_root = lifecycle_fixture

    def fail_finish(**_kwargs: object) -> run_lifecycle.LifecycleTerminal:
        raise error

    monkeypatch.setattr(run_lifecycle, "finish_run", fail_finish)

    rc = run_lifecycle.finalize_main(
        ["--repo-root", str(repo), "--skill", "status", "--run-id", "run-id"]
    )

    captured = capsys.readouterr()
    assert rc != 0
    assert captured.out.splitlines() == [
        "RUN_LOG_PUBLICATION=failed",
        "LIFECYCLE_FLUSHED=false",
        "LIFECYCLE_TERMINALIZED=false",
    ]
    assert "run lifecycle finalize failed" in captured.err
