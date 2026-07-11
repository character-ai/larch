"""Tests for the Step 8 architectural assessment coordinator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.core import config
from larch.implement import architectural_assessment as assessment


def _evidence(kind: str = config.ASSESSMENT_KIND_GUIDELINES) -> assessment.MaterializedEvidence:
    return assessment.MaterializedEvidence(
        kind=kind,
        head_sha="a" * 40,
        base_ref="origin/main",
        diff_path=Path("/tmp/diff"),
        diff_text="diff --git a/python/a.py b/python/a.py\n",
        diff_fingerprint="b" * 64,
        knowledge_path=Path("/tmp/knowledge"),
        knowledge_sha256="c" * 64,
        identifiers=frozenset({"G-Py-4"} if kind == config.ASSESSMENT_KIND_GUIDELINES else {"I-Stale-1"}),
    )


def test_normalize_kinds_deduplicates_and_orders() -> None:
    assert assessment.normalize_kinds(["guidelines", "invariants", "guidelines"]) == ("invariants", "guidelines")


@pytest.mark.parametrize("kinds", [[], ["other"]])
def test_normalize_kinds_rejects_invalid_requests(kinds: list[str]) -> None:
    with pytest.raises(ValueError, match=r"required|unsupported"):
        _ = assessment.normalize_kinds(kinds)


@pytest.mark.parametrize(
    ("diff_text", "expected"),
    [
        ("diff --git a/docs/a.md b/docs/a.md\n", True),
        ("diff --git a/larch-logs/run/a.txt b/larch-logs/run/a.txt\n", True),
        ("diff --git a/python/a.py b/python/a.py\n", False),
        ("diff --git a/docs/a.md b/docs/b.md\n", False),
        ("Binary files a/x and b/x differ\n", False),
        ("diff --git a/../x b/../x\n", False),
    ],
)
def test_deterministic_filter_is_conservative(diff_text: str, expected: bool) -> None:
    assert assessment.deterministic_out_of_scope(diff_text) is expected


def test_parse_combined_results_orders_and_validates_identity() -> None:
    invariant = _evidence(config.ASSESSMENT_KIND_INVARIANTS)
    guideline = _evidence()
    payload: dict[str, object] = {
        "schema_version": "1",
        "results": [
            {
                "kind": "guidelines",
                "state": "deviation",
                "assessment": "G-Py-4 applies.",
                "identifiers": ["G-Py-4"],
                "head_sha": guideline.head_sha,
                "base_ref": guideline.base_ref,
                "diff_fingerprint": guideline.diff_fingerprint,
                "knowledge_sha256": guideline.knowledge_sha256,
            },
            {
                "kind": "invariants",
                "state": "clean",
                "assessment": "No violations identified.",
                "identifiers": [],
                "head_sha": invariant.head_sha,
                "base_ref": invariant.base_ref,
                "diff_fingerprint": invariant.diff_fingerprint,
                "knowledge_sha256": invariant.knowledge_sha256,
            },
        ],
    }
    parsed = assessment._parse_results(json.dumps(payload), [guideline, invariant])  # pyright: ignore[reportPrivateUsage]
    assert [row.kind for row in parsed] == ["invariants", "guidelines"]


def test_parse_results_rejects_extra_prose_and_unknown_identifier() -> None:
    evidence = _evidence()
    payload = {
        "schema_version": "1",
        "results": [{
            "kind": "guidelines", "state": "clean", "assessment": "Clean.",
            "identifiers": ["G-Unknown-1"], "head_sha": evidence.head_sha,
            "base_ref": evidence.base_ref, "diff_fingerprint": evidence.diff_fingerprint,
            "knowledge_sha256": evidence.knowledge_sha256,
        }],
    }
    with pytest.raises(ValueError, match="exactly one JSON object"):
        _ = assessment._parse_results(json.dumps(payload) + " trailing", [evidence])  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="unknown architectural identifier"):
        _ = assessment._parse_results(json.dumps(payload), [evidence])  # pyright: ignore[reportPrivateUsage]


def test_launcher_uses_exact_read_only_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> object:
        captured["argv"] = argv
        captured.update(kwargs)
        return type("Completed", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()

    monkeypatch.setattr(assessment.subprocess, "run", fake_run)
    request = assessment.LaunchRequest(
        argv=("claude", "--print", "--model", "claude-sonnet-4-6", "--add-dir", str(tmp_path), "--allowedTools", "Read", "--permission-mode", "plan"),
        cwd=tmp_path,
        prompt="prompt",
        evidence_dir=tmp_path,
    )
    result = assessment.ClaudeLauncher().launch(request)
    assert result.returncode == 0
    assert captured["argv"] == list(request.argv)
    assert captured["cwd"] == tmp_path
    assert captured["input"] == "prompt"
