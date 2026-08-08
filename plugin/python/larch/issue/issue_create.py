# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""The in-process `/issue` batch-input grammar.

Every command this module once served has moved to the Rust owner: the issue
query and input verbs in #8167 and #8168, `issue create-one`,
`issue write-sentinel`, and `issue cleanup-failed` in #8169, and the two
issue-graph writes — `issue add-blocked-by` and `issue add-sub-issue` — in
#8170. `parse_issue_input` stays because it is not a command: it is the
grammar ``larch.issue.file_oos``, ``larch.issue.umbrella``, and
``larch.issue.learn_from_bugs`` still call in process, and those modules
migrate with their own command leaves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from larch.design.plan_grammar import balanced_fence_line_indices

OOS_HEADING_RE = re.compile(r"^###[ \t]+OOS_[0-9]+:[ \t]+(.+)$")
PLAIN_HEADING_RE = re.compile(r"^###[ \t]+(.+)$")
DESC_RE = re.compile(r"^-[ \t]+\*\*Description\*\*:[ \t]*(.*)$")
# FINDING-block OOS (review pipeline) uses `**Concern**` for the body and
# `**Reviewer(s)**` for attribution; treat them as Description/Reviewer
# equivalents so review-surfaced accepted OOS file with a non-empty body (#5260).
CONCERN_RE = re.compile(r"^-[ \t]+\*\*Concern\*\*:[ \t]*(.*)$")
REVIEWER_RE = re.compile(r"^-[ \t]+\*\*Reviewer(?:\(s\))?\*\*:[ \t]+(.+)$")
VOTE_RE = re.compile(r"^-[ \t]+\*\*Vote tally\*\*:[ \t]+(.+)$")
PHASE_RE = re.compile(r"^-[ \t]+\*\*Phase\*\*:[ \t]+(.+)$")


@dataclass(frozen=True)
class ParsedItem:
    title: str
    body: str
    reviewer: str = ""
    vote: str = ""
    phase: str = ""
    malformed: bool = False


# Mutable parser state: methods update current_* / pending_* / items in place while scanning.
@dataclass
class ParseState:
    current_title: str = ""
    current_body: str = ""
    current_reviewer: str = ""
    current_vote: str = ""
    current_phase: str = ""
    in_body: bool = False
    current_mode: str = ""
    parse_mode: str = "generic"
    pending_heading: str = ""
    pending_body: str = ""
    items: list[ParsedItem] = field(default_factory=list)

    def fold_pending(self) -> None:
        if not self.pending_heading:
            return
        if self.current_body:
            self.current_body += "\n" + self.pending_heading
        else:
            self.current_body = self.pending_heading
        if self.pending_body:
            self.current_body += "\n" + self.pending_body
        self.pending_heading = ""
        self.pending_body = ""

    def emit_current(self, *, force_malformed: bool = False) -> None:
        if not self.current_title:
            self.reset()
            return
        malformed = force_malformed or not self.current_body
        self.items.append(
            ParsedItem(
                self.current_title,
                self.current_body,
                self.current_reviewer,
                self.current_vote,
                self.current_phase,
                malformed,
            ),
        )
        self.reset()

    def split_pending(self) -> None:
        if not self.pending_heading:
            return
        pending_heading = self.pending_heading
        pending_body = self.pending_body
        self.pending_heading = ""
        self.pending_body = ""
        if self.current_title:
            self.items.append(
                ParsedItem(
                    self.current_title,
                    self.current_body,
                    self.current_reviewer,
                    self.current_vote,
                    self.current_phase,
                    malformed=True,
                ),
            )
        self.current_title = ""
        self.current_body = ""
        self.current_reviewer = ""
        self.current_vote = ""
        self.current_phase = ""
        self.in_body = False
        self.current_mode = ""
        match = PLAIN_HEADING_RE.match(pending_heading)
        if match:
            self.items.append(ParsedItem(match.group(1), pending_body, malformed=not bool(pending_body)))

    def reset(self) -> None:
        self.current_title = ""
        self.current_body = ""
        self.current_reviewer = ""
        self.current_vote = ""
        self.current_phase = ""
        self.in_body = False
        self.current_mode = ""
        self.pending_heading = ""
        self.pending_body = ""

    def consume_oos_field(self, line: str) -> bool:
        """Consume an OOS metadata/body field line, returning True on a match.

        `**Concern**` is treated as a Description-equivalent and `**Reviewer(s)**`
        as a Reviewer-equivalent so FINDING-block accepted OOS still capture a
        body instead of dropping it (#5260).
        """
        if match := DESC_RE.match(line):
            self.fold_pending()
            self.current_body = match.group(1)
            self.in_body = True
            return True
        if match := CONCERN_RE.match(line):
            self.fold_pending()
            inline = match.group(1)
            if not self.current_body:
                self.current_body = inline
            elif inline:
                self.current_body += "\n" + inline
            self.in_body = True
            return True
        if match := REVIEWER_RE.match(line):
            self.fold_pending()
            self.current_reviewer = match.group(1)
            self.in_body = False
            return True
        if match := VOTE_RE.match(line):
            self.fold_pending()
            self.current_vote = match.group(1)
            self.in_body = False
            return True
        if match := PHASE_RE.match(line):
            self.fold_pending()
            self.current_phase = match.group(1)
            self.in_body = False
            return True
        return False


def parse_issue_input(text: str) -> tuple[list[ParsedItem], str]:
    state = ParseState()
    lines = text.splitlines()
    fenced_lines = balanced_fence_line_indices(lines)
    for index, line in enumerate(lines):
        in_fence = index in fenced_lines
        if not in_fence and (match := OOS_HEADING_RE.match(line)):
            if state.current_mode == "generic" and state.in_body and state.current_body.strip():
                state.current_body += "\n" + line
            else:
                new_title = match.group(1)
                state.split_pending()
                state.emit_current()
                state.current_title = new_title
                # Default to body capture so an OOS block with no `- **Description**:`
                # line still accumulates its content instead of dropping it (#5260).
                # A following `- **Reviewer(s)**:`/`- **Vote tally**:`/`- **Phase**:`
                # line still flips this back off as metadata.
                state.in_body = True
                state.current_mode = "oos"
                state.parse_mode = "oos"
        elif not in_fence and (match := PLAIN_HEADING_RE.match(line)):
            if state.current_mode == "oos" and state.in_body:
                if not state.pending_heading:
                    state.pending_heading = line
                elif state.pending_body:
                    state.pending_body += "\n" + line
                else:
                    state.pending_body = line
            else:
                state.emit_current()
                state.current_title = match.group(1)
                state.in_body = True
                state.current_mode = "generic"
        elif not in_fence and state.current_mode == "oos" and state.consume_oos_field(line):
            pass
        elif state.in_body:
            if state.pending_heading:
                if state.pending_body:
                    state.pending_body += "\n" + line
                else:
                    state.pending_body = line
            elif state.current_body:
                state.current_body += "\n" + line
            else:
                state.current_body = line
    state.split_pending()
    state.emit_current()
    return state.items, state.parse_mode
