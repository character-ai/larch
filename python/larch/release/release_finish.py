"""Stage, validate, and publish an immutable GitHub Release."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from larch.core import proc, redact
from larch.core.repo_roots import larch_entrypoint
from larch.git import gh
from larch.release import assets

_API_VERSION: Final = "2026-03-10"
_ASSET_WORKFLOW: Final = "rust-release-assets.yaml"
_ASSET_SIGNER_WORKFLOW: Final = ".github/workflows/rust-release-assets.yaml"
_REPO_RE: Final = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_SEMVER_RE: Final = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
_TAG_RE: Final = re.compile(
    r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
_SHA_RE: Final = re.compile(r"[0-9a-f]{40}")
_DIGEST_RE: Final = re.compile(r"sha256:([0-9a-f]{64})")
_LS_REMOTE_FIELD_COUNT: Final = 2

JsonObject = dict[str, object]


class ReleaseError(RuntimeError):
    """A release state transition failed closed."""


@dataclass(frozen=True)
class PullRequestState:
    state: str
    head_oid: str


@dataclass(frozen=True)
class RemoteAsset:
    name: str
    size: int
    digest: str
    state: str


@dataclass(frozen=True)
class ReleaseState:
    database_id: int
    tag: str
    draft: bool
    immutable: bool
    assets: tuple[RemoteAsset, ...]


@dataclass(frozen=True)
class CandidateRequest:
    version: str
    repo: str
    pr: int
    cwd: Path

    @property
    def tag(self) -> str:
        return f"v{self.version}"


@dataclass(frozen=True)
class ReleaseCandidate:
    version: str
    repo: str
    pr: int
    source_commit: str
    cwd: Path

    @property
    def tag(self) -> str:
        return f"v{self.version}"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _origin_repo(root: Path, runner: proc.Runner) -> str:
    override = os.environ.get("LARCH_RELEASE_FINISH_ORIGIN_REPO", "")
    if override:
        return override
    result = runner.run(
        [str(larch_entrypoint(root)), "gh", "remote-repo", "origin"],
        cwd=str(root),
    )
    if result.returncode != 0 or not _REPO_RE.fullmatch(result.stdout.strip()):
        raise ReleaseError("origin repository could not be resolved")
    return result.stdout.strip()


def _gh(runner: proc.Runner, argv: list[str], *, cwd: Path) -> proc.CommandResult:
    return gh.command(runner, argv, cwd=str(cwd))


def _git(runner: proc.Runner, argv: list[str], *, cwd: Path) -> proc.CommandResult:
    return runner.run(["git", *argv], cwd=str(cwd))


def _require_success(result: proc.CommandResult, label: str) -> proc.CommandResult:
    if result.returncode != 0:
        diagnostic = redact.redact_outbound(result.stderr or result.stdout).replace(
            "\n", " "
        )[:500]
        raise ReleaseError(f"{label} failed: {diagnostic or 'no diagnostic'}")
    return result


@contextlib.contextmanager
def _redacted_notes(notes_file: Path) -> Generator[Path, None, None]:
    text = notes_file.read_text(encoding="utf-8")
    scrubbed = redact.redact(redact.redact_tmpdir_paths(text))
    with tempfile.TemporaryDirectory(
        prefix="larch-release-notes-",
        dir=tempfile.gettempdir(),
    ) as temporary:
        redacted_path = Path(temporary) / "notes.md"
        _ = redacted_path.write_text(scrubbed, encoding="utf-8")
        yield redacted_path


def _json_object(result: proc.CommandResult, label: str) -> JsonObject:
    _ = _require_success(result, label)
    try:
        value = cast("object", json.loads(result.stdout))
    except json.JSONDecodeError as error:
        raise ReleaseError(f"{label} returned invalid JSON") from error
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} returned a non-object JSON value")
    return cast("JsonObject", value)


def _json_array(result: proc.CommandResult, label: str) -> list[object]:
    _ = _require_success(result, label)
    try:
        value = cast("object", json.loads(result.stdout))
    except json.JSONDecodeError as error:
        raise ReleaseError(f"{label} returned invalid JSON") from error
    if not isinstance(value, list):
        raise ReleaseError(f"{label} returned a non-array JSON value")
    return cast("list[object]", value)


def _validated_args(version: str, repo: str, pr: str) -> tuple[str, int]:
    if _SEMVER_RE.fullmatch(version) is None:
        raise ReleaseError(f"invalid semver: {version}")
    if _REPO_RE.fullmatch(repo) is None:
        raise ReleaseError(f"invalid repository: {repo}")
    if not pr.isdigit() or int(pr) <= 0:
        raise ReleaseError(f"invalid PR number: {pr}")
    return f"v{version}", int(pr)


def _pr_state(
    runner: proc.Runner, *, repo: str, pr: int, cwd: Path
) -> PullRequestState:
    data = _json_object(
        _gh(
            runner,
            ["pr", "view", str(pr), "--repo", repo, "--json", "state,headRefOid"],
            cwd=cwd,
        ),
        "PR read",
    )
    state = data.get("state")
    head_oid = data.get("headRefOid")
    if (
        not isinstance(state, str)
        or not isinstance(head_oid, str)
        or _SHA_RE.fullmatch(head_oid) is None
    ):
        raise ReleaseError("PR state has invalid or missing fields")
    return PullRequestState(state=state, head_oid=head_oid)


def _plugin_version_at(runner: proc.Runner, *, oid: str, cwd: Path) -> str:
    result = _require_success(
        _git(runner, ["show", f"{oid}:.claude-plugin/plugin.json"], cwd=cwd),
        f"plugin.json read at {oid}",
    )
    try:
        data = cast("object", json.loads(result.stdout))
    except json.JSONDecodeError as error:
        raise ReleaseError(f"plugin.json at {oid} is invalid JSON") from error
    if not isinstance(data, dict):
        raise ReleaseError(f"plugin.json at {oid} has no version")
    typed_data = cast("dict[str, object]", data)
    version = typed_data.get("version")
    if not isinstance(version, str):
        raise ReleaseError(f"plugin.json at {oid} has no version")
    return version


def _remote_tag_oid(runner: proc.Runner, *, tag: str, cwd: Path) -> str:
    result = _require_success(
        _git(
            runner,
            ["ls-remote", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            cwd=cwd,
        ),
        "remote tag read",
    )
    direct = ""
    peeled = ""
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != _LS_REMOTE_FIELD_COUNT:
            continue
        if fields[1] == f"refs/tags/{tag}^{{}}":
            peeled = fields[0]
        elif fields[1] == f"refs/tags/{tag}":
            direct = fields[0]
    oid = peeled or direct
    if oid and _SHA_RE.fullmatch(oid) is None:
        raise ReleaseError("remote tag resolved to an invalid object ID")
    return oid


def _asset_from_json(value: object) -> RemoteAsset:
    if not isinstance(value, dict):
        raise ReleaseError("release asset metadata is not an object")
    typed_value = cast("dict[str, object]", value)
    name = typed_value.get("name")
    size = typed_value.get("size")
    digest = typed_value.get("digest")
    state = typed_value.get("state")
    if not isinstance(name, str):
        raise ReleaseError("release asset metadata has no name")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ReleaseError(f"release asset metadata has invalid size: {name}")
    if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
        raise ReleaseError(f"release asset metadata has invalid digest: {name}")
    if state != "uploaded":
        raise ReleaseError(f"release asset is not uploaded: {name}")
    return RemoteAsset(name=name, size=size, digest=digest, state="uploaded")


def _release_data_for_tag(releases: list[object], *, tag: str) -> JsonObject | None:
    matches: list[JsonObject] = []
    for value in releases:
        if not isinstance(value, dict):
            raise ReleaseError("release list contains a non-object entry")
        typed_value = cast("JsonObject", value)
        if typed_value.get("tag_name") == tag:
            matches.append(typed_value)
    if len(matches) > 1:
        raise ReleaseError(f"multiple releases found for tag {tag}")
    return matches[0] if matches else None


def _release_state(
    runner: proc.Runner,
    *,
    repo: str,
    tag: str,
    cwd: Path,
    missing_ok: bool = False,
) -> ReleaseState | None:
    # The active candidate is newly created. One bounded page includes it and any
    # duplicate drafts without rescanning the repository's full release history.
    releases = _json_array(
        _gh(
            runner,
            [
                "api",
                "-H",
                f"X-GitHub-Api-Version: {_API_VERSION}",
                f"repos/{repo}/releases?per_page=100",
            ],
            cwd=cwd,
        ),
        "release list read",
    )
    data = _release_data_for_tag(releases, tag=tag)
    if data is None:
        if missing_ok:
            return None
        raise ReleaseError(f"release {tag} was not found")
    database_id = data.get("id")
    tag_name = data.get("tag_name")
    draft = data.get("draft")
    immutable = data.get("immutable")
    raw_assets = data.get("assets")
    if not isinstance(database_id, int) or isinstance(database_id, bool):
        raise ReleaseError("release state has an invalid database ID")
    if tag_name != tag:
        raise ReleaseError("release state has an invalid tag")
    if not isinstance(draft, bool) or not isinstance(immutable, bool):
        raise ReleaseError("release state has invalid mutability fields")
    if not isinstance(raw_assets, list):
        raise ReleaseError("release state has an invalid asset list")
    typed_assets = cast("list[object]", raw_assets)
    parsed_assets = tuple(_asset_from_json(value) for value in typed_assets)
    return ReleaseState(database_id, tag, draft, immutable, parsed_assets)


def _verify_policy(runner: proc.Runner, *, repo: str, cwd: Path) -> None:
    repository = _json_object(
        _gh(runner, ["api", f"repos/{repo}"], cwd=cwd),
        "repository policy read",
    )
    if repository.get("allow_merge_commit") is not True:
        raise ReleaseError("repository merge commits are not enabled")
    immutable = _json_object(
        _gh(
            runner,
            [
                "api",
                "-H",
                f"X-GitHub-Api-Version: {_API_VERSION}",
                f"repos/{repo}/immutable-releases",
            ],
            cwd=cwd,
        ),
        "immutable release policy read",
    )
    if immutable.get("enabled") is not True:
        raise ReleaseError("immutable releases are not enabled")


def ensure_policy(*, runner: proc.Runner, repo: str, cwd: Path) -> None:
    if _REPO_RE.fullmatch(repo) is None:
        raise ReleaseError(f"invalid repository: {repo}")
    _ = _require_success(
        _gh(
            runner,
            [
                "api",
                "--method",
                "PATCH",
                f"repos/{repo}",
                "-F",
                "allow_merge_commit=true",
            ],
            cwd=cwd,
        ),
        "enable merge commits",
    )
    _ = _require_success(
        _gh(
            runner,
            [
                "api",
                "--method",
                "PUT",
                "-H",
                f"X-GitHub-Api-Version: {_API_VERSION}",
                f"repos/{repo}/immutable-releases",
            ],
            cwd=cwd,
        ),
        "enable immutable releases",
    )
    _verify_policy(runner, repo=repo, cwd=cwd)


def _stage_tag(runner: proc.Runner, *, tag: str, source_commit: str, cwd: Path) -> None:
    remote_oid = _remote_tag_oid(runner, tag=tag, cwd=cwd)
    if remote_oid and remote_oid != source_commit:
        raise ReleaseError(
            f"remote tag {tag} points at {remote_oid}, not {source_commit}"
        )
    if not remote_oid:
        local = _git(runner, ["rev-parse", "--verify", f"{tag}^{{commit}}"], cwd=cwd)
        if local.returncode == 0 and local.stdout.strip() != source_commit:
            raise ReleaseError(f"local tag {tag} points at a different commit")
        if local.returncode != 0:
            _ = _require_success(
                _git(runner, ["tag", tag, source_commit], cwd=cwd), "local tag create"
            )
        _ = _require_success(
            _git(
                runner, ["push", "origin", f"refs/tags/{tag}:refs/tags/{tag}"], cwd=cwd
            ),
            "tag push",
        )
    if _remote_tag_oid(runner, tag=tag, cwd=cwd) != source_commit:
        raise ReleaseError("remote tag postcondition failed")


def stage_candidate(
    *,
    runner: proc.Runner,
    request: CandidateRequest,
    notes_file: Path,
) -> str:
    _verify_policy(runner, repo=request.repo, cwd=request.cwd)
    pr_state = _pr_state(runner, repo=request.repo, pr=request.pr, cwd=request.cwd)
    if pr_state.state != "OPEN":
        raise ReleaseError("release candidate PR must be open while staging")
    source_commit = pr_state.head_oid
    if (
        _plugin_version_at(runner, oid=source_commit, cwd=request.cwd)
        != request.version
    ):
        raise ReleaseError(
            "release candidate plugin version does not match the requested version"
        )
    _stage_tag(runner, tag=request.tag, source_commit=source_commit, cwd=request.cwd)
    with _redacted_notes(notes_file) as redacted_notes:
        release = _release_state(
            runner,
            repo=request.repo,
            tag=request.tag,
            cwd=request.cwd,
            missing_ok=True,
        )
        if release is None:
            _ = _require_success(
                _gh(
                    runner,
                    [
                        "release",
                        "create",
                        request.tag,
                        "--repo",
                        request.repo,
                        "--draft",
                        "--verify-tag",
                        "--latest=false",
                        "--title",
                        request.tag,
                        "--notes-file",
                        str(redacted_notes),
                    ],
                    cwd=request.cwd,
                ),
                "draft release create",
            )
        elif release.draft and not release.immutable:
            _ = _require_success(
                _gh(
                    runner,
                    [
                        "release",
                        "edit",
                        request.tag,
                        "--repo",
                        request.repo,
                        "--title",
                        request.tag,
                        "--notes-file",
                        str(redacted_notes),
                    ],
                    cwd=request.cwd,
                ),
                "draft release notes update",
            )
        release = _release_state(
            runner,
            repo=request.repo,
            tag=request.tag,
            cwd=request.cwd,
        )
    if release is None or not release.draft or release.immutable:
        raise ReleaseError("staged release is not a mutable draft")
    return source_commit


def resolve_asset_run(
    *, runner: proc.Runner, repo: str, tag: str, source_commit: str, cwd: Path
) -> tuple[int, str]:
    runs = _json_array(
        _gh(
            runner,
            [
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                _ASSET_WORKFLOW,
                "--branch",
                tag,
                "--event",
                "push",
                "--commit",
                source_commit,
                "--limit",
                "10",
                "--json",
                "databaseId,headSha,url",
            ],
            cwd=cwd,
        ),
        "asset workflow run read",
    )
    matches: list[tuple[int, str]] = []
    for value in runs:
        if not isinstance(value, dict):
            continue
        typed_value = cast("dict[str, object]", value)
        if typed_value.get("headSha") != source_commit:
            continue
        database_id = typed_value.get("databaseId")
        url = typed_value.get("url")
        if (
            isinstance(database_id, int)
            and not isinstance(database_id, bool)
            and isinstance(url, str)
        ):
            matches.append((database_id, url))
    if not matches:
        raise ReleaseError("tag-triggered asset workflow run is not registered")
    return max(matches, key=lambda item: item[0])


def _download_assets(
    runner: proc.Runner,
    *,
    candidate: ReleaseCandidate,
    names: tuple[str, ...],
    destination: Path,
) -> None:
    for name in names:
        _ = _require_success(
            _gh(
                runner,
                [
                    "release",
                    "download",
                    candidate.tag,
                    "--repo",
                    candidate.repo,
                    "--dir",
                    str(destination),
                    "--pattern",
                    name,
                ],
                cwd=candidate.cwd,
            ),
            f"download release asset {name}",
        )


def _verify_artifact_attestations(
    runner: proc.Runner,
    *,
    candidate: ReleaseCandidate,
    paths: tuple[Path, ...],
) -> None:
    signer = f"{candidate.repo}/{_ASSET_SIGNER_WORKFLOW}"
    for path in paths:
        _ = _require_success(
            _gh(
                runner,
                [
                    "attestation",
                    "verify",
                    str(path),
                    "--repo",
                    candidate.repo,
                    "--signer-workflow",
                    signer,
                    "--source-ref",
                    f"refs/tags/{candidate.tag}",
                    "--source-digest",
                    candidate.source_commit,
                    "--deny-self-hosted-runners",
                ],
                cwd=candidate.cwd,
            ),
            f"artifact attestation verify {path.name}",
        )


def validate_release_assets(
    *,
    runner: proc.Runner,
    candidate: ReleaseCandidate,
    require_draft: bool | None,
) -> ReleaseState:
    _verify_policy(runner, repo=candidate.repo, cwd=candidate.cwd)
    pr_state = _pr_state(
        runner, repo=candidate.repo, pr=candidate.pr, cwd=candidate.cwd
    )
    if pr_state.head_oid != candidate.source_commit:
        raise ReleaseError(
            "release candidate PR head changed after the tag was created"
        )
    if (
        _remote_tag_oid(runner, tag=candidate.tag, cwd=candidate.cwd)
        != candidate.source_commit
    ):
        raise ReleaseError("release tag no longer names the candidate commit")
    release = _release_state(
        runner,
        repo=candidate.repo,
        tag=candidate.tag,
        cwd=candidate.cwd,
    )
    if release is None:
        raise ReleaseError("release is missing")
    if require_draft is True and (not release.draft or release.immutable):
        raise ReleaseError("release must remain a mutable draft before merge")
    if require_draft is False and (release.draft or not release.immutable):
        raise ReleaseError("published release must be immutable")
    identity = assets.release_identity(
        candidate.version,
        candidate.tag,
        candidate.source_commit,
    )
    expected_names = assets.expected_asset_names(identity)
    actual_names = tuple(asset.name for asset in release.assets)
    if len(set(actual_names)) != len(actual_names) or set(actual_names) != set(
        expected_names
    ):
        raise ReleaseError(
            f"release asset allowlist mismatch: missing={sorted(set(expected_names) - set(actual_names))}, "
            f"unexpected={sorted(set(actual_names) - set(expected_names))}"
        )
    metadata_by_name = {asset.name: asset for asset in release.assets}
    with tempfile.TemporaryDirectory(
        prefix="larch-release-validate-",
        dir=tempfile.gettempdir(),
    ) as temporary:
        asset_dir = Path(temporary) / "assets"
        asset_dir.mkdir(mode=0o700)
        _download_assets(
            runner,
            candidate=candidate,
            names=expected_names,
            destination=asset_dir,
        )
        downloaded = tuple(asset_dir / name for name in expected_names)
        for path in downloaded:
            metadata = metadata_by_name[path.name]
            if path.stat().st_size != metadata.size:
                raise ReleaseError(f"release asset size mismatch: {path.name}")
            digest_match = _DIGEST_RE.fullmatch(metadata.digest)
            if digest_match is None or assets.sha256_file(path) != digest_match.group(
                1
            ):
                raise ReleaseError(f"release asset digest mismatch: {path.name}")
        license_result = _require_success(
            _git(
                runner,
                ["show", f"{candidate.source_commit}:LICENSE"],
                cwd=candidate.cwd,
            ),
            "candidate LICENSE read",
        )
        license_path = Path(temporary) / "LICENSE"
        _ = license_path.write_text(license_result.stdout, encoding="utf-8")
        assets.validate_assets(
            output_dir=asset_dir, license_path=license_path, identity=identity
        )
        _verify_artifact_attestations(
            runner,
            candidate=candidate,
            paths=downloaded,
        )
    return release


def _verify_release_attestation(
    *, runner: proc.Runner, candidate: ReleaseCandidate
) -> None:
    _ = _require_success(
        _gh(
            runner,
            [
                "release",
                "verify",
                candidate.tag,
                "--repo",
                candidate.repo,
                "--format",
                "json",
            ],
            cwd=candidate.cwd,
        ),
        "immutable release attestation verify",
    )
    identity = assets.release_identity(
        candidate.version,
        candidate.tag,
        candidate.source_commit,
    )
    with tempfile.TemporaryDirectory(
        prefix="larch-release-attestation-",
        dir=tempfile.gettempdir(),
    ) as temporary:
        destination = Path(temporary)
        names = assets.expected_asset_names(identity)
        _download_assets(
            runner,
            candidate=candidate,
            names=names,
            destination=destination,
        )
        for name in names:
            _ = _require_success(
                _gh(
                    runner,
                    [
                        "release",
                        "verify-asset",
                        candidate.tag,
                        str(destination / name),
                        "--repo",
                        candidate.repo,
                        "--format",
                        "json",
                    ],
                    cwd=candidate.cwd,
                ),
                f"immutable release asset verify {name}",
            )
    _ = validate_release_assets(
        runner=runner,
        candidate=candidate,
        require_draft=False,
    )


def _is_latest(runner: proc.Runner, *, repo: str, tag: str, cwd: Path) -> bool:
    result = _require_success(
        _gh(
            runner,
            [
                "release",
                "list",
                "--repo",
                repo,
                "--limit",
                "100",
                "--json",
                "tagName,isLatest",
            ],
            cwd=cwd,
        ),
        "Latest release read",
    )
    releases = _json_array(result, "Latest release read")
    for value in releases:
        if not isinstance(value, dict):
            continue
        typed_value = cast("dict[str, object]", value)
        if typed_value.get("tagName") != tag:
            continue
        latest = typed_value.get("isLatest")
        if isinstance(latest, bool):
            return latest
        raise ReleaseError("Latest release state is missing")
    raise ReleaseError(f"release {tag} was not found in the release list")


def finish_release(*, runner: proc.Runner, candidate: ReleaseCandidate) -> str:
    _ = _require_success(
        _git(runner, ["fetch", "origin", "main"], cwd=candidate.cwd),
        "origin/main fetch",
    )
    pr_state = _pr_state(
        runner,
        repo=candidate.repo,
        pr=candidate.pr,
        cwd=candidate.cwd,
    )
    if pr_state.state != "MERGED" or pr_state.head_oid != candidate.source_commit:
        raise ReleaseError("release candidate PR is not merged at the tagged commit")
    if (
        _git(
            runner,
            ["merge-base", "--is-ancestor", candidate.source_commit, "origin/main"],
            cwd=candidate.cwd,
        ).returncode
        != 0
    ):
        raise ReleaseError("tagged release candidate is not an ancestor of origin/main")
    if (
        _plugin_version_at(
            runner,
            oid=candidate.source_commit,
            cwd=candidate.cwd,
        )
        != candidate.version
    ):
        raise ReleaseError("plugin version at the release tag does not match")
    if (
        _plugin_version_at(runner, oid="origin/main", cwd=candidate.cwd)
        != candidate.version
    ):
        raise ReleaseError(
            "plugin version on origin/main does not match the release tag"
        )
    release = _release_state(
        runner,
        repo=candidate.repo,
        tag=candidate.tag,
        cwd=candidate.cwd,
    )
    if release is None:
        raise ReleaseError("staged release is missing")
    action = "resume-published"
    if release.draft:
        _ = validate_release_assets(
            runner=runner,
            candidate=candidate,
            require_draft=True,
        )
        _ = _require_success(
            _gh(
                runner,
                [
                    "release",
                    "edit",
                    candidate.tag,
                    "--repo",
                    candidate.repo,
                    "--draft=false",
                    "--latest=false",
                    "--prerelease=false",
                ],
                cwd=candidate.cwd,
            ),
            "publish immutable release",
        )
        action = "publish"
    _verify_release_attestation(
        runner=runner,
        candidate=candidate,
    )
    if not _is_latest(
        runner,
        repo=candidate.repo,
        tag=candidate.tag,
        cwd=candidate.cwd,
    ):
        _ = _require_success(
            _gh(
                runner,
                [
                    "release",
                    "edit",
                    candidate.tag,
                    "--repo",
                    candidate.repo,
                    "--latest",
                    "--prerelease=false",
                ],
                cwd=candidate.cwd,
            ),
            "promote immutable release to Latest",
        )
    if not _is_latest(
        runner,
        repo=candidate.repo,
        tag=candidate.tag,
        cwd=candidate.cwd,
    ):
        raise ReleaseError("Latest release promotion postcondition failed")
    return action


def ensure_policy_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release ensure-policy")
    _ = parser.add_argument("--repo", required=True)
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        if _origin_repo(root, proc) != args.repo:
            raise ReleaseError("origin repository does not match --repo")
        ensure_policy(runner=proc, repo=args.repo, cwd=root)
    except ReleaseError as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print("MERGE_COMMITS_ENABLED=true")
    print("IMMUTABLE_RELEASES_ENABLED=true")
    return 0


def stage_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release stage")
    _ = parser.add_argument("--version", required=True)
    _ = parser.add_argument("--notes-file", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--pr", required=True)
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        tag, pr = _validated_args(args.version, args.repo, args.pr)
        notes_file = Path(args.notes_file)
        if not notes_file.is_file() or notes_file.is_symlink():
            raise ReleaseError("notes file is missing or unsafe")
        if _origin_repo(root, proc) != args.repo:
            raise ReleaseError("origin repository does not match --repo")
        source_commit = stage_candidate(
            runner=proc,
            request=CandidateRequest(
                version=args.version,
                repo=args.repo,
                pr=pr,
                cwd=root,
            ),
            notes_file=notes_file,
        )
    except (OSError, ReleaseError, assets.AssetError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print(f"TAG={tag}")
    print(f"SOURCE_COMMIT={source_commit}")
    print("DRAFT_READY=true")
    return 0


def asset_run_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release asset-run")
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--tag", required=True)
    _ = parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        if (
            _REPO_RE.fullmatch(args.repo) is None
            or _TAG_RE.fullmatch(args.tag) is None
            or _SHA_RE.fullmatch(args.source_commit) is None
        ):
            raise ReleaseError("invalid release identity")
        if _origin_repo(root, proc) != args.repo:
            raise ReleaseError("origin repository does not match --repo")
        run_id, url = resolve_asset_run(
            runner=proc,
            repo=args.repo,
            tag=args.tag,
            source_commit=args.source_commit,
            cwd=root,
        )
    except ReleaseError as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print(f"ASSET_RUN_ID={run_id}")
    print(f"ASSET_RUN_URL={url}")
    return 0


def validate_draft_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release validate-draft")
    _ = parser.add_argument("--version", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--pr", required=True)
    _ = parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        tag, pr = _validated_args(args.version, args.repo, args.pr)
        if _SHA_RE.fullmatch(args.source_commit) is None:
            raise ReleaseError("invalid source commit")
        if _origin_repo(root, proc) != args.repo:
            raise ReleaseError("origin repository does not match --repo")
        _ = validate_release_assets(
            runner=proc,
            candidate=ReleaseCandidate(
                version=args.version,
                repo=args.repo,
                pr=pr,
                source_commit=args.source_commit,
                cwd=root,
            ),
            require_draft=True,
        )
    except (OSError, ReleaseError, assets.AssetError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print(f"TAG={tag}")
    print(f"SOURCE_COMMIT={args.source_commit}")
    print("DRAFT_ASSETS_VALID=true")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release finish")
    _ = parser.add_argument("--version", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--pr", required=True)
    _ = parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    root = _repo_root()
    try:
        tag, pr = _validated_args(args.version, args.repo, args.pr)
        if _SHA_RE.fullmatch(args.source_commit) is None:
            raise ReleaseError("invalid source commit")
        if _origin_repo(root, proc) != args.repo:
            raise ReleaseError("origin repository does not match --repo")
        action = finish_release(
            runner=proc,
            candidate=ReleaseCandidate(
                version=args.version,
                repo=args.repo,
                pr=pr,
                source_commit=args.source_commit,
                cwd=root,
            ),
        )
    except (OSError, ReleaseError, assets.AssetError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print(f"RELEASE_ACTION={action}")
    print(f"SOURCE_COMMIT={args.source_commit}")
    print(f"TAG={tag}")
    print(f"VERSION={args.version}")
    print("IMMUTABLE_RELEASE_VALID=true")
    print("LATEST=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
