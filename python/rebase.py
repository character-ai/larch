"""Rebase component: fetch/rebase, conflict resolution, re-bump, force-push (Phase 3)."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import agents
import changelog
import config
import git
import redact
import retry
import version_bump
from errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from outcomes import Outcome
from proc import CommandResult, Runner

_BUMP_SUBJECT_RE = re.compile(r"^Bump version to ([0-9]+\.[0-9]+\.[0-9]+)$")
_CHANGELOG_BASENAMES = frozenset({"CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG"})
_SEMVER_RE = re.compile(config.SEMVER_RE)

_redact_outbound = redact.redact_outbound

ConflictLaunchFn = Callable[[str, str], agents.TierAttempt]


@dataclass(frozen=True)
class RebaseResult:
    outcome: Outcome
    rebased: bool
    pushed: bool
    new_version: str | None
    attempts: int
    detail: str


def _rebump_bullets_path(
    tmpdir: str | None,
    bullets_path: Path | str | None,
) -> Path | None:
    if bullets_path is not None:
        return Path(bullets_path)
    if tmpdir:
        return Path(tmpdir) / ".rrr-rebump-bullets.md"
    env_tmp = os.environ.get(config.ENV_IMPLEMENT_TMPDIR)
    if env_tmp:
        return Path(env_tmp) / ".rrr-rebump-bullets.md"
    return None


def _is_no_match_drop_error(error: str) -> bool:
    lowered = error.lower()
    return "no bump commit found" in lowered or "no changelog commit found" in lowered


def _parse_bump_version_from_sha(runner: Runner, sha: str, *, cwd: str | None) -> str:
    subject = git.log_subject(runner, sha, cwd=cwd)
    match = _BUMP_SUBJECT_RE.fullmatch(subject)
    if match:
        return match.group(1)
    return ""


def _stage_rebump_bullets(
    runner: Runner,
    *,
    old_version: str,
    bullets_path: Path,
    cwd: str | None,
) -> None:
    if not _SEMVER_RE.fullmatch(old_version):
        return
    changelog_path = config.CHANGELOG_DEFAULT_PATH
    root = Path(cwd) if cwd else Path.cwd()
    if not (root / changelog_path).is_file():
        return
    if bullets_path.exists():
        bullets_path.unlink()
    changelog_text = (root / changelog_path).read_text(encoding="utf-8")
    fmt = changelog.detect_format(changelog_text, path=changelog_path)
    extracted = changelog.extract_version_body(
        changelog_text,
        old_version,
        fmt=fmt,
    )
    if extracted:
        _ = bullets_path.write_text(extracted, encoding="utf-8")
    elif bullets_path.exists():
        bullets_path.unlink()

    drop = changelog.drop_changelog_commit(
        runner,
        old_version,
        max_depth=config.DROP_CHANGELOG_MAX_DEPTH,
        cwd=cwd,
    )
    if drop.dropped:
        return
    if _is_no_match_drop_error(drop.error):
        if bullets_path.exists():
            bullets_path.unlink()
        return
    if bullets_path.exists():
        bullets_path.unlink()
    msg = _redact_outbound(
        "drop-changelog-commit returned DROPPED=false without no-match reason",
    )
    raise Stalled(msg)


def _changelog_ready_after_rebump(
    runner: Runner,
    new_version: str,
    old_version: str,
    *,
    cwd: str | None,
) -> bool:
    root = Path(cwd) if cwd else Path.cwd()
    changelog_path = root / config.CHANGELOG_DEFAULT_PATH
    if not changelog_path.is_file():
        return False
    text = changelog_path.read_text(encoding="utf-8")
    if not re.search(rf"^## \[{re.escape(new_version)}\] - ", text, re.MULTILINE):
        return False
    if (
        _SEMVER_RE.fullmatch(old_version)
        and old_version != new_version
        and re.search(rf"^## \[{re.escape(old_version)}\] - ", text, re.MULTILINE)
    ):
        return False
    status = git.status_porcelain(runner, untracked_files="no", cwd=cwd)
    if status.returncode != 0:
        return False
    for line in status.stdout.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if line.startswith(("R", "C")) and " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path == config.CHANGELOG_DEFAULT_PATH:
            return False
    return True


def _commit_changelog_after_rebump(
    runner: Runner,
    new_version: str,
    old_version: str,
    bullets_path: Path,
    *,
    cwd: str | None,
) -> None:
    root = Path(cwd) if cwd else Path.cwd()
    if not (root / config.CHANGELOG_DEFAULT_PATH).is_file():
        return
    if not _SEMVER_RE.fullmatch(new_version):
        return

    used_bullets = False
    if bullets_path.is_file() and bullets_path.stat().st_size > 0:
        cl_path = root / config.CHANGELOG_DEFAULT_PATH
        cl_text = cl_path.read_text(encoding="utf-8")
        fmt = changelog.detect_format(cl_text, path=config.CHANGELOG_DEFAULT_PATH)
        dup = changelog.duplicate_version_heading_count(
            cl_text,
            new_version,
            fmt=fmt,
        )
        if dup > 0:
            if bullets_path.exists():
                bullets_path.unlink()
            msg = _redact_outbound(
                f"origin/main already has ## [{new_version}] with staged bullets",
            )
            raise Stalled(msg)
        body = bullets_path.read_text(encoding="utf-8")
        try:
            new_text = changelog.write_changelog_entry(
                cl_text,
                new_version,
                body,
                fmt=fmt,
            )
        except changelog.ChangelogError as exc:
            if bullets_path.exists():
                bullets_path.unlink()
            raise Stalled(_redact_outbound(str(exc))) from None
        _ = cl_path.write_text(new_text, encoding="utf-8")
        used_bullets = True

    if bullets_path.exists():
        bullets_path.unlink()

    replaces: str | None = None
    if not used_bullets:
        if (
            _SEMVER_RE.fullmatch(old_version)
            and old_version != new_version
        ):
            replaces = old_version
        else:
            show = git.show_file(
                runner,
                f"origin/main:{config.PLUGIN_JSON_PATH}",
                cwd=cwd,
            )
            if show.returncode == 0:
                try:
                    origin_ver = json.loads(show.stdout).get("version", "")
                except json.JSONDecodeError:
                    origin_ver = ""
                if (
                    isinstance(origin_ver, str)
                    and _SEMVER_RE.fullmatch(origin_ver)
                    and origin_ver != new_version
                ):
                    replaces = origin_ver

    result = changelog.commit_changelog(
        runner,
        new_version,
        replaces_version=replaces,
        cwd=cwd,
    )
    if result.committed:
        return
    if _changelog_ready_after_rebump(runner, new_version, old_version, cwd=cwd):
        return
    msg = _redact_outbound(
        f"commit-changelog failed before CHANGELOG verified at {new_version}",
    )
    raise Stalled(msg)


def _sync_local_main(
    runner: Runner,
    *,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> None:
    branch = git.try_current_branch(runner, cwd=cwd)
    if branch == "main":
        raise Stalled(
            _redact_outbound(
                "git-sync-local-main.sh: refusing to update local 'main' "
                "while checked out on main",
            ),
        )
    if git.try_rev_parse(runner, "main", cwd=cwd) is None:
        return
    base_target = f"{base_remote}/{base_ref}"
    local_main = git.try_rev_parse(runner, "main", cwd=cwd)
    remote_main = git.try_rev_parse(runner, base_target, cwd=cwd)
    if local_main and remote_main and local_main == remote_main:
        return
    if remote_main is None:
        return
    _ = git.branch_force(runner, "main", base_target, cwd=cwd)


def _is_empty_or_already_applied_rebase_error(text: str) -> bool:
    lowered = text.lower()
    if "nothing to commit" in lowered:
        return True
    if "no changes" in lowered:
        return True
    return "all merge conflicts were fixed" in lowered


def _abort_rebase(runner: Runner, *, cwd: str | None) -> None:
    _ = git.rebase(runner, "--abort", cwd=cwd)


def _is_plugin_json_path(path: str) -> bool:
    return path == config.PLUGIN_JSON_PATH or path.endswith(
        f"/{config.PLUGIN_JSON_PATH}",
    )


def _deterministic_prepass(
    runner: Runner,
    paths: list[str],
    *,
    cwd: str | None,
) -> list[str]:
    remaining: list[str] = []
    for path in paths:
        base = Path(path).name
        if base in _CHANGELOG_BASENAMES:
            if changelog.auto_resolve(runner, path, cwd=cwd):
                _ = git.add(runner, path, cwd=cwd)
            else:
                remaining.append(path)
            continue
        if base == "plugin.json" and _is_plugin_json_path(path):
            result = git.checkout_ours(runner, path, cwd=cwd)
            if result.returncode == 0:
                _ = git.add(runner, path, cwd=cwd)
            else:
                remaining.append(path)
            continue
        if base in ("version.go", "go.sum"):
            result = git.checkout_ours(runner, path, cwd=cwd)
            if result.returncode == 0:
                _ = git.add(runner, path, cwd=cwd)
            else:
                remaining.append(path)
            continue
        remaining.append(path)
    return remaining


def _unmerged_paths(runner: Runner, *, cwd: str | None) -> list[str]:
    try:
        return git.unmerged_paths(runner, cwd=cwd)
    except ShipError:
        raise Stalled(_redact_outbound("git diff --diff-filter=U failed")) from None


def make_conflict_launch_fn(
    runner: Runner,
    *,
    repo: str,
    run_id: str,
    output_dir: str | Path,
    cwd: str | None = None,
) -> ConflictLaunchFn:
    """Build a fixer launch_fn using ``build_launch_argv`` / ``launch_tier`` parity."""
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    def launch(tier: str, conflict_csv: str) -> agents.TierAttempt:
        output = out_root / f"conflict-{tier}.out"
        failure_log = out_root / f"conflict-{tier}.fail.log"
        result = agents.launch_tier(
            runner,
            tier,
            role=config.FIXER_ROLE,
            output=str(output),
            run_id=run_id,
            repo=repo,
            conflict_files=conflict_csv,
            cwd=cwd,
        )
        launcher_exit = agents.parse_launcher_exit_text(result.stdout)
        failure = agents.classify_launch_failure(
            launcher_exit,
            failure_log if failure_log.is_file() else None,
            tool=tier,
            output_file=output,
        )
        flog: str | Path | None = failure_log if failure_log.is_file() else None
        return agents.TierAttempt(
            tier=tier,
            wrapper_rc=result.returncode,
            launcher_exit=launcher_exit,
            failure=failure,
            failure_log=flog,
        )

    return launch


def _resolve_conflicts(
    runner: Runner,
    launch_fn: ConflictLaunchFn,
    *,
    repo: str,
    run_id: str,
    cwd: str | None,
) -> None:
    _ = repo, run_id
    while True:
        unmerged = _unmerged_paths(runner, cwd=cwd)
        if unmerged:
            remaining = _deterministic_prepass(runner, unmerged, cwd=cwd)
            if remaining:
                conflict_csv = ",".join(remaining)

                def _tier_launch(tier: str, csv: str = conflict_csv) -> agents.TierAttempt:
                    return launch_fn(tier, csv)

                waterfall = agents.run_waterfall(
                    config.FIXER_TIER_ORDER,
                    _tier_launch,
                    runner=runner,
                    cwd=cwd,
                )
                if waterfall.winning_tier is None:
                    raise NeedsUserInput(
                        _redact_outbound(
                            "fixer waterfall could not resolve conflicts",
                        ),
                    )
                if _unmerged_paths(runner, cwd=cwd):
                    raise NeedsUserInput(
                        _redact_outbound(
                            "conflicts remain after fixer waterfall",
                        ),
                    )

        continue_result = git.rebase_continue(runner, cwd=cwd)
        if continue_result.returncode == 0:
            if _unmerged_paths(runner, cwd=cwd):
                continue
            return

        unmerged_after = _unmerged_paths(runner, cwd=cwd)
        combined = f"{continue_result.stdout}\n{continue_result.stderr}"
        if unmerged_after:
            continue
        if _is_empty_or_already_applied_rebase_error(combined):
            skip_result = git.rebase_skip(runner, cwd=cwd)
            if skip_result.returncode != 0:
                _abort_rebase(runner, cwd=cwd)
                raise Stalled(_redact_outbound("git rebase --skip failed"))
            continue
        _abort_rebase(runner, cwd=cwd)
        raise Stalled(_redact_outbound("rebase --continue failed without unmerged paths"))


def _force_push_branch(
    runner: Runner,
    *,
    cwd: str | None,
    sleep_fn: Callable[[float], None] = time.sleep,
    expected_remote_oid: str | None = None,
) -> CommandResult:
    status = git.status_porcelain(runner, cwd=cwd)
    if status.returncode != 0:
        raise Stalled(_redact_outbound("git status failed before force-push"))
    if status.stdout.strip():
        raise Stalled(_redact_outbound("dirty worktree before force-push"))

    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        raise Stalled(_redact_outbound("not on a named branch before force-push"))

    remote = "origin"
    refspec = branch
    _ = git.fetch(runner, remote, branch, cwd=cwd)

    def _push() -> CommandResult:
        if expected_remote_oid:
            return git.force_push_with_lease_expecting(
                runner,
                remote,
                f"refs/heads/{refspec}",
                expected_remote_oid,
                cwd=cwd,
            )
        return git.force_push_with_lease(runner, remote, refspec, cwd=cwd)

    first = _push()
    if first.returncode == 0:
        return first

    _ = git.fetch(runner, remote, branch, cwd=cwd)
    head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    remote_tip = git.try_rev_parse(runner, f"{remote}/{branch}", cwd=cwd)
    if head and remote_tip and head == remote_tip:
        return CommandResult(first.argv, 0, "", "", first.duration)

    sleep_fn(5)
    second = _push()
    if second.returncode == 0:
        return second
    raise Stalled(_redact_outbound("force-push failed after retry"))


def rebase_and_rebump(
    runner: Runner,
    launch_fn: ConflictLaunchFn | None = None,
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
    repo: str,
    run_id: str,
    cwd: str | None = None,
    tmpdir: str | None = None,
    bullets_path: Path | str | None = None,
    rebase_attempt: int = 0,
    max_attempts: int = config.REBASE_MAX_ATTEMPTS,
    has_bump: bool = True,
    defer_push: bool = False,
) -> RebaseResult:
    """Rebase onto base, resolve conflicts, optionally re-bump, optionally force-push.

    When ``has_bump`` is False, classification and ``apply_bump`` are skipped and
    ``RebaseResult.new_version`` stays None. When ``defer_push`` is True, rebase and
    rebump may still run locally but force-push is skipped and ``RebaseResult.pushed``
    is False.
    """
    resolved_bullets_early = _rebump_bullets_path(tmpdir, bullets_path)
    if launch_fn is None:
        if resolved_bullets_early is None:
            raise Stalled(_redact_outbound("rebump bullets path not configured"))
        launch_fn = make_conflict_launch_fn(
            runner,
            repo=repo,
            run_id=run_id,
            output_dir=resolved_bullets_early.parent / ".conflict-launch",
            cwd=cwd,
        )
    if rebase_attempt >= max_attempts:
        raise Stalled(_redact_outbound("rebase attempt cap exceeded"))

    base_err = git.validate_base_remote_ref(base_remote, base_ref)
    if base_err is not None:
        raise Stalled(_redact_outbound(base_err))

    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        raise Stalled(_redact_outbound("detached HEAD or no current branch"))

    resolved_bullets = _rebump_bullets_path(tmpdir, bullets_path)
    if resolved_bullets is None:
        raise Stalled(_redact_outbound("rebump bullets path not configured"))

    old_version = ""
    rebased = False

    drop_bump = version_bump.drop_bump_commit(
        runner,
        allow_changelog_only=True,
        max_depth=config.DROP_CHANGELOG_MAX_DEPTH,
        cwd=cwd,
    )
    if not drop_bump.dropped and not _is_no_match_drop_error(drop_bump.error):
        raise Stalled(_redact_outbound(drop_bump.error or "drop bump failed"))
    if drop_bump.dropped:
        old_version = _parse_bump_version_from_sha(runner, drop_bump.old_sha, cwd=cwd)
        _stage_rebump_bullets(
            runner,
            old_version=old_version,
            bullets_path=resolved_bullets,
            cwd=cwd,
        )

    base_target = f"{base_remote}/{base_ref}"
    fetch_result = git.fetch(runner, base_remote, base_ref, cwd=cwd)
    if fetch_result.returncode != 0:
        _abort_rebase(runner, cwd=cwd)
        combined = f"{fetch_result.stdout}\n{fetch_result.stderr}"
        if retry.is_transient_net_signature(combined):
            raise TransientNetworkError(
                _redact_outbound("fetch failed with transient network signature"),
                result=fetch_result,
            )
        raise Stalled(_redact_outbound("fetch failed"))

    if git.is_ancestor(runner, base_target, "HEAD", cwd=cwd):
        rebased = False
    else:
        rebase_result = git.rebase(runner, base_target, cwd=cwd)
        if rebase_result.returncode == 0:
            rebased = True
        elif _unmerged_paths(runner, cwd=cwd):
            rebased = True
            _resolve_conflicts(
                runner,
                launch_fn,
                repo=repo,
                run_id=run_id,
                cwd=cwd,
            )
        else:
            _abort_rebase(runner, cwd=cwd)
            raise Stalled(_redact_outbound("rebase failed without conflicts"))

    _sync_local_main(runner, base_remote=base_remote, base_ref=base_ref, cwd=cwd)

    new_version: str | None = None
    if has_bump:
        classification = version_bump.classify_bump(runner, cwd=cwd)
        bump_type = classification.bump_type
        target_version = classification.new_version

        if bump_type != "NONE" and target_version:
            show = git.show_file(
                runner,
                f"{base_remote}/{base_ref}:{config.PLUGIN_JSON_PATH}",
                cwd=cwd,
            )
            origin_version = ""
            if show.returncode == 0:
                try:
                    origin_version = json.loads(show.stdout).get("version", "")
                except json.JSONDecodeError:
                    origin_version = ""
            if (
                isinstance(origin_version, str)
                and _SEMVER_RE.fullmatch(origin_version)
                and version_bump._semver_lt(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    target_version,
                    origin_version,
                )
            ):
                target_version = version_bump._apply_bump_type(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    origin_version,
                    bump_type,
                )

            apply_result = version_bump.apply_bump(
                runner,
                target_version,
                base_remote=base_remote,
                base_ref=base_ref,
                cwd=cwd,
            )
            if not apply_result.applied:
                raise Stalled(_redact_outbound(apply_result.error or "apply bump failed"))
            new_version = apply_result.new_version
            _commit_changelog_after_rebump(
                runner,
                new_version,
                old_version,
                resolved_bullets,
                cwd=cwd,
            )

    pushed = False
    if not defer_push:
        _ = _force_push_branch(runner, cwd=cwd)
        pushed = True

    return RebaseResult(
        outcome=Outcome.OK,
        rebased=rebased,
        pushed=pushed,
        new_version=new_version,
        attempts=rebase_attempt + 1,
        detail="",
    )
