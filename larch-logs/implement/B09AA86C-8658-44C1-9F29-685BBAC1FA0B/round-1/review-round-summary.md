# Review Round 1

- Mode: `diff`
- 12 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Test harness uses mismatched diff fingerprint
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-guidelines-flow-output.txt
- **Severity**: important
- **Concern**: `test-architectural-guidelines-step.sh` stages `--diff-fingerprint fp` without a matching diff snapshot. `pin_note_from_staged()` rejects the fingerprint mismatch, durable `architectural-guideline-note.md` is never written, and the harness fails at `cmp`. Shard 15 therefore does not guard the staged→durable contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Write a real diff snapshot and set diff-fingerprint to diff_fingerprint(snapshot), or pass --diff-file in the harness.
  - From codex-specialist-edge-cases-output.txt: Use `python/cli.py architectural-guidelines write-staged-assessment` with a matching `--diff-file`, or pass the SHA-256 fingerprint of the empty diff snapshot.
  - From cursor-specialist-testing-output.txt: Pass a fingerprint matching the empty diff snapshot, or write a diff file whose hash equals fp before pinning.
  - From dyn-dyn-guidelines-flow-output.txt: Materialize or write a real diff snapshot, set `--diff-fingerprint` to `diff_fingerprint(<that diff>)`, assert `ARCHITECTURAL_GUIDELINES_PIN_STATUS=ok`, and only then `cmp` staged vs durable bodies.


### FINDING_2: Step 16 pin path omits repo_root and accepts weak fingerprint validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-guidelines-flow-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: The Step 16 pin CLI and wrapper do not pass `repo_root`, so live implementation-diff checks are skipped. When the materialized diff snapshot is missing, `_staged_fingerprint_valid()` can return `True` from sidecar metadata alone. Stale staged assessments can be pinned to a new HEAD without tying them to the current implementation diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add --repo-root to pin CLI and wrapper; pass into pin_note_from_staged like ship._pin_and_load_guidelines_note.
  - From cursor-specialist-edge-cases-output.txt: Pass repo root into pin_note_from_staged_main and resolve it in the wrapper via git toplevel
  - From dyn-dyn-guidelines-flow-output.txt: Add `--repo-root` to the pin CLI/wrapper (resolved from `session-env.sh` like `final_report._implement_repo_root()`), require a readable snapshot matching `DIFF_FINGERPRINT`, and reject pin when live fingerprint cannot be verified.
  - From dyn-dyn-note-safety-output.txt: Add `--repo-root` to the pin wrapper (resolve from `session-env.sh` / `CLAUDE_PROJECT_DIR`, mirroring `final_report._implement_repo_root()`), plumb it through `pin_note_from_staged_main()`, and reject pin when neither a valid diff snapshot nor a successful live fingerprint check exists.


### FINDING_3: `_staged_fingerprint_valid` fail-open on live diff materialization failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-guidelines-flow-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `_staged_fingerprint_valid()` returns `True` when `materialize_implementation_diff()` raises `RuntimeError` (e.g., git remote/ref outage). Ship pre-compose pin and Step 16 can publish guideline notes without verifying the live diff, allowing stale Phase A assessments to surface in PR bodies or final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return False on RuntimeError during live fingerprint check (fail closed), consistent with note_fingerprint_stale.
  - From cursor-specialist-edge-cases-output.txt: Fail closed on RuntimeError; skip pin and log a warning unless live diff check succeeds
  - From dyn-dyn-guidelines-flow-output.txt: Fail closed when live fingerprint computation fails (`return False`), and skip durable surfacing unless both snapshot and live fingerprints match.
  - From dyn-dyn-note-safety-output.txt: Fail closed on live diff verification errors (return `False` and skip pin), or require a matching on-disk diff snapshot when live verification is unavailable; only allow pin when snapshot fingerprint matches sidecar metadata.


### FINDING_4: Phase A write-staged aborts when diff materialization leaves no diff file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If diff materialization fails and leaves no diff file, `step-architectural-guidelines-write-staged.sh` still passes `--diff-file`. `write_staged_assessment_main` raises `FileNotFoundError` on `read_text`, aborting Phase A instead of warn-and-continue per plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Guard missing diff file in shell or Python; skip --diff-file when absent and emit failed status with warning.


### FINDING_5: `final_report` repo root resolution skips stale-note guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_implement_repo_root` reads `CLAUDE_PROJECT_DIR` from `session-env.sh`, but session write-env never stores that key. `note_fingerprint_stale` is usually skipped in the final-summary path, so the plan's stale-note guard for `summary-final.md` is ineffective.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Resolve repo root via git toplevel or persist repo root path in session env at bootstrap.
  - From cursor-specialist-edge-cases-output.txt: Resolve consumer repo root via git toplevel or an existing persisted session key


### FINDING_7: `read_guidelines()` does not catch invalid UTF-8
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `read_guidelines()` catches `OSError` but not `UnicodeDecodeError`. A present `ARCHITECTURAL_GUIDELINES.md` with invalid UTF-8 crashes the helper instead of returning `invalid` with a warning, blocking the required invalid-warning-and-continue path in `/design` or `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Catch `UnicodeDecodeError` with `OSError` and return `_invalid(..., "unreadable file (...)")`.


### FINDING_8: `_read_env()` can raise on unreadable sidecars
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_read_env()` can raise on unreadable or non-UTF-8 staged/durable sidecars. The plan requires unreadable, symlinked, stale, or unconsumable notes to be treated as absent rather than failing PR creation or final-report rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make `_read_env()` fail closed by catching `OSError` and `UnicodeDecodeError` and returning `{}`.


### FINDING_11: `pin_note_from_staged()` lets durable-note write failures abort ship
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `pin_note_from_staged()` lets durable-note write failures propagate. A malformed stale artifact (e.g., `architectural-guideline-note.md` as a directory) makes `write_implement_note()` raise and can abort PR creation, despite the contract that pin failures only warn and continue without the guideline section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Catch `OSError` around `write_implement_note()`, return `False`, and let `_pin_and_load_guidelines_note()` log the existing warning path.


### FINDING_12: Final-report guideline surfacing silently drops notes on read/redaction failure
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Final-report guideline surfacing silently drops a consumable note when note read or redaction fails. That hides the warning surface from `summary-final.md` while returning a successful final report, conflicting with the fail-closed/redacted-publication contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Treat redaction failures as final-report failures, and only suppress expected non-consumable cases before this block.


### FINDING_13: `note_fingerprint_stale()` fail-open on live diff materialization failure
- **Reviewer(s)**: dyn-dyn-guidelines-flow-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `note_fingerprint_stale()` returns `False` ("not stale") when live diff materialization fails. A durable note pinned before later implementation changes can remain consumable at final-summary time if git verification fails, even when live git would have invalidated it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guidelines-flow-output.txt: Treat fingerprint probe failure as stale/unconsumable (return `True` or a third "unknown" state that blocks surfacing), matching the SECURITY.md contract for stale-note non-consumption.
  - From dyn-dyn-note-safety-output.txt: Treat git verification failure during stale checks as stale/unknown and refuse consumption (return empty section / skip PR append), or fall back to comparing the durable meta fingerprint against the on-disk diff snapshot when live git is unavailable.


### FINDING_14: Missing open-PR resume pin-before-compose test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required open-PR resume pin-before-compose coverage is missing; existing test only calls `_pin_and_load_guidelines_note` in isolation. An open-PR resume regression could skip pinning or reorder pin vs compose without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a run_ship open-pr resume test that spies pin vs compose order and asserts architectural_guidelines_note is passed to compose_pr_body.


### FINDING_18: Live fingerprint validation compares all-files diff instead of implementation-only diff
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Live fingerprint validation compares the staged implementation-diff fingerprint to a fresh all-files `base..HEAD` diff. Fresh PR prep can add a log-only `larch-logs` commit before compose, causing `pin_note_from_staged` via `ship.py` to skip the guideline note and omit required PR/final-summary surfacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Do not live-compare all-files base..HEAD at pin/final surfacing, or fingerprint the same implementation-only diff Phase A assessed; add a git-backed log-only HEAD bump regression test using the repo_root pin path.


