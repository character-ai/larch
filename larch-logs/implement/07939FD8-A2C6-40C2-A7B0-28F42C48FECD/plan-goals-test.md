## Goal
Implement issue #3552: [IMPLEMENTING] [OOS] Housekeeping batch: implement-timing harness coverage (#3432) + ci-monitor outcome tests + design-outline doc fix + dynamic-Codex log follow-ups (#3504)\n\nThis issue batches four independent **out-of-scope (OOS)** follow-ups surfaced by recent larch workflow runs. They are grouped only to amortize `/design` + `/implement` per-cycle overhead — they touch **different code areas** and have no inter-dependency, so the implementer may land them as separate commits within one PR (or split if review warrants). All are small, low-risk changes with **no production behavior change**. Reviewer remedy text is informational only — the implementer chooses the actual fix..

## Implementation Plan
## Plan

# Implementation Plan — #3552 Housekeeping batch (A/B/C/D)

SIMPLE-tier batch of four independent OOS follow-ups. A1/A3/B/C/D are
test/doc/comment-only; A2 adds surgical `LARCH_TIMING_SKILL=implement` pins on
five existing launcher `record-vendor-task` lines (telemetry skill attribution
only under polluted shells — no dispatch or workflow-path change). Land as
separate commits in one PR. Round 1 decisions are binding: B = add focused
tests; D3 = document (no truncate); D4 = by-design + SECURITY.md
cross-reference (no new assertions).

## Files to modify/create

### UPDATED: `scripts/test-implement-structure.sh`
A1 + A3 harness extension.

- **A1 (general timing-pin invariant)**: add one awk-based scanner that enumerates
  the known implement production scripts that emit timing calls and asserts every
  `timing-ledger.sh mark`, `timing-ledger.sh record-vendor-task`, and
  `timing-report.sh` invocation co-locates `LARCH_TIMING_SKILL=implement` on the
  same command line. Match by basename (`timing-ledger.sh` / `timing-report.sh`)
  not by a `scripts/` path prefix — production scripts invoke via `$SCRIPT_DIR`.
  Scanned set: `scripts/implement-bootstrap.sh`,
  `skills/implement/scripts/step2-implement.sh`,
  `skills/implement/scripts/commit-implementation.sh`,
  `skills/implement/scripts/commit-review-fixes.sh`,
  `skills/implement/scripts/step-7a.sh`, `scripts/refresh-run-logs.sh`,
  `scripts/implement-finalize.sh`, `scripts/step-telemetry-mark.sh`,
  `scripts/run-step5-review.sh`, `scripts/run-relevant-checks-captured.sh`,
  `scripts/launch-codex-implement.sh`, `scripts/launch-cursor-implement.sh`,
  `scripts/launch-codex-ci.sh`, `scripts/launch-cursor-ci.sh`,
  `scripts/launch-claude-ci.sh`.
  Keep the existing literal `grep -qF` per-mark pins (Step 4 / Step 7 / Step 7a /
  Step 0 etc.) — the scanner is additive so dropped pins in the known set fail CI,
  and future implement timing emitters must be added to the scanner list.
  Model the scanner on the same-line index() approach already in
  `test-implement-timing-rehydration.sh` Invariant B.
- **A3 (workflow-free Step 2 + stale-path-ignored)**: extend the existing
  workflow-path assertions (currently `run-step2-dispatch.sh` must not pass
  `--workflow`; `implement-bootstrap.sh` must not persist workflow path) with
  targeted assertions that the Step 2 dispatch stack
  (`skills/implement/scripts/run-step2-dispatch.sh`,
  `skills/implement/scripts/step2-implement.sh`) contains no tier/workflow
  branching tokens (`workflow_path`, `HARD`/`SIMPLE` workflow switches), and that
  production implement code does not read a `workflow_path` key (stale values from
  pre-#3432 run-params are ignored). Scope the `workflow_path` read-assertion to
  the same explicit production `.sh` set as the A1 scanner (exclude `test-*.sh`)
  to avoid false-failures on fixture references. Pin exact tokens with
  `grep -Fq`/`! grep -Fq`.

### UPDATED: `scripts/launch-codex-implement.sh`
A2. Pin the inline `"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task`
line with the same inline prefix shape used by the existing implement marks:
`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \`.
This prevents a polluted ambient `LARCH_TIMING_SKILL=design` shell from tagging
the Codex vendor row `design`.

### UPDATED: `scripts/launch-cursor-implement.sh`
A2. Same one-line pin on the Cursor launcher's inline
`"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task` line, mirroring
the Codex change per external-tool-launcher-parity. Do NOT touch
`scripts/launch-review.sh` `record-vendor-task` — it also serves `/review`, where
pinning `=implement` would mis-tag review usage (intentional exclusion).

### UPDATED: `scripts/launch-codex-ci.sh`
A2. Pin the inline `"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task`
line near EOF with the same inline prefix shape:
`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \`.
Prevents a polluted ambient `LARCH_TIMING_SKILL=design` from tagging Codex
CI-fix vendor rows as `design`.

### UPDATED: `scripts/launch-cursor-ci.sh`
A2. Same one-line pin on the Cursor CI launcher's inline
`record-vendor-task` line near EOF, mirroring the Codex CI change.
Keep `scripts/launch-review.sh` excluded (serves `/review`; pinning
`=implement` there would mis-tag review-phase rows).

### UPDATED: `scripts/launch-claude-ci.sh` (A2 pin only)
A2. Pin the inline `"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task`
line in the Claude CI-fix launcher with the same prefix shape:
`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \`.
This script is a production `/implement` CI-fix launcher that emits
`record-vendor-task`; without the pin, Claude CI-fix vendor rows can be tagged
`design` under a polluted shell, and the A1 scanner would flag it as unpinned.
Keep `scripts/launch-review.sh` and `scripts/launch-claude-subprocess.sh` excluded.

### UPDATED: `python/test_ci_monitor.py`
B. Add a focused set (≈2–4) of monitor-level outcome tests, additive only,
following the existing `RecordingRunner` / `test_monitor_*` / `test_decide_parity_table`
patterns. Target terminal outcomes not already exercised by the resume/counter and
`evaluate_failure` suites. Candidates to confirm and cover:
- `monitor()` `already_merged` short-circuit → `Outcome.OK`.
- `monitor()` consecutive status-gather error bail → `Outcome.TRANSIENT` (assert
  after three consecutive `ci-status.sh` no-output failures exhaust the bail
  threshold; `monitor()` routes this bail reason through transient-network
  signature matching, which classifies "no valid output 3 times" as
  `Outcome.TRANSIENT`, not `Outcome.STALLED` — mirrors intentional bash parity in
  `scripts/lib-net.sh`). Use the `RecordingRunner` stub from
  `python/test_ci_monitor.py:330-351` (gh pr view rc=1 shape); assert
  `detail` contains `"3 times consecutively"`.
Drop the unknown-status wait candidate: `poll_ci` loops on `action==wait` and
never surfaces unknown-status wait through `monitor()`; bash rejects unknown
statuses rather than treating them as wait. The implementer verifies which
`Outcome` each path yields and adds only the genuinely-uncovered ones. Keep
within the ~30–60 LOC the OOS scoped.

### UPDATED: `scripts/test-larch-log-write-round.sh`
D1. Add two static-Codex sidecar fixtures —
`codex-specialist-security-output.txt.json` and
`codex-specialist-security-output.txt.cap-hit` — and two `assert_not_file`
assertions that both are excluded from the staged round. The exclusion is already
enforced by the `codex-specialist-*-output.txt.json|...cap-hit` deny clause in
`larch-log.sh round_artifact_included()`; this adds the missing regression coverage
next to the existing `.meta`/`.done`/`.diag` exclusion assertions.

### UPDATED: `scripts/larch-log.sh`
D2 + D4 comment-only edits in `round_artifact_included()`.

- **D2**: reword the dynamic-Codex allow comment (above the
  `dyn-*-codex-output.txt|...` allow case) to state precisely that the explicit
  clause pins the KNOWN dynamic-Codex shapes (`dyn-*-codex-output.txt`,
  `dyn-*-codex-output-phase*.txt` plus `.meta`/`.json`/`.cap-hit`); other/future
  shapes fall through to the broad `*-output*` allow; retry outputs
  (`dyn-*-codex-output-retry*`) are explicitly denied above. Remove the
  overstated "does not depend on catch-all transcript globs" framing.
- **D4**: add a one-line comment near the same dynamic-Codex allow noting the
  retained families (`dyn-*-codex-output.txt` and `dyn-*-codex-output-phase*.txt`
  plus sidecars; retry outputs remain excluded) rely on the documented
  pattern-based redaction posture (see `SECURITY.md`). No logic change.

### UPDATED: `scripts/larch-log.md`
D2 + D4 prose-only sync with `scripts/larch-log.sh`: align the write-round contract
to say the explicit dynamic-Codex clause pins the known
`dyn-*-codex-output.txt` / `dyn-*-codex-output-phase*.txt` families and their
`.meta`/`.json`/`.cap-hit` sidecars; retry outputs (`dyn-*-codex-output-retry*`)
remain explicitly denied and are not covered by this clause; other/future output
shapes may still fall through to the broad `*-output*` allow; cross-reference the
documented pattern-based redaction posture in `SECURITY.md`.

### UPDATED: `python/logging_util.py`
D3. Add a comment at the quiet-log open site in `quiet_init()` (the `path.open("a")`
+ `os.O_APPEND` lines) documenting that Python quiet logs append for crash/retry
forensics, diverging intentionally from the bash quiet-log truncate-per-run
behavior. Comment only — do NOT change the open mode.

### UPDATED: `python/README.md`
D3 prose-only clarification beside the `logging_util.py` description: Python quiet
logging mirrors bash quiet stream routing, but intentionally uses append-forensics
log opens rather than bash's truncate-per-initialization behavior.

### UPDATED: `scripts/lib-quiet.md`
D3. Add a surgical sentence to the quiet-log contract documenting that
`larch_quiet_init` truncates the selected bash quiet log before redirecting
stdout/stderr (truncate-per-initialization), contrasting with the Python
append-forensics behavior documented in `python/logging_util.py` and
`python/README.md`. Comment/docs only — no behavior change.

### UPDATED: `SECURITY.md`
D4. Two edits in the run-log redaction section:

1. **Narrow residual-risk cross-reference**: add a sentence noting that the
   specific dynamic-Codex output families explicitly retained by #3504 —
   `dyn-*-codex-output.txt` and `dyn-*-codex-output-phase*.txt` plus their
   `.meta`/`.json`/`.cap-hit` sidecars; retry outputs (`dyn-*-codex-output-retry*`)
   remain excluded — are published under the same pattern-based
   `redact-secrets.sh` / scrub-log-secrets posture already documented for
   committed `larch-logs/`. Frame as by-design residual risk, not a new control.

2. **Soften existing "safe without scanner" prose**: in the same edit, soften any
   existing sentence suggesting consumer repos need no third-party scanner for
   run-log flushes to be fully safe. Rephrase to say no third-party scanner is
   required for covered secret-shaped token families, but run logs remain sensitive
   documents and secrets or PII not matched by the scrubber patterns (non-standard
   tokens, private hostnames, domain-specific sensitive data) still require
   operator discipline before publication.

Obey markdownlint MD038/heading-increment.

## Approach

- Treat each item as its own commit; keep edits surgical.
- **A2 before A1**: A2 pins must be committed (same commit or a prior commit)
  before A1 scanner lands. The scanner immediately flags any unpinned
  `record-vendor-task` lines in the scanned set (including `launch-claude-ci.sh`);
  committing A1 alone creates a transiently failing CI tree until all A2 pins are
  in place.
- **C (already resolved — no edit)**: `skills/design/references/design-outline.md`
  Step-3 paragraph already states the corrected post-#3511 contract
  (`plan-review-scope-anchor.txt`; "not merged into the binding reviewer scope
  anchor"). Commit `c3a6c4de4` (Fixes #3511, PR #3548) landed the fix; a repo-wide
  grep for the stale "MAY merge … feature-context" / "design-outline.md into the
  feature-context" text returns zero hits. C is a verify-and-close no-op. Before
  closing, the implementer re-greps `skills/`, `docs/`, `README.md`, and the
  `plan-review-loop` surfaces; if any stale reference survives, fix that file and
  note it — otherwise record C as already-resolved with no code change.
- A1/A2 compose: the A1 general scanner covers the `record-vendor-task` lines A2
  pins (including the Claude CI launcher), so the new pins are enforced by the
  same guard.
- Keep sibling `.md` contracts in sync only where prose changes: update
  `scripts/larch-log.md` for the dynamic-Codex retention rationale (D2/D4);
  update `python/README.md` and `scripts/lib-quiet.md` for the documented
  quiet-log divergence (D3 — Python append-forensics vs bash truncate-per-run).
  `test-implement-structure.md`, `launch-codex-implement.md`,
  `launch-cursor-implement.md`, `test-larch-log-write-round.md` need no contract
  change for additive test/comment edits.

## Edge cases

- A1 scanner must match timing invocations by basename (`timing-ledger.sh` /
  `timing-report.sh`), not by a literal `scripts/` path prefix; production scripts
  invoke via `$SCRIPT_DIR` and a prefix-required pattern silently misses those calls.
- A1 scanner must handle multi-line `record-vendor-task \` continuations: assert the
  pin on the command's first line (the `timing-ledger.sh` line), not the flag lines.
- A1 scanner must not flag non-timing subcommands (e.g. `timing-ledger.sh dump`) or
  `token-ledger.sh mark`; match only `mark`, `record-vendor-task`, `timing-report.sh`.
- A1 scanner must include all three CI-fix launchers (`scripts/launch-codex-ci.sh`,
  `scripts/launch-cursor-ci.sh`, `scripts/launch-claude-ci.sh`) alongside the Step 2,
  Step 5 review/resume, and captured relevant-checks timing emitters; no known
  production timing surface may be silently missed. Keep `scripts/launch-review.sh`
  and `scripts/launch-claude-subprocess.sh` excluded.
- A3 `workflow_path` read-assertion grep must be scoped to the same explicit
  production `.sh` set as A1 (exclude `test-*.sh`) to avoid false failures on
  fixture references.
- D1 fixtures must use a `codex-specialist-*-output.txt` basename so they hit the
  static deny clause (not the dynamic `dyn-*` allow).
- B tests must use the existing `RecordingRunner` stub so no real `gh`/`git` runs;
  assert `Outcome.TRANSIENT` (not `Outcome.STALLED`) for the consecutive-error
  bail path — `monitor()` routes this through transient-network classification.
- SECURITY.md edit: narrow dynamic-Codex family references to exact retained shapes
  and explicitly exclude retry outputs; keep code-span boundaries whitespace-free;
  increment headings by one level.

## Failure modes

- **A1 scanner false signal**: an over-broad regex flags a legitimate line or
  misses a multi-line form, breaking CI or giving false safety. Earliest signal:
  the harness fails (or passes with an obviously unpinned line). Mitigation: scope
  the file set explicitly; reuse the proven `index()` shape from
  `test-implement-timing-rehydration.sh`; the harness must pass on the tree only
  after all A2 pins are applied (including all three CI-launcher pins). Include Step 2,
  Step 5 review/resume, captured relevant-checks, and all CI-fix launcher emitters
  in that explicit set; if future implement timing emitters are added, update the
  scanner in the same change.
- **A1/A2 commit ordering**: committing A1 before A2 creates a transiently
  failing scanner (unpinned CI-launcher `record-vendor-task` lines — including
  `launch-claude-ci.sh` — are flagged). Commit all A2 pins in the same commit as
  A1, or apply A2 first. Earliest signal: scanner fails on any tree that lacks the
  CI-launcher pins.
- **A2 pin breaks launcher quoting**: prepending the env prefix shifts the
  `>/dev/null 2>&1 || true` tail or trips shellcheck. Signal: launcher harness or
  `make lint` failure. Mitigation: copy the exact prefix shape from an existing
  pinned mark; run shellcheck + `test-codex-implementer.sh` /
  `test-cursor-implementer.sh` and `make lint` on all three CI launchers.
- **C false no-op**: closing C while a stale reference hides in an unscanned
  surface. Signal: a later reviewer/grep finds old contract text. Mitigation:
  widen the pre-close grep to `README.md` and `plan-review-loop` files; fix any hit.

## Testing strategy

- `bash scripts/test-implement-structure.sh` (A1, A3).
- `bash skills/implement/scripts/test-codex-implementer.sh` and
  `bash skills/implement/scripts/test-cursor-implementer.sh` (A2 implement
  launchers); run `make lint` / shellcheck on `scripts/launch-codex-ci.sh`,
  `scripts/launch-cursor-ci.sh`, and `scripts/launch-claude-ci.sh` (A2 CI
  launchers; extend to `test-launch-claude-ci.sh` if that harness exists).
- `make py-test` or `python -m pytest python/test_ci_monitor.py` (B).
- `bash scripts/test-larch-log-write-round.sh` (D1; D2/D4 script/doc prose is non-functional).
- `bash scripts/relevant-checks.sh` / `make lint` repo-wide (markdownlint for
  SECURITY.md and `.md` contract sync including `scripts/lib-quiet.md`, bash 3.2 lint for any new awk/shell,
  shellcheck).

## Acceptance

All four batched sections are handled per Round 1 decisions; **no production behavior change**; landed as separate commits in one PR.

- **A1**: `scripts/test-implement-structure.sh` gains a general scanner asserting every `timing-ledger.sh mark`, `timing-ledger.sh record-vendor-task`, and `timing-report.sh` invocation in the enumerated implement production scripts co-locates `LARCH_TIMING_SKILL=implement` on the same command (basename match; multi-line continuation aware). Existing literal per-mark pins retained. `bash scripts/test-implement-structure.sh` passes.
- **A2**: `launch-codex-implement.sh`, `launch-cursor-implement.sh`, `launch-codex-ci.sh`, `launch-cursor-ci.sh`, and `launch-claude-ci.sh` pin `LARCH_TIMING_SKILL=implement` on their `record-vendor-task` line. `launch-review.sh` and `launch-claude-subprocess.sh` are unchanged. A2 lands in the same commit as (or before) A1 so the scanner never sees an unpinned tree.
- **A3**: the harness asserts the Step 2 dispatch stack (`run-step2-dispatch.sh`, `step2-implement.sh`) carries no tier/workflow branching tokens, and production implement `.sh` code reads no `workflow_path` key (assertion scoped to the production set, excluding `test-*.sh`).
- **B**: `python/test_ci_monitor.py` adds a focused set (~2 tests, ~30–60 LOC) of monitor-level outcome tests via `RecordingRunner` (e.g. `already_merged → Outcome.OK`, consecutive status-gather bail → `Outcome.TRANSIENT`). `make py-test` passes.
- **C**: verified already resolved by commit `c3a6c4de4` (PR #3548); repo-wide grep confirms no stale "merge design-outline into feature-context" contract remains. No code change unless a residual stale reference is found during the pre-close grep.
- **D1**: `scripts/test-larch-log-write-round.sh` adds `codex-specialist-security-output.txt.json` and `.cap-hit` fixtures with `assert_not_file` exclusion assertions. `bash scripts/test-larch-log-write-round.sh` passes.
- **D2**: `scripts/larch-log.sh` and `scripts/larch-log.md` reworded so the dynamic-Codex allow comment accurately scopes the pinned shapes (retry outputs excluded; future shapes use the broad allow). Comment/prose only.
- **D3**: `python/logging_util.py`, `python/README.md`, and `scripts/lib-quiet.md` document the intentional Python append-for-forensics vs bash truncate-per-run divergence. No open-mode change.
- **D4**: `SECURITY.md` adds the dynamic-Codex retained-families redaction cross-reference (by-design residual risk) and softens any "safe without scanner" prose. No new test assertions.
- `bash scripts/relevant-checks.sh` / `make lint` pass repo-wide (markdownlint, bash 3.2 lint, shellcheck, `.md` sibling-contract sync).

diff_lines: 230

## Test plan
(no test plan section in plan-file)
