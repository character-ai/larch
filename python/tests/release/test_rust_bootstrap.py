"""Rust clean-install bootstrap, verification, locking, and attack coverage."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from larch.release import assets

VERSION = "1.2.3"
TAG = f"v{VERSION}"
SOURCE_COMMIT = "a" * 40
REPO_ROOT = Path(__file__).parents[3]
SCRIPT = REPO_ROOT / "scripts" / "larch.sh"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
RELEASE_SKILL = REPO_ROOT / ".claude" / "skills" / "release" / "SKILL.md"
PREFLIGHT_STDOUT = f"LARCH_PREFLIGHT_PIN_VERIFIED=true\nLARCH_PREFLIGHT_VERSION={VERSION}\n"


@dataclass(frozen=True)
class BootstrapFixture:
    root: Path
    data: Path
    release: Path
    tools: Path
    log: Path
    target: str


def _fake_binary(version: str, target: str) -> bytes:
    return f"""#!/bin/sh
case "$1" in
  --version) printf 'larch {version}\\n' ;;
  bootstrap)
    [ "${{2:-}}" = self-check ] || exit 2
    printf '%s\\n' '{{"schema_version":1,"version":"{version}","target":"{target}"}}'
    ;;
  *) printf 'ran:%s\\n' "$*" ;;
esac
""".encode()


def _archive_bytes(
    binary: bytes,
    *,
    first_name: str = "larch",
    first_type: bytes = tarfile.REGTYPE,
    include_extra: bool = False,
) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(
        fileobj=tar_buffer, mode="w", format=tarfile.USTAR_FORMAT
    ) as archive:
        first = tarfile.TarInfo(first_name)
        first.mode = 0o755
        first.mtime = 0
        first.uid = 0
        first.gid = 0
        first.type = first_type
        if first_type == tarfile.REGTYPE:
            first.size = len(binary)
            archive.addfile(first, io.BytesIO(binary))
        elif first_type == tarfile.SYMTYPE:
            first.linkname = "LICENSE"
            archive.addfile(first)
        else:
            archive.addfile(first)

        license_info = tarfile.TarInfo("LICENSE")
        license_bytes = b"test license\n"
        license_info.mode = 0o644
        license_info.mtime = 0
        license_info.uid = 0
        license_info.gid = 0
        license_info.size = len(license_bytes)
        archive.addfile(license_info, io.BytesIO(license_bytes))

        if include_extra:
            extra = tarfile.TarInfo("unexpected")
            extra.mode = 0o644
            extra.mtime = 0
            extra.uid = 0
            extra.gid = 0
            extra.size = 1
            archive.addfile(extra, io.BytesIO(b"x"))

    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_buffer, mtime=0) as output:
        _ = output.write(tar_buffer.getvalue())
    return gzip_buffer.getvalue()


def _manifest(release: Path) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for target in assets.TARGETS:
        archive_name = f"larch-v{VERSION}-{target}.tar.gz"
        archive_data = (release / archive_name).read_bytes()
        records.append(
            {
                "target": target,
                "archive": archive_name,
                "byte_size": len(archive_data),
                "sha256": hashlib.sha256(archive_data).hexdigest(),
                "binary_path": "larch",
                "minimum_os_or_libc": assets.TARGET_CONTRACTS[target].to_json(),
            }
        )
    return {
        "schema_version": 1,
        "plugin_version": VERSION,
        "tag": TAG,
        "source_commit": SOURCE_COMMIT,
        "assets": records,
    }


def _refresh_metadata(release: Path, manifest: dict[str, object] | None = None) -> None:
    manifest_value = _manifest(release) if manifest is None else manifest
    manifest_path = release / f"larch-v{VERSION}-manifest.json"
    _ = manifest_path.write_text(
        json.dumps(manifest_value, indent=2) + "\n", encoding="utf-8"
    )
    names = [f"larch-v{VERSION}-{target}.tar.gz" for target in assets.TARGETS]
    names.append(manifest_path.name)
    checksums = "".join(
        f"{hashlib.sha256((release / name).read_bytes()).hexdigest()}  {name}\n"
        for name in names
    )
    _ = (release / f"larch-v{VERSION}-SHA256SUMS").write_text(
        checksums, encoding="ascii"
    )


def _write_tool(path: Path, text: str) -> None:
    _ = path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _stub_tools(tools: Path) -> None:
    tools.mkdir()
    _write_tool(
        tools / "uname",
        """#!/bin/sh
case "$1" in
  -s) printf '%s\\n' "$TEST_UNAME_S" ;;
  -m) printf '%s\\n' "$TEST_UNAME_M" ;;
  *) exit 2 ;;
esac
""",
    )
    _write_tool(
        tools / "gh",
        """#!/bin/sh
set -eu
if [ "$1:$2:${3:-}" = "release:verify:--help" ]; then
  printf 'verify release attestation\\n'
  exit 0
fi
if [ "$1:$2:${3:-}" = "attestation:verify:--help" ]; then
  printf 'verify artifact attestation\\n'
  exit 0
fi
if [ "$1:$2:${3:-}" = "release:view:--help" ]; then
  printf 'JSON FIELDS: isImmutable assets\\n'
  exit 0
fi
if [ "$1:$2" = "release:verify" ]; then
  [ "${GH_FAIL:-}" != release ]
  exit 0
fi
if [ "$1:$2" = "release:view" ]; then
  [ "${GH_FAIL:-}" != view ]
  printf '%s\\n' "v$TEST_VERSION" true false false \
    "larch-v$TEST_VERSION-aarch64-apple-darwin.tar.gz" \
    "larch-v$TEST_VERSION-manifest.json" \
    "larch-v$TEST_VERSION-SHA256SUMS"
  exit 0
fi
if [ "$1:$2" = "api:--help" ]; then
  printf 'GitHub API help\n'
  exit 0
fi
if [ "$1" = api ] && [ "$2" = --paginate ]; then
  printf '%s\\n' 'gh: Only the first 1000 results are available. (HTTP 422)' >&2
  exit 1
fi
if [ "$1" = api ]; then
  case "$2" in
    */releases/latest)
      printf 'latest-api:%s\\n' "$*" >> "$GH_LOG"
      printf '%s\\n' "v$TEST_VERSION"
      ;;
    */git/ref/heads/*) printf '%s\\n' "${TEST_PIN_COMMIT:-$TEST_SOURCE_COMMIT}" ;;
    *) printf '%s\\n' "$TEST_SOURCE_COMMIT" ;;
  esac
  exit 0
fi
if [ "$1:$2" = "release:download" ]; then
  [ "${GH_FAIL:-}" != download ]
  printf 'download\\n' >> "$GH_LOG"
  if [ "${GH_DOWNLOAD_DELAY:-0}" != 0 ]; then sleep "$GH_DOWNLOAD_DELAY"; fi
  download_dir=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = --dir ]; then
      download_dir="$2"
      shift 2
    else
      shift
    fi
  done
  cp "$TEST_RELEASE/larch-v$TEST_VERSION-manifest.json" "$download_dir/"
  cp "$TEST_RELEASE/larch-v$TEST_VERSION-SHA256SUMS" "$download_dir/"
  cp "$TEST_RELEASE/larch-v$TEST_VERSION-$TEST_TARGET.tar.gz" "$download_dir/"
  exit 0
fi
if [ "$1:$2" = "attestation:verify" ]; then
  [ "${GH_FAIL:-}" != attestation ]
  printf 'attestation\\n' >> "$GH_LOG"
  exit 0
fi
exit 2
""",
    )


def _fixture(
    tmp_path: Path, target: str = "aarch64-apple-darwin"
) -> BootstrapFixture:
    root = tmp_path / "plugin"
    data = tmp_path / "data"
    release = tmp_path / "release"
    tools = tmp_path / "tools"
    log = tmp_path / "gh.log"
    (root / ".claude-plugin").mkdir(parents=True)
    release.mkdir()
    _ = (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "larch", "version": VERSION}, indent=2) + "\n",
        encoding="utf-8",
    )
    for release_target in assets.TARGETS:
        archive_name = f"larch-v{VERSION}-{release_target}.tar.gz"
        _ = (release / archive_name).write_bytes(
            _archive_bytes(_fake_binary(VERSION, release_target))
        )
    _refresh_metadata(release)
    _stub_tools(tools)
    return BootstrapFixture(root, data, release, tools, log, target)


def _host_for_target(target: str) -> tuple[str, str]:
    mapping = {
        "aarch64-apple-darwin": ("Darwin", "arm64"),
        "x86_64-apple-darwin": ("Darwin", "x86_64"),
        "aarch64-unknown-linux-gnu": ("Linux", "aarch64"),
        "x86_64-unknown-linux-gnu": ("Linux", "x86_64"),
    }
    return mapping[target]


def _environment(fixture: BootstrapFixture, **updates: str) -> dict[str, str]:
    os_name, architecture = _host_for_target(fixture.target)
    environment: dict[str, str] = {
        **os.environ,
        "CLAUDE_PLUGIN_ROOT": str(fixture.root),
        "CLAUDE_PLUGIN_DATA": str(fixture.data),
        "GH_LOG": str(fixture.log),
        "PATH": f"{fixture.tools}:{os.environ['PATH']}",
        "TEST_RELEASE": str(fixture.release),
        "TEST_SOURCE_COMMIT": SOURCE_COMMIT,
        "TEST_TARGET": fixture.target,
        "TEST_UNAME_M": architecture,
        "TEST_UNAME_S": os_name,
        "TEST_VERSION": VERSION,
    }
    # These tests exercise the bootstrap's own install and verification path, so
    # the session-wide `LARCH_BINARY` double must not short-circuit it. Cases
    # that need an override pass one through `updates`.
    _ = environment.pop("LARCH_BINARY", None)
    environment.update(updates)
    return environment


def _run(
    fixture: BootstrapFixture,
    *arguments: str,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(SCRIPT), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=_environment(fixture) if environment is None else environment,
        timeout=20,
    )


@pytest.mark.parametrize("target", assets.TARGETS)
def test_clean_install_maps_every_supported_target_and_executes(
    target: str, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path, target)

    result = _run(fixture, "example", "echo", target)

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"ran:example echo {target}\n"
    assert (fixture.root / "bin" / "larch").is_file()
    assert fixture.log.read_text(encoding="utf-8").splitlines().count("download") == 1
    assert (
        fixture.log.read_text(encoding="utf-8").splitlines().count("attestation") == 3
    )


def test_release_preflight_verifies_without_touching_plugin_cache_root(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    marker = fixture.root / "prior-root-marker"
    _ = marker.write_text("unchanged", encoding="utf-8")

    result = _run(fixture, "--preflight-release", VERSION)

    assert result.returncode == 0, result.stderr
    assert result.stdout == PREFLIGHT_STDOUT
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert not (fixture.root / "bin").exists()
    assert not list(fixture.data.glob(".larch-bootstrap.*"))


def _pin_ref() -> str:
    """The branch token the bootstrap and the marketplace descriptor share."""
    match = re.search(
        r'^readonly RELEASE_PIN_REF="([^"]+)"$',
        SCRIPT.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match is not None, "scripts/larch.sh no longer declares RELEASE_PIN_REF"
    return match.group(1)


def test_bootstrap_and_descriptor_name_the_same_release_pin_branch() -> None:
    """One token for the pin: the descriptor's writer and the bootstrap's
    verifier must not drift (issue #8007, G-Cfg-3).
    """
    descriptor = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    source = next(
        plugin["source"]
        for plugin in descriptor["plugins"]
        if plugin["name"] == "larch"
    )

    assert source["source"] == "git-subdir"
    assert source["path"] == "plugin"
    assert source["ref"] == _pin_ref()


def test_pin_ref_cannot_collide_with_release_candidate_branches() -> None:
    """Git refs are paths: `refs/heads/<pin>` and `<pin>/v1.2.3` cannot coexist,
    so the pin must not be the first segment of a release candidate branch.
    """
    candidates = re.findall(
        r'git checkout -b "([^"$]+)', RELEASE_SKILL.read_text(encoding="utf-8")
    )
    assert candidates, "release SKILL.md no longer creates a candidate branch"

    pin = _pin_ref()
    for candidate in candidates:
        assert candidate.split("/")[0] != pin, (
            f"pin branch {pin!r} collides with candidate branch {candidate!r}"
        )


def test_release_pin_mismatch_fails_preflight_before_downloading_assets(
    tmp_path: Path,
) -> None:
    """The exact smarts#323 shape: the pinned branch trails the release being
    installed, so plugin content and executable would come from two commits.
    """
    fixture = _fixture(tmp_path)
    environment = _environment(fixture)
    environment["TEST_PIN_COMMIT"] = "b" * 40

    result = _run(fixture, "--preflight-release", VERSION, environment=environment)

    assert result.returncode == 1
    assert "come from different commits" in result.stderr
    assert f"refs/heads/{_pin_ref()}" in result.stderr
    assert "LARCH_PREFLIGHT_PIN_VERIFIED" not in result.stdout
    assert "LARCH_PREFLIGHT_VERSION" not in result.stdout
    assert not fixture.log.exists(), "no asset download or attestation should run"


def test_clean_install_does_not_gate_on_the_moving_release_pin(tmp_path: Path) -> None:
    """An install already at an older release must keep bootstrapping its own
    matching binary after the pin advances to a newer release.
    """
    fixture = _fixture(tmp_path)
    environment = _environment(fixture)
    environment["TEST_PIN_COMMIT"] = "b" * 40

    result = _run(fixture, "example", "echo", "ok", environment=environment)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "ran:example echo ok\n"
    assert (fixture.root / "bin" / "larch").is_file()


def _macos_shaped_tmpdir(tmp_path: Path) -> tuple[str, Path]:
    """A TMPDIR shaped like macOS: trailing slash, ancestor reached via a symlink.

    Mirrors /var -> private/var, where the real per-user temp directory lives.
    Returns the TMPDIR value and the symlink-free real directory.
    """
    real = tmp_path / "private" / "T"
    real.mkdir(parents=True)
    (tmp_path / "var").symlink_to(tmp_path / "private")
    return f"{tmp_path}/var/T/", real


def _fence_parent_block() -> str:
    """Extract the Step 7 fence's guarded PLUGIN_DATA_PARENT composition block."""
    lines = RELEASE_SKILL.read_text(encoding="utf-8").splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if line.strip() == 'PLUGIN_DATA_PARENT=""'
    ]
    assert len(starts) == 1, "Step 7 fence no longer initializes PLUGIN_DATA_PARENT once"
    end = next(
        index
        for index in range(starts[0], len(lines))
        if lines[index].strip() == "esac"
    )
    return "\n".join(lines[starts[0] : end + 1])


def _fence_bash(tmpdir_value: str, tail: str) -> str:
    """Run the fence's guarded parent composition plus a probe line in bash."""
    result = subprocess.run(
        ["/bin/bash", "-c", f"{_fence_parent_block()}\n{tail}"],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"], "TMPDIR": tmpdir_value},
        timeout=20,
    )
    return result.stdout


def _fence_composed_plugin_data(tmpdir_value: str) -> str:
    """Evaluate the release Step 7 fence's CLAUDE_PLUGIN_DATA composition in bash."""
    skill = RELEASE_SKILL.read_text(encoding="utf-8")
    composition = re.search(r'CLAUDE_PLUGIN_DATA="(\$\{PLUGIN_DATA_PARENT[^"]*)"', skill)
    assert composition is not None, "Step 7 fence no longer composes CLAUDE_PLUGIN_DATA"
    return _fence_bash(tmpdir_value, f'printf "%s" "{composition.group(1)}"')


def test_step7_fence_plugin_data_passes_preflight_with_symlinked_tmpdir(
    tmp_path: Path,
) -> None:
    """The fence composition survives the full symlink-ancestor walk (#7926)."""
    fixture = _fixture(tmp_path)
    tmpdir_value, real_parent = _macos_shaped_tmpdir(tmp_path)
    composed = _fence_composed_plugin_data(tmpdir_value)
    assert composed == f"{real_parent.resolve()}/larch-plugin-data"
    environment = _environment(fixture)
    environment["CLAUDE_PLUGIN_DATA"] = composed

    result = _run(fixture, "--preflight-release", VERSION, environment=environment)

    assert result.returncode == 0, result.stderr
    assert result.stdout == PREFLIGHT_STDOUT


def test_step7_fence_leaves_parent_empty_for_broken_or_relative_tmpdir(
    tmp_path: Path,
) -> None:
    """A missing or relative TMPDIR must not compose a misleading staging path;
    the fence leaves the parent empty and reports it instead (#7926 review).
    """
    probe = 'printf "%s" "$PLUGIN_DATA_PARENT"'
    assert _fence_bash(f"{tmp_path}/does-not-exist/", probe) == ""
    assert _fence_bash("relative-tmp", probe) == ""


def test_symlink_ancestor_plugin_data_fails_preflight_closed(tmp_path: Path) -> None:
    """Negative control replaying the v55.0.0 Step 7 failure: a TMPDIR-composed
    path whose ancestor is a symlink dies in the walk, proving the sibling
    positive test exercises the guard and not only the case-arm (#7926).
    """
    fixture = _fixture(tmp_path)
    tmpdir_value, _ = _macos_shaped_tmpdir(tmp_path)
    environment = _environment(fixture)
    # Pre-#7926 fence shape: TMPDIR taken verbatim, only the trailing slash trimmed.
    assert tmpdir_value.endswith("/")
    environment["CLAUDE_PLUGIN_DATA"] = f"{tmpdir_value.rstrip('/')}/larch-plugin-data"

    result = _run(fixture, "--preflight-release", VERSION, environment=environment)

    assert result.returncode == 1
    assert "is a symlink" in result.stderr
    assert f"{tmp_path}/var" in result.stderr
    assert not (fixture.root / "bin").exists()


def test_latest_stable_version_uses_one_bounded_latest_release_request(
    tmp_path: Path,
) -> None:
    """The latest endpoint avoids GitHub's 1,000-item pagination ceiling."""
    fixture = _fixture(tmp_path)

    result = _run(fixture, "--latest-stable-version")

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"LARCH_STABLE_VERSION={VERSION}\n"
    assert fixture.log.read_text(encoding="utf-8") == (
        "latest-api:api repos/character-ai/larch/releases/latest --jq .tag_name\n"
    )


@pytest.mark.parametrize(
    ("os_name", "architecture", "detail"),
    [
        ("FreeBSD", "x86_64", "architecture: FreeBSD/x86_64"),
        ("Darwin", "x86_64", "for release install: x86_64-apple-darwin"),
        ("Linux", "aarch64", "for release install: aarch64-unknown-linux-gnu"),
        ("Linux", "x86_64", "for release install: x86_64-unknown-linux-gnu"),
    ],
)
def test_unsupported_target_fails_with_retry_guidance(
    os_name: str, architecture: str, detail: str, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    environment = _environment(
        fixture, TEST_UNAME_S=os_name, TEST_UNAME_M=architecture
    )

    result = _run(fixture, environment=environment)

    assert result.returncode == 1
    assert "unsupported operating system or architecture" in result.stderr
    assert detail in result.stderr
    assert "Retry the command" in result.stderr
    assert not (fixture.root / "bin" / "larch").exists()


def test_larch_binary_override_works_on_non_release_hosts(tmp_path: Path) -> None:
    """A locally built binary keeps working where releases do not ship (#7921)."""
    fixture = _fixture(tmp_path, target="x86_64-unknown-linux-gnu")
    override = tmp_path / "built-larch"
    _ = override.write_bytes(_fake_binary(VERSION, fixture.target))
    override.chmod(0o755)
    environment = _environment(fixture, LARCH_BINARY=str(override))

    result = _run(fixture, "example", "echo", "linux-dev", environment=environment)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "ran:example echo linux-dev\n"
    assert not (fixture.root / "bin").exists()


def test_missing_required_tool_fails_closed_with_retry_guidance(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    isolated_tools = tmp_path / "isolated-tools"
    isolated_tools.mkdir()
    required = [
        "awk",
        "bash",
        "chmod",
        "cmp",
        "dd",
        "gzip",
        "ln",
        "mkdir",
        "mktemp",
        "mv",
        "rm",
        "rmdir",
        "sed",
        "sleep",
        "sort",
        "tar",
        "tr",
        "uname",
        "wc",
    ]
    sha_tool = "sha256sum" if shutil.which("sha256sum") is not None else "shasum"
    required.append(sha_tool)
    for command in required:
        source = shutil.which(command)
        assert source is not None
        (isolated_tools / command).symlink_to(source)
    environment = _environment(fixture)
    environment["PATH"] = str(isolated_tools)

    result = _run(fixture, environment=environment)

    assert result.returncode == 1
    assert "required tool is missing: gh" in result.stderr
    assert "Retry the command" in result.stderr


@pytest.mark.parametrize("failure", ["release", "view", "download", "attestation"])
def test_github_and_attestation_failures_leave_existing_binary_untouched(
    failure: str, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    binary = fixture.root / "bin" / "larch"
    binary.parent.mkdir()
    original = _fake_binary("1.2.2", fixture.target)
    _ = binary.write_bytes(original)
    binary.chmod(0o755)

    result = _run(fixture, environment=_environment(fixture, GH_FAIL=failure))

    assert result.returncode != 0
    assert "Retry the command" in result.stderr
    assert binary.read_bytes() == original
    assert not list(binary.parent.glob(".larch-bootstrap.*"))


def test_same_version_wrong_target_is_atomically_replaced(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    binary = fixture.root / "bin" / "larch"
    binary.parent.mkdir()
    _ = binary.write_bytes(_fake_binary(VERSION, "x86_64-apple-darwin"))
    binary.chmod(0o755)
    previous_inode = binary.stat().st_ino

    result = _run(fixture, "example", "echo", "replacement")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "ran:example echo replacement\n"
    assert binary.stat().st_ino != previous_inode
    assert fixture.log.read_text(encoding="utf-8").splitlines().count("download") == 1


def test_digest_mismatch_fails_before_replacement(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    archive = fixture.release / f"larch-v{VERSION}-{fixture.target}.tar.gz"
    _ = archive.write_bytes(archive.read_bytes() + b"corrupt")

    result = _run(fixture)

    assert result.returncode == 1
    assert "archive byte size does not match" in result.stderr
    assert not (fixture.root / "bin" / "larch").exists()


def test_manifest_schema_and_identity_are_strict(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    manifest = _manifest(fixture.release)
    manifest["unexpected"] = True
    _refresh_metadata(fixture.release, manifest)

    result = _run(fixture)

    assert result.returncode == 1
    assert "manifest violates the strict schema" in result.stderr


@pytest.mark.parametrize(
    ("first_name", "first_type", "include_extra"),
    [
        ("../larch", tarfile.REGTYPE, False),
        ("larch", tarfile.SYMTYPE, False),
        ("larch", tarfile.CHRTYPE, False),
        ("larch", tarfile.REGTYPE, True),
    ],
)
def test_archive_attacks_are_rejected(
    first_name: str, first_type: bytes, include_extra: bool, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    archive = fixture.release / f"larch-v{VERSION}-{fixture.target}.tar.gz"
    _ = archive.write_bytes(
        _archive_bytes(
            _fake_binary(VERSION, fixture.target),
            first_name=first_name,
            first_type=first_type,
            include_extra=include_extra,
        )
    )
    _refresh_metadata(fixture.release)

    result = _run(fixture)

    assert result.returncode == 1
    assert "archive" in result.stderr
    assert not (fixture.root / "bin" / "larch").exists()


def test_staged_version_mismatch_is_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    archive = fixture.release / f"larch-v{VERSION}-{fixture.target}.tar.gz"
    _ = archive.write_bytes(_archive_bytes(_fake_binary("9.9.9", fixture.target)))
    _refresh_metadata(fixture.release)

    result = _run(fixture)

    assert result.returncode == 1
    assert "staged executable reports the wrong version" in result.stderr


def test_dead_lock_is_recovered_and_waiter_installs(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    lock = fixture.data / "bootstrap.lock"
    lock.mkdir(parents=True)
    _ = (lock / "owner").write_text("999999999\n", encoding="ascii")

    result = _run(fixture, "example", "echo", "recovered")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "ran:example echo recovered\n"
    assert not lock.exists()


def test_concurrent_first_use_downloads_once(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    environment = _environment(fixture, GH_DOWNLOAD_DELAY="1")
    command = ["/bin/bash", str(SCRIPT), "example", "echo", "concurrent"]

    with (
        subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        ) as first,
        subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        ) as second,
    ):
        first_stdout, first_stderr = first.communicate(timeout=20)
        second_stdout, second_stderr = second.communicate(timeout=20)

    assert first.returncode == 0, first_stderr
    assert second.returncode == 0, second_stderr
    assert first_stdout == "ran:example echo concurrent\n"
    assert second_stdout == "ran:example echo concurrent\n"
    assert fixture.log.read_text(encoding="utf-8").splitlines().count("download") == 1


def test_interrupted_staging_is_ignored_and_only_owned_stage_is_cleaned(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    interrupted = fixture.root / "bin" / ".larch-bootstrap.interrupted"
    interrupted.mkdir(parents=True)
    _ = (interrupted / "partial").write_text(
        "keep for explicit cleanup\n", encoding="utf-8"
    )

    result = _run(fixture, "example", "echo", "fresh")

    assert result.returncode == 0, result.stderr
    assert (interrupted / "partial").is_file()
    owned_stages = [
        path
        for path in interrupted.parent.glob(".larch-bootstrap.*")
        if path != interrupted
    ]
    assert owned_stages == []


def test_local_plugin_dir_requires_explicit_matching_override(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    (fixture.root / ".git").mkdir()

    refused = _run(fixture)

    assert refused.returncode == 1
    assert "local --plugin-dir checkout needs an explicit build" in refused.stderr
    assert not (fixture.root / "bin").exists()

    override = tmp_path / "built-larch"
    _ = override.write_bytes(_fake_binary(VERSION, fixture.target))
    override.chmod(0o755)
    environment = _environment(fixture, LARCH_BINARY=str(override))
    accepted = _run(fixture, "example", "echo", "override", environment=environment)

    assert accepted.returncode == 0, accepted.stderr
    assert accepted.stdout == "ran:example echo override\n"
    assert not (fixture.root / "bin").exists()
