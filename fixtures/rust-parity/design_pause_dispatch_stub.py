"""Test-only bridge from frozen Python fixtures to the Rust pause owner.

The migrated Step 0 and plan-quality references remain byte-frozen and import
the pause module that existed when those snapshots were taken. Production no
longer ships that module after #8589, so their harnesses inject this dispatcher
instead of retaining a second pause implementation.
"""

from __future__ import annotations

import os
import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from larch.core.repo_roots import larch_entrypoint


def _design_package() -> ModuleType:
    """Return a test-only package for retired ``larch.design`` imports."""
    package = sys.modules.get("larch.design")
    if package is None:
        package = ModuleType("larch.design")
        package.__path__ = []  # type: ignore[attr-defined]
        sys.modules[package.__name__] = package

        import larch  # noqa: PLC0415 - attach after the root package exists

        larch.design = package  # type: ignore[attr-defined]
    return package


def _install_plan_grammar(package: ModuleType) -> None:
    """Load the frozen grammar only inside migrated-reference processes."""
    name = "larch.design.plan_grammar"
    if name in sys.modules:
        package.plan_grammar = sys.modules[name]
        return
    path = Path(__file__).resolve().with_name("plan_grammar_frozen.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    package.plan_grammar = module


def _install_architectural_helpers() -> None:
    """Attach the frozen pure helpers needed by retired design modules."""
    name = "_larch_architectural_guidelines_frozen"
    module = sys.modules.get(name)
    if module is None:
        path = Path(__file__).resolve().with_name("architectural_guidelines_frozen.py")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load frozen module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)

    from larch.core import architectural_guidelines  # noqa: PLC0415 - fixture patch

    for attribute in (
        "ArchitecturalGuidelinesResult",
        "GuidelineException",
        "guideline_active_exception",
        "read_guidelines",
        "read_invariants",
    ):
        setattr(architectural_guidelines, attribute, getattr(module, attribute))


def _install_difficulty_helpers() -> None:
    """Attach retired plan-metadata helpers to the live non-grammar module."""
    name = "_larch_difficulty_plan_metadata_frozen"
    module = sys.modules.get(name)
    if module is None:
        path = Path(__file__).resolve().with_name(
            "difficulty_plan_metadata_frozen.py"
        )
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load frozen module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)

    from larch.calibration import difficulty  # noqa: PLC0415 - fixture patch

    for attribute in (
        "plan_difficulty",
        "trailing_plan_difficulty",
        "trailing_plan_metadata_lines",
    ):
        setattr(difficulty, attribute, getattr(module, attribute))


def _install_issue_block_helpers() -> None:
    """Attach the frozen named-block reader needed by retired design code."""
    name = "_larch_issue_blocks_frozen"
    module = sys.modules.get(name)
    if module is None:
        path = Path(__file__).resolve().with_name("issue_blocks_frozen.py")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load frozen module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)

    from larch.issue import issue_wire  # noqa: PLC0415 - fixture patch

    issue_wire.parse_named_block = module.parse_named_block


def _install_issue_support() -> None:
    """Load the shared issue-support installer by its absolute fixture path."""
    name = "_larch_issue_support_loader"
    module = sys.modules.get(name)
    if module is None:
        path = Path(__file__).resolve().with_name("issue_support_loader.py")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load frozen module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    module.install_issue_support()


def _install_issue_mutation_stub() -> None:
    """Keep retired OOS references importable without restoring an owner."""
    name = "larch.issue.issue_mutation"
    if name in sys.modules:
        return
    module = ModuleType(name)

    def retired(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("retired issue-mutation fixture path was invoked")

    module.read_snapshot = retired
    module.update_labels = retired
    sys.modules[name] = module

    import larch.issue  # noqa: PLC0415 - attach after the package exists

    larch.issue.issue_mutation = module  # type: ignore[attr-defined]


def _run(verb: str, argv: Sequence[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    executable = os.environ.get("LARCH_BINARY") or str(larch_entrypoint(root))
    return subprocess.run(
        [executable, "design", verb, *argv],
        check=False,
    ).returncode


def install_shared_retired_dependencies() -> None:
    """Install retired imports shared by frozen parity processes."""
    package = _design_package()
    _install_plan_grammar(package)
    _install_issue_block_helpers()
    _install_difficulty_helpers()
    _install_issue_support()
    _install_issue_mutation_stub()


def install() -> None:
    """Install historical ``larch.design`` imports for frozen tests."""

    install_shared_retired_dependencies()
    package = _design_package()
    _install_architectural_helpers()

    def pause_save_main(argv: Sequence[str]) -> int:
        return _run("pause-save", argv)

    def pause_load_main(argv: Sequence[str]) -> int:
        return _run("pause-load", argv)

    module = ModuleType("larch.design.design_pause")
    module.pause_save_main = pause_save_main
    module.pause_load_main = pause_load_main
    sys.modules[module.__name__] = module
    package.design_pause = module
