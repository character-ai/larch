"""Offline harness parity for implement shell helper scripts.

Adapter and bgjob behavior for Step 5/6/checks lives in Rust tests. This module
ports only the Bash harness assertions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.repo_contract import repo_root

_REPO = repo_root()
_IMPLEMENT_SCRIPTS = _REPO / "skills" / "implement" / "scripts"
_STEP8_HELPER = _IMPLEMENT_SCRIPTS / "step-8-ship.sh"
_STEP8_GUARD = _IMPLEMENT_SCRIPTS / "step-8-python-guard.sh"
_STEP8_SEEDER = _IMPLEMENT_SCRIPTS / "step-8-seed-initial.sh"
_STEP8_OOS = _IMPLEMENT_SCRIPTS / "step-8-oos-checkpoint.sh"

_STEP5_WRAPPERS: tuple[str, ...] = ()

_STEP5_RUST_WRAPPERS = (
    "run-step-checks.sh",
    "step-5-review.sh",
    "step-5-resume.sh",
    "step-6-entry.sh",
)

_STEP8_HELPER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ('implement step-8-ship "$@"', "static: thin wrapper delegates to Rust", True),
    ("scripts/larch.sh", "static: wrapper enters through verified bootstrap", True),
    ("python/cli.py", "static: Python owner is retired", False),
    ("bgjob adapt", "static: bash wrapper no longer owns bgjob adapt", False),
    ("bgjob start", "static: direct bgjob start retired", False),
    ("persist_handoff", "static: sidecar handoff writer retired", False),
    ("stdout-capture", "static: stdout capture retired", False),
    ("tee -a", "static: stdout tee retired", False),
    ("step-8-ship-handoff", "static: rc and JSON sidecars retired", False),
    ("run_in_background", "static: helper prose/code no legacy background literal", False),
    ("printf 'PID=%s", "static: legacy bg-wait marker writer removed", False),
    ("rehydrate_plugin_root", "static: rehydrate helpers moved to Rust", False),
)

_STEP8_SEEDER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ('implement step-8-seed-initial "$@"', "static: thin wrapper delegates to Rust", True),
    ("scripts/larch.sh", "static: wrapper enters through verified bootstrap", True),
    ("python/cli.py", "static: Python owner is retired", False),
    ("ship seed-initial-state", "static: bash wrapper no longer calls seeder directly", False),
    ("read-session-env-key.sh", "static: retired session reader absent", False),
    ("rehydrate_plugin_root", "static: rehydrate helpers moved to Rust", False),
)


def _wrapper_source(name: str) -> str:
    return (_IMPLEMENT_SCRIPTS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_set_euo_pipefail(wrapper: str) -> None:
    assert "set -euo pipefail" in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_RUST_WRAPPERS, ids=_STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_exec_larch_implement(wrapper: str) -> None:
    assert 'exec "$PLUGIN_ROOT/scripts/larch.sh" implement' in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_no_bgjob_start(wrapper: str) -> None:
    assert "bgjob start" not in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_no_registry(wrapper: str) -> None:
    assert "registry" not in _wrapper_source(wrapper)


@pytest.mark.parametrize(
    ("needle", "label", "should_contain"),
    _STEP8_HELPER_STATIC_PINS,
    ids=[label for _needle, label, _should in _STEP8_HELPER_STATIC_PINS],
)
def test_step8_helper_static_pin(needle: str, label: str, should_contain: bool) -> None:
    text = _STEP8_HELPER.read_text(encoding="utf-8")
    if should_contain:
        assert needle in text, label
    else:
        assert needle not in text, label


@pytest.mark.parametrize(
    ("needle", "label", "should_contain"),
    _STEP8_SEEDER_STATIC_PINS,
    ids=[label for _needle, label, _should in _STEP8_SEEDER_STATIC_PINS],
)
def test_step8_seeder_static_pin(needle: str, label: str, should_contain: bool) -> None:
    text = _STEP8_SEEDER.read_text(encoding="utf-8")
    if should_contain:
        assert needle in text, label
    else:
        assert needle not in text, label


@pytest.mark.parametrize(
    ("wrapper", "verb"),
    [
        (_STEP8_GUARD, "step-8-python-guard"),
        (_STEP8_OOS, "step-8-oos-checkpoint"),
    ],
)
def test_step8_guard_and_oos_wrappers_delegate_to_rust(wrapper: Path, verb: str) -> None:
    source = wrapper.read_text(encoding="utf-8")
    assert "scripts/larch.sh" in source
    assert f'implement {verb} "$@"' in source
    assert "python/cli.py" not in source
