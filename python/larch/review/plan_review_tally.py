"""In-process plan-review vote tally (ports the retired tally-plan-review.sh).

Replaces the gzip-embedded bash body previously executed via
``plan_review._run_legacy()``. Calls ``voting.py`` primitives directly instead
of spawning one ``cli.py`` subprocess per vote, eliminating the ~``F*(3V+5)``
process spawns per tally (F findings, V voters) that dominated
``test-findings-classification`` and every production design plan-review round.

Output is byte-compatible with the retired script: the 22-column
``findings-classification.tsv``, ``voting-tally.md`` (findings table plus
reviewer scoreboard), the ``accepted-plan-findings.md`` /
``rejected-findings.md`` / ``oos.md`` / ``oos-accepted-design.md`` artifacts,
the ``KEY=value`` contract grammar (``TALLY_PLAN_REVIEW_STATUS``,
``VOTING_TALLY_FILE``), stderr diagnostics, and exit codes.

See docs/python-migration.md (C3a1 façade) and
skills/design/scripts/test-findings-classification.sh for the contract.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import NoReturn

from larch.review import findings_ledger
from larch.core import logging_util
from larch.review import plan_review_round
from larch.review import voting
from larch.state.session_env import validate_design_tmpdir

_VALID_SLOTS = {"1", "2", "3", "Claude", "Codex", "Cursor", "MainAgent"}
_LATENT_BODY_SEVERITY = re.compile(
    r"(?im)^-[ \t]*\*\*Severity\*\*:[ \t]*latent[ \t]*$"
)
_BODY_SEVERITY_PREFIX = re.compile(r"^[\s-]*\*\*Severity\*\*:[ \t]*")
_FULL_PANEL = 3
LABEL_MAP_MIN_COLS = 2


def _finding_oos_reroute_marker(*, block_text: str, neutral_rescued: bool) -> str:
    if _LATENT_BODY_SEVERITY.search(block_text):
        return "latent-rerouted"
    if neutral_rescued:
        return "neutral-rescued"
    return ""


def _record_plan_review_score_rows(
    *,
    score_state: tuple[list[tuple[str, str, str, int, float]], list[str], float],
    reviewer: str,
    kind: str,
    result: str,
    vote_inputs: tuple[list[str], list[str]],
) -> int:
    score_rows, attribution_labels, active_bonus = score_state
    votes, severities = vote_inputs
    neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
        result,
        yes_votes=votes,
        severities=severities,
    )
    score_kind = "oos" if kind == "oos" or neutral_rescued else "finding"
    accepted_weight = (
        voting.accepted_finding_points_from_severities(severities, votes=votes)
        if score_kind == "finding" and result == "accepted"
        else 0
    )
    split_reviewers = voting.split_classification_attribution(
        reviewer,
        column="finding_reviewers",
        labels=attribution_labels,
    )
    if not split_reviewers:
        split_reviewers = [part.strip() for part in reviewer.split(",") if part.strip()]
    bonus_float = (
        active_bonus
        if score_kind == "finding" and result == "accepted" and len(split_reviewers) == 1 and active_bonus > 0
        else 0.0
    )
    score_rows.extend((reviewer_slot, score_kind, result, accepted_weight, bonus_float) for reviewer_slot in split_reviewers)
    return 1 if bonus_float > 0 else 0


class _AbortTally(Exception):
    """Unwind to the CLI boundary with a specific exit code (bash ``exit N``)."""

    def __init__(self, code: int = 2) -> None:
        super().__init__(code)
        self.code = code


def _sanitize_tsv_cell(value: str) -> str:
    """Port of the bash ``sanitize_tsv_cell``: strip tab/newline, escape formulae.

    The bash glob ``[=+-@]*`` is a character class where ``+-@`` is the range
    ``+`` (0x2B) through ``@`` (0x40); ``=`` (0x3D) falls inside it. A leading
    char in that range is prefixed with ``'`` (spreadsheet formula guard).
    Preserved exactly for byte parity with the retired script.
    """
    cell = (value or "").replace("\t", " ").replace("\n", " ")
    if cell and "+" <= cell[0] <= "@":
        return "'" + cell
    return cell


def _body_severity_for_block(block_path: str | Path) -> str:
    """First ``**Severity**:`` value in a block (port of the awk extractor)."""
    try:
        lines = Path(block_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        if _BODY_SEVERITY_PREFIX.match(line):
            value = _BODY_SEVERITY_PREFIX.sub("", line, count=1)
            return re.sub(r"[ \t]+$", "", value)
    return ""


class _Tally:
    """Mutable tally state mirroring the retired script's shell globals."""

    def __init__(self) -> None:
        self.design_tmpdir = ""
        self.ballot_file = ""
        self.findings_out = ""
        self.voter_specs: list[str] = []
        self.voter_files: list[str] = []
        self.seen_voter = False
        self.seen_voter_files = False
        self.slot_file: dict[int, str] = {1: "", 2: "", 3: ""}
        self.slot_tool: dict[int, str] = {1: "", 2: "", 3: ""}
        self.main_agent_voter = ""
        self.tally_voter_file = ""
        self.eligible = 0
        self.tally_file = ""
        self.status_emitted = False
        self.block_dir = ""
        self.workdir = ""
        self.proposer_map_file = ""
        self.proposer_sidecar_required = False

    # -- usage / diagnostics -------------------------------------------------
    @staticmethod
    def _usage() -> None:
        logging_util.diagnostic(
            "usage: tally-plan-review.sh --ballot-file FILE "
            "[--voter SLOT:FILE...|POS:TOOL:FILE...] [--voter-files FILE...] "
            "--design-tmpdir DIR [--findings-classification-out FILE]"
        )

    # -- stub writers --------------------------------------------------------
    def _write_tally_stub(self, message: str) -> None:
        _ = Path(self.tally_file).write_text(
            f"# Plan Review Voting Tally\n\n{message}\n", encoding="utf-8"
        )

    def _write_findings_classification_stub(self) -> None:
        out = Path(self.findings_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        _ = out.write_text(voting.findings_classification_header() + "\n", encoding="utf-8")

    def _error_exit(
        self,
        stderr_message: str,
        stub_message: str = "",
        *,
        write_classification_stub: bool = True,
    ) -> NoReturn:
        """Port of bash ``tally_error_exit``: diagnose, stub, emit, exit 2."""
        logging_util.diagnostic(stderr_message)
        if stub_message:
            self._write_tally_stub(stub_message)
        if write_classification_stub:
            self._write_findings_classification_stub()
        self.status_emitted = True
        if self.tally_file and Path(self.tally_file).exists() and Path(self.tally_file).stat().st_size > 0:
            logging_util.emit_kv(key="VOTING_TALLY_FILE", value=self.tally_file)
        logging_util.emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="tally-error")
        raise _AbortTally(2)

    # -- voter-slot resolution (ports of the like-named bash helpers) --------
    @staticmethod
    def _infer_voter_slot(*, path: str, index: int) -> str:
        base = Path(path).name.lower()
        if "claude" in base:
            return "Claude"
        if "codex" in base:
            return "Codex"
        if "cursor" in base:
            return "Cursor"
        return {1: "Claude", 2: "Codex"}.get(index, "Cursor")

    @staticmethod
    def _canonical_position_for_slot(slot: str) -> str:
        return {"1": "1", "Claude": "1", "2": "2", "Codex": "2", "3": "3", "Cursor": "3"}.get(slot, "0")

    @staticmethod
    def _canonical_tool_for_slot(slot: str) -> str:
        return {
            "Claude": "Claude", "Codex": "Codex", "Cursor": "Cursor",
            "1": "Claude", "2": "Codex", "3": "Cursor",
        }.get(slot, slot)

    def _position_for_voter(self, *, tool: str, path: str) -> str:
        base = Path(path).name.lower()
        groups = (
            (1, ("voter-1", "voter1", "slot1", "slot-1", "claude-vote-output")),
            (2, ("voter-2", "voter2", "slot2", "slot-2", "codex-vote-output")),
            (3, ("voter-3", "voter3", "slot3", "slot-3", "cursor-vote-output")),
        )
        for pos, needles in groups:
            if any(n in base for n in needles):
                return str(pos)
        if tool == "Claude" and not self.slot_file[1]:
            return "1"
        if tool == "Codex" and not self.slot_file[2]:
            return "2"
        if tool == "Cursor" and not self.slot_file[3]:
            return "3"
        for pos in (1, 2, 3):
            if not self.slot_file[pos]:
                return str(pos)
        return "0"

    def _assign_voter(self, *, tool: str, path: str, pos: str = "") -> None:
        if tool == "MainAgent":
            self.main_agent_voter = path
            return
        if not pos:
            pos = self._position_for_voter(tool=tool, path=path)
        if pos == "0":
            self._error_exit(
                stderr_message="tally-plan-review.sh: too many voters; expected at most three non-MainAgent voters",
                stub_message="**⚠ Tally aborted: too many voters; at most three non-MainAgent voters allowed.**",
            )
        slot = int(pos)
        if self.slot_file[slot]:
            self._error_exit(
                stderr_message=f"error: duplicate voter position {pos}",
                stub_message=f"**⚠ Tally aborted: duplicate voter position {pos}.**",
            )
        self.slot_file[slot] = path
        self.slot_tool[slot] = tool

    # -- vote tallying -------------------------------------------------------
    def _tally_votes_for_id(self, item_id: str) -> tuple[int, int, int, str]:
        yes = no = judge_error = 0
        if self.tally_voter_file:
            vote = voting.vote_for_id(ballot_id=item_id, voter_file=self.tally_voter_file)
            if vote == "YES":
                yes = 1
            elif vote == "NO":
                no = 1
            else:
                judge_error = 1
        elif self.eligible > 0:
            for pos in (1, 2, 3):
                voter_file = self.slot_file[pos]
                if not voter_file:
                    continue
                vote = voting.vote_for_id(ballot_id=item_id, voter_file=voter_file)
                if vote == "YES":
                    yes += 1
                elif vote == "NO":
                    no += 1
                else:
                    judge_error += 1
        result = voting.classify_result(yes=yes, no=no, exonerate=0, eligible=self.eligible)
        return yes, no, judge_error, result

    def _attribution_labels(self) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()

        def add(label: str) -> None:
            clean = label.strip()
            if clean and clean not in seen:
                labels.append(clean)
                seen.add(clean)

        label_map = Path(self.design_tmpdir) / "plan-review-prune-label-map.tsv"
        if label_map.is_file():
            for line in label_map.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split("\t")
                if len(parts) >= LABEL_MAP_MIN_COLS:
                    add(parts[1])
        for value in self.slot_tool.values():
            add(value)
        manifest = Path(self.design_tmpdir) / "panel-manifest.ndjson"
        if manifest.is_file():
            for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                slot = row.get("slot")
                if isinstance(slot, str):
                    add(plan_review_round._slot_human_label(slot))  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        if self.proposer_map_file:
            try:
                for reviewer, _line in voting.read_proposer_map(self.proposer_map_file).values():
                    voting.grow_attribution_labels(labels, seen, reviewer)
            except voting.TallyError:
                pass
        block_root = Path(self.block_dir) if self.block_dir else None
        if block_root and block_root.is_dir():
            for block in block_root.glob("*.md"):
                reviewer = voting.reviewer_for_block(block)
                voting.grow_attribution_labels(labels, seen, reviewer)
        return labels

    def _votes_and_severities_for_item(self, item_id: str) -> tuple[list[str], list[str]]:
        votes: list[str] = []
        severities: list[str] = []
        if self.tally_voter_file:
            try:
                _vote, _correctness, severity, _quality, _uncertain = voting.parse_judge_vote(
                    voter_file=self.tally_voter_file, ballot_id=item_id
                )
            except (OSError, FileNotFoundError):
                severity = ""
            votes.append(voting.vote_for_id(ballot_id=item_id, voter_file=self.tally_voter_file))
            severities.append(severity)
            return votes, severities
        for pos in (1, 2, 3):
            voter_file = self.slot_file[pos]
            if not voter_file or self.eligible <= 0:
                continue
            try:
                _vote, _correctness, severity, _quality, _uncertain = voting.parse_judge_vote(voter_file=voter_file, ballot_id=item_id)
            except (OSError, FileNotFoundError):
                severity = ""
            votes.append(voting.vote_for_id(ballot_id=item_id, voter_file=voter_file))
            severities.append(severity)
        return votes, severities

    def _vote_and_severity_for_slot(self, item_id: str, *, pos: int) -> tuple[str, str]:
        voter_file = self.slot_file[pos]
        if not voter_file:
            return "", ""
        try:
            _vote, _correctness, severity, _quality, _uncertain = voting.parse_judge_vote(voter_file=voter_file, ballot_id=item_id)
        except (OSError, FileNotFoundError):
            return "", ""
        vote = voting.vote_for_id(ballot_id=item_id, voter_file=voter_file)
        if vote == "JUDGE_ERROR":
            vote = ""
        return vote, severity

    def _voter_agreement_row_for_item(self, item_id: str, *, result: str) -> dict[str, object] | None:
        voter_votes: list[tuple[str, str]] = []
        voter_severities: list[str] | None = None
        if self.eligible > 0 and not self.tally_voter_file:
            voter_severities = []
            fallback = {1: "Claude", 2: "Codex", 3: "Cursor"}
            for pos in (1, 2, 3):
                vote, severity = self._vote_and_severity_for_slot(item_id=item_id, pos=pos)
                voter_votes.append((self.slot_tool[pos] or fallback[pos], vote))
                voter_severities.append(severity)
        return voting.voter_agreement_row_from_panel(
            voting_result=result,
            voter_votes=voter_votes,
            panel="design",
            voter_severities=voter_severities,
        )

    # -- findings-classification TSV ----------------------------------------
    def _write_findings_classification(self, sorted_ids: list[str]) -> None:
        out = Path(self.findings_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        buf = voting.findings_classification_header() + "\n"
        for item_id in sorted_ids:
            block = Path(self.block_dir) / f"{item_id}.md"
            reviewer = _sanitize_tsv_cell(self._proposer_for_item(item_id=item_id, block=block))
            body_severity = _sanitize_tsv_cell(_body_severity_for_block(block))
            _, _, _, result = self._tally_votes_for_id(item_id)
            tsv_result = "rejected" if self.main_agent_voter else result
            votes, severities = self._votes_and_severities_for_item(item_id)
            neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
                result,
                yes_votes=votes,
                severities=severities,
            )
            row = [item_id, reviewer, tsv_result]
            for pos in (1, 2, 3):
                voter_file = self.slot_file[pos]
                tool = self.slot_tool[pos]
                if voter_file and self.tally_voter_file != voter_file and self.eligible > 0:
                    try:
                        _, correctness, severity, quality, uncertain = voting.parse_judge_vote(voter_file=voter_file, ballot_id=item_id)
                    except (OSError, FileNotFoundError):
                        correctness = severity = quality = uncertain = ""
                    vote = voting.vote_for_id(ballot_id=item_id, voter_file=voter_file)
                    if vote == "JUDGE_ERROR":
                        vote = ""
                    row += [
                        _sanitize_tsv_cell(vote),
                        _sanitize_tsv_cell(correctness),
                        _sanitize_tsv_cell(severity),
                        _sanitize_tsv_cell(quality),
                        _sanitize_tsv_cell(uncertain),
                        _sanitize_tsv_cell(tool),
                    ]
                else:
                    row += ["", "", "", "", "", ""]
            row.append(body_severity)
            row.append("oos" if item_id.startswith("OOS_") or neutral_rescued else "in_scope")
            buf += "\t".join(row) + "\n"
        tmp = out.with_name(f"{out.name}.{os.getpid()}.tmp")
        _ = tmp.write_text(buf, encoding="utf-8")
        _ = tmp.replace(out)

    def _round_num_for_ledger(self) -> int:
        out = Path(self.findings_out)
        parts = out.parts
        for idx, part in enumerate(parts):
            if part == "plan-review" and idx + 1 < len(parts):
                match = re.fullmatch(r"round-([0-9]+)", parts[idx + 1])
                if match:
                    return int(match.group(1))
        return 1

    @staticmethod
    def _ledger_title(*, block_text: str, item_id: str) -> str:
        first = block_text.splitlines()[0] if block_text.splitlines() else ""
        title = re.sub(rf"^###\s+{re.escape(item_id)}:\s*", "", first).strip()
        return title or item_id

    @staticmethod
    def _ledger_file_line(block_text: str) -> str:
        for regex in voting.FILE_LINE_REGEXES.values():
            match = re.search(regex, block_text)
            if match:
                return match.group(0).strip(" \t\n\r`*()[],:;")
        return ""

    @staticmethod
    def _ledger_reason(block_text: str) -> str:
        for line in block_text.splitlines()[1:]:
            normalized = line.replace("*", "").strip()
            if re.match(r"^[- ]*(Concern|Scenario|Reason|Suggested (revision|fix)):", normalized, re.IGNORECASE):
                return re.sub(r"^[- ]*[^:]+:\s*", "", normalized).strip()
        return ""

    def _write_findings_ledger(self, sorted_ids: list[str]) -> None:
        entries: list[dict[str, object]] = []
        for item_id in sorted_ids:
            block = Path(self.block_dir) / f"{item_id}.md"
            block_text = block.read_text(encoding="utf-8", errors="replace")
            yes, _no, _judge_error, result = self._tally_votes_for_id(item_id)
            votes, severities = self._votes_and_severities_for_item(item_id)
            neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
                result,
                yes_votes=votes,
                severities=severities,
            )
            outcome = "oos" if item_id.startswith("OOS_") else result
            if neutral_rescued:
                outcome = "oos"
            if _LATENT_BODY_SEVERITY.search(block_text) and outcome != "accepted":
                outcome = "oos"
            entries.append(
                {
                    "finding_id": item_id,
                    "title": self._ledger_title(block_text=block_text, item_id=item_id),
                    "file_line": self._ledger_file_line(block_text),
                    "outcome": outcome,
                    "vote_tally": f"YES={yes}/{self.eligible}",
                    "reason": self._ledger_reason(block_text),
                }
            )
        findings_ledger.write_round(
            findings_ledger.ledger_root(Path(self.design_tmpdir), design_tmpdir=self.design_tmpdir),
            self._round_num_for_ledger(),
            entries,
        )

    def _write_findings_outputs(self, sorted_ids: list[str]) -> None:
        self._write_findings_classification(sorted_ids)
        self._write_findings_ledger(sorted_ids)

    # -- argument parsing ----------------------------------------------------
    def _parse_args(self, argv: list[str]) -> int | None:
        i = 0
        n = len(argv)
        while i < n:
            arg = argv[i]
            if arg == "--design-tmpdir":
                self.design_tmpdir = self._value(argv=argv, i=i, message="--design-tmpdir requires a value")
                i += 2
            elif arg == "--ballot-file":
                self.ballot_file = self._value(argv=argv, i=i, message="--ballot-file requires a value")
                i += 2
            elif arg == "--findings-classification-out":
                self.findings_out = self._value(argv=argv, i=i, message="--findings-classification-out requires a value")
                i += 2
            elif arg == "--proposer-map-file":
                self.proposer_map_file = self._value(argv=argv, i=i, message="--proposer-map-file requires a value")
                self.proposer_sidecar_required = True
                i += 2
            elif arg == "--voter":
                self.seen_voter = True
                self.voter_specs.append(self._value(argv=argv, i=i, message="--voter requires SLOT:PATH"))
                i += 2
            elif arg == "--voter-files":
                self.seen_voter_files = True
                i += 1
                while i < n and not argv[i].startswith("--"):
                    self.voter_files.append(argv[i])
                    i += 1
            elif arg in ("-h", "--help"):
                self._usage()
                return 0
            else:
                logging_util.diagnostic(f"tally-plan-review.sh: unknown argument: {arg}")
                self._usage()
                raise _AbortTally(2)
        return None

    def _value(self, *, argv: list[str], i: int, message: str) -> str:
        if i + 1 >= len(argv):
            logging_util.diagnostic(message)
            raise _AbortTally(2)
        return argv[i + 1]

    # -- voter spec resolution ----------------------------------------------
    def _resolve_voters(self) -> None:
        if self.seen_voter:
            for spec in self.voter_specs:
                if ":" not in spec:
                    self._error_exit(
                        stderr_message=f"error: invalid voter slot: {spec} (must be 1|2|3|Claude|Codex|Cursor|MainAgent)",
                        stub_message=f"**⚠ Tally aborted: invalid voter slot: {spec}; no votes tallied.**",

                        write_classification_stub=False,
                    )
                match = re.match(r"^([123]):([^:]+):(.*)$", spec)
                if match:
                    slot, tool, path = match.group(1), match.group(2), match.group(3)
                else:
                    slot, _, path = spec.partition(":")
                    tool = self._canonical_tool_for_slot(slot)
                if slot not in _VALID_SLOTS:
                    self._error_exit(
                        stderr_message=f"error: invalid voter slot: {slot} (must be 1|2|3|Claude|Codex|Cursor|MainAgent)",
                        stub_message=f"**⚠ Tally aborted: invalid voter slot: {slot}; no votes tallied.**",

                        write_classification_stub=False,
                    )
                self.voter_files.append(path)
                if slot == "MainAgent":
                    self._assign_voter(tool=slot, path=path)
                    continue
                self._assign_voter(tool=tool, path=path, pos=self._canonical_position_for_slot(slot))
        else:
            if self.seen_voter_files:
                logging_util.diagnostic("deprecated: --voter-files; use --voter <SLOT>:<PATH>")
            for idx, path in enumerate(self.voter_files, start=1):
                self._assign_voter(tool=self._infer_voter_slot(path=path, index=idx), path=path)

        if self.main_agent_voter:
            non_main = sum(1 for pos in (1, 2, 3) if self.slot_file[pos])
            if non_main > 0 or len(self.voter_specs) > 1:
                self._error_exit(
                    stderr_message="error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)",
                    stub_message="**⚠ Tally aborted: --voter MainAgent is only valid as the sole voter; no votes tallied.**",
                )

        if self.main_agent_voter:
            self.tally_voter_file = self.main_agent_voter
            self.eligible = 1
        else:
            self.eligible = sum(1 for pos in (1, 2, 3) if self.slot_file[pos])

    # -- main driver ---------------------------------------------------------
    def run(self, argv: list[str]) -> int:
        early = self._parse_args(argv=argv)
        if early is not None:
            return early

        if not self.design_tmpdir or not self.ballot_file:
            logging_util.diagnostic(
                "tally-plan-review.sh: --design-tmpdir and --ballot-file are required"
            )
            self._usage()
            raise _AbortTally(2)

        if not self.findings_out:
            self.findings_out = str(
                Path(self.design_tmpdir, "plan-review", "round-1", "findings-classification.tsv")
            )
        ballot_path = Path(self.ballot_file)
        if not self.proposer_map_file:
            default_map = Path(self.design_tmpdir) / "proposer-map.tsv"
            if default_map.is_file() and voting.ballot_is_neutralized(ballot_path):
                self.proposer_map_file = str(default_map)
                self.proposer_sidecar_required = True
        if not self.proposer_sidecar_required and voting.ballot_is_neutralized(ballot_path):
            self.proposer_sidecar_required = True
        if self.proposer_map_file and voting.ballot_is_neutralized(ballot_path):
            try:
                voting.validate_proposer_map_for_neutralized_ballot(ballot_file=ballot_path, map_file=self.proposer_map_file)
            except voting.TallyError as exc:
                self._error_exit(
                    stderr_message=f"tally-plan-review.sh: {exc}",
                    stub_message="**⚠ Tally aborted: proposer map validation failed; no votes tallied.**",
                )

        ok, message = validate_design_tmpdir(self.design_tmpdir)
        if not ok:
            logging_util.diagnostic(message)
            raise _AbortTally(2)
        Path(self.design_tmpdir).mkdir(parents=True, exist_ok=True)
        self.tally_file = str(Path(self.design_tmpdir, "voting-tally.md"))

        if self.seen_voter and self.seen_voter_files:
            self._error_exit(
                stderr_message="error: --voter and --voter-files are mutually exclusive",
                stub_message="**⚠ Tally aborted: --voter and --voter-files are mutually exclusive; no votes tallied.**",

                write_classification_stub=False,
            )

        if not os.access(self.ballot_file, os.R_OK):
            self._error_exit(
                stderr_message=f"tally-plan-review.sh: ballot file is missing or unreadable: {self.ballot_file}",
                stub_message=f"**⚠ Tally aborted: ballot file unreadable: {self.ballot_file}; no votes tallied.**",
            )

        self._resolve_voters()

        for voter_file in self.voter_files:
            if not os.access(voter_file, os.R_OK):
                self._error_exit(
                    stderr_message=f"tally-plan-review.sh: voter file is missing or unreadable: {voter_file}",
                    stub_message=f"**⚠ Tally aborted: voter file unreadable: {voter_file}; no votes tallied.**",
                )

        self.workdir = tempfile.mkdtemp(prefix="larch-tally-plan-review.")
        self.block_dir = str(Path(self.workdir, "blocks"))
        try:
            voting.split_ballot(ballot_file=self.ballot_file, out_dir=self.block_dir)
        except SystemExit:
            self._error_exit(
                stderr_message="tally-plan-review.sh: duplicate or malformed FINDING/OOS headings in ballot",
                stub_message="**⚠ Tally aborted: duplicate or malformed FINDING/OOS headings in ballot; no votes tallied.**",
            )

        sorted_ids = self._sorted_ids()

        accepted_plan = Path(self.design_tmpdir) / "accepted-plan-findings.md"
        accepted_plan_all = Path(self.design_tmpdir) / "accepted-plan-findings-all.md"
        rejected_plan = Path(self.design_tmpdir) / "rejected-findings.md"
        oos_file = Path(self.design_tmpdir) / "oos.md"
        oos_accepted_local = Path(self.design_tmpdir) / "oos-accepted-design.md"
        for artifact in (accepted_plan, rejected_plan, oos_file):
            _ = artifact.write_text("", encoding="utf-8")

        active_bonus = voting.unique_finder_bonus_from_env()
        if self.eligible == 0:
            _ = Path(self.tally_file).write_text(
                "# Plan Review Voting Tally\n\n"
                "**⚠ Degraded plan-review panel: 0 judges available. "
                "Panel tier: main-agent-required.**\n\n"
                + voting.render_voter_agreement_and_severity_scoreboards([]),
                encoding="utf-8",
            )
            self._write_findings_classification(sorted_ids)
            self.status_emitted = True
            logging_util.emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="main-agent-vote-required")
            logging_util.emit_kv(key="VOTING_TALLY_FILE", value=self.tally_file)
            return 0

        self._render(
            sorted_ids=sorted_ids,
            accepted_plan=accepted_plan,
            accepted_plan_all=accepted_plan_all,
            rejected_plan=rejected_plan,
            oos_file=oos_file,
            oos_accepted_local=oos_accepted_local,
            active_bonus=active_bonus,
        )
        self._write_findings_outputs(sorted_ids)
        self.status_emitted = True
        logging_util.emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="ok")
        logging_util.emit_kv(key="VOTING_TALLY_FILE", value=self.tally_file)
        return 0

    def _sorted_ids(self) -> list[str]:
        ids = [path.stem for path in Path(self.block_dir).glob("*.md")]

        def key(item_id: str) -> tuple[int, int]:
            finding = re.match(r"^FINDING_([0-9]+)$", item_id)
            if finding:
                return (1, int(finding.group(1)))
            oos = re.match(r"^OOS_([0-9]+)$", item_id)
            if oos:
                return (2, int(oos.group(1)))
            return (3, 0)

        eligible = [i for i in ids if re.match(r"^(FINDING|OOS)_[0-9]+$", i)]
        return sorted(eligible, key=key)

    def _proposer_for_item(self, *, item_id: str, block: Path) -> str:
        try:
            return voting.proposer_for_item(
                item_id=item_id,
                block_file=block,
                map_file=self.proposer_map_file,
                sidecar_required=self.proposer_sidecar_required,
            )
        except voting.TallyError as exc:
            self._error_exit(
                stderr_message=f"tally-plan-review.sh: {exc}",
                stub_message=f"**⚠ Tally aborted: missing proposer attribution for {item_id}; no votes tallied.**",
            )

    def _artifact_text_for_item(self, *, item_id: str, block: Path) -> str:
        block_text = block.read_text(encoding="utf-8")
        reviewer_line = voting.reviewer_line_for_item(item_id=item_id, map_file=self.proposer_map_file)
        return voting.restore_reviewer_attribution(block_text=block_text, reviewer_line=reviewer_line)

    def _render(
        self,
        *,
        sorted_ids: list[str],
        accepted_plan: Path,
        accepted_plan_all: Path,
        rejected_plan: Path,
        oos_file: Path,
        oos_accepted_local: Path,
        active_bonus: float,
    ) -> None:
        buf = "# Plan Review Voting Tally\n\n"
        if self.main_agent_voter:
            buf += "**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-adjudicated.**\n\n"
        elif self.eligible < _FULL_PANEL:
            tier = voting.panel_tier(self.eligible)
            buf += f"**⚠ Degraded plan-review panel: {self.eligible} judge(s) available. Panel tier: {tier}.**\n\n"
        buf += "## Findings\n\n"
        buf += "| Item | YES | NO | JERR | Result |\n"
        buf += "|---|---:|---:|---:|---|\n"

        accepted_chunks: list[str] = []
        rejected_chunks: list[str] = []
        oos_chunks: list[str] = []
        oos_accepted_chunks: list[str] = []
        oos_pool_chunks: list[str] = []
        score_rows: list[tuple[str, str, str, int, float]] = []
        sole_finder_reward_count = 0
        attribution_labels = self._attribution_labels()
        agreement_rows: list[dict[str, object]] = []

        for item_id in sorted_ids:
            block = Path(self.block_dir) / f"{item_id}.md"
            yes, no, judge_error, result = self._tally_votes_for_id(item_id)
            buf += f"| {item_id} | {yes} | {no} | {judge_error} | {result} |\n"
            agreement_row = self._voter_agreement_row_for_item(item_id=item_id, result=result)
            if agreement_row is not None:
                agreement_rows.append(agreement_row)

            reviewer = self._proposer_for_item(item_id=item_id, block=block)
            votes, severities = self._votes_and_severities_for_item(item_id)
            neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
                result,
                yes_votes=votes,
                severities=severities,
            )
            kind = "oos" if item_id.startswith("OOS_") else "finding"
            sole_finder_reward_count += _record_plan_review_score_rows(
                score_state=(score_rows, attribution_labels, active_bonus),
                reviewer=reviewer,
                kind=kind,
                result=result,
                vote_inputs=(votes, severities),
            )
            artifact_text = self._artifact_text_for_item(item_id=item_id, block=block)
            security = voting.is_security_block_text(artifact_text)
            reroute_marker = _finding_oos_reroute_marker(block_text=artifact_text, neutral_rescued=neutral_rescued)

            _record_plan_review_artifact_chunks(
                item=(kind, result, reroute_marker, item_id, artifact_text, security),
                vote_counts=(yes, no, judge_error),
                chunks=(accepted_chunks, rejected_chunks, oos_chunks, oos_accepted_chunks, oos_pool_chunks),
            )

        buf += "\n## Reviewer Competition Scoreboard\n\n"
        buf += (
            "| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | "
            "OOS-Accepted | OOS-Neutral | OOS-Rejected | Score |\n"
        )
        buf += "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        buf += self._scoreboard(score_rows)
        if active_bonus > 0 and sole_finder_reward_count:
            buf += "\n" + voting.unique_finder_bonus_note(bonus=active_bonus, rewarded_count=sole_finder_reward_count) + "\n"
        buf += "\n" + voting.render_voter_agreement_and_severity_scoreboards(agreement_rows)

        _ = Path(self.tally_file).write_text(buf, encoding="utf-8")
        _append(path=accepted_plan, chunks=accepted_chunks)
        _accumulate_round_accepted_all(path=accepted_plan_all, chunks=accepted_chunks)
        _append(path=rejected_plan, chunks=rejected_chunks)
        _append(path=oos_file, chunks=oos_chunks)
        _accumulate_round_oos(path=oos_accepted_local, chunks=oos_accepted_chunks)
        _accumulate_round_oos(path=Path(self.design_tmpdir) / "oos-aggregate-pool.md", chunks=oos_pool_chunks)

    @staticmethod
    def _scoreboard(score_rows: list[tuple[str, str, str, int, float]]) -> str:
        agg: dict[str, dict[str, float]] = {}
        for reviewer, kind, result, accepted_weight, bonus_float in score_rows:
            row = agg.setdefault(
                reviewer,
                {"proposed": 0.0, "accepted": 0.0, "neutral": 0.0, "rejected": 0.0,
                 "oos_proposed": 0.0, "oos_accepted": 0.0, "oos_neutral": 0.0, "oos_rejected": 0.0,
                 "accepted_weight": 0.0, "unique_bonus": 0.0},
            )
            if kind == "finding":
                row["proposed"] += 1
                if result == "accepted":
                    row["accepted"] += 1
                    row["accepted_weight"] += accepted_weight
                    row["unique_bonus"] += bonus_float
                elif result == "neutral":
                    row["neutral"] += 1
                else:
                    row["rejected"] += 1
            else:
                row["oos_proposed"] += 1
                if result == "accepted":
                    row["oos_accepted"] += 1
                elif result == "neutral":
                    row["oos_neutral"] += 1
                else:
                    row["oos_rejected"] += 1
        lines: list[str] = []
        for reviewer, row in agg.items():
            score = (
                row["accepted_weight"]
                - (row["neutral"] * voting.NEUTRAL_FINDING_COST)
                + row["oos_accepted"]
                - row["rejected"]
                - row["oos_rejected"]
                + row["unique_bonus"]
            )
            lines.append(
                f"| {reviewer} | {int(row['proposed'])} | {int(row['accepted'])} | {int(row['neutral'])} | "
                f"{int(row['rejected'])} | {int(row['oos_proposed'])} | {int(row['oos_accepted'])} | "
                f"{int(row['oos_neutral'])} | {int(row['oos_rejected'])} | {voting.format_score(score)} |\n"
            )
        lines.sort()
        return "".join(lines)


def _record_plan_review_artifact_chunks(
    *,
    item: tuple[str, str, str, str, str, bool],
    vote_counts: tuple[int, int, int],
    chunks: tuple[list[str], list[str], list[str], list[str], list[str]],
) -> None:
    kind, result, reroute_marker, item_id, artifact_text, security = item
    accepted_chunks, rejected_chunks, oos_chunks, oos_accepted_chunks, oos_pool_chunks = chunks
    yes, no, judge_error = vote_counts
    if kind == "finding":
        if result == "accepted":
            accepted_chunks.append(artifact_text + "\n")
        elif reroute_marker:
            oos_artifact = (
                artifact_text
                + f"\nVote tally: YES={yes} NO={no} JUDGE_ERROR={judge_error} "
                f"Result={result} ({reroute_marker})\n\n"
            )
            oos_chunks.append(oos_artifact)
            oos_pool_chunks.extend(_public_oos_pool_chunks(artifact=oos_artifact, security=security))
        else:
            rejected_chunks.append(f"### [Plan Review] {item_id}\n\n{artifact_text}\n")
        return
    if result == "accepted" and security:
        return
    oos_artifact = artifact_text + f"\nVote tally: YES={yes} NO={no} JUDGE_ERROR={judge_error} Result={result}\n\n"
    oos_chunks.append(oos_artifact)
    oos_pool_chunks.extend(_public_oos_pool_chunks(artifact=oos_artifact, security=security))
    if result == "accepted":
        oos_accepted_chunks.append(artifact_text + "\n")


def _public_oos_pool_chunks(*, artifact: str, security: bool) -> list[str]:
    return [] if security else [artifact]


def _append(*, path: Path, chunks: list[str]) -> None:
    if chunks:
        with path.open("a", encoding="utf-8") as handle:
            _ = handle.write("".join(chunks))


_ARTIFACT_BLOCK_HEADING_RE = re.compile(r"(?m)^### (?:FINDING|OOS)_[0-9]+(?:\b|:).*$")


def _read_regular_file_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _markdown_artifact_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        return []
    matches = list(_ARTIFACT_BLOCK_HEADING_RE.finditer(normalized))
    if not matches:
        return [_ensure_trailing_newline(normalized)]
    blocks: list[str] = []
    if normalized[: matches[0].start()].strip():
        blocks.append(_ensure_trailing_newline(normalized[: matches[0].start()]))
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        block = normalized[match.start():end]
        if block.strip():
            blocks.append(_ensure_trailing_newline(block))
    return blocks


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _append_unique_artifact_blocks(*, path: Path, chunks: list[str]) -> None:
    if not chunks:
        return
    existing_text = _read_regular_file_text(path)
    seen = set(_markdown_artifact_blocks(existing_text))
    new_blocks: list[str] = []
    for chunk in chunks:
        for block in _markdown_artifact_blocks(chunk):
            if block not in seen:
                seen.add(block)
                new_blocks.append(block)
    if not new_blocks:
        return
    separator = "\n" if existing_text and not existing_text.endswith("\n") else ""
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(separator + "".join(new_blocks))


def _accumulate_round_accepted_all(*, path: Path, chunks: list[str]) -> None:
    _append_unique_artifact_blocks(path=path, chunks=chunks)


def _accumulate_round_oos(*, path: Path, chunks: list[str]) -> None:
    _append_unique_artifact_blocks(path=path, chunks=chunks)


def main(argv: list[str]) -> int:
    """In-process entry point for ``plan-review tally`` (replaces _run_legacy)."""
    logging_util.quiet_init(argv0="cli.py")
    tally = _Tally()
    try:
        return tally.run(list(argv))
    except _AbortTally as exc:
        return exc.code
    except Exception as exc:  # mirror bash cleanup trap: any failure -> tally-error
        logging_util.diagnostic(f"tally-plan-review: unexpected error: {exc}")
        if not tally.status_emitted:
            if tally.tally_file and Path(tally.tally_file).exists() and Path(tally.tally_file).stat().st_size > 0:
                logging_util.emit_kv(key="VOTING_TALLY_FILE", value=tally.tally_file)
            logging_util.emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="tally-error")
        return 2
    finally:
        if tally.workdir and Path(tally.workdir).is_dir():
            shutil.rmtree(tally.workdir, ignore_errors=True)
