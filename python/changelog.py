"""CHANGELOG read/write and merge-conflict resolution (Phase 2 port)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import config
import git
import redact
from bump_worktree import (
    DropResult,
    drop_replay_commit,
    find_subject_commit_depth,
    porcelain_tracked_only,
    sorted_changed_files,
)
from proc import Runner

_VERSION_HEADING_MD = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - ")
_SEMVER = re.compile(config.SEMVER_RE)
_RST_ADORNMENT_CHARS = set("#*=-~^\"'`:.+_")
_MIN_RST_ADORNMENT_LEN = 3
_MIN_RST_SECTIONS_FOR_DOC_TITLE_SKIP = 2


def _today_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


class ChangelogFormat(Enum):
    MARKDOWN = "markdown"
    RST = "rst"


_redact_outbound = redact.redact_outbound


def _rst_version_from_title(title: str) -> str | None:
    if _SEMVER.fullmatch(title):
        return title
    bracket = re.search(r"\[([0-9]+\.[0-9]+\.[0-9]+)\]", title)
    if bracket:
        return bracket.group(1)
    version_prefix = re.match(r"Version ([0-9]+\.[0-9]+\.[0-9]+)", title)
    if version_prefix:
        return version_prefix.group(1)
    return None


def _rst_matches_version_title(title: str, version: str) -> bool:
    found = _rst_version_from_title(title)
    return found == version


def _rst_release_section_indices(lines: list[str]) -> list[int]:
    return [
        idx
        for idx in _rst_title_indices(lines)
        if _rst_version_from_title(lines[idx]) is not None
    ]


def _rst_second_title_index(lines: list[str], fh: int) -> int:
    for i in range(fh + 2, len(lines) - 1):
        title = lines[i]
        ul = lines[i + 1]
        if not title or not ul or title[0].isspace():
            continue
        if not re.search(r"[A-Za-z0-9]", title):
            continue
        if is_rst_adornment(ul, title):
            return i
    return 0


class ChangelogError(Exception):
    """Changelog transform failed (no-anchor=3, duplicate=4 in bash parity)."""

    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CommitResult:
    committed: bool
    commit_sha: str = ""
    error: str = ""


def detect_format(text: str, *, path: str = "") -> ChangelogFormat:
    """Resolve Markdown vs RST from extension or content sniffing."""
    basename = Path(path).name
    if basename.endswith(".rst"):
        return ChangelogFormat.RST
    if basename.endswith(".md"):
        return ChangelogFormat.MARKDOWN
    for line in text.splitlines():
        if line.startswith("## "):
            return ChangelogFormat.MARKDOWN
    return ChangelogFormat.RST


def is_rst_adornment(underline: str, title: str) -> bool:
    if not underline or not title:
        return False
    len_t = len(title)
    if len(underline) < len_t or len(underline) < _MIN_RST_ADORNMENT_LEN:
        return False
    if not all(c in _RST_ADORNMENT_CHARS for c in underline):
        return False
    char = underline[0]
    return all(c == char for c in underline)


def _rst_title_indices(lines: list[str]) -> list[int]:
    indices: list[int] = []
    n = len(lines)
    for i in range(n - 1):
        title = lines[i]
        ul = lines[i + 1]
        if not title or not ul:
            continue
        if title[0].isspace():
            continue
        if not re.search(r"[A-Za-z0-9]", title):
            continue
        if is_rst_adornment(ul, title):
            indices.append(i)
    return indices


def _rst_merge_first_index(lines: list[str]) -> int:
    indices = _rst_title_indices(lines)
    if not indices:
        return -1
    fh1 = indices[0]
    ul = lines[fh1 + 1]
    is_doc_title = (
        is_rst_adornment(ul, lines[fh1])
        and ul
        and all(c == "=" for c in ul)
    )
    if is_doc_title:
        if len(indices) < _MIN_RST_SECTIONS_FOR_DOC_TITLE_SKIP:
            return -1
        return indices[1]
    return fh1


def _rst_section_end_index(lines: list[str], anchor: int) -> int:
    """Index of the next section after the anchor title (exclusive end of anchor block)."""
    release_indices = _rst_release_section_indices(lines)
    if anchor in release_indices:
        for idx in release_indices:
            if idx > anchor:
                return idx
        return len(lines)
    for idx in release_indices:
        if idx > anchor:
            return idx
    for idx in _rst_title_indices(lines):
        if idx > anchor + 1:
            return idx
    return len(lines)


def _md_first_heading_index(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    return -1


def _md_second_heading_index(lines: list[str], start: int) -> int:
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            return i
    return -1


def first_version_heading(text: str, *, fmt: ChangelogFormat) -> str | None:
    if fmt == ChangelogFormat.MARKDOWN:
        for line in text.splitlines():
            if line.startswith("## [Unreleased]"):
                continue
            match = _VERSION_HEADING_MD.match(line)
            if match:
                return match.group(1)
        return None
    lines = text.splitlines()
    for idx in _rst_release_section_indices(lines):
        version = _rst_version_from_title(lines[idx])
        if version:
            return version
    return None


def duplicate_version_heading_count(
    text: str,
    version: str,
    *,
    fmt: ChangelogFormat,
) -> int:
    if fmt == ChangelogFormat.MARKDOWN:
        prefix = f"## [{version}] - "
        return sum(1 for line in text.splitlines() if line.startswith(prefix))
    lines = text.splitlines()
    count = 0
    for idx in _rst_release_section_indices(lines):
        if _rst_matches_version_title(lines[idx], version):
            count += 1
    return count


def extract_version_body(
    text: str,
    version: str,
    *,
    fmt: ChangelogFormat,
) -> str | None:
    if fmt == ChangelogFormat.MARKDOWN:
        return _extract_md_body(text, version)
    return _extract_rst_body(text, version)


def _extract_md_body(text: str, version: str) -> str | None:
    lines = text.splitlines()
    in_section = False
    body: list[str] = []
    pending_blanks = 0
    seen_non_blank = False
    heading = f"## [{version}] - "
    for line in lines:
        if line.startswith(heading):
            in_section = True
            continue
        if in_section and line.startswith("## ["):
            break
        if in_section:
            if not line.strip():
                if seen_non_blank:
                    pending_blanks += 1
            else:
                body.extend([""] * pending_blanks)
                pending_blanks = 0
                body.append(line)
                seen_non_blank = True
    if not seen_non_blank:
        return None
    return "\n".join(body)


def _extract_rst_body(text: str, version: str) -> str | None:
    lines = text.splitlines()
    indices = _rst_release_section_indices(lines)
    start = -1
    for idx in indices:
        if _rst_matches_version_title(lines[idx], version):
            start = idx
            break
    if start < 0:
        return None
    body_start = start + 2
    end = len(lines)
    for idx in indices:
        if idx > start:
            end = idx
            break
    body_lines = lines[body_start:end]
    while body_lines and not body_lines[-1].strip():
        _ = body_lines.pop()
    while body_lines and not body_lines[0].strip():
        _ = body_lines.pop(0)
    if not any(line.strip() for line in body_lines):
        return None
    return "\n".join(body_lines)


def drop_version_section(text: str, version: str, *, fmt: ChangelogFormat) -> str:
    if fmt == ChangelogFormat.MARKDOWN:
        return _drop_md_section(text, version)
    return _drop_rst_section(text, version)


def _drop_md_section(text: str, version: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    heading = re.compile(rf"^## \[{re.escape(version)}\] - ")
    for line in lines:
        if heading.match(line):
            skipping = True
            continue
        if skipping and line.startswith("## ["):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _drop_rst_section(text: str, version: str) -> str:
    lines = text.splitlines()
    indices = _rst_release_section_indices(lines)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if i in indices and _rst_matches_version_title(lines[i], version):
            end = len(lines)
            for j in indices:
                if j > i:
                    end = j
                    break
            i = end
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def write_changelog_entry(
    text: str,
    version: str,
    categories: str,
    *,
    fmt: ChangelogFormat,
    replaces_version: str = "",
) -> str:
    if fmt == ChangelogFormat.MARKDOWN:
        return _write_md_entry(text, version, categories, replaces_version=replaces_version)
    return _write_rst_entry(text, version, categories, replaces_version=replaces_version)


def _entry_block_md(version: str, categories: str) -> list[str]:
    today = _today_iso()
    block = [f"## [{version}] - {today}", ""]
    if categories.strip():
        block.extend(categories.rstrip("\n").splitlines())
    return block


def _insert_md_at_anchor(
    lines: list[str],
    block: list[str],
    *,
    has_unreleased: bool | None = None,
) -> tuple[list[str], bool]:
    """Insert block at the canonical Markdown anchor; return (lines, inserted)."""
    if has_unreleased is None:
        has_unreleased = any(line.startswith("## [Unreleased]") for line in lines)
    out: list[str] = []
    inserted = False
    in_unreleased = False
    for line in lines:
        if line.startswith("## [Unreleased]"):
            out.append(line)
            in_unreleased = True
            continue
        if in_unreleased and line.startswith("## ["):
            in_unreleased = False
            if not inserted:
                out.extend(block)
                out.append("")
                inserted = True
            out.append(line)
            continue
        if in_unreleased:
            out.append(line)
            continue
        if (
            not has_unreleased
            and "and this project adheres to [Semantic Versioning]" in line
        ):
            out.append(line)
            if not inserted:
                out.append("")
                out.extend(block)
                inserted = True
            continue
        if not inserted and line.startswith("## ["):
            out.extend(block)
            out.append("")
            inserted = True
        out.append(line)
    if in_unreleased and not inserted:
        out.append("")
        out.extend(block)
        inserted = True
    return out, inserted


def _write_md_entry(
    text: str,
    version: str,
    categories: str,
    *,
    replaces_version: str,
) -> str:
    lines = text.splitlines()
    entry = _entry_block_md(version, categories)
    has_unreleased = any(line.startswith("## [Unreleased]") for line in lines)
    out: list[str] = []
    inserted = False
    skipping = False
    match_count = 0
    entry_from_version_match = False

    def emit_entry() -> None:
        nonlocal inserted, entry_from_version_match
        if inserted:
            return
        out.extend(entry)
        inserted = True
        entry_from_version_match = True

    for line in lines:
        version_match = line.startswith(f"## [{version}] - ")
        replace_match = (
            replaces_version
            and replaces_version != version
            and line.startswith(f"## [{replaces_version}] - ")
        )
        if version_match or replace_match:
            match_count += 1
            if match_count > 1:
                raise ChangelogError("duplicate version heading", code=4)
            emit_entry()
            skipping = True
            continue
        if skipping and line.startswith("## ["):
            if entry_from_version_match:
                out.append("")
            skipping = False
            entry_from_version_match = False
        if skipping:
            continue
        out.append(line)

    if not inserted:
        out, inserted = _insert_md_at_anchor(out, entry, has_unreleased=has_unreleased)
    if not inserted:
        return _insert_md_version_anchor(text, version, entry_lines=entry)
    result = "\n".join(out)
    return result + ("\n" if text.endswith("\n") else "")


def _write_rst_entry(
    text: str,
    version: str,
    categories: str,
    *,
    replaces_version: str,
) -> str:
    lines = text.splitlines()
    today = _today_iso()
    title = f"Version {version} ({today})"
    underline = "-" * len(title)
    entry_lines = [title, underline, ""]
    if categories.strip():
        entry_lines.extend(categories.rstrip("\n").splitlines())

    ends_with_newline = text.endswith("\n")
    release_indices = _rst_release_section_indices(lines)
    release_set = set(release_indices)
    out: list[str] = []
    inserted = False
    match_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        at_release = i in release_set
        version_match = at_release and _rst_matches_version_title(line, version)
        replace_match = (
            at_release
            and replaces_version
            and replaces_version != version
            and _rst_matches_version_title(line, replaces_version)
        )
        if version_match or replace_match:
            match_count += 1
            if match_count > 1:
                raise ChangelogError("duplicate version heading", code=4)
            if not inserted:
                out.extend(entry_lines)
                inserted = True
            end = len(lines)
            for j in release_indices:
                if j > i:
                    end = j
                    break
            if end < len(lines):
                out.append("")
            i = end
            continue
        out.append(line)
        i += 1

    if not inserted:
        anchor = _rst_merge_first_index(lines)
        if anchor < 0:
            raise ChangelogError("no anchor found for changelog entry", code=3)
        if replaces_version and replaces_version != version:
            return _drop_rst_section(
                _insert_rst_after(
                    lines,
                    anchor,
                    entry_lines,
                    ends_with_newline=ends_with_newline,
                ),
                replaces_version,
            )
        return _insert_rst_after(
            lines,
            anchor,
            entry_lines,
            ends_with_newline=ends_with_newline,
        )

    result = "\n".join(out)
    return result + ("\n" if ends_with_newline else "")


def _insert_rst_after(
    lines: list[str],
    anchor: int,
    entry_lines: list[str],
    *,
    ends_with_newline: bool,
) -> str:
    insert_at = _rst_section_end_index(lines, anchor)
    out = lines[:insert_at]
    if out and out[-1].strip():
        out.append("")
    out.extend(entry_lines)
    if insert_at < len(lines):
        out.append("")
    out.extend(lines[insert_at:])
    result = "\n".join(out)
    return result + ("\n" if ends_with_newline else "")


def _auto_resolve_markdown(ours: list[str], theirs: list[str]) -> list[str] | None:
    h2_idx = _md_first_heading_index(ours)
    h3_idx = _md_first_heading_index(theirs)
    if h2_idx < 0 or h3_idx < 0:
        return None
    if ours[h2_idx] != theirs[h3_idx]:
        return None
    sh2 = _md_second_heading_index(ours, h2_idx)
    sh3 = _md_second_heading_index(theirs, h3_idx)
    tail2 = ours[sh2:] if sh2 > 0 else []
    tail3 = theirs[sh3:] if sh3 > 0 else []
    if tail2 != tail3:
        return None
    end2 = sh2 if sh2 > 0 else len(ours)
    end3 = sh3 if sh3 > 0 else len(theirs)
    out: list[str] = []
    out.extend(ours[:h2_idx])
    out.append(ours[h2_idx])
    seen: set[str] = set()
    for line in ours[h2_idx + 1 : end2]:
        out.append(line)
        seen.add(line)
    for line in theirs[h3_idx + 1 : end3]:
        if line not in seen:
            out.append(line)
            seen.add(line)
    if sh2 > 0:
        out.extend(ours[sh2:])
    return out


def _auto_resolve_rst(ours: list[str], theirs: list[str]) -> list[str] | None:
    fh2 = _rst_merge_first_index(ours)
    fh3 = _rst_merge_first_index(theirs)
    if fh2 < 0 or fh3 < 0 or ours[fh2] != theirs[fh3]:
        return None
    second2 = _rst_second_title_index(ours, fh2)
    second3 = _rst_second_title_index(theirs, fh3)
    tail2 = ours[second2:] if second2 > 0 else []
    tail3 = theirs[second3:] if second3 > 0 else []
    if tail2 != tail3:
        return None
    end2 = second2 if second2 > 0 else len(ours)
    end3 = second3 if second3 > 0 else len(theirs)
    out: list[str] = []
    out.extend(ours[:fh2])
    out.append(ours[fh2])
    out.append(ours[fh2 + 1])
    seen: set[str] = set()
    for line in ours[fh2 + 2 : end2]:
        out.append(line)
        seen.add(line)
    for line in theirs[fh3 + 2 : end3]:
        if line not in seen:
            out.append(line)
            seen.add(line)
    if second2 > 0:
        out.extend(ours[second2:])
    return out


def _md_has_any_l2_heading(text: str) -> bool:
    return any(line.startswith("## ") for line in text.splitlines())


def _md_first_heading_line(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("## "):
            return line
    return ""


def _detect_conflict_format(ours_text: str, theirs_text: str, path: str) -> ChangelogFormat | None:
    """Resolve merge format for extensionless paths (parity with auto-resolve-changelog.sh)."""
    basename = Path(path).name
    if basename.endswith(".rst"):
        return ChangelogFormat.RST
    if basename.endswith(".md"):
        return ChangelogFormat.MARKDOWN
    has2 = _md_has_any_l2_heading(ours_text)
    has3 = _md_has_any_l2_heading(theirs_text)
    if has2 or has3:
        h2 = _md_first_heading_line(ours_text)
        h3 = _md_first_heading_line(theirs_text)
        if h2 and h3 and h2 == h3:
            return ChangelogFormat.MARKDOWN
        return None
    return ChangelogFormat.RST


def _resolve_repo_path(root: Path, rel_path: str) -> Path:
    base = root.resolve()
    target = (base / rel_path).resolve()
    try:
        _ = target.relative_to(base)
    except ValueError as exc:
        msg = f"path escapes repository root: {rel_path}"
        raise ChangelogError(msg) from exc
    return target


def auto_resolve(runner: Runner, conflict_path: str, *, cwd: str | None = None) -> bool:
    """Merge :2: and :3: changelog conflict stages when headings/tails match."""
    ours_result = git.show_file(runner, f":2:{conflict_path}", cwd=cwd)
    theirs_result = git.show_file(runner, f":3:{conflict_path}", cwd=cwd)
    if ours_result.returncode != 0 or theirs_result.returncode != 0:
        return False

    ours_lines = ours_result.stdout.splitlines()
    theirs_lines = theirs_result.stdout.splitlines()
    fmt = _detect_conflict_format(ours_result.stdout, theirs_result.stdout, conflict_path)
    if fmt is None:
        return False

    merged: list[str] | None
    if fmt == ChangelogFormat.MARKDOWN:
        merged = _auto_resolve_markdown(ours_lines, theirs_lines)
    else:
        merged = _auto_resolve_rst(ours_lines, theirs_lines)

    if merged is None:
        return False

    root = Path(cwd) if cwd else Path.cwd()
    target = _resolve_repo_path(root, conflict_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(merged)
    if ours_result.stdout.endswith("\n"):
        text += "\n"
    _ = target.write_text(text, encoding="utf-8")
    return True


def _insert_md_version_anchor(
    text: str,
    version: str,
    *,
    entry_lines: list[str] | None = None,
) -> str:
    """Insert a version heading block at the canonical Markdown anchor."""
    lines = text.splitlines()
    today = _today_iso()
    block = entry_lines if entry_lines is not None else [f"## [{version}] - {today}"]
    out, inserted = _insert_md_at_anchor(lines, block)
    if not inserted:
        raise ChangelogError("no anchor found for changelog entry", code=3)
    result = "\n".join(out)
    return result + ("\n" if text.endswith("\n") else "")


def _insert_version_heading_md(text: str, version: str) -> str:
    """Insert empty ## [version] - today heading (commit-changelog.sh parity)."""
    return _insert_md_version_anchor(text, version)


def _retitle_version_heading_md(
    text: str,
    old_version: str,
    new_version: str,
) -> str | None:
    """Retitle old version heading; return None when old heading absent."""
    lines = text.splitlines()
    today = _today_iso()
    out: list[str] = []
    replaced = False
    dropping_old = False
    has_new = any(line.startswith(f"## [{new_version}] - ") for line in lines)
    for line in lines:
        if line.startswith(f"## [{old_version}] - "):
            if not replaced:
                if not has_new:
                    out.append(f"## [{new_version}] - {today}")
                else:
                    dropping_old = True
                replaced = True
            continue
        if dropping_old and line.startswith("## ["):
            dropping_old = False
        if dropping_old:
            continue
        out.append(line)
    if not replaced:
        return None
    result = "\n".join(out)
    return result + ("\n" if text.endswith("\n") else "")


def commit_changelog(
    runner: Runner,
    version: str,
    *,
    replaces_version: str | None = None,
    path: str = config.CHANGELOG_DEFAULT_PATH,
    cwd: str | None = None,
) -> CommitResult:
    """Insert/retitle changelog heading and commit (Markdown only; RST deferred to Phase 7)."""
    if not _SEMVER.fullmatch(version):
        return CommitResult(
            committed=False,
            error=_redact_outbound(f"invalid --version: {version}"),
        )

    root = Path(cwd) if cwd else Path.cwd()
    try:
        changelog_path = _resolve_repo_path(root, path)
    except ChangelogError as exc:
        return CommitResult(committed=False, error=_redact_outbound(str(exc)))
    if not changelog_path.is_file():
        return CommitResult(committed=False, error=_redact_outbound(f"{path} not found"))

    text = changelog_path.read_text(encoding="utf-8")
    original_text = text
    fmt = detect_format(text, path=path)
    if fmt != ChangelogFormat.MARKDOWN:
        return CommitResult(
            committed=False,
            error=_redact_outbound("commit_changelog supports Markdown only"),
        )

    if duplicate_version_heading_count(text, version, fmt=fmt) > 1:
        return CommitResult(
            committed=False,
            error=_redact_outbound(f"multiple existing ## [{version}] - headings"),
        )

    status = git.status_porcelain(runner, untracked_files="no", cwd=cwd)
    if status.returncode == 0:
        for line in status.stdout.splitlines():
            if not line:
                continue
            file_path = line[3:].strip()
            if line.startswith(("R", "C")) and " -> " in file_path:
                file_path = file_path.split(" -> ", 1)[1]
            if file_path != path:
                return CommitResult(
                    committed=False,
                    error=_redact_outbound(f"tracked file dirty outside {path}: {file_path}"),
                )

    replace = replaces_version or ""
    if replace and replace != version:
        retitled = _retitle_version_heading_md(text, replace, version)
        if retitled is None:
            try:
                text = _insert_version_heading_md(text, version)
            except ChangelogError:
                return CommitResult(
                    committed=False,
                    error=_redact_outbound(f"replaces-version not found: {replace}"),
                )
        else:
            text = retitled

    _ = changelog_path.write_text(text, encoding="utf-8")

    has_diff = not git.diff_quiet(runner, path, cwd=cwd) or not git.diff_quiet(
        runner,
        path,
        cached=True,
        cwd=cwd,
    )
    if not has_diff:
        return CommitResult(committed=False)

    msg = config.CHANGELOG_COMMIT_SUBJECT_TEMPLATE.format(version=version)
    add_result = git.add(runner, path, cwd=cwd)
    if add_result.returncode != 0:
        _ = changelog_path.write_text(original_text, encoding="utf-8")
        return CommitResult(committed=False, error=_redact_outbound("git add failed"))
    commit_result = git.commit(runner, msg, only=path, cwd=cwd)
    if commit_result.returncode != 0:
        _ = changelog_path.write_text(original_text, encoding="utf-8")
        return CommitResult(committed=False, error=_redact_outbound("git commit failed"))
    sha = git.try_rev_parse(runner, "HEAD", cwd=cwd) or ""
    return CommitResult(committed=True, commit_sha=sha)


def drop_changelog_commit(
    runner: Runner,
    version: str,
    *,
    max_depth: int = config.DROP_CHANGELOG_MAX_DEPTH,
    cwd: str | None = None,
) -> DropResult:
    """Drop the most recent Update CHANGELOG commit for version."""
    if not _SEMVER.fullmatch(version):
        return DropResult(dropped=False, error=_redact_outbound("invalid version"))

    tracked = porcelain_tracked_only(runner, cwd=cwd)
    if tracked is None:
        return DropResult(dropped=False, error=_redact_outbound("git status failed"))
    if tracked:
        return DropResult(dropped=False, error=_redact_outbound("dirty worktree"))

    expected = config.CHANGELOG_COMMIT_SUBJECT_TEMPLATE.format(version=version)
    found_at = find_subject_commit_depth(
        runner,
        max_depth=max_depth,
        subject=expected,
        cwd=cwd,
    )

    if found_at < 0:
        return DropResult(dropped=False, error=_redact_outbound("no changelog commit found"))

    parent_ref = f"HEAD~{found_at + 1}"
    if git.try_rev_parse(runner, parent_ref, cwd=cwd) is None:
        return DropResult(dropped=False, error=_redact_outbound("parent missing"))

    changed = sorted_changed_files(
        runner,
        parent_ref,
        f"HEAD~{found_at}",
        cwd=cwd,
    )
    if changed != config.CHANGELOG_DEFAULT_PATH:
        return DropResult(dropped=False, error=_redact_outbound("unexpected files"))

    old_sha = git.try_rev_parse(runner, f"HEAD~{found_at}", cwd=cwd) or ""
    replay_err = drop_replay_commit(
        runner,
        found_at=found_at,
        cwd=cwd,
        reset_error="reset failed",
        rebase_error="rebase failed",
    )
    if replay_err is not None:
        return DropResult(dropped=False, error=_redact_outbound(replay_err))

    return DropResult(dropped=True, old_sha=old_sha)
