"""Runtime-only Claude plugin projection coverage."""

from __future__ import annotations

import json
from pathlib import Path

from larch.release import plugin_runtime

ROOT = Path(__file__).resolve().parents[3]


def test_projection_matches_runtime_manifest() -> None:
    assert plugin_runtime.projection_errors(ROOT) == []


def test_projection_excludes_repository_tooling_and_sources() -> None:
    paths = set(plugin_runtime.runtime_paths(ROOT))
    forbidden_prefixes = (
        ".github/",
        ".claude/",
        "crates/",
        "python/tests/",
        "python/larch/release/",
        "scripts/test-",
    )
    assert not any(path.startswith(forbidden_prefixes) for path in paths)
    assert not any(Path(path).name.startswith(("test-", "test_")) for path in paths)
    assert not any("fixtures" in Path(path).parts for path in paths)
    assert not any(path.startswith("python/larch/lint/") for path in paths)
    assert not paths.intersection(plugin_runtime._DEV_ONLY_PYTHON)  # pyright: ignore[reportPrivateUsage]
    assert not any(path.endswith(".rs") for path in paths)
    assert not any(
        Path(path).name in {"Cargo.toml", "Cargo.lock", "Makefile"} for path in paths
    )


def test_marketplace_installs_the_projection() -> None:
    marketplace = json.loads(
        (ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    assert marketplace["plugins"][0]["source"] == {
        "source": "git-subdir",
        "url": "https://github.com/character-ai/larch.git",
        "path": "plugin",
    }
    projected_manifest = ROOT / "plugin/.claude-plugin/plugin.json"
    assert not projected_manifest.is_symlink()
    assert (
        projected_manifest.read_bytes()
        == (ROOT / ".claude-plugin/plugin.json").read_bytes()
    )
