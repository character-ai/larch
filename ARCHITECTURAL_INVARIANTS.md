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
backing: `python3 python/cli.py lint agent-tool-contract` over agent
frontmatter, plus fail-closed prompt language in the triage agent definition.
