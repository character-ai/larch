"""Version bump classification and application (Phase 2 port of bump-version scripts)."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import config
import git
import redact
from bump_worktree import (
    DropResult,
    drop_replay_commit,
    find_commit_depth,
    porcelain_tracked_only,
    sorted_changed_files,
)
from errors import ShipError, Stalled
from proc import Runner

BumpType = Literal["MAJOR", "MINOR", "PATCH", "NONE"]
CountStatus = Literal["ok", "missing_main_ref", "git_error"]

_BUMP_SUBJECT_RE = re.compile(r"^Bump version to [0-9]+\.[0-9]+\.[0-9]+$")
_FLAG_TOKEN_RE = re.compile(r"--[a-zA-Z0-9_-]+")
_SKILL_PATH = "skills/*/SKILL.md"
_AGENT_PATH = "agents/*.md"
_SHORT_SHA_LEN = 7
_PORCELAIN_STATUS_PREFIX_LEN = 2
_NAME_STATUS_RENAME_PATH_INDEX = 2


@dataclass(frozen=True)
class BumpClassification:
    current_version: str
    new_version: str
    bump_type: BumpType
    major_reasons: tuple[str, ...]
    minor_reasons: tuple[str, ...]
    reasoning: str


@dataclass(frozen=True)
class ApplyResult:
    applied: bool
    new_version: str = ""
    commit_sha: str = ""
    error: str = ""


@dataclass(frozen=True)
class BumpPreCheck:
    has_bump: bool
    commits_before: int
    status: CountStatus


@dataclass(frozen=True)
class BumpVerify:
    verified: bool
    commits_after: int
    expected: int
    status: CountStatus


def _redact_outbound(text: str) -> str:
    if not text:
        return text
    out = redact.redact(text)
    if text.endswith("\n"):
        return out
    return out.rstrip("\n")


def _plugin_path(cwd: Path | None) -> Path:
    root = cwd or Path.cwd()
    return root / config.PLUGIN_JSON_PATH


def _read_plugin_version(path: Path) -> str:
    if not path.is_file():
        msg = f"{config.PLUGIN_JSON_PATH} not found"
        raise ShipError(msg)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"{config.PLUGIN_JSON_PATH} is not valid JSON"
        raise ShipError(msg) from exc
    version = data.get("version")
    if not isinstance(version, str) or not version:
        msg = f"{config.PLUGIN_JSON_PATH} missing .version field"
        raise ShipError(msg)
    if not re.fullmatch(config.SEMVER_RE, version):
        msg = f"version {version!r} is not semver (expected X.Y.Z)"
        raise ShipError(msg)
    return version


def _semver_parts(version: str) -> tuple[int, int, int]:
    maj_s, min_s, pat_s = version.split(".", 2)
    return int(maj_s), int(min_s), int(pat_s)


def _semver_lt(left: str, right: str) -> bool:
    return _semver_parts(left) < _semver_parts(right)


def _apply_bump_type(current: str, bump_type: str) -> str:
    maj, min_, pat = _semver_parts(current)
    if bump_type == "MAJOR":
        return f"{maj + 1}.0.0"
    if bump_type == "MINOR":
        return f"{maj}.{min_ + 1}.0"
    return f"{maj}.{min_}.{pat + 1}"


def _infer_bump_type(original_current: str, initial_target: str) -> BumpType:
    c_maj, c_min, _ = _semver_parts(original_current)
    n_maj, n_min, _ = _semver_parts(initial_target)
    if n_maj > c_maj:
        return "MAJOR"
    if n_min > c_min:
        return "MINOR"
    return "PATCH"


def _public_surface_path(path: str) -> bool:
    return fnmatch.fnmatch(path, _SKILL_PATH) or fnmatch.fnmatch(path, _AGENT_PATH)


def _extract_frontmatter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    buf: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(buf)
        buf.append(line)
    return ""


def _frontmatter_field(frontmatter: str, field: str) -> str:
    prefix = f"{field}: "
    for line in frontmatter.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _flag_tokens(text: str) -> set[str]:
    return set(_FLAG_TOKEN_RE.findall(text))


def _resolve_classify_base(runner: Runner, *, cwd: str | None) -> str:
    base = git.try_merge_base(runner, "main", "HEAD", cwd=cwd)
    if base:
        return base
    base = git.try_merge_base(runner, "origin/main", "HEAD", cwd=cwd)
    if base:
        return base
    msg = "could not resolve merge-base against main or origin/main"
    raise ShipError(msg)


def _idempotency_transparent(runner: Runner, ref: str, *, cwd: str | None) -> bool:
    subject = git.log_subject(runner, ref, cwd=cwd)
    if subject.startswith(config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX):
        expected_prefix = config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX
    elif subject.startswith(config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX):
        expected_prefix = config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX
    else:
        return False

    result = git.diff_tree_name_only(runner, ref, cwd=cwd)
    if result.returncode != 0:
        return False
    changed = [line for line in result.stdout.splitlines() if line]
    if not changed:
        return False

    for file in changed:
        if expected_prefix == config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX:
            if file != config.CHANGELOG_DEFAULT_PATH:
                return False
        elif not file.startswith("larch-logs/"):
            return False
    return True


def _idempotency_ref(runner: Runner, *, cwd: str | None) -> str:
    ref = "HEAD"
    depth = 0
    while depth < config.IDEMPOTENCY_DEPTH:
        if git.try_rev_parse(runner, ref, cwd=cwd) is None:
            break
        if _idempotency_transparent(runner, ref, cwd=cwd):
            depth += 1
            ref = f"HEAD~{depth}"
            continue
        break
    return ref


def _build_reasoning(
    *,
    base: str,
    current_version: str,
    bump_type: BumpType,
    new_version: str,
    major_reasons: tuple[str, ...],
    minor_reasons: tuple[str, ...],
) -> str:
    lines = [
        "# Version Bump Reasoning",
        "",
        f"- **Base commit**: `{base[:_SHORT_SHA_LEN] if len(base) >= _SHORT_SHA_LEN else base}`",
        f"- **Current version**: `{current_version}`",
        "- **Classification scope**: `skills/**` and `agents/**` only "
        "(public plugin surface).",
        "",
        f"## Result: {bump_type}",
        "",
        f"- **New version**: `{new_version}`",
        "",
    ]
    if major_reasons:
        lines.append("### MAJOR evidence")
        lines.extend(f"- {reason}" for reason in major_reasons)
        lines.append("")
    if minor_reasons:
        lines.append("### MINOR evidence")
        lines.extend(f"- {reason}" for reason in minor_reasons)
        lines.append("")
    if bump_type == "PATCH":
        lines.extend([
            "### PATCH rationale",
            "",
            "No MAJOR or MINOR evidence found in the public plugin surface. "
            'Defaulting to PATCH per policy ("every PR must bump at least PATCH").',
        ])
    return "\n".join(lines)


def classify_bump(runner: Runner, *, cwd: str | None = None) -> BumpClassification:
    """Classify semver bump from public-surface diff vs main."""
    root = Path(cwd) if cwd else Path.cwd()
    current_version = _read_plugin_version(_plugin_path(root))

    _ = git.fetch(runner, "origin", "main", cwd=cwd)

    base = _resolve_classify_base(runner, cwd=cwd)
    idem_ref = _idempotency_ref(runner, cwd=cwd)
    head_subject = git.log_subject(runner, idem_ref, cwd=cwd)
    if _BUMP_SUBJECT_RE.fullmatch(head_subject):
        reasoning = _build_reasoning(
            base=base,
            current_version=current_version,
            bump_type="NONE",
            new_version=current_version,
            major_reasons=(),
            minor_reasons=(),
        )
        return BumpClassification(
            current_version=current_version,
            new_version=current_version,
            bump_type="NONE",
            major_reasons=(),
            minor_reasons=(),
            reasoning=_redact_outbound(reasoning),
        )

    major: list[str] = []
    minor: list[str] = []

    diff = git.diff_name_status(
        runner,
        base,
        "HEAD",
        paths=config.CLASSIFY_SCOPE_DIRS,
        find_renames=True,
        cwd=cwd,
    )
    if diff.returncode != 0:
        name_status_lines: list[str] = []
    else:
        name_status_lines = diff.stdout.splitlines()

    for line in name_status_lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        old_path = parts[1] if len(parts) > 1 else ""
        new_path = (
            parts[_NAME_STATUS_RENAME_PATH_INDEX]
            if len(parts) > _NAME_STATUS_RENAME_PATH_INDEX
            else ""
        )

        if status == "D" and _public_surface_path(old_path):
            major.append(f"Deleted `{old_path}`")
        elif status == "A" and _public_surface_path(old_path):
            minor.append(f"Added `{old_path}`")
        elif status.startswith("R"):
            if fnmatch.fnmatch(old_path, _SKILL_PATH):
                major.append(f"Renamed skill `{old_path}` → `{new_path}`")
            elif fnmatch.fnmatch(old_path, _AGENT_PATH):
                major.append(f"Renamed agent `{old_path}` → `{new_path}`")
        elif status == "M" and _public_surface_path(old_path):
            old_show = git.show_file(runner, f"{base}:{old_path}", cwd=cwd)
            new_show = git.show_file(runner, f"HEAD:{old_path}", cwd=cwd)
            if old_show.returncode != 0 or new_show.returncode != 0:
                continue
            old_fm = _extract_frontmatter(old_show.stdout)
            new_fm = _extract_frontmatter(new_show.stdout)

            old_name = _frontmatter_field(old_fm, "name")
            new_name = _frontmatter_field(new_fm, "name")
            if old_name and not new_name:
                major.append(f"Removed `name:` frontmatter from `{old_path}`")
            elif old_name and new_name and old_name != new_name:
                major.append(
                    f"Renamed `name:` frontmatter in `{old_path}` "
                    f"({old_name} → {new_name})",
                )

            old_hint = _frontmatter_field(old_fm, "argument-hint")
            new_hint = _frontmatter_field(new_fm, "argument-hint")
            if old_hint or new_hint:
                removed = _flag_tokens(old_hint) - _flag_tokens(new_hint)
                added = _flag_tokens(new_hint) - _flag_tokens(old_hint)
                major.extend(
                    f"Removed `{tok}` from argument-hint in `{old_path}`"
                    for tok in sorted(removed)
                )
                minor.extend(
                    f"Added `{tok}` to argument-hint in `{old_path}`"
                    for tok in sorted(added)
                )

    if major:
        bump_type: BumpType = "MAJOR"
    elif minor:
        bump_type = "MINOR"
    else:
        bump_type = "PATCH"

    new_version = _apply_bump_type(current_version, bump_type)
    reasoning = _build_reasoning(
        base=base,
        current_version=current_version,
        bump_type=bump_type,
        new_version=new_version,
        major_reasons=tuple(major),
        minor_reasons=tuple(minor),
    )
    return BumpClassification(
        current_version=current_version,
        new_version=new_version,
        bump_type=bump_type,
        major_reasons=tuple(major),
        minor_reasons=tuple(minor),
        reasoning=_redact_outbound(reasoning),
    )


def bump_branch_guard(
    branch_name: str,
    current_branch: str,
    *,
    forked: bool = False,
) -> None:
    """Raise Stalled when bump must not proceed on this branch."""
    if not branch_name or not current_branch:
        msg = f"bump-branch-guard: BRANCH_NAME={branch_name} current={current_branch}"
        raise Stalled(msg)
    if branch_name != current_branch:
        msg = f"bump-branch-guard: BRANCH_NAME={branch_name} current={current_branch}"
        raise Stalled(msg)
    if not forked and branch_name in ("main", "master"):
        msg = f"bump-branch-guard: BRANCH_NAME={branch_name} current={current_branch}"
        raise Stalled(msg)


def _count_commits_with_status(runner: Runner, *, cwd: str | None) -> tuple[int, CountStatus]:
    if git.try_rev_parse(runner, "main", cwd=cwd) is not None:
        base_ref = "main"
    elif git.try_rev_parse(runner, "origin/main", cwd=cwd) is not None:
        base_ref = "origin/main"
    else:
        return 0, "missing_main_ref"

    result = git.rev_list_count(runner, f"{base_ref}..HEAD", cwd=cwd)
    if result.returncode != 0:
        return 0, "git_error"
    try:
        return int(result.stdout.strip() or "0"), "ok"
    except ValueError:
        return 0, "git_error"


def check_bump_version_pre(
    runner: Runner,
    *,
    cwd: str | None = None,
    implement_tmpdir: str | None = None,
) -> BumpPreCheck:
    """Pre-check: bump skill presence and commit count before bump."""
    root = Path(cwd) if cwd else Path.cwd()
    has_bump = (root / config.BUMP_VERSION_SKILL_PATH).is_file()
    if has_bump and implement_tmpdir:
        armed = Path(implement_tmpdir) / config.BUMP_VERSION_ARMED_SENTINEL
        try:
            if Path(implement_tmpdir).is_dir():
                armed.touch(exist_ok=True)
        except OSError:
            pass
    count, status = _count_commits_with_status(runner, cwd=cwd)
    return BumpPreCheck(has_bump=has_bump, commits_before=count, status=status)


def verify_bump_commit_count(
    runner: Runner,
    before_count: int,
    *,
    cwd: str | None = None,
) -> BumpVerify:
    """Post-check: exactly one new commit since pre-check."""
    count, status = _count_commits_with_status(runner, cwd=cwd)
    expected = before_count + 1
    verified = status == "ok" and count == expected
    return BumpVerify(
        verified=verified,
        commits_after=count,
        expected=expected,
        status=status,
    )


def _porcelain_all(runner: Runner, *, cwd: str | None) -> list[str] | None:
    result = git.status_porcelain(runner, cwd=cwd)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _tolerated_untracked(line: str) -> bool:
    if not line.startswith("?? "):
        return False
    path = line[3:]
    return any(path.endswith(suffix) for suffix in config.APPLY_BUMP_ALLOWED_UNTRACKED_SUFFIXES)


def _unmerged_paths_from_lines(lines: list[str]) -> list[str]:
    unmerged: list[str] = []
    for line in lines:
        if len(line) < _PORCELAIN_STATUS_PREFIX_LEN + 1:
            continue
        code = line[:2]
        if code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
            unmerged.append(line[3:].strip())
    return unmerged


def apply_bump(
    runner: Runner,
    new_version: str,
    *,
    cwd: str | None = None,
) -> ApplyResult:
    """Apply version bump to plugin.json and commit."""
    if not re.fullmatch(config.SEMVER_RE, new_version):
        return ApplyResult(
            applied=False,
            error=_redact_outbound(f"--new-version {new_version!r} is not semver"),
        )

    root = Path(cwd) if cwd else Path.cwd()
    plugin_path = _plugin_path(root)
    backup_path = plugin_path.with_suffix(plugin_path.suffix + ".bump-backup")

    raw = _porcelain_all(runner, cwd=cwd)
    if raw is None:
        return ApplyResult(applied=False, error=_redact_outbound("git status failed"))

    unmerged = _unmerged_paths_from_lines(raw)
    if unmerged:
        files = ",".join(unmerged)
        return ApplyResult(
            applied=False,
            error=_redact_outbound(
                f"unmerged paths present: {files}. Resolve conflicts from the "
                "in-progress merge or rebase before bumping.",
            ),
        )
    non_internal = [
        line for line in raw
        if not _tolerated_untracked(line)
    ]
    if non_internal:
        return ApplyResult(
            applied=False,
            error=_redact_outbound(
                "Working tree is not clean (staged, unstaged, or untracked changes "
                "present); refusing to bump version.",
            ),
        )

    try:
        original_current = _read_plugin_version(plugin_path)
    except ShipError as exc:
        return ApplyResult(applied=False, error=_redact_outbound(str(exc)))

    initial_target = new_version
    tmp_path = plugin_path.with_suffix(".tmp")

    def _cleanup_stage_artifacts() -> None:
        if backup_path.is_file():
            backup_path.unlink()
        if tmp_path.is_file():
            tmp_path.unlink()

    def rollback_before_commit() -> None:
        if backup_path.is_file():
            _ = shutil.copy2(backup_path, plugin_path)
            backup_path.unlink()
            _ = git.unstage(runner, config.PLUGIN_JSON_PATH, cwd=cwd)
        if tmp_path.is_file():
            tmp_path.unlink()

    def backup_rewrite_stage(target: str) -> ApplyResult | None:
        try:
            _ = shutil.copy2(plugin_path, backup_path)
            data = json.loads(plugin_path.read_text(encoding="utf-8"))
            data["version"] = target
            _ = tmp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            _ = tmp_path.replace(plugin_path)
            add_result = git.add(runner, config.PLUGIN_JSON_PATH, cwd=cwd)
            if add_result.returncode != 0:
                if backup_path.is_file():
                    _ = shutil.copy2(backup_path, plugin_path)
                _ = git.unstage(runner, config.PLUGIN_JSON_PATH, cwd=cwd)
                _cleanup_stage_artifacts()
                return ApplyResult(applied=False, error=_redact_outbound("git add failed"))
        except (OSError, json.JSONDecodeError) as exc:
            if backup_path.is_file():
                _ = shutil.copy2(backup_path, plugin_path)
            _ = git.unstage(runner, config.PLUGIN_JSON_PATH, cwd=cwd)
            _cleanup_stage_artifacts()
            return ApplyResult(applied=False, error=_redact_outbound(str(exc)))
        return None

    stage_err = backup_rewrite_stage(new_version)
    if stage_err is not None:
        return stage_err

    retry_count = 0
    while True:
        fetch_result = git.fetch(runner, "origin", "main", cwd=cwd)
        if fetch_result.returncode != 0:
            rollback_before_commit()
            return ApplyResult(
                applied=False,
                error=_redact_outbound(
                    "git fetch origin main failed; cannot verify origin/main version guards",
                ),
            )

        origin_show = git.show_file(
            runner,
            "origin/main:.claude-plugin/plugin.json",
            cwd=cwd,
        )
        origin_version = ""
        if origin_show.returncode == 0:
            try:
                origin_data = json.loads(origin_show.stdout)
                ov = origin_data.get("version", "")
                if isinstance(ov, str):
                    origin_version = ov
            except json.JSONDecodeError:
                origin_version = ""

        if not re.fullmatch(config.SEMVER_RE, origin_version):
            rollback_before_commit()
            return ApplyResult(
                applied=False,
                error=_redact_outbound("could not parse origin/main published version"),
            )

        if origin_version == new_version or _semver_lt(new_version, origin_version):
            rollback_before_commit()
            if retry_count >= config.APPLY_BUMP_MAX_RETRIES:
                return ApplyResult(
                    applied=False,
                    error=_redact_outbound(
                        "origin/main bump race: could not land version after "
                        f"{config.APPLY_BUMP_MAX_RETRIES} retries "
                        f"(last origin/main={origin_version})",
                    ),
                )
            bump_type = _infer_bump_type(original_current, initial_target)
            new_version = _apply_bump_type(origin_version, bump_type)
            retry_count += 1
            stage_err = backup_rewrite_stage(new_version)
            if stage_err is not None:
                return stage_err
            continue
        break

    commit_msg = config.BUMP_COMMIT_SUBJECT_TEMPLATE.format(version=new_version)
    commit_result = git.commit(runner, commit_msg, cwd=cwd)
    if commit_result.returncode != 0:
        rollback_before_commit()
        return ApplyResult(
            applied=False,
            error=_redact_outbound(
                f"git commit failed; rolled back {config.PLUGIN_JSON_PATH} from backup",
            ),
        )

    if backup_path.is_file():
        backup_path.unlink()
    sha = git.rev_parse(runner, "HEAD", cwd=cwd)
    return ApplyResult(applied=True, new_version=new_version, commit_sha=sha)


def _guard4_allows(
  changed: str,
  *,
  allow_changelog_only: bool,
  bump_files: tuple[str, ...] | None,
) -> bool:
    if bump_files is not None:
        allowed = [*bump_files, config.CHANGELOG_DEFAULT_PATH]
        if not allowed:
            return False
        changed_list = [f for f in changed.split("\n") if f]
        bump_found = False
        for file in changed_list:
            if file not in allowed:
                return False
            if file != config.CHANGELOG_DEFAULT_PATH:
                bump_found = True
        if bump_found:
            return True
        return allow_changelog_only and changed == config.CHANGELOG_DEFAULT_PATH

    default_files = config.DEFAULT_BUMP_FILES
    allowed_one = "\n".join(default_files)
    allowed_two = "\n".join((*default_files, config.CHANGELOG_DEFAULT_PATH))
    if changed in (allowed_one, allowed_two):
        return True
    return allow_changelog_only and changed == config.CHANGELOG_DEFAULT_PATH


def drop_bump_commit(
    runner: Runner,
    *,
    max_depth: int = config.DROP_BUMP_MAX_DEPTH,
    allow_changelog_only: bool = False,
    bump_files: tuple[str, ...] | None = None,
    cwd: str | None = None,
) -> DropResult:
    """Drop the most recent bump version commit within max_depth."""
    tracked = porcelain_tracked_only(runner, cwd=cwd)
    if tracked is None:
        return DropResult(dropped=False, error=_redact_outbound("git status failed"))
    if tracked:
        return DropResult(dropped=False, error="uncommitted tracked changes")

    found_at = find_commit_depth(
        runner,
        max_depth=max_depth,
        subject_matches=lambda subject: bool(_BUMP_SUBJECT_RE.fullmatch(subject or "")),
        cwd=cwd,
    )

    if found_at < 0:
        return DropResult(dropped=False, error="no bump commit found")

    parent_ref = f"HEAD~{found_at + 1}"
    if git.try_rev_parse(runner, parent_ref, cwd=cwd) is None:
        return DropResult(dropped=False, error="parent does not exist")

    changed = sorted_changed_files(
        runner,
        parent_ref,
        f"HEAD~{found_at}",
        cwd=cwd,
    )
    env_bump = os.environ.get(config.ENV_LARCH_BUMP_FILES)
    effective_bump_files = bump_files
    if env_bump is not None and bump_files is None:
        segments = [s.strip() for s in env_bump.split(":") if s.strip()]
        if not segments:
            return DropResult(
                dropped=False,
                error=_redact_outbound(
                    "LARCH_BUMP_FILES is set but empty after parsing; refusing to drop",
                ),
            )
        effective_bump_files = tuple(segments)

    if not _guard4_allows(
        changed,
        allow_changelog_only=allow_changelog_only,
        bump_files=effective_bump_files,
    ):
        return DropResult(dropped=False, error=_redact_outbound("unexpected changed files"))

    old_sha = git.rev_parse(runner, f"HEAD~{found_at}", cwd=cwd)
    replay_err = drop_replay_commit(
        runner,
        found_at=found_at,
        cwd=cwd,
        reset_error="git reset --hard HEAD~1 failed",
        rebase_error="git rebase --onto failed",
    )
    if replay_err is not None:
        return DropResult(dropped=False, error=replay_err)

    return DropResult(dropped=True, old_sha=old_sha)
