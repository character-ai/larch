"""Render /design approval gate prompt copy as KEY=value rows."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from larch.review.plan_review_common import effective_authorized_cap


_TRUE_FALSE = frozenset({"true", "false"})
_GATE_C_OTHER_AFFORDANCE = (
    "Use Other to request debate <decision>: <option A> vs <option B> "
    "(or debate <candidate-id> when fingerprint-valid candidates exist)."
)
_GATE_C_APPROVE_LABEL = "Approve final design"
_GATE_C_PANEL_FAILED_APPROVE_LABEL = "Approve final design (acknowledge panel failure)"


@dataclass(frozen=True)
class GateOption:
    label: str
    description: str


@dataclass(frozen=True)
class GateRender:
    gate: str
    header: str = ""
    question: str = ""
    options: tuple[GateOption, ...] = ()
    extra: tuple[tuple[str, str], ...] = ()

    def rows(self) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = [("GATE_RENDER_STATUS", "ok"), ("GATE", self.gate)]
        if self.header:
            rows.append(("HEADER", self.header))
        if self.question:
            rows.append(("QUESTION", self.question))
        rows.append(("OPTION_COUNT", str(len(self.options))))
        for index, option in enumerate(self.options, start=1):
            rows.append((f"OPTION_{index}_LABEL", option.label))
            rows.append((f"OPTION_{index}_DESCRIPTION", option.description))
        rows.extend(self.extra)
        return tuple(rows)


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render /design Gate A/B/C prompt copy as KEY=value rows")
    _ = parser.add_argument("--gate", required=True, choices=("A", "B", "C"))
    _ = parser.add_argument("--without-see-full-plan", action="store_true")
    _ = parser.add_argument("--accepted-count", type=int, default=0)
    _ = parser.add_argument("--approve-requested", choices=tuple(sorted(_TRUE_FALSE)), default="false")
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--panel-failed", choices=tuple(sorted(_TRUE_FALSE)), default="false")
    _ = parser.add_argument("--accepted-audit-escalation", choices=tuple(sorted(_TRUE_FALSE)), default="false")
    return parser


def _nonnegative(value: int, flag: str) -> None:
    if value < 0:
        raise ValueError(f"{flag} must be non-negative")


def _gate_a_options(*, without_see_full_plan: bool) -> tuple[GateOption, ...]:
    options = [
        GateOption(
            "Ready for review",
            "Launch the design review against the current plan.",
        ),
        GateOption(
            "Discuss more",
            "Continue the post-plan discussion before review.",
        ),
    ]
    if without_see_full_plan:
        return tuple(options)
    return (
        GateOption(
            "See full plan",
            "Re-display the current plan, then return to this prompt without advancing.",
        ),
        *options,
    )


def _render_gate_a(*, without_see_full_plan: bool) -> GateRender:
    return GateRender(
        gate="A",
        header="Design discussion",
        question=(
            "All open design questions appear discussed. Ready to launch the design review, "
            "or would you like to discuss more first?"
        ),
        options=_gate_a_options(without_see_full_plan=without_see_full_plan),
    )


def _render_gate_b(*, accepted_count: int, approve_requested: bool) -> GateRender:
    _nonnegative(accepted_count, "--accepted-count")
    if approve_requested:
        return GateRender(
            gate="B",
            extra=(
                ("PROMPT_REQUIRED", "true"),
                ("EXPLICIT_COPY_OWNER", "skills/design/references/approval-gates-explicit.md"),
            ),
        )
    return GateRender(
        gate="B",
        extra=(
            ("PROMPT_REQUIRED", "false"),
            ("AUTO_APPLY_MESSAGE", f"\u2139 3.5: Gate B — auto-applying {accepted_count} accepted finding(s)"),
        ),
    )


def _review_count(design_tmpdir: str | None) -> tuple[int, str]:
    if not design_tmpdir:
        return 0, ""
    path = Path(design_tmpdir) / "review-round-count.txt"
    if not path.is_file() or path.is_symlink():
        return 0, ""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return 0, ""
    if not raw:
        return 0, ""
    if not re.fullmatch(r"[0-9]+", raw):
        return 0, "non-numeric"
    return int(raw, 10), ""


def _gate_c_approve_description(*, panel_failed: bool, accepted_audit_escalation: bool) -> str:
    if accepted_audit_escalation and panel_failed:
        return (
            "Approve despite the main-agent accepted-findings audit's strong dissent "
            "and acknowledge panel failure, then continue immediately to finalize."
        )
    if accepted_audit_escalation:
        return (
            "Approve despite the main-agent accepted-findings audit's strong dissent "
            "and continue immediately to finalize."
        )
    return "Approve the current plan and continue immediately to finalize."


def _gate_c_options(
    *,
    without_see_full_plan: bool,
    at_cap: bool,
    panel_failed: bool,
    accepted_audit_escalation: bool,
) -> tuple[GateOption, ...]:
    approve_label = _GATE_C_PANEL_FAILED_APPROVE_LABEL if panel_failed else _GATE_C_APPROVE_LABEL
    options = [
        GateOption(
            approve_label,
            _gate_c_approve_description(
                panel_failed=panel_failed,
                accepted_audit_escalation=accepted_audit_escalation,
            ),
        )
    ]
    if not without_see_full_plan:
        options.append(
            GateOption(
                "See full plan",
                "Show the full current plan, then return to this prompt without advancing.",
            )
        )
    options.append(
        GateOption(
            "Discuss further",
            "Return to Gate A discussion before another review pass.",
        )
    )
    if not at_cap:
        options.append(
            GateOption(
                "Re-run review panel",
                "Launch another review panel against the current plan.",
            )
        )
    return tuple(options)


def _gate_c_question(*, at_cap: bool) -> str:
    if at_cap:
        base = "Final design plan is ready. Approve, see the full plan, or discuss further?"
    else:
        base = (
            "Final design plan is ready. Approve, see the full plan, discuss further, "
            "or re-run the review panel against this plan?"
        )
    return f"{base} {_GATE_C_OTHER_AFFORDANCE}"


def _render_gate_c(
    *,
    design_tmpdir: str | None,
    without_see_full_plan: bool,
    panel_failed: bool,
    accepted_audit_escalation: bool,
) -> GateRender:
    count, warning = _review_count(design_tmpdir)
    cap = effective_authorized_cap(Path(design_tmpdir)) if design_tmpdir else 2
    at_cap = count >= cap
    extra: list[tuple[str, str]] = [("REVIEW_ROUND_CAP", str(cap))]
    if warning:
        extra.append(("REVIEW_ROUND_COUNT_WARN", warning))
    return GateRender(
        gate="C",
        header="Final design",
        question=_gate_c_question(at_cap=at_cap),
        options=_gate_c_options(
            without_see_full_plan=without_see_full_plan,
            at_cap=at_cap,
            panel_failed=panel_failed,
            accepted_audit_escalation=accepted_audit_escalation,
        ),
        extra=tuple(extra),
    )


def _bool_arg(value: str) -> bool:
    return value == "true"


def _die(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def _validate_rows(rows: tuple[tuple[str, str], ...]) -> None:
    for key, value in rows:
        if "\n" in value or "\r" in value:
            _die(f"rendered value for {key} contains CR/LF")


def _emit_rows(rows: tuple[tuple[str, str], ...]) -> None:
    _validate_rows(rows)
    for key, value in rows:
        print(f"{key}={value}")


def render_gate_main(argv: list[str] | None = None) -> int:
    parser = _arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.gate == "A":
            render = _render_gate_a(without_see_full_plan=args.without_see_full_plan)
        elif args.gate == "B":
            render = _render_gate_b(
                accepted_count=args.accepted_count,
                approve_requested=_bool_arg(args.approve_requested),
            )
        else:
            render = _render_gate_c(
                design_tmpdir=args.design_tmpdir,
                without_see_full_plan=args.without_see_full_plan,
                panel_failed=_bool_arg(args.panel_failed),
                accepted_audit_escalation=_bool_arg(args.accepted_audit_escalation),
            )
    except ValueError as exc:
        parser.error(str(exc))
    _emit_rows(render.rows())
    return 0
