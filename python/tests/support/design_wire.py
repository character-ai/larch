"""Canonical wire-format builders for design and plan fixtures.

The builders deliberately serialize only valid, ordinary fixture shapes. Tests
that exercise malformed or legacy wire data should keep their literals inline.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, get_args

from larch.design.plan_grammar import HeadingKind, TrailerKey, compose_trailer_lines
from larch.io import atomic_write, format_kvs
from tests.support.session import run_params_text

_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

PlanHeadingKind = Literal["NEW", "UPDATED"]
_PLAN_HEADING_KINDS: frozenset[HeadingKind] = frozenset(get_args(PlanHeadingKind))
PlanSection = tuple[PlanHeadingKind, str]
ResultEnvRows = Mapping[str, str] | Sequence[tuple[str, str]]


def dialectic_candidate_json(*, option_a: str, option_b: str) -> str:
    """Serialize one ordinary dialectic decision fixture."""
    return json.dumps({"decisions": [{
        "id": "fork", "title": "Fork", "option_a": option_a, "option_b": option_b,
        "tradeoff": "Different failure modes", "drafter_pick": "option_a",
        "why_this_matters": "Operator should see it",
    }]})


def _validate_env_key(key: str) -> None:
    if not _KEY_RE.fullmatch(key):
        msg = f"invalid environment key name: {key!r}"
        raise ValueError(msg)


def _validate_env_value(key: str, value: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        msg = f"unsafe environment value for {key}: contains newline, CR, or NUL"
        raise ValueError(msg)


def _validate_section_path(path: str) -> None:
    if not path.strip() or "\n" in path or "\r" in path:
        msg = f"invalid plan section path: {path!r}"
        raise ValueError(msg)


def _as_row_pairs(rows: ResultEnvRows) -> list[tuple[str, str]]:
    if isinstance(rows, Mapping):
        pairs = [(str(key), str(value)) for key, value in rows.items()]
    else:
        pairs = [(str(key), str(value)) for key, value in rows]
    for key, value in pairs:
        _validate_env_key(key)
        _validate_env_value(key, value)
    return pairs


def diff_lines_trailer(  # noqa: PLR0913 - trailer fields map directly to the wire format.
    diff_lines: int,
    *,
    difficulty: str | None = None,
    diff_added: int | None = None,
    diff_deleted: int | None = None,
    mechanical_churn: bool | None = None,
    oversize_override: str | None = None,
) -> str:
    """Build the terminal trailer block ending in ``diff_lines: <N>``."""
    values: dict[TrailerKey, str | int | bool | None] = {
        "difficulty": difficulty,
        "diff_added": diff_added,
        "diff_deleted": diff_deleted,
        "mechanical_churn": mechanical_churn,
        "oversize_override": oversize_override,
        "diff_lines": diff_lines,
    }
    lines: tuple[str, ...] = compose_trailer_lines(values)
    return "\n".join(lines) + "\n"


def plan_body(  # noqa: PLR0913 - plan fixture fields map directly to the wire format.
    *,
    sections: Sequence[PlanSection] | None = None,
    body: str = "",
    diff_lines: int | None = None,
    difficulty: str | None = None,
    diff_added: int | None = None,
    diff_deleted: int | None = None,
    mechanical_churn: bool | None = None,
    oversize_override: str | None = None,
    header: str = "## Plan",
    executable: bool = False,
) -> str:
    """Build canonical plan text with optional firm headings and trailers.

    When ``executable`` is true, emit the M1 facet sections required by the
    executable-plan contract (closed decisions, ordered implementation,
    acceptance, breaking/migration) around the caller body and sections.
    """
    if executable:
        text = _executable_plan_body(header=header, sections=sections, body=body)
    else:
        text = _ordinary_plan_body(header=header, sections=sections, body=body)
    if diff_lines is None:
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    return text + diff_lines_trailer(
        diff_lines,
        difficulty=difficulty,
        diff_added=diff_added,
        diff_deleted=diff_deleted,
        mechanical_churn=mechanical_churn,
        oversize_override=oversize_override,
    )


def _append_section_headings(chunks: list[str], sections: Sequence[PlanSection]) -> None:
    for kind, path in sections:
        if kind not in _PLAN_HEADING_KINDS:
            msg = f"unsupported plan heading kind: {kind!r}"
            raise ValueError(msg)
        _validate_section_path(path)
        chunks.append(f"### {kind}: {path}\n")


def _ordinary_plan_body(*, header: str, sections: Sequence[PlanSection] | None, body: str) -> str:
    chunks: list[str] = [header]
    if sections:
        chunks.append("\n")
        _append_section_headings(chunks, sections)
        if body:
            chunks.append(body if body.endswith("\n") else f"{body}\n")
    else:
        chunks.append("\n\n")
        if body:
            chunks.append(body if body.endswith("\n") else f"{body}\n")
    return "".join(chunks)


def _executable_plan_body(*, header: str, sections: Sequence[PlanSection] | None, body: str) -> str:
    chunks: list[str] = [
        header,
        "\n\n",
        "### Closed decisions and ownership\n\n- Fixture owns this plan shape.\n\n",
        "### Ordered implementation\n\n1. Apply the planned edits.\n\n",
        "## Files to modify/create\n\n",
    ]
    _append_section_headings(chunks, sections or (("UPDATED", "README.md"),))
    if body:
        chunks.append("\n")
        chunks.append(body if body.endswith("\n") else f"{body}\n")
    chunks.append("\n## Acceptance\n\n- Fixture acceptance holds.\n\n")
    chunks.append("## Breaking changes and migration\n\nNone.\n")
    return "".join(chunks)


def result_env_lines(rows: ResultEnvRows) -> str:
    r"""Serialize ordered ``KEY=value\n`` pairs; reject unsafe keys or values."""
    return format_kvs(_as_row_pairs(rows))


def write_result_env(path: Path | str, rows: ResultEnvRows) -> Path:
    """Atomically write ``result_env_lines`` output; refuse symlink targets."""
    dest = Path(path)
    if dest.is_symlink():
        msg = f"refusing to write symlink result env: {dest}"
        raise OSError(msg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        path=dest,
        text=result_env_lines(rows),
        create_parent=True,
        nofollow=True,
        mode=0o600,
    )
    return dest


def run_params_json(*, overrides: Mapping[str, object] | None = None) -> str:
    """Return schema-v3 ``run-params.json`` text matching ``seed_run_params``."""
    return run_params_text(overrides=overrides)
