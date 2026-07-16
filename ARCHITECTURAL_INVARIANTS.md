# Architectural Invariants

Absolute invariants: rules that must always hold, with no legitimate exception.
Unlike the aspirational entries in `ARCHITECTURAL_GUIDELINES.md`, an invariant
has no "Deviate when" clause, and any violation is a defect. Where an invariant
can be enforced mechanically, back it with a lint, hook, or test; this file is
the human-readable specification, not a replacement for those checks.

## Workflow integrity

### I-Gate-1: A gate never disarms on data authored by the gated entity

A hard gate (a size trigger, a publish gate, a safety check) must not be
suppressed, weakened, or disarmed solely by metadata that the gated entity
itself declared, such as a drafting model's self-reported `diff_added` or
`mechanical_churn`. Disarming a hard gate requires independently computed
evidence or an explicit operator decision recorded in run state. Self-declared
metadata may soften presentation, never the trigger condition. Evidence of
violation: a gate whose disarm inputs are all writable by the entity under
evaluation (#6542, #6524).

### I-Gate-2: A variant path runs every persistence step its mainline gate runs

A flag carve-out, fallback lane, or legacy-shape path may skip pauses,
approvals, and presentation waits. It must not skip a gate's persistence or
verification steps: after any path passes a gate, every artifact the mainline
path persists at that gate exists and verifies, and every freshness check the
mainline runs has run. A variant that drops a persist step turns the next
consumer's fail-closed check into a false stall or a fail-open pass. Evidence
of violation: `--skip-approve` skipped the Gate C invariant present-note and
assessment persistence, so Step 5c false-blocked (#7250); legacy `unavailable`
durable notes passed the Step 8 merge gate with no live-fingerprint check
(#7216). Mechanical backing: per-variant prompt-contract pins, such as the
skip-approve Gate C pins in `python/tests/core/test_architectural_guidelines.py`;
add an equivalent pin whenever a gate gains a new variant path.

### I-Pause-1: A pause snapshot contains every artifact a resume guard reads

The /design pause snapshot must include every file and sentinel that any
resume-path guard or validator reads to corroborate prior progress, including
the `.completed/` step sentinels. When a guard gains a new required artifact,
the snapshot allowlist changes in the same commit. A resume that false-refuses
on an artifact the pause omitted is a defect of the snapshot, not of the guard
(#6548). Mechanical backing: the pause snapshot regression tests in
`python/tests/design/test_design_pause.py` cover `.completed/` inclusion;
extend them when the guard-read artifact set grows.

### I-Stale-1: A persisted step result is consumed only against the inputs that produced it

- Why: Any step result persisted for later consumption, including a bgjob result env, staged or durable assessment, cached verdict, or completion sentinel with a payload, carries an identity of the inputs that produced it, such as a content hash, `HEAD` SHA, or diff fingerprint.
- Why: Every consumer validates that identity against the live inputs before acting; on mismatch, the consumer re-runs the producing step or fails loudly. It never silently reuses the stale result.
- Why: Evidence of violation: /design review re-entry rejoined a pre-edit bgjob result env after `plan.txt` changed (#6633); the /implement guideline note was repeatedly consumed after HEAD drift invalidated the diff it assessed (#5337, #5675, #5969, #6059, #6106).
- Why: Mechanical backing: input fingerprints in persisted result envs plus consumer-side validation, mirroring `DIFF_FINGERPRINT` and `HEAD_SHA` checks in `python/larch/core/architectural_guidelines.py` (`note_consumable`, `_staged_fingerprint_valid`); extend the same pattern to bgjob result envs consumed on re-entry.

## Run-log integrity

### I-Flush-1: A missing required run-log artifact is a recorded execution issue, never a silent status string

Every run-log flush must either commit the run's required artifact set (session
transcript, voted-finding bodies, final report) or record the omission as a
category-keyed execution issue that flushes into the committed run log. A
capture failure that exists only as a status value inside the session tmpdir is
invisible to every audit surface and is a defect of the flush, not acceptable
drift. Evidence of violation: every post-migration /implement run recorded
`SESSION_TRANSCRIPT_STATUS=write-failed` with no execution issue while runs
completed green (#6263), and rejected and neutral finding bodies were absent
from committed logs with nothing recorded anywhere (#6027). Mechanical backing:
a post-flush manifest completeness check that asserts the expected artifact set,
or its recorded execution-issue entries, before the run-log commit, with
regression tests in `python/tests/report/test_run_log_flush.py`.

### I-Commit-1: A committed run-log field embeds its content, never a pointer into a session-tmpdir file

A field written into a committed run-log artifact under `larch-logs/` either embeds the redacted content it needs downstream or omits the field. It never stores a path into the session or system tmpdir (for example `$TMPDIR`, `IMPLEMENT_TMPDIR`, or `/var/folders/...`). A reader of a committed run log must be able to adjudicate the run from the committed artifact alone, without reaching into a session tmpdir that no longer exists. Evidence of violation: rejected and neutral finding bodies were absent from committed logs and survived only as pointers into session-tmpdir files that were never staged, so post-hoc adjudication could not evaluate whether a rejection was sound (#6027). Mechanical backing: a commit-time scan of staged `larch-logs/` content for session- and system-tmpdir path prefixes, with a failing check that rejects the commit; extend the run-log flush path that already stages redacted bodies so every voted finding commits its body through the existing redaction pipeline.

### I-Outcome-1: A committed outcome label for an in-flight run is neutral

A pre-terminal run-log snapshot commits only neutral in-progress labels such as
`shipping` or `in-progress`, never terminal failure words such as `stalled`,
`bailed`, or `bailed-needs-user-input`, and a stalled-then-recovered run must
not stay committed as stalled. The terminal outcome is reconciled at the last
allowed commit window. Evidence of violation: pre-terminal snapshots froze
merged runs as bailed or stalled in the committed logs, corrupting every
downstream outcome census (#5646, #5676, #5970, #4900). Mechanical backing: the
shared pre-terminal label guard in `python/larch/report/run_log_flush.py`
blocks forbidden labels in refresh, `run-log flush`, `run-log commit`, and
`capture-transcript` direct-commit paths, with regression tests in
`python/tests/report/test_run_log_flush.py`, recovery expectations in
`python/tests/report/test_run_logs.py`, and Step 7a bypass coverage in
`python/tests/implement/test_step_7a.py`.

## Panel integrity

### I-Slot-1: A panel slot never disappears without a per-slot record

When a reviewer or voter slot is dropped, substituted, pruned,
format-rejected, or excused, the orchestration layer appends a per-slot record
naming the slot, the stage, and the reason to the execution-issues log or the
slot manifest before the slot leaves accounting. An aggregate count or generic
warning does not satisfy this. When record volume is a concern, bound the
record size, never its existence. Evidence of violation: silent slot drops hid
systemic reviewer loss for weeks, and downstream coverage gates could not see
drops that were never persisted (#3392, #3423, #5047, #5529). Mechanical
backing: per-slot prune ledgers and manifests such as
`reviewer-prune-ledger.tsv`, `*-slots.ndjson`, and dropped-slot sidecars, plus
drop-path coverage in `python/tests/review/test_plan_review_round.py`,
`python/tests/review/test_plan_review_panel.py`, and the agent waterfall tests.

## Agent contracts

### I-Agent-1: A machine-ingested agent verdict is backed by evidence the agent actually read

An agent whose output is machine-parsed (JSONL verdicts, vote rows, manifests)
must either read its evidence through its own tools or emit the designated
cannot-read outcome for that item. It must never emit well-formed output for
evidence it could not open. A dispatch that inlines evidence must fit the
worst case computed from the owning cap constants; when it cannot, it passes
paths and grants a Read tool. Evidence of violation: a toolless triage agent
play-acted tool calls and fabricated JSONL verdicts, and the dispatching
skill's inlining assumption failed at the configured caps (#6671). Mechanical
backing: the pinned `agent-lint` release rules A012 and A013 over agent
frontmatter, plus fail-closed prompt language in the triage agent definition.

### I-Lane-1: A role's agent lanes share one dispatch, retry, and accounting surface

Every lane of a given agent role (reviewer, voter, drafter, fixer, assessor)
is launched, retried, excused, and counted by the same shared surface as its
sibling lanes: one slot manifest, one waterfall, one retry policy, one
accounting path. A lane-specific carve-out never silently skips the shared
surface; it ships with a parity note naming exactly what differs and why.
Evidence of violation: voter-1 ran outside the waterfall and was never
re-dispatched (#5837, #5448), dispatch success was keyed to a single voter
(#5637), dynamic reviewers were excluded from failure thresholds and slot
accounting (#5529) and launched without the shared render scaffold (#4841),
self-review wrote no tally artifact (#4424, #4618), and the same
empty-output retry was re-implemented lane by lane (#5677, #5732, #5971, #5605, #5674).
Mechanical backing: partial, via the shared waterfall and
slot manifests; carve-outs are caught in review against this entry.

## Ship lifecycle

### I-Ship-1: A recovery route never applies pre-merge mutations to a merged or closed PR

Once a run's PR is merged or closed, no recovery, retry, or resume route may
schedule or perform a pre-merge mutation on that PR: no rebase, no force-push
of the PR branch, no reopen-and-reship. A failure observed after merge routes
only to postmerge-scoped recovery: rerun the failed check, finalize as merged,
or stop at NEEDS_USER_INPUT. Generic outcome-to-route conversions must not
assume the pre-merge shape; the mutation choke point carries the PR-state
guard. Evidence of violation: the postmerge transient retry converted through
the generic reship path and requested a pre-fix rebase for a closed PR
(#6668), after the #6610 fix repaired only the literal repro. Mechanical
backing: the PR_CLOSED=true no-op guard on the pre-fix rebase in
python/larch/implement/dispatch_ship.py, with regression tests
test_ship_pre_fix_rebase_closed_pr_skips_physical_rebase and
test_ship_pre_fix_rebase_closed_pr_does_not_override_conflict_handoff in
python/tests/implement/test_implement_dispatch.py; extend the guard and tests
when a new recovery route can reach a rebase or push for a closed or merged
PR.
