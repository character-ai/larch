"""Regression coverage for trusted main-cache candidate staging and promotion."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from larch.cli import _REGISTRY  # pyright: ignore[reportPrivateUsage]  # Dispatcher registry is the CLI contract.
from larch.implement import main_cache_candidate as candidate


_CACHE_CLASS = "coverage-target"
_CACHE_KEY = "coverage-target-deps-v1-Linux-X64-identity"
_ARTIFACT_NAME = "main-cache-coverage-target-candidate"
_PRODUCER_REF = "refs/heads/gh-readonly-queue/main/pr-8362-0123456789abcdef"
_SOURCE_SHA = "0123456789abcdef0123456789abcdef01234567"


def _request(tmp_path: Path, *, candidate_dir: Path | None = None) -> candidate.CandidateRequest:
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    (source / ".fingerprint").mkdir(exist_ok=True)
    _ = (source / ".fingerprint" / "dependency.json").write_text("dependency\n", encoding="utf-8")
    executable = source / "larch"
    _ = executable.write_bytes(b"#!/bin/sh\nprintf larch\n")
    executable.chmod(0o755)
    return candidate.CandidateRequest(
        artifact_name=_ARTIFACT_NAME,
        cache_class=_CACHE_CLASS,
        cache_key=_CACHE_KEY,
        candidate_dir=candidate_dir or tmp_path / "candidate",
        maximum_bytes=1024 * 1024,
        producer_event="merge_group",
        producer_job="rust-full",
        producer_ref=_PRODUCER_REF,
        source_sha=_SOURCE_SHA,
        sources=(candidate.CandidateSource(name="llvm-cov-target", path=source),),
        tool_versions={"cargo-llvm-cov": "cargo-llvm-cov 0.8.7", "rustc": "rustc test"},
    )


def _contract(request: candidate.CandidateRequest) -> candidate.CandidateContract:
    return candidate.CandidateContract(
        artifact_name=request.artifact_name,
        cache_class=request.cache_class,
        cache_key=request.cache_key,
        maximum_bytes=request.maximum_bytes,
        producer_job=request.producer_job,
        source_sha=request.source_sha,
        expected_tool_versions=request.tool_versions,
    )


def _read_manifest(path: Path) -> dict[str, object]:
    parsed: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    # json.loads returns an unparameterized dict; JSON object keys are strings.
    return cast("dict[str, object]", parsed)


def _alter_payload_member(candidate_dir: Path) -> None:
    _ = candidate_dir.joinpath("payload", "llvm-cov-target", "larch").write_bytes(b"altered")


def _replace_manifest_with_empty_object(candidate_dir: Path) -> None:
    _ = candidate_dir.joinpath("manifest.json").write_text("{}\n", encoding="utf-8")


def test_stage_and_promote_main_cache_candidate_rechecks_every_member(tmp_path: Path) -> None:
    request = _request(tmp_path)

    staged = candidate.stage_candidate(request)

    assert staged.cache_class == _CACHE_CLASS
    assert staged.artifact_name == _ARTIFACT_NAME
    assert staged.cache_key == _CACHE_KEY
    assert staged.producer_event == "merge_group"
    assert staged.producer_ref == _PRODUCER_REF
    manifest = _read_manifest(request.candidate_dir / "manifest.json")
    assert manifest["cache_key"] == _CACHE_KEY
    assert manifest["artifact_name"] == _ARTIFACT_NAME
    artifact_sha256 = manifest["artifact_sha256"]
    assert isinstance(artifact_sha256, str)
    assert len(artifact_sha256) == 64
    key_input_digest = manifest["key_input_digest"]
    assert isinstance(key_input_digest, str)
    assert len(key_input_digest) == 64
    assert manifest["producer_job"] == "rust-full"
    assert manifest["tool_versions"] == {
        "cargo-llvm-cov": "cargo-llvm-cov 0.8.7",
        "rustc": "rustc test",
    }

    output = tmp_path / "promoted"
    promoted = candidate.promote_candidate(
        candidate_dir=request.candidate_dir,
        output_dir=output,
        contract=_contract(request),
    )

    assert promoted.total_bytes == staged.total_bytes
    assert (output / "llvm-cov-target" / ".fingerprint" / "dependency.json").read_text(
        encoding="utf-8"
    ) == "dependency\n"
    assert (output / "llvm-cov-target" / "larch").stat().st_mode & 0o111


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (_alter_payload_member, "members do not match"),
        (_replace_manifest_with_empty_object, "unexpected schema"),
    ],
)
def test_promote_main_cache_candidate_rejects_tampered_artifact(
    tmp_path: Path,
    mutator: Callable[[Path], None],
    expected: str,
) -> None:
    request = _request(tmp_path)
    _ = candidate.stage_candidate(request)
    mutator(request.candidate_dir)

    with pytest.raises(candidate.CandidateError, match=expected):
        _ = candidate.promote_candidate(
            candidate_dir=request.candidate_dir,
            output_dir=tmp_path / "promoted",
            contract=_contract(request),
        )


@pytest.mark.parametrize(
    ("producer_event", "producer_ref", "expected"),
    [
        ("pull_request", _PRODUCER_REF, "producer event"),
        ("merge_group", "refs/heads/main", "producer ref"),
    ],
)
def test_stage_main_cache_candidate_accepts_only_merge_group_provenance(
    tmp_path: Path,
    producer_event: str,
    producer_ref: str,
    expected: str,
) -> None:
    request = _request(tmp_path)
    rejected = candidate.CandidateRequest(
        artifact_name=request.artifact_name,
        cache_class=request.cache_class,
        cache_key=request.cache_key,
        candidate_dir=request.candidate_dir,
        maximum_bytes=request.maximum_bytes,
        producer_event=producer_event,
        producer_job=request.producer_job,
        producer_ref=producer_ref,
        source_sha=request.source_sha,
        sources=request.sources,
        tool_versions=request.tool_versions,
    )

    with pytest.raises(candidate.CandidateError, match=expected):
        _ = candidate.stage_candidate(rejected)


def test_stage_main_cache_candidate_rejects_symlinked_source(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _ = target.write_text("target\n", encoding="utf-8")
    source = tmp_path / "source"
    source.mkdir()
    (source / "link").symlink_to(target)
    request = candidate.CandidateRequest(
        artifact_name="main-cache-cargo-inputs-candidate",
        cache_class="cargo-inputs",
        cache_key="cargo-inputs-v1-Linux-X64-identity",
        candidate_dir=tmp_path / "candidate",
        maximum_bytes=0,
        producer_event="merge_group",
        producer_job="rust-lint",
        producer_ref=_PRODUCER_REF,
        source_sha=_SOURCE_SHA,
        sources=(candidate.CandidateSource(name="registry", path=source),),
        tool_versions={"cargo": "cargo test"},
    )

    with pytest.raises(candidate.CandidateError, match="symlink"):
        _ = candidate.stage_candidate(request)


@pytest.mark.parametrize(
    ("attribute", "value", "expected"),
    [
        ("artifact_name", "main-cache-rust-policy-candidate", "artifact name"),
        ("cache_key", "coverage-target-deps-v1-Linux-X64-other", "cache key identity"),
        ("source_sha", "fedcba9876543210fedcba9876543210fedcba98", "source SHA"),
    ],
)
def test_promote_main_cache_candidate_rejects_wrong_identity(
    tmp_path: Path,
    attribute: str,
    value: str,
    expected: str,
) -> None:
    request = _request(tmp_path)
    _ = candidate.stage_candidate(request)
    contract = _contract(request)
    if attribute == "artifact_name":
        contract = replace(contract, artifact_name=value)
    elif attribute == "cache_key":
        contract = replace(contract, cache_key=value)
    else:
        contract = replace(contract, source_sha=value)

    with pytest.raises(candidate.CandidateError, match=expected):
        _ = candidate.promote_candidate(
            candidate_dir=request.candidate_dir,
            output_dir=tmp_path / "promoted",
            contract=contract,
        )


@pytest.mark.parametrize(
    ("manifest_field", "expected"),
    [
        ("artifact_sha256", "artifact digest"),
        ("key_input_digest", "cache key identity"),
    ],
)
def test_promote_main_cache_candidate_rejects_digest_tampering(
    tmp_path: Path,
    manifest_field: str,
    expected: str,
) -> None:
    request = _request(tmp_path)
    _ = candidate.stage_candidate(request)
    manifest_path = request.candidate_dir / "manifest.json"
    manifest = _read_manifest(manifest_path)
    manifest[manifest_field] = "0" * 64
    _ = manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    with pytest.raises(candidate.CandidateError, match=expected):
        _ = candidate.promote_candidate(
            candidate_dir=request.candidate_dir,
            output_dir=tmp_path / "promoted",
            contract=_contract(request),
        )


def test_promote_main_cache_candidate_rejects_wrong_tool_versions(tmp_path: Path) -> None:
    request = _request(tmp_path)
    _ = candidate.stage_candidate(request)

    with pytest.raises(candidate.CandidateError, match="tool versions"):
        _ = candidate.promote_candidate(
            candidate_dir=request.candidate_dir,
            output_dir=tmp_path / "promoted",
            contract=replace(
                _contract(request),
                expected_tool_versions={"cargo-llvm-cov": "cargo-llvm-cov 0.8.8"},
            ),
        )


def test_stage_main_cache_candidate_rejects_multiline_tool_identity(tmp_path: Path) -> None:
    request = replace(
        _request(tmp_path),
        tool_versions={"cargo-nextest": "cargo-nextest 0.9.137\nrelease: 0.9.137"},
    )

    with pytest.raises(candidate.CandidateError, match="tool versions"):
        _ = candidate.stage_candidate(request)


def test_stage_main_cache_candidate_rejects_duplicate_and_oversize_payloads(tmp_path: Path) -> None:
    request = _request(tmp_path)
    _ = candidate.stage_candidate(request)

    with pytest.raises(candidate.CandidateError, match="already exists"):
        _ = candidate.stage_candidate(request)

    oversize_root = tmp_path / "oversize"
    oversize_root.mkdir()
    oversize_request = _request(oversize_root, candidate_dir=tmp_path / "oversize-candidate")
    oversize_request = candidate.CandidateRequest(
        artifact_name=oversize_request.artifact_name,
        cache_class=oversize_request.cache_class,
        cache_key=oversize_request.cache_key,
        candidate_dir=oversize_request.candidate_dir,
        maximum_bytes=1,
        producer_event=oversize_request.producer_event,
        producer_job=oversize_request.producer_job,
        producer_ref=oversize_request.producer_ref,
        source_sha=oversize_request.source_sha,
        sources=oversize_request.sources,
        tool_versions=oversize_request.tool_versions,
    )
    with pytest.raises(candidate.CandidateError, match="exceeds its maximum size"):
        _ = candidate.stage_candidate(oversize_request)


def test_main_cache_candidate_cli_entries_are_registered() -> None:
    assert _REGISTRY[("ci", "stage-main-cache-candidate")] == (
        "larch.implement.main_cache_candidate",
        "stage_main_cache_candidate_main",
        True,
    )
    assert _REGISTRY[("ci", "verify-main-cache-candidate")] == (
        "larch.implement.main_cache_candidate",
        "verify_main_cache_candidate_main",
        True,
    )
