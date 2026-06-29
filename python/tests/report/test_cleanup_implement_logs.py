# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Tests for cleanup_implement_logs.py — the --run-dir containment guard."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.report import cleanup_implement_logs as cil
if TYPE_CHECKING:
    import pytest


def _make_impl_root(tmp_path: Path) -> Path:
    impl_root = tmp_path / "larch-logs" / "implement"
    impl_root.mkdir(parents=True)
    return impl_root


def test_resolve_single_run_dir_accepts_child(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    run_dir = impl_root / "0199-RUN-UUID"
    run_dir.mkdir()
    resolved = cil._resolve_single_run_dir(run_dir_arg=str(run_dir), impl_root=impl_root)  # pyright: ignore[reportPrivateUsage]
    assert resolved == run_dir.resolve()


def test_resolve_single_run_dir_accepts_impl_root_itself(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    resolved = cil._resolve_single_run_dir(run_dir_arg=str(impl_root), impl_root=impl_root)  # pyright: ignore[reportPrivateUsage]
    assert resolved == impl_root.resolve()


def test_resolve_single_run_dir_rejects_sibling_outside(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    outside = tmp_path / "not-implement"
    outside.mkdir()
    assert cil._resolve_single_run_dir(run_dir_arg=str(outside), impl_root=impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_resolve_single_run_dir_rejects_parent_traversal(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    sneaky = str(impl_root / ".." / ".." / "etc")
    assert cil._resolve_single_run_dir(run_dir_arg=sneaky, impl_root=impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_resolve_single_run_dir_rejects_symlink_escape(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    outside = tmp_path / "outside-target"
    outside.mkdir()
    link = impl_root / "escape-link"
    link.symlink_to(outside, target_is_directory=True)
    # The symlink lives inside impl_root but resolves outside it.
    assert cil._resolve_single_run_dir(run_dir_arg=str(link), impl_root=impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_list_bulk_run_dirs_includes_real_dirs(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    a = impl_root / "0199-RUN-A"
    b = impl_root / "0199-RUN-B"
    a.mkdir()
    b.mkdir()
    (impl_root / "stray-file.txt").write_text("not a dir\n", encoding="utf-8")

    result = cil._list_bulk_run_dirs(impl_root)  # pyright: ignore[reportPrivateUsage]

    assert result == [a, b]


def test_list_bulk_run_dirs_skips_symlink_escape(tmp_path: Path) -> None:
    # Bulk mode (no --run-dir) iterates impl_root.iterdir(). A symlink planted
    # inside impl_root that resolves outside it must be excluded, or the
    # destructive cleanup actions would follow it and delete files outside the
    # larch-logs/implement/ tree. Mirrors the --run-dir containment guard.
    impl_root = _make_impl_root(tmp_path)
    real_run = impl_root / "0199-REAL-RUN"
    real_run.mkdir()

    outside = tmp_path / "outside-target"
    outside.mkdir()
    link = impl_root / "escape-link"
    link.symlink_to(outside, target_is_directory=True)

    result = cil._list_bulk_run_dirs(impl_root)  # pyright: ignore[reportPrivateUsage]

    assert real_run in result
    assert link not in result
    assert all(d.resolve().is_relative_to(impl_root.resolve()) for d in result)


def test_main_rejects_run_dir_outside_impl_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A dyn-*-prompt.md outside the real larch-logs/implement/ tree would be
    # deleted by the unguarded rglob. The guard must refuse and leave it intact.
    victim = tmp_path / "round-1" / "dyn-evil-prompt.md"
    victim.parent.mkdir(parents=True)
    victim.write_text("do not delete me\n", encoding="utf-8")

    rc = cil.main(["--run-dir", str(tmp_path), "--execute"])

    assert rc == 1
    assert victim.exists(), "guard must block deletion outside larch-logs/implement/"
    assert "--run-dir must resolve to a path inside" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Inner-symlink containment (escaping symlinks *inside* a run dir)
# ---------------------------------------------------------------------------

def _run_and_external(tmp_path: Path) -> tuple[Path, Path]:
    """Return (run_dir, external_dir) for inner-symlink containment tests."""
    run_dir = tmp_path / "larch-logs" / "implement" / "0199-RUN"
    run_dir.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    return run_dir, external


def test_within_run_dir_accepts_inside_and_rejects_escape(tmp_path: Path) -> None:
    run_dir, external = _run_and_external(tmp_path)
    inside = run_dir / "a" / "b.txt"
    inside.parent.mkdir()
    inside.write_text("x\n", encoding="utf-8")
    assert cil._within_run_dir(path=inside, run_dir_resolved=run_dir.resolve())  # pyright: ignore[reportPrivateUsage]

    target = external / "f"
    target.write_text("y\n", encoding="utf-8")
    link = run_dir / "link"
    link.symlink_to(target)
    assert not cil._within_run_dir(path=link, run_dir_resolved=run_dir.resolve())  # pyright: ignore[reportPrivateUsage]


def test_within_run_dir_rejects_symlink_loop(tmp_path: Path) -> None:
    run_dir, _ = _run_and_external(tmp_path)
    loop = run_dir / "dyn-loop-prompt.md"
    loop.symlink_to(loop)
    assert not cil._within_run_dir(path=loop, run_dir_resolved=run_dir.resolve())  # pyright: ignore[reportPrivateUsage]


def test_delete_dyn_prompts_skips_symlink_loop(tmp_path: Path) -> None:
    run_dir, _ = _run_and_external(tmp_path)
    loop = run_dir / "dyn-loop-prompt.md"
    loop.symlink_to(loop)

    stats = cil.Stats()
    cil.delete_dyn_prompts(run_dir=run_dir, execute=True, stats=stats)

    assert loop.is_symlink(), "symlink loop entry must not be unlinked"
    assert stats.dyn_prompt_deleted == 0


def test_delete_dyn_prompts_skips_escaping_sidecar(tmp_path: Path) -> None:
    run_dir, external = _run_and_external(tmp_path)
    prompt = run_dir / "dyn-evil-prompt.md"
    prompt.write_text("ok\n", encoding="utf-8")
    victim = external / "dyn-evil-prompt.md.meta"
    victim.write_text("secret\n", encoding="utf-8")
    (run_dir / "dyn-evil-prompt.md.meta").symlink_to(victim)

    stats = cil.Stats()
    cil.delete_dyn_prompts(run_dir=run_dir, execute=True, stats=stats)

    assert victim.exists(), "escaping sidecar target must survive"
    assert not prompt.exists(), "contained primary file should be deleted"
    assert stats.dyn_prompt_deleted == 1


def test_delete_dyn_prompts_skips_symlink_escape(tmp_path: Path) -> None:
    # A dyn-*-prompt.md symlink inside the run dir that points outside it must be
    # left untouched, not followed and unlinked.
    run_dir, external = _run_and_external(tmp_path)
    victim = external / "dyn-evil-prompt.md"
    victim.write_text("do not delete\n", encoding="utf-8")
    (run_dir / "dyn-evil-prompt.md").symlink_to(victim)

    stats = cil.Stats()
    cil.delete_dyn_prompts(run_dir=run_dir, execute=True, stats=stats)

    assert victim.exists(), "escaping symlink target must survive"
    assert stats.dyn_prompt_deleted == 0


def test_delete_identical_aggregator_skips_escaping_findings_symlink(tmp_path: Path) -> None:
    # aggregator-output.txt is a real in-tree file, but its sibling findings.md is
    # an escaping symlink. Comparing through it would read external content and
    # could delete the in-tree aggregator as a false "identical" hit. The guard
    # must skip the pair: the external target stays untouched and the aggregator
    # survives. Completes the symlink-escape coverage (dyn-prompts, transcripts,
    # tally, breadcrumbs) for the aggregator/findings pair.
    run_dir, external = _run_and_external(tmp_path)
    body = "identical body\n"
    agg = run_dir / "aggregator-output.txt"
    agg.write_text(body, encoding="utf-8")
    victim = external / "findings.md"
    victim.write_text(body, encoding="utf-8")  # byte-identical: would match but for the guard
    (run_dir / "findings.md").symlink_to(victim)

    stats = cil.Stats()
    cil.delete_identical_aggregator(run_dir=run_dir, execute=True, stats=stats)

    assert victim.exists(), "escaping findings.md target must survive"
    assert agg.exists(), "aggregator must not be deleted when findings.md escapes the run dir"
    assert stats.aggregator_deleted == 0


def test_upgrade_transcripts_skips_symlink_escape(tmp_path: Path) -> None:
    # session-transcript.jsonl as an escaping symlink would be read and rewritten
    # in place, corrupting the external file. The guard must skip it.
    run_dir, external = _run_and_external(tmp_path)
    external_target = external / "session-transcript.jsonl"
    original = '{"v":1}\n{"role":"user","blocks":[]}\n'
    external_target.write_text(original, encoding="utf-8")
    (run_dir / "session-transcript.jsonl").symlink_to(external_target)

    stats = cil.Stats()
    cil.upgrade_transcripts(run_dir=run_dir, execute=True, stats=stats)

    assert external_target.read_text(encoding="utf-8") == original, (
        "must not write through an escaping symlink"
    )
    assert stats.transcript_upgraded == 0


def test_strip_tally_body_skips_symlink_escape(tmp_path: Path) -> None:
    run_dir, external = _run_and_external(tmp_path)
    external_target = external / "code-review-tally.json"
    original = '[{"body":"keep","x":1}]'
    external_target.write_text(original, encoding="utf-8")
    (run_dir / "code-review-tally.json").symlink_to(external_target)

    stats = cil.Stats()
    cil.strip_tally_body(run_dir=run_dir, execute=True, stats=stats)

    assert external_target.read_text(encoding="utf-8") == original, (
        "must not write through an escaping symlink"
    )
    assert stats.tally_body_stripped == 0


def test_consolidate_breadcrumbs_skips_symlinked_dir(tmp_path: Path) -> None:
    # breadcrumbs/ itself as a symlink to an external dir would make the
    # consolidation read/write/unlink inside that external dir.
    run_dir, external = _run_and_external(tmp_path)
    ext_log = external / "larch-quiet-1.log"
    ext_log.write_text("external\n", encoding="utf-8")
    (run_dir / "breadcrumbs").symlink_to(external, target_is_directory=True)

    stats = cil.Stats()
    cil.consolidate_breadcrumbs(run_dir=run_dir, execute=True, stats=stats)

    assert ext_log.exists(), "external breadcrumb file must survive"
    assert not (external / "quiet.log").exists(), "must not write quiet.log into external dir"
    assert stats.breadcrumbs_consolidated == 0


def test_consolidate_breadcrumbs_skips_symlinked_log_entry(tmp_path: Path) -> None:
    # An escaping larch-quiet-*.log symlink must not be read into quiet.log, but
    # real sibling breadcrumb files are still consolidated.
    run_dir, external = _run_and_external(tmp_path)
    bc = run_dir / "breadcrumbs"
    bc.mkdir()
    secret = external / "secret.log"
    secret.write_text("SECRET\n", encoding="utf-8")
    (bc / "larch-quiet-escape.log").symlink_to(secret)
    (bc / "larch-quiet-1.log").write_text("real breadcrumb\n", encoding="utf-8")

    stats = cil.Stats()
    cil.consolidate_breadcrumbs(run_dir=run_dir, execute=True, stats=stats)

    quiet = bc / "quiet.log"
    assert secret.exists(), "external symlink target must survive"
    body = quiet.read_text(encoding="utf-8")
    assert "SECRET" not in body, "must not read external content through an escaping symlink"
    assert "real breadcrumb" in body, "real sibling breadcrumb must still be consolidated"


def test_consolidate_breadcrumbs_skips_symlinked_quiet_log(tmp_path: Path) -> None:
    # quiet.log planted as a symlink to a (non-existent) external path would make
    # write_text() create/overwrite that external file. The guard must refuse.
    run_dir, external = _run_and_external(tmp_path)
    bc = run_dir / "breadcrumbs"
    bc.mkdir()
    (bc / "larch-quiet-1.log").write_text("real\n", encoding="utf-8")
    external_quiet = external / "quiet-target.log"
    (bc / "quiet.log").symlink_to(external_quiet)

    stats = cil.Stats()
    cil.consolidate_breadcrumbs(run_dir=run_dir, execute=True, stats=stats)

    assert not external_quiet.exists(), (
        "must not create/write an external file through a symlinked quiet.log"
    )
    assert stats.breadcrumbs_consolidated == 0


def test_process_run_dir_leaves_external_tree_intact(tmp_path: Path) -> None:
    # End-to-end: a run dir seeded with several escaping symlinks must leave the
    # entire external tree untouched after a full process_run_dir pass.
    run_dir, external = _run_and_external(tmp_path)
    ext_prompt = external / "dyn-x-prompt.md"
    ext_prompt.write_text("ext prompt\n", encoding="utf-8")
    ext_tally = external / "code-review-tally.json"
    ext_tally.write_text('[{"body":"keep"}]', encoding="utf-8")
    (run_dir / "dyn-x-prompt.md").symlink_to(ext_prompt)
    (run_dir / "code-review-tally.json").symlink_to(ext_tally)

    stats = cil.Stats()
    cil.process_run_dir(run_dir=run_dir, execute=True, stats=stats)

    assert ext_prompt.read_text(encoding="utf-8") == "ext prompt\n"
    assert ext_tally.read_text(encoding="utf-8") == '[{"body":"keep"}]'
