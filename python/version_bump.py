"""Version bump classification and application (Phase 2 port of release scripts)."""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import config
import git
import redact
from errors import ShipError, Stalled
from proc import Runner

BumpType = Literal["MAJOR", "MINOR", "PATCH", "NONE"]

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




_redact_outbound = redact.redact_outbound


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


def _apply_bump_type(current: str, bump_type: str) -> str:
    maj, min_, pat = _semver_parts(current)
    if bump_type == "MAJOR":
        return f"{maj + 1}.0.0"
    if bump_type == "MINOR":
        return f"{maj}.{min_ + 1}.0"
    return f"{maj}.{min_}.{pat + 1}"


def _public_surface_path(path: str) -> bool:
    return fnmatch.fnmatch(path, _SKILL_PATH) or fnmatch.fnmatch(path, _AGENT_PATH)


def _extract_frontmatter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return ""
    buf: list[str] = []
    for line in lines[1:]:
        if line == "---":
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
    if not subject.startswith(config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX):
        return False

    result = git.diff_tree_name_only(runner, ref, cwd=cwd)
    if result.returncode != 0:
        return False
    changed = [line for line in result.stdout.splitlines() if line]
    if not changed:
        return False

    return all(file.startswith("larch-logs/") for file in changed)


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
        msg = "git diff --name-status failed during classify"
        raise ShipError(msg)
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
        major_reasons=tuple(_redact_outbound(reason) for reason in major),
        minor_reasons=tuple(_redact_outbound(reason) for reason in minor),
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
    tolerated = [line for line in raw if _tolerated_untracked(line)]
    non_internal = [line for line in raw if not _tolerated_untracked(line)]
    if non_internal:
        return ApplyResult(
            applied=False,
            error=_redact_outbound(
                "Working tree is not clean (staged, unstaged, or untracked changes "
                "present); refusing to bump version.",
            ),
        )
    if tolerated:
        internal_list = " ".join(line[3:] for line in tolerated)
        warn = (
            "WARN: larch-internal untracked artifacts present "
            f"(tolerated before bump): {internal_list}\n"
        )
        _ = sys.stderr.write(_redact_outbound(warn))

    try:
        _ = _read_plugin_version(plugin_path)
    except ShipError as exc:
        return ApplyResult(applied=False, error=_redact_outbound(str(exc)))

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
    sha = git.try_rev_parse(runner, "HEAD", cwd=cwd) or ""
    return ApplyResult(applied=True, new_version=new_version, commit_sha=sha)
