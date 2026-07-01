"""Plan command data types, parsing, and validation helpers."""
# ruff: noqa: S108, PLR2004, PLW2901, PLR1714
# pylint: skip-file
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from larch import io as larch_io
from collections.abc import Iterable

from larch.core import config
from larch.core.ctx import Ctx
from larch.core.logging_util import diagnostic, emit, emit_kv, quiet_init
from larch.git.repo_roots import consumer_repo_root
from larch.state.session_env import validate_design_tmpdir

HEADER = "row_type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid"
OPTIONAL_KEYS = ("diff_added", "diff_deleted", "mechanical_churn")

@dataclass(frozen=True)
class PlanCommandRow:
    row_type: str
    source_line: int
    script_path: str = ""
    flag: str = ""
    flag_value: str = ""
    note: str = ""
    cmd_uid: str = ""

    def to_tsv(self) -> str:
        return "\t".join(
            [
                self.row_type,
                str(self.source_line),
                _tsv_escape(self.script_path),
                _tsv_escape(self.flag),
                _tsv_escape(self.flag_value),
                _tsv_escape(self.note),
                _tsv_escape(self.cmd_uid),
            ]
        )


@dataclass(frozen=True)
class OptionalMetadata:
    metadata_trailer_lines: int
    diff_added: str | None
    diff_deleted: str | None
    mechanical_churn: str
    keys: tuple[str, ...]
    values: tuple[str, ...]


@dataclass(frozen=True)
class ValidationSummary:
    status: str
    defect_count: int
    skipped_count: int
    unsafe_token_count: int
    log_text: str


# ---------------------------------------------------------------------------
# Generic helpers


def _git_repo_root(path: Path) -> Path | None:
    return consumer_repo_root(path)


def _repo_root_from(path: Path | None = None) -> Path:
    start = path or Path.cwd()
    repo = _git_repo_root(start)
    if repo:
        return repo
    return Path.cwd().resolve()


def _repo_root_for_plan(*, plan: Path, explicit_repo_root: str | None = None) -> Path:
    if explicit_repo_root:
        return Path(explicit_repo_root).resolve()
    return _git_repo_root(plan.parent) or _repo_root_from(Path(__file__).resolve().parent)


def _plugin_root(repo_root: Path) -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(repo_root))).resolve()


def _atomic_write(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, prefix=f".{path.name}.")


def _tsv_escape(text: str) -> str:
    return text.replace("\r", "").replace("\n", "").replace("\t", "")


def _bad_field(text: str) -> bool:
    return any(ch in text for ch in "\t\n\r")


def _strip_md_ticks(text: str) -> str:
    return re.sub(r"`+\s*$", "", re.sub(r"^\s*`+", "", text)).strip()


def _last_nonempty_line(lines: list[str]) -> tuple[int, str]:
    for idx in range(len(lines) - 1, -1, -1):
        if lines[idx].strip():
            return idx + 1, lines[idx]
    return 0, ""


def last_nonempty_line_number(path: str | Path) -> int:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    return _last_nonempty_line(lines)[0]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Plan command parser


def _emit_parse_note(*, rows: list[PlanCommandRow], line: int, reason: str) -> None:
    if _bad_field(reason):
        rows.append(PlanCommandRow("parse_note", line, note="charset-violation"))
    else:
        rows.append(PlanCommandRow("parse_note", line, note=reason))


def _emit_new_script(*, rows: list[PlanCommandRow], path: str, line: int) -> None:
    path = _strip_md_ticks(path)
    if not path:
        return
    if _bad_field(path):
        _emit_parse_note(rows=rows, line=line, reason="allowlist-path-charset")
    else:
        rows.append(PlanCommandRow("new_script", line, script_path=path))


def _emit_updated_flag(*, rows: list[PlanCommandRow], path: str, flag: str, line: int) -> None:
    path = _strip_md_ticks(path)
    flag = _strip_md_ticks(flag)
    flag = flag.removeprefix("--")
    if not path or not flag:
        return
    if _bad_field(path) or _bad_field(flag):
        _emit_parse_note(rows=rows, line=line, reason="allowlist-charset")
    else:
        rows.append(PlanCommandRow("updated_flag", line, script_path=path, flag=flag))


def _heading_path(line: str) -> str:
    _, _, rest = line.partition(":")
    return _strip_md_ticks(rest)


def _bracket_heading_path(line: str) -> str:
    start = line.find("[")
    end = line.find("]", start + 1)
    if start < 0 or end <= start:
        return ""
    return _strip_md_ticks(line[start + 1 : end])


def _join_continuations(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        while re.search(r"\\\s*$", line) and not re.search(r"\\\\\s*$", line):
            line = re.sub(r"\\\s*$", "", line)
            i += 1
            if i >= len(lines):
                break
            line += lines[i]
        out.append(line)
        i += 1
    return "\n".join(out)


def _strip_heredoc_multiline(*, lines: list[str], fence_start: int, rows: list[PlanCommandRow]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    i = 0
    compressed = 0
    while i < len(lines):
        line = lines[i]
        pos = line.find("<<")
        if pos < 0:
            compressed += 1
            out.append((fence_start + compressed, line))
            i += 1
            continue
        pre = line[:pos].strip()
        if pre:
            compressed += 1
            out.append((fence_start + compressed, pre))
        rest = line[pos + 2 :].lstrip()
        delim = ""
        if rest.startswith("'"):
            q = rest.find("'", 1)
            if q > 0:
                delim = rest[1:q]
        elif rest.startswith('"'):
            q = rest.find('"', 1)
            if q == -1:
                _emit_parse_note(rows=rows, line=fence_start + compressed + 1, reason="heredoc-unterminated-quote")
                compressed += 1
                out.append((fence_start + compressed, line))
                i += 1
                continue
            delim = rest[1:q]
        else:
            match = re.match(r"[A-Za-z0-9_]+", rest)
            if match:
                delim = match.group(0)
        if not delim:
            compressed += 1
            out.append((fence_start + compressed, line))
            i += 1
            continue
        i += 1
        while i < len(lines) and lines[i] != delim:
            i += 1
        if i < len(lines):
            i += 1
    return out


def _split_segments(segment: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_s = in_d = esc = False
    i = 0
    while i < len(segment):
        ch = segment[i]
        if esc:
            buf.append(ch)
            esc = False
            i += 1
            continue
        if ch == "\\" and (in_s or in_d):
            buf.append(ch)
            esc = True
            i += 1
            continue
        if not in_d and ch == "'" and not in_s:
            in_s = True
            buf.append(ch)
            i += 1
            continue
        if in_s:
            buf.append(ch)
            if ch == "'":
                in_s = False
            i += 1
            continue
        if not in_s and ch == '"' and not in_d:
            in_d = True
            buf.append(ch)
            i += 1
            continue
        if in_d:
            buf.append(ch)
            if ch == '"':
                in_d = False
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        if depth > 0:
            buf.append(ch)
            i += 1
            continue
        two = segment[i : i + 2]
        if two in {"&&", "||"}:
            value = "".join(buf)
            if value:
                parts.append(value)
            buf = []
            i += 2
            continue
        if ch in {"|", ";"}:
            value = "".join(buf)
            if value:
                parts.append(value)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    value = "".join(buf)
    if value:
        parts.append(value)
    return parts


def _has_command_substitution(seg: str) -> bool:
    i = 0
    while True:
        idx = seg.find("$(", i)
        if idx < 0:
            return False
        if not seg.startswith("$((", idx):
            return True
        i = idx + 2


def _tokenize(seg: str) -> list[str]:
    toks: list[str] = []
    cur: list[str] = []
    in_s = in_d = esc = False
    for ch in seg:
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\" and (in_s or in_d):
            cur.append(ch)
            esc = True
            continue
        if not in_d and ch == "'" and not in_s:
            in_s = True
            cur.append(ch)
            continue
        if in_s:
            cur.append(ch)
            if ch == "'":
                in_s = False
            continue
        if not in_s and ch == '"' and not in_d:
            in_d = True
            cur.append(ch)
            continue
        if in_d:
            cur.append(ch)
            if ch == '"':
                in_d = False
            continue
        if ch.isspace():
            if cur:
                toks.append("".join(cur))
                cur = []
            continue
        cur.append(ch)
    if cur:
        toks.append("".join(cur))
    return toks


def _normalize_token(*, token: str, repo_root: Path, plugin_root: Path) -> str:
    value = token.strip()
    if len(value) >= 2 and ((value[0] == value[-1] == "'") or (value[0] == value[-1] == '"')):
        value = value[1:-1]
    value = value.replace("${CLAUDE_PLUGIN_ROOT}/", "").replace("$CLAUDE_PLUGIN_ROOT/", "")
    for root in (plugin_root, repo_root):
        prefix = str(root).rstrip("/") + "/"
        value = value.removeprefix(prefix)
    return value.strip()


def _parse_command_segment(
    *,
    rows: list[PlanCommandRow],
    source_line: int,
    seg: str,
    repo_root: Path,
    plugin_root: Path,
    uid_next: list[int],
) -> None:
    if _has_command_substitution(seg):
        _emit_parse_note(rows=rows, line=source_line, reason="subshell")
        return
    if "<(" in seg:
        _emit_parse_note(rows=rows, line=source_line, reason="process_substitution")
        return
    if re.search(r"(^|\s)eval(\s|$)", seg):
        _emit_parse_note(rows=rows, line=source_line, reason="eval")
        return
    toks = _tokenize(seg)
    while toks:
        first = _normalize_token(token=toks[0], repo_root=repo_root, plugin_root=plugin_root)
        if first in {"bash", "sh", "dash", "/bin/bash", "/bin/sh", "env"}:
            toks.pop(0)
            continue
        if first == "-c":
            _emit_parse_note(rows=rows, line=source_line, reason="inline-shell")
            return
        if first == "--":
            toks.pop(0)
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", first):
            toks.pop(0)
            continue
        break
    if not toks:
        return
    script = _normalize_token(token=toks[0], repo_root=repo_root, plugin_root=plugin_root)
    if not script or script.startswith("-"):
        return
    if ".." in script or script.startswith("/"):
        _emit_parse_note(rows=rows, line=source_line, reason="non-canonical-script-path")
        return
    if _bad_field(script):
        _emit_parse_note(rows=rows, line=source_line, reason="charset-violation")
        return
    uid_next[0] += 1
    uid = str(uid_next[0])
    flags = 0
    k = 1
    while k < len(toks):
        tok = _normalize_token(token=toks[k], repo_root=repo_root, plugin_root=plugin_root)
        if not tok:
            k += 1
            continue
        if not tok.startswith("--"):
            k += 1
            continue
        if tok == "--":
            break
        body = tok[2:]
        if not body:
            k += 1
            continue
        if "=" in body:
            flag, value = body.split("=", 1)
        else:
            flag = body
            value = ""
            if k + 1 < len(toks):
                nxt = _normalize_token(token=toks[k + 1], repo_root=repo_root, plugin_root=plugin_root)
                if nxt and not nxt.startswith("-"):
                    value = nxt
                    k += 1
        if _bad_field(flag) or _bad_field(value):
            _emit_parse_note(rows=rows, line=source_line, reason="charset-violation")
            return
        rows.append(PlanCommandRow("invocation", source_line, script_path=script, flag=flag, flag_value=value, cmd_uid=uid))
        flags += 1
        k += 1
    if flags == 0:
        rows.append(PlanCommandRow("invocation_no_flags", source_line, script_path=script, cmd_uid=uid))


def parse_plan_commands(*, plan_text: str, repo_root: str | Path | None = None, plugin_root: str | Path | None = None) -> list[PlanCommandRow]:
    repo = Path(repo_root).resolve() if repo_root else _repo_root_from()
    plugin = Path(plugin_root).resolve() if plugin_root else _plugin_root(repo)
    rows: list[PlanCommandRow] = []
    lines = plan_text.splitlines()
    files_section = ""
    pending_updated = ""
    in_fence = False
    fence_start = 0
    fence_buf: list[str] = []
    uid_next = [0]

    def process_fence(*, start: int, text: str) -> None:
        if not text:
            return
        joined = _join_continuations(text)
        phys = joined.split("\n")
        for line_no, piece in _strip_heredoc_multiline(lines=phys, fence_start=start, rows=rows):
            if not piece:
                continue
            for seg in _split_segments(piece):
                seg = seg.strip()
                if seg:
                    _parse_command_segment(rows=rows, source_line=line_no, seg=seg, repo_root=repo, plugin_root=plugin, uid_next=uid_next)

    for idx, raw in enumerate(lines, start=1):
        if re.match(r"^###[ \t]+Files[ \t]+to[ \t]+create([ \t]|$)", raw):
            files_section = "create"
            pending_updated = ""
            continue
        if re.match(r"^###[ \t]+Files[ \t]+to[ \t]+update([ \t]|$)", raw):
            files_section = "update"
            pending_updated = ""
            continue
        h3_misc = bool(re.match(r"^###[ \t]+", raw)) and not raw.startswith("####") and not re.match(r"^###[ \t]+Files[ \t]+to[ \t]+(create|update)", raw)
        h2_misc = bool(re.match(r"^##[ \t]+", raw)) and not raw.startswith("###") and not re.match(r"^##[ \t]+Files[ \t]+to[ \t]+(create|update)", raw)
        if h3_misc or h2_misc:
            br_new = bool(re.match(r"^#{2,3}[ \t]+NEW[ \t]+\[", raw))
            br_upd = bool(re.match(r"^#{2,3}[ \t]+UPDATED[ \t]+\[", raw))
            if re.match(r"^#{2,3}[ \t]+NEW:", raw) or br_new:
                _emit_new_script(rows=rows, path=_bracket_heading_path(raw) if br_new else _heading_path(raw), line=idx)
            if re.match(r"^#{2,3}[ \t]+UPDATED:", raw) or br_upd:
                pending_updated = _bracket_heading_path(raw) if br_upd else _heading_path(raw)
            elif re.match(r"^#{2,3}[ \t]+", raw):
                pending_updated = ""
            if not (re.match(r"^#{2,3}[ \t]+(NEW:|UPDATED:)", raw) or br_new or br_upd):
                files_section = ""
            continue
        if pending_updated and re.match(r"^[ \t]*-[ \t]+Adds[ \t]+flag:", raw):
            flag = re.sub(r"^[ \t]*-[ \t]+Adds[ \t]+flag:[ \t]*", "", raw).strip()
            _emit_updated_flag(rows=rows, path=pending_updated, flag=flag, line=idx)
            continue
        if files_section == "create" and "**NEW**:" in raw:
            path = re.sub(r"^[^*]*\*\*NEW\*\*:[ \t]*", "", raw).strip()
            _emit_new_script(rows=rows, path=path, line=idx)
        if files_section == "update" and "**UPDATED**:" in raw:
            pending_updated = _strip_md_ticks(re.sub(r"^[^*]*\*\*UPDATED\*\*:[ \t]*", "", raw).strip())
            continue
        if files_section == "update" and pending_updated and re.match(r"^[ \t]+-[ \t]+Adds[ \t]+flag:", raw):
            flag = re.sub(r"^[ \t]+-[ \t]+Adds[ \t]+flag:[ \t]*", "", raw).strip()
            _emit_updated_flag(rows=rows, path=pending_updated, flag=flag, line=idx)

        if re.match(r"^```[ \t]*(bash|sh)[ \t]*$", raw):
            in_fence = True
            fence_start = idx
            fence_buf = []
            continue
        if in_fence and re.match(r"^```[ \t]*$", raw):
            process_fence(start=fence_start, text="\n".join(fence_buf))
            in_fence = False
            fence_start = 0
            fence_buf = []
            continue
        if in_fence:
            fence_buf.append(raw)
    if in_fence and fence_buf:
        process_fence(start=fence_start, text="\n".join(fence_buf))
    return rows


def render_plan_command_tsv(rows: Iterable[PlanCommandRow]) -> str:
    return HEADER + "\n" + "\n".join(row.to_tsv() for row in rows) + "\n"


def parse_plan_commands_main(argv: list[str]) -> int:
    quiet_init(argv0="plan parse-commands")
    parser = argparse.ArgumentParser(prog="cli.py plan parse-commands")
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    plan = Path(args.plan_file)
    if not plan.is_file():
        diagnostic(f"parse-commands: plan file missing or unreadable: {plan}")
        return 2
    repo = _repo_root_for_plan(plan=plan, explicit_repo_root=args.repo_root)
    rows = parse_plan_commands(plan_text=plan.read_text(encoding="utf-8", errors="replace"), repo_root=repo, plugin_root=_plugin_root(repo))
    _atomic_write(path=Path(args.output), text=render_plan_command_tsv(rows))
    return 0


# ---------------------------------------------------------------------------
# Validator


def _read_tsv(path: Path) -> list[PlanCommandRow]:
    rows: list[PlanCommandRow] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for idx, line in enumerate(handle):
            line = line.rstrip("\n")
            if idx == 0:
                continue
            parts = line.split("\t")
            parts += [""] * (7 - len(parts))
            try:
                source_line = int(parts[1] or "0")
            except ValueError:
                source_line = 0
            rows.append(PlanCommandRow(parts[0], source_line, parts[2], parts[3], parts[4], parts[5], parts[6]))
    return rows


def _is_repo_script(path: str) -> bool:
    while path.startswith("./"):
        path = path[2:]
    if ".." in path:
        return False
    return path.startswith("scripts/") or (path.startswith("skills/") and "/scripts/" in path) or (path.startswith(".claude/skills/") and "/scripts/" in path)


def _distinct_flag_in_help(*, flag: str, help_text: str) -> bool:
    target = f"--{flag}"
    for match in re.finditer(re.escape(target), help_text):
        before = " " if match.start() == 0 else help_text[match.start() - 1]
        if match.start() > 0 and re.match(r"[A-Za-z0-9_]", before):
            continue
        after = help_text[match.end() : match.end() + 1]
        if after == "" or after == "=" or re.match(r"[\s\)),;:\]|]", after):
            return True
        if re.match(r"[A-Za-z0-9_-]", after):
            continue
        return True
    return False


def _registry_hooks(path: Path) -> dict[str, str]:
    hooks: dict[str, str] = {}
    if not path.is_file():
        return hooks
    with path.open(encoding="utf-8", errors="replace") as handle:
        for idx, line in enumerate(handle):
            if idx == 0:
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                hooks[parts[0]] = parts[1]
    return hooks


def _unsafe_token(token: str) -> bool:
    return any(x in token for x in ("..", "`", "$", "*", "?", "[", "]", ";", "|", "&", ">", "<", "(", ")"))


def _canonical_script_path(path: str) -> str:
    while path.startswith("./"):
        path = path[2:]
    return path


def _is_new_script(*, rows: list[PlanCommandRow], script: str) -> bool:
    script = _canonical_script_path(script)
    return any(row.row_type == "new_script" and _canonical_script_path(row.script_path) == script for row in rows)


def _allow_flag(*, rows: list[PlanCommandRow], script: str, flag: str) -> bool:
    script = _canonical_script_path(script)
    return any(row.row_type == "updated_flag" and _canonical_script_path(row.script_path) == script and row.flag == flag for row in rows)


def _redact_capture(*, repo_root: Path, text: str) -> str:
    cli = repo_root / "python" / "cli.py"
    if cli.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(cli), "redact", "secrets"],
                input=text[:65536],
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode == 0:
                return proc.stdout
        except OSError:
            pass
    return "[redaction unavailable; capture withheld]\n"


def redact_capture(*, repo_root: Path, text: str) -> str:
    return _redact_capture(repo_root=repo_root, text=text)


def _resolve_repo_script(*, script: str, repo: Path, plugin: Path | None) -> tuple[Path | None, str]:
    """Resolve a repo-relative plan-command script against the consumer repo
    root first, then the plugin root.

    Returns ``(resolved_path, "")`` when the script stays canonical under one of
    the roots and exists there. Otherwise returns ``(None, kind)`` where ``kind``
    is ``"missing-script"`` when at least one root kept the path canonical (the
    file is simply absent) or ``"non-canonical-path"`` when every root escaped
    its tree. Checking both roots lets scripts that live only in the consumer
    repo or only in the plugin cache pass the existence check (#4490).
    """
    roots = [repo]
    if plugin is not None and plugin != repo:
        roots.append(plugin)
    canonical_seen = False
    for root in roots:
        candidate = (root / script).resolve()
        try:
            _ = candidate.relative_to(root)
        except ValueError:
            continue
        canonical_seen = True
        if candidate.is_file():
            return candidate, ""
    return None, "missing-script" if canonical_seen else "non-canonical-path"


def validate_plan_command_rows(
    *,
    rows: list[PlanCommandRow],
    repo_root: str | Path,
    registry: str | Path | None = None,
    source_kind: str = "plan",
    help_timeout: float = 10,
    dry_run_timeout: float = 10,
    plugin_root: str | Path | None = None,
) -> ValidationSummary:
    repo = Path(repo_root).resolve()
    plugin = Path(plugin_root).resolve() if plugin_root else None
    reg = Path(registry).resolve() if registry else repo / "scripts" / "dry-runnable-scripts.tsv"
    hooks = _registry_hooks(reg)
    log: list[str] = []
    defect_count = 0
    skipped_count = 0
    unsafe_count = 0

    def defect(line: str) -> None:
        nonlocal defect_count
        log.append(line)
        defect_count += 1

    def skip(line: str) -> None:
        nonlocal skipped_count
        log.append(line)
        skipped_count += 1

    grouped: dict[tuple[str, str, str], list[PlanCommandRow]] = {}
    noflags: set[tuple[str, str, str]] = set()
    for row in rows:
        if row.row_type not in {"invocation", "invocation_no_flags"}:
            continue
        key = (str(row.source_line), row.cmd_uid, row.script_path)
        grouped.setdefault(key, [])
        if row.row_type == "invocation":
            grouped[key].append(row)
        else:
            noflags.add(key)

    help_cache: dict[str, tuple[int, str, bool]] = {}
    for (_line, _uid, script), flags in grouped.items():
        if not script or not _is_repo_script(script):
            continue
        if _is_new_script(rows=rows, script=script):
            skip(f"SKIPPED script={script} reason=new-script")
            continue
        abs_path, existence_defect = _resolve_repo_script(script=script, repo=repo, plugin=plugin)
        if abs_path is None:
            defect(f"DEFECT script={script} kind={existence_defect}")
            continue
        if script not in help_cache:
            env = os.environ.copy()
            env["LARCH_QUIET_DISABLE"] = "1"
            try:
                help_proc = subprocess.run(
                    [str(abs_path), "--help"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=help_timeout,
                    env=env,
                    check=False,
                )
                text = help_proc.stdout or ""
                help_empty = not (text and help_proc.returncode in {0, 1, 2})
                help_cache[script] = (help_proc.returncode, text, help_empty)
            except subprocess.TimeoutExpired:
                help_cache[script] = (124, "", True)
            except OSError:
                help_cache[script] = (127, "", True)
        _, help_text, help_empty = help_cache[script]
        help_ok = not help_empty
        if not help_ok:
            skip(f"SKIPPED_FLAG_CHECK script={script} reason=no-help")
        tier2_defect = False
        for row in flags:
            if help_ok and not _allow_flag(rows=rows, script=script, flag=row.flag) and not _distinct_flag_in_help(flag=row.flag, help_text=help_text):
                defect(f"DEFECT script={script} kind=unknown-flag flag={row.flag}")
                tier2_defect = True
        if source_kind == "composed":
            continue
        hook = hooks.get(script, "")
        if not hook:
            continue
        if hook not in {"--validate-only", "LARCH_DRY_RUN=1"}:
            defect(f"DEFECT script={script} kind=unknown-registry-hook hook={hook}")
            continue
        if tier2_defect:
            continue
        argv = [str(abs_path)]
        for row in flags:
            argv.append(f"--{row.flag}")
            if row.flag_value:
                argv.append(row.flag_value)
        if any(_unsafe_token(tok) for tok in argv):
            defect(f"DEFECT script={script} kind=unsafe-token token=<redacted>")
            unsafe_count += 1
            continue
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
            "USER": os.environ.get("USER", ""),
            "LOGNAME": os.environ.get("LOGNAME", os.environ.get("USER", "")),
        }
        if os.environ.get("LANG"):
            env["LANG"] = os.environ["LANG"]
        run_argv = argv + (["--validate-only"] if hook == "--validate-only" else [])
        if hook == "LARCH_DRY_RUN=1":
            env["LARCH_DRY_RUN"] = "1"
        try:
            dry = subprocess.run(
                run_argv,
                cwd=str(repo),
                text=True,
                capture_output=True,
                timeout=dry_run_timeout,
                env=env,
                check=False,
            )
            cap = dry.stdout + dry.stderr
            dry_rc = dry.returncode
        except subprocess.TimeoutExpired as exc:
            cap = (exc.stdout or "") + (exc.stderr or "")
            dry_rc = 124
        log.append(f"TIER3_CAPTURE script={script} exit={dry_rc}")
        log.append(_redact_capture(repo_root=repo, text=cap) if cap else "(empty capture)")
        if dry_rc != 0:
            defect(f"DEFECT script={script} kind=dry-run-failed exit={dry_rc}")
    status = "defects-found" if defect_count else "ok"
    summary = f"VALIDATE_STATUS={status}\tDEFECT_COUNT={defect_count}\tSKIPPED_COUNT={skipped_count}\tUNSAFE_TOKEN_COUNT={unsafe_count}"
    log.append(summary)
    return ValidationSummary(status, defect_count, skipped_count, unsafe_count, "\n".join(log) + "\n")


def validate_plan_commands_main(argv: list[str]) -> int:
    quiet_init(argv0="plan validate-commands")
    parser = argparse.ArgumentParser(prog="cli.py plan validate-commands")
    parser.add_argument("--tsv-file", required=True)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--dry-runnable-registry")
    parser.add_argument("--source-kind", choices=("plan", "composed"), default="plan")
    parser.add_argument("--help-timeout", type=float, default=10)
    parser.add_argument("--dry-run-timeout", type=float, default=10)
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    tsv = Path(args.tsv_file)
    if not tsv.is_file():
        diagnostic(f"validate-commands: unreadable TSV: {tsv}")
        return 2
    repo = _repo_root_for_plan(plan=tsv.parent, explicit_repo_root=args.repo_root)
    summary = validate_plan_command_rows(
        rows=_read_tsv(tsv), repo_root=repo, registry=args.dry_runnable_registry, source_kind=args.source_kind, help_timeout=args.help_timeout, dry_run_timeout=args.dry_run_timeout, plugin_root=_plugin_root(repo)
    )
    _atomic_write(path=Path(args.log_file), text=summary.log_text)
    emit(f"VALIDATE_STATUS={summary.status}\tDEFECT_COUNT={summary.defect_count}\tSKIPPED_COUNT={summary.skipped_count}\tUNSAFE_TOKEN_COUNT={summary.unsafe_token_count}")
    return 0


def validate_plan_main(argv: list[str]) -> int:
    quiet_init(argv0="plan validate")
    parser = argparse.ArgumentParser(prog="cli.py plan validate")
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--source-kind", choices=("plan", "composed"))
    parser.add_argument("--design-tmpdir")
    args = parser.parse_args(argv)
    plan = Path(args.plan_file)
    if not plan.is_file():
        diagnostic(f"validate: unreadable plan file: {plan}")
        return 2
    repo = _repo_root_for_plan(plan=plan, explicit_repo_root=args.repo_root)
    plugin = _plugin_root(repo)
    source_kind = args.source_kind or ("composed" if plan.name == "composed-plan.md" else "plan")
    rows = parse_plan_commands(plan_text=plan.read_text(encoding="utf-8", errors="replace"), repo_root=repo, plugin_root=plugin)
    summary = validate_plan_command_rows(rows=rows, repo_root=repo, registry=None, source_kind=source_kind, plugin_root=plugin)
    emit_kv(key="VALIDATE_STATUS", value=summary.status)
    emit_kv(key="VALIDATE_DEFECT_COUNT", value=str(summary.defect_count))
    emit_kv(key="VALIDATE_SKIPPED_COUNT", value=str(summary.skipped_count))
    emit_kv(key="VALIDATE_UNSAFE_TOKEN_COUNT", value=str(summary.unsafe_token_count))
    design_tmpdir_raw = args.design_tmpdir or os.environ.get(config.ENV_DESIGN_TMPDIR, "")
    argv_overrides: dict[str, str] = {}
    design_tmpdir = Path(design_tmpdir_raw).resolve() if design_tmpdir_raw else None
    if design_tmpdir_raw:
        ok, _message = validate_design_tmpdir(design_tmpdir_raw)
    else:
        ok = False
    if ok and design_tmpdir is not None:
        argv_overrides[config.ENV_DESIGN_TMPDIR] = str(design_tmpdir)
    ctx = Ctx.from_mapping({**os.environ, **argv_overrides})
    if ok and design_tmpdir and design_tmpdir.is_dir():
        log_path = design_tmpdir / "validate-plan-commands.log"
        _atomic_write(path=log_path, text=summary.log_text)
    else:
        fd, name = tempfile.mkstemp(prefix="larch-validate-plan-commands.log.", dir=ctx.tmpdir or "/tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(summary.log_text)
        log_path = Path(name)
    emit_kv(key="VALIDATE_LOG_FILE", value=str(log_path))
    return 0


