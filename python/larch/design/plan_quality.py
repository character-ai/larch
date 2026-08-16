"""Plan-quality library retained for still-Python design callers (#8576).

Command ownership for parse/validate/check-size/revise/auto-fix lives in Rust.
This module keeps optional-trailer parsing used by remaining design Python and
tests until later design leaves retire it.
"""
# pylint: skip-file
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from larch.core import config
from larch.design import plan_grammar
from larch.calibration import difficulty

OPTIONAL_KEYS = plan_grammar.OPTIONAL_SIZE_TRAILER_KEYS


@dataclass(frozen=True)
class OptionalMetadata:
    metadata_trailer_lines: int
    diff_added: str | None
    diff_deleted: str | None
    mechanical_churn: str
    oversize_override: str | None
    keys: tuple[str, ...]
    values: tuple[str, ...]


def _read_plan(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_optional_metadata(plan_text: str) -> OptionalMetadata:
    trailers = plan_grammar.parse_final_trailers(plan_text, require_diff_lines=True)
    diff_added: str | None = None
    diff_deleted: str | None = None
    mechanical = "false"
    oversize_override: str | None = None
    has_added = has_deleted = has_mech = has_difficulty = has_oversize_override = False
    for match in trailers.matches:
        if match.key == "diff_added":
            diff_added = match.value
            has_added = True
        elif match.key == "diff_deleted":
            diff_deleted = match.value
            has_deleted = True
        elif match.key == "mechanical_churn":
            mechanical = str(match.parsed_value).lower()
            has_mech = True
        elif match.key == "oversize_override":
            oversize_override = config.OVERSIZE_OVERRIDE_OPERATOR
            has_oversize_override = True
        elif match.key == "difficulty":
            has_difficulty = True
    keys = tuple(
        k
        for k, present in (
            ("difficulty", has_difficulty),
            ("diff_added", has_added),
            ("diff_deleted", has_deleted),
            ("mechanical_churn", has_mech),
            ("oversize_override", has_oversize_override),
        )
        if present
    )
    vals: list[str] = []
    if has_added and diff_added is not None:
        vals.append(f"diff_added={diff_added}")
    if has_deleted and diff_deleted is not None:
        vals.append(f"diff_deleted={diff_deleted}")
    if has_mech:
        vals.append(f"mechanical_churn={mechanical}")
    if has_oversize_override and oversize_override is not None:
        vals.append(f"oversize_override={oversize_override}")
    return OptionalMetadata(
        max(0, len(trailers.lines) - 1),
        diff_added,
        diff_deleted,
        mechanical,
        oversize_override,
        keys,
        tuple(vals),
    )


def parse_difficulty_metadata(plan_text: str) -> str:
    return difficulty.plan_difficulty(plan_text)


def validate_difficulty_metadata(plan_text: str, *, require: bool) -> tuple[bool, str]:
    found = parse_difficulty_metadata(plan_text)
    if found:
        return True, found
    if require:
        return False, ""
    return True, ""


def validate_optional_trailer_keys_preserved(*, plan_file: str | Path, keys_file: str | Path) -> bool:
    expected = [
        line
        for line in Path(keys_file).read_text(encoding="utf-8", errors="replace").splitlines()
        if line
    ]
    meta = parse_optional_metadata(_read_plan(plan_file))
    return all(key in meta.keys for key in expected)


def validate_optional_trailers_preserved(*, plan_file: str | Path, values_file: str | Path) -> bool:
    values_path = Path(values_file)
    if values_path.name.endswith(".values"):
        keys_path = Path(str(values_path)[: -len(".values")])
    else:
        keys_path = values_path
        values_path = Path(str(values_path) + ".values")
    if not validate_optional_trailer_keys_preserved(plan_file=plan_file, keys_file=keys_path):
        return False
    if values_path.is_file():
        current = "\n".join(parse_optional_metadata(_read_plan(plan_file)).values)
        if current:
            current += "\n"
        return values_path.read_text(encoding="utf-8", errors="replace") == current
    return True
