## Goal
Implement issue #5564: [IMPLEMENTING] md-to-py-VII: relocate two rare-path /implement bodies to on-entry references (--self-review mode block; Step 0 dirty-recovery / degraded-prompt).

## Implementation Plan
## Plan

## Approach

Implement the prompt split only. Do not move runtime behavior into Python or scripts.

- Add two `/implement` on-entry references with the standard column-0 header triplet.
- Replace the large inline Step 0 recovery and Step 5 self-review bodies with mandatory-load stubs that use the **full** step18-style read literal (not filename-only anchors).
- **Delete** the standalone `**Degraded prompt handling.**` and `Step 0 dirty-tree recovery gate:` sections from `SKILL.md` once `bootstrap-recovery.md` owns them.
- Update the **Rebase Checkpoint Macro** absorbed `1.r` degraded carve-out in `SKILL.md` (line 158) to mandate `bootstrap-recovery.md`, not deleted inline prose.
- **Update** (not optionally patch) `rebase-checkpoint-routing.md` so the absorbed `1.r` degraded carve-out points at `bootstrap-recovery.md` before treating absent routing keys as rebase failure.
- Preserve route predicates, fail-closed envelope rules, and existing Bash launcher shapes.
- Retarget every harness and pytest pin that currently slices or asserts against moved prose in `SKILL.md`.
- Use path literals in structure-harness `require()` / `require_near()` / `forbid()` calls; never pass preloaded file-body strings where helpers call `Path(path).read_text()`.
- Add mandatory `forbid(skill, ...)` pins for relocated authority strings (mirror `step18-cleanup.md` relocation pattern).
- Add **mandatory** relocation-authority verification loops for both new references (mirror `cleanup_ref` at `scripts/test-implement-structure.sh:632–654`); do not leave body verification optional.

### Canonical mandatory-read literals

Use these exact strings everywhere named below. Do not invent variants.

**Bootstrap-recovery stub / `require_near` pin** (table stubs and harness):

```text
**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely.
```

Table stubs append branch prose **after** that literal with a single period on `completely.` — e.g. `Then execute the degraded-prompt branch.` (capital `Then`; no double period).

**Bootstrap-recovery degraded carve-out** (Rebase Checkpoint Macro line 158, `rebase-checkpoint-routing.md` lines 5 and 7, `rebase_ref` loop):

**MANDATORY — READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` for degraded-prompt handling before treating absent routing keys as rebase failure.

**Self-review stub / `require_near` pin**:

**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.

## Files to modify/create

### NEW: skills/implement/references/self-review.md

Create the on-entry reference for Step 5 `--self-review`.

Open with column-0 header triplet exactly like sibling references (`rebase-checkpoint-routing.md:1-5`). **Do not fence the triplet**; headers must start at column 0 for `make test-references-headers`:

**Consumer**: Step 5 when `self_review=true`.
**Contract**: Authoritative body for inline main-agent self-review.
**When to load**: **MANDATORY — READ ENTIRE FILE** only when `self_review=true`.

Move the current self-review body from `skills/implement/SKILL.md` (lines 545–587) here, with these changes:

- Fold the standalone telemetry-mark fence into the first self-review verb: instruct the orchestrator to mark telemetry best-effort as part of entering self-review, then print the Step 5 banner. Keep a valid launcher line in reference prose if needed for harness pins. Preserve the exact best-effort guard:

  `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true`

- Keep plan read, diff capture, changed-file read, OOS policy load, review rubric, rejected-finding rules, composite checks-commit route, tally write, and anti-halt continuation.
- Preserve all four new-shape launcher fences relocated from `SKILL.md`:
  1. `python/cli.py timing telemetry-mark` (with `|| true`)
  2. `python/cli.py review-and-fix write-pre-self-review-snapshot`
  3. `python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review`
  4. `python/cli.py review-and-fix write-self-review-tally`
- Preserve the `checks-commit-route --checks-site step5-self-review --commit-site step5-self-review` contract with `**⚠ Immediate-background required — set run_in_background: true and timeout: 14700000.**`
- Preserve invalid composite handling with the **verbatim** fail-closed sentence currently pinned at `scripts/test-implement-structure.sh:433`:

  `set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18`

  (include `prompt-side` and `and skip to Step 18`; do not shorten).
- Preserve the `NEXT_ACTION=main-agent-edit` re-entry branch and the line-anchored `NEXT_ACTION` parse from current `SKILL.md` line 575:

  `On NEXT_ACTION=main-agent-edit, follow the reference's in-step Edit/Write and re-entry contract, then re-run this same composite launcher with identical argv.`

- Preserve mandatory-read hooks for `execution-issues-tracking.md` and `checks-repair-loop.md`.
- Preserve the five-line anti-halt opener contract before the composite `checks-commit-route` invocation:

  `> **Continue after child returns.**` with nearby `REDACTED_LOG_FILE` / `NOT raw \`LOG_FILE\`` failure guidance and success-path continuation prose (the anti-halt harness will scan this file with `EXPECTED_SITES=1`).
- Replace `section below` cross-refs with explicit `skills/implement/SKILL.md` anchors:
  - `### Track Rejected Code Review Findings` in `skills/implement/SKILL.md` (not "below").
  - `### Cross-Skill Presence Propagation` in `skills/implement/SKILL.md` for the post-Step-5 chain.
- Add prose between consecutive Bash fences where needed to satisfy `lint-consecutive-bash`.

### NEW: skills/implement/references/bootstrap-recovery.md

Create the on-entry reference for Step 0 `BOOTSTRAP_NEXT=degraded-prompt` and `BOOTSTRAP_NEXT=dirty-recovery`.

Open with column-0 header triplet:

**Consumer**: Step 0 routing rows for `degraded-prompt` and `dirty-recovery`.
**Contract**: Authoritative degraded-prompt handling and dirty-tree recovery gate after bootstrap returns a non-`step2` directive.
**When to load**: **MANDATORY — READ ENTIRE FILE** before executing either routing row.

Move the current rare-path details here:

- Degraded explanation presentation.
- `AskUserQuestion` choices (**Continue (reduced panel — unavailable tools dropped, no cross-tool or Claude padding)** / **Abort**).
- `.degraded-tools-gate-prompted` continue sentinel.
- `PRESENCE_INPUT_EMPTY=true` warning behavior.
- `DEGRADED_PROMPT_REQUIRED=true` handling when absorbed continue-tail surfaces it on resume paths.
- Both-down hard-stop behavior (`DEGRADED_HARD_FAIL=true`).
- Dirty-tree prompt, cleanup requirement, recheck requirement, and resume shape.
- Dirty-tree env write with `STATUS=dirty-or-unknown`, `STAGE=step0-plan-materialize`, and `RECOVERY_REQUIRED=true`.
- Dirty-tree recheck: re-run `python/cli.py dirty-tree checkpoint` and only continue when it returns `STATUS=clean`; rewrite env with `RECOVERY_REQUIRED=false` once clean; keep `RECOVERY_REQUIRED=true` until the clean re-check succeeds.
- Stale-state reset on successful clean recheck: `unset IMPLEMENT_BAIL_REASON` before resume.
- Resumed-tail rebinding: parse resumed `step-0-bootstrap.sh --mode resume` stdout before re-evaluating `BOOTSTRAP_NEXT` so `IMPLEMENT_BAIL_REASON`, `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE` come from the resumed tail rather than the pre-recovery pass.
- Dirty-tree operator paths: **Restore a clean tree and continue** / **Cancel this implement run**.
- The dirty-tree `step-0-bootstrap.sh --mode resume` old-shape Bash fence with `CLAUDE_PLUGIN_ROOT` rehydration prelude (the third `LARCH_CLAUDE_PLUGIN_ROOT=` awk fallback currently in `SKILL.md` lines 303–308).
- NEVER #21 edit-gate reminder, because these branches still occur before `BOOTSTRAP_NEXT=step2`.
- Wording that resumed bootstrap stdout must be parsed before re-evaluating `BOOTSTRAP_NEXT`.

Include the moved authority strings that the structure harness will verify (degraded presentation, `AskUserQuestion`, Continue/Abort choices, dirty-tree gate heading, `.dirty-tree-prompted-step0-plan-materialize`, `DEGRADED_PROMPT_REQUIRED=true`, `STAGE=step0-plan-materialize`, `STATUS=dirty-or-unknown` / `RECOVERY_REQUIRED` / `RECOVERY_REQUIRED=false` / `STATUS=clean` recheck literals, `IMPLEMENT_BAIL_REASON` / `BRANCH_NAME` / `BRANCH_ACTION` / `PLAN_FILE` rebinding, restore/cancel operator paths, resume fence, and NEVER #21 reminder).

### UPDATED: skills/implement/SKILL.md

Keep the Step 0 initial bootstrap body inline.

**Remove entirely** once `bootstrap-recovery.md` exists:

- The standalone `**Degraded prompt handling.**` paragraph (current line 292).
- The standalone `Step 0 dirty-tree recovery gate:` numbered list and its resume fence (current lines 296–309).

**Update Rebase Checkpoint Macro** (current line 158): replace

`When DEGRADED_PROMPT_REQUIRED=true on the absorbed 1.r path, follow the degraded prompt path instead of treating absent macro keys as rebase failure.`

with the canonical degraded carve-out literal:

`When DEGRADED_PROMPT_REQUIRED=true on the absorbed 1.r path, **MANDATORY — READ ENTIRE FILE** \`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md\` for degraded-prompt handling before treating absent routing keys as rebase failure.`

Replace the Step 0 rare-path table rows and Step 5 self-review body with compact routing stubs using **full** mandatory-read literals (match step18-cleanup stub style, not filename-only mentions):

- `BOOTSTRAP_NEXT=degraded-prompt`: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely. Then execute the degraded-prompt branch.
- `BOOTSTRAP_NEXT=dirty-recovery`: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely. Then execute the dirty-recovery branch.
- `BOOTSTRAP_NEXT=rebase-routing`: keep pointing at `rebase-checkpoint-routing.md`.
- `BOOTSTRAP_NEXT=step2` and `cleanup`: keep inline.
- Keep absorbed continue-tail and Step 1.r overview inline only as always-needed routing context.
- Table rows for `degraded-prompt` and `dirty-recovery` must be compact stubs only (no verbose execution prose that duplicates the reference).

Replace Step 5 self-review body with a compact stub under `### Self-review mode (--self-review)`:

- When `self_review=true`, skip the scripted review loop.
- **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.
- State that the reference owns inline review, composite checks-commit route, `NEXT_ACTION=main-agent-edit` re-entry, tally write, and post-Step-5 continuation.
- Do **not** retain moved launcher strings, timeout pins, tally artifact paths, or invalid-envelope fail-closed prose inline (harnesses relocate those pins to the reference).
- Leave the scripted review loop unchanged.

Do not remove cross-cutting safety anchors, NEVER rules, or the Step 5 scripted review contract.

### UPDATED: skills/implement/references/rebase-checkpoint-routing.md

When `DEGRADED_PROMPT_REQUIRED=true` on the absorbed `1.r` path, replace the degraded carve-out prose at lines 5 and 7 that says "follow the degraded prompt path instead" with the canonical degraded carve-out literal:


Apply at both the **When to load** carve-out (line 5) and the **Absorbed Step 1.r** paragraph (line 7) so neither entrypoint leaves a gap after inline degraded prose is deleted from `SKILL.md`.

### UPDATED: scripts/test-implement-fence-shape.sh

Update `EXPECTED_OLD` / `EXPECTED_NEW` after edits:

- `EXPECTED_OLD`: drop from **4** to **3** when the dirty-tree resume old-shape fence moves only to `bootstrap-recovery.md` (keep `--mode initial` in `SKILL.md`).
- `EXPECTED_NEW`: drop from **30** to **26** when all four self-review new-shape fences leave `SKILL.md`. Lower `EXPECTED_NEW` by exactly **four** for these departing fences:
  1. `python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review"`
  3. `python/cli.py implement checks-commit-route --checks-site step5-self-review`
- Re-run locally and set exact values from harness output. Do not extend this harness to scan references unless failure output requires it.

### UPDATED: scripts/test-implement-timing-rehydration.sh

Invariant C (lines 84–85) counts `LARCH_CLAUDE_PLUGIN_ROOT=` awk fallbacks only inside `SKILL.md` bash fences and currently requires `awk_count >= 3`. After relocating the dirty-tree `--mode resume` fence, `SKILL.md` retains two (preflight + Step 0 initial).

Lower the minimum threshold from **3** to **2** (preferred: invariant purpose is pre-bootstrap awk fallbacks remain in `SKILL.md` only; resume fence awk fallback lives in `bootstrap-recovery.md`).

Re-run `make test-implement-timing-rehydration` and set the chosen threshold from harness output.

### UPDATED: scripts/test-implement-structure.sh

Mirror the `step18-cleanup.md` relocation pattern. Optionally preload ref text only for `require_text()` / relocation-authority loops (like `cleanup_ref` at lines 632–654); **never** pass preloaded body strings to `require()` or `require_near()`.

**Reference existence and headers** (lines 55–67 loop):

- Add `bootstrap-recovery.md` and `self-review.md` to the mandatory reference list.
- `require(skill, ...)` pointers for both new refs.

**Old-shape wrapper loop** (lines 69–74):

- Keep only `step-0-bootstrap.sh" --mode initial` in the `skill` old-shape loop.
- Drop `--mode resume` from the `skill` loop.
- `require('skills/implement/references/bootstrap-recovery.md', 'step-0-bootstrap.sh" --mode resume', ...)` for the relocated resume fence.

**Launcher list** (line 131):

- Remove `python/cli.py implement checks-commit-route --checks-site step5-self-review ...` from the `require(skill, ...)` launcher loop.
- `require('skills/implement/references/self-review.md', launcher + 'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review', ...)`.

**Immediate-background / timeout pairs** (lines 229–238):

- Remove the `step5-self-review` / `timeout: 14700000` tuple from the `for script, timeout in [...]` loop on `skill`.
- Add standalone `require_near` calls on `'skills/implement/references/self-review.md'` for the composite launcher, `Immediate-background required`, and `timeout: 14700000` (this removes the for-loop tuple literal that `python/test_implement_dispatch.py` currently asserts).
- Keep Step 5 scripted review, Step 5-resume, Step 6, Step 7a, Step 8 pins on `skill`.

**Duplicate resume pins** (lines 382–383):

- Keep `require(skill, 'step-0-bootstrap.sh" --mode initial', ...)`.
- Drop `require(skill, 'step-0-bootstrap.sh" --mode resume', ...)`.
- `require('skills/implement/references/bootstrap-recovery.md', 'step-0-bootstrap.sh" --mode resume', ...)`.

**Self-review invalid-envelope fail-closed** (line 433):

- Relocate the **full verbatim** pin from `require(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18', ...)` to `require('skills/implement/references/self-review.md', ...)` with the **same** needle string (do not drop `and skip to Step 18`).
- Keep scripted-loop composite envelope pins on `skill` where they still apply.

**Mandatory-read-before-branch pins** (mirror `step18-cleanup` `require_near` at 319–326):

Define read-literal variables matching the canonical literals:

```python
bootstrap_recovery_read = '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely.'
self_review_read = '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.'
require_near(skill, bootstrap_recovery_read, 'BOOTSTRAP_NEXT=degraded-prompt', 'degraded-prompt mandatory read before branch', 900)
require_near(skill, bootstrap_recovery_read, 'BOOTSTRAP_NEXT=dirty-recovery', 'dirty-recovery mandatory read before branch', 900)
require_near(skill, self_review_read, 'When `self_review=true`', 'self-review mandatory read before branch', 900)

Use the exact capitalized stub anchor `When \`self_review=true\`` (matches the proposed `### Self-review mode` stub line); do not use lower-case `when`.

Do **not** use filename-only anchors (`bootstrap-recovery.md` without the full mandatory-read literal).

**rebase_ref degraded-path enforcement** (extend existing loop at lines 260–273):

After loading `rebase_ref`, add checks that the absorbed `1.r` degraded carve-out mandates loading `bootstrap-recovery.md`:

bootstrap_recovery_read_degraded = '**MANDATORY — READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` for degraded-prompt handling before treating absent routing keys as rebase failure.'
for needle in [
    'skills/implement/references/bootstrap-recovery.md',
    bootstrap_recovery_read_degraded,
    'DEGRADED_PROMPT_REQUIRED=true',
    'before treating absent routing keys as rebase failure',
]:
    if needle not in rebase_ref:
        checks.append(f'rebase-checkpoint-routing.md missing degraded bootstrap-recovery pointer {needle!r}')
forbid(rebase_ref, 'follow the degraded prompt path instead', 'rebase degraded carve-out must not retain stale inline-degraded prose')

Also add `require(skill, bootstrap_recovery_read_degraded, 'SKILL Rebase Checkpoint Macro bootstrap-recovery pointer')` so the SKILL macro edit is pinned.

**Mandatory forbid pins for relocated authority** (mirror `step18-cleanup` forbid block at 680–684):

bootstrap_recovery_ref = 'skills/implement/references/bootstrap-recovery.md'
self_review_ref = 'skills/implement/references/self-review.md'

forbid(skill, '**Degraded prompt handling.**', 'SKILL degraded-prompt body moved to bootstrap-recovery.md')
forbid(skill, 'Step 0 dirty-tree recovery gate:', 'SKILL dirty-tree gate moved to bootstrap-recovery.md')
forbid(skill, '.dirty-tree-prompted-step0-plan-materialize', 'SKILL dirty-tree prompt sentinel moved to bootstrap-recovery.md')
forbid(skill, 'Present the relayed degraded explanation block verbatim (from bootstrap stderr during Step 0)', 'SKILL verbose degraded-prompt table prose moved to bootstrap-recovery.md')
forbid(skill, 'Enter dirty-tree recovery. Preserve `$IMPLEMENT_TMPDIR`', 'SKILL verbose dirty-recovery table prose moved to bootstrap-recovery.md')
forbid(skill, 'python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review"', 'SKILL self-review telemetry fence moved to self-review.md')
forbid(skill, 'python/cli.py review-and-fix write-pre-self-review-snapshot', 'SKILL self-review snapshot fence moved to self-review.md')
forbid(skill, 'checks-commit-route --checks-site step5-self-review', 'SKILL self-review composite fence moved to self-review.md')
forbid(skill, 'python/cli.py review-and-fix write-self-review-tally', 'SKILL self-review tally fence moved to self-review.md')
forbid(skill, 'timeout: 14700000', 'SKILL self-review timeout pin moved to self-review.md')
forbid(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent', 'SKILL self-review invalid-envelope prose moved to self-review.md')

**Mandatory relocation-authority loop for `bootstrap-recovery.md`** (required, not optional; mirror `cleanup_ref` loop):

bootstrap_recovery_text = Path('skills/implement/references/bootstrap-recovery.md').read_text()
    '**Degraded prompt handling.**',
    'Step 0 dirty-tree recovery gate:',
    '.dirty-tree-prompted-step0-plan-materialize',
    'Present the relayed degraded explanation block verbatim',
    'AskUserQuestion',
    'Continue (reduced panel — unavailable tools dropped, no cross-tool or Claude padding)',
    'Abort',
    'PRESENCE_INPUT_EMPTY=true',
    'DEGRADED_HARD_FAIL=true',
    '.degraded-tools-gate-prompted',
    'STATUS=dirty-or-unknown',
    'STAGE=step0-plan-materialize',
    'RECOVERY_REQUIRED=true',
    'RECOVERY_REQUIRED=false',
    'STATUS=clean',
    'python/cli.py dirty-tree checkpoint',
    'Restore a clean tree and continue',
    'Cancel this implement run',
    'unset IMPLEMENT_BAIL_REASON',
    'IMPLEMENT_BAIL_REASON',
    'BRANCH_NAME',
    'BRANCH_ACTION',
    'PLAN_FILE',
    'Bootstrap edit gate (NEVER #21)',
    'step-0-bootstrap.sh" --mode resume',
    'LARCH_CLAUDE_PLUGIN_ROOT=',
    'Parse the resumed wrapper stdout before',
    if needle not in bootstrap_recovery_text:
        checks.append(f'bootstrap-recovery.md missing relocated authority {needle!r}')

**Mandatory relocation-authority loop for `self-review.md`** (required; mirror `cleanup_ref` loop):

self_review_text = Path('skills/implement/references/self-review.md').read_text()
    'python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true',
    'python/cli.py review-and-fix write-pre-self-review-snapshot',
    'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review',
    'python/cli.py review-and-fix write-self-review-tally',
    'timeout: 14700000',
    'Immediate-background required',
    'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18',
    'NEXT_ACTION=main-agent-edit',
    're-run this same composite launcher with identical argv',
    'parse exactly one line-anchored composite `NEXT_ACTION=` record',
    '$IMPLEMENT_TMPDIR/plan.txt',
    'git diff "$(git merge-base HEAD origin/main)"..HEAD',
    'execution-issues-tracking.md',
    'correctness — logic errors',
    'security — injection',
    'OOS triage policy',
    '### [Code Review] Self-review accepted',
    'rejected-findings.md',
    '> **Continue after child returns.**',
    'REDACTED_LOG_FILE',
    'NOT raw `LOG_FILE`',
    '$IMPLEMENT_TMPDIR/self-review-accepted.md',
    'checks-repair-loop.md',
    if needle not in self_review_text:
        checks.append(f'self-review.md missing relocated authority {needle!r}')

**Self-review SKILL residual-authority loop** (separate second loop; mirror `cleanup_ref` inverse checks):

skill_text = Path(skill).read_text()
    'write-pre-self-review-snapshot',
    'checks-commit-route --checks-site step5-self-review',
    'write-self-review-tally',
    '|| true',
    if needle in skill_text and 'self-review.md' not in skill_text.split(needle)[0][-200:]:
        # Only flag when needle appears outside the self-review stub pointer context
        if 'checks-commit-route --checks-site step5-self-review' in skill_text or 'write-pre-self-review-snapshot' in skill_text or 'write-self-review-tally' in skill_text:
            checks.append(f'SKILL.md still contains relocated self-review authority {needle!r}')

Simpler approach preferred: use explicit `forbid(skill, ...)` pins above for launcher strings and add one `forbid(skill, 'NEXT_ACTION=main-agent-edit', ...)` for the moved composite parse branch. Drop the heuristic split logic; rely on the forbid block plus the explicit residual loop:

    if needle in skill_text:
        checks.append(f'SKILL.md still contains relocated self-review authority {needle!r}')

Keep existing tests that still apply to inline routing stubs and `BOOTSTRAP_NEXT` malformed-envelope wording.

### UPDATED: python/test_review_and_fix.py

Retarget `test_self_review_prompt_reconciles_tally_counts_from_artifacts`:

- Read `skills/implement/references/self-review.md` instead of slicing `SKILL.md` between `### Self-review mode` and `### Scripted review loop`.
- Keep assertions: no `grep -c`, no `<ACCEPTED_COUNT>` / `<REJECTED_COUNT>`, no `--accepted`, presence of `$IMPLEMENT_TMPDIR/self-review-accepted.md`, `$IMPLEMENT_TMPDIR/rejected-findings.md`, and `write-self-review-tally --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$RUN_ID"`.

### UPDATED: python/test_implement_dispatch.py

In `test_composite_outer_timeout_budgets_match_leg_sums_and_fences`:

- Keep structure-harness assertion for the `step6` for-loop tuple literal.
- **Replace line 1742** (and related `skill` reads at 1743–1745 for self-review): assert the relocated structure-harness pins instead of the removed for-loop tuple. For example:
  - Assert `require_near('skills/implement/references/self-review.md'` (or equivalent path literal) appears in `scripts/test-implement-structure.sh`.
  - Assert `timeout: 14700000` and `checks-commit-route --checks-site step5-self-review` appear in `skills/implement/references/self-review.md`, **not** in `SKILL.md`.
- Do not leave assertions that require `"python/cli.py implement checks-commit-route --checks-site step5-self-review', 'timeout: 14700000'"` as a for-loop tuple in `test-implement-structure.sh` after relocation.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

Split scan into two explicit passes with fixed site counts:

1. **`SKILL.md` pass**: `EXPECTED_SITES=3` (Step 3, Step 5-resume handoff, Step 6 composite). Update header comment to document that Step 5 self-review moved to the reference.
2. **`self-review.md` pass**: second awk run against `skills/implement/references/self-review.md` with `EXPECTED_SITES=1` for the Step 5 self-review composite `checks-commit-route` site; assert the five-line opener contract (`> **Continue after child returns.**`, `REDACTED_LOG_FILE`, `NOT raw \`LOG_FILE\``, success-path continuation) immediately precedes the composite invocation.

Combined total must remain **4** sites (3 + 1). Do not rely on a SKILL-only count after relocation.

## Edge cases

- Do not make Step 0 stubs too small. Stubs must carry the **full** `**MANDATORY — READ ENTIRE FILE**: Read \`...\` completely.` literal, not bare filenames.
- Stub branch prose uses `completely.` with a single period, then `Then execute ...` — never `completely., then`.
- Use the two canonical bootstrap-recovery literals exactly as defined above; do not mix stub and degraded-carve-out forms on the wrong surface.
- Do not move the initial Step 0 bootstrap fence. It is always needed.
- Do not drop NEVER #21 from pre-`step2` paths. `bootstrap-recovery.md` must carry it.
- Do not let self-review proceed to Step 6 on composite-envelope ambiguity.
- Do not drop `NEXT_ACTION=main-agent-edit` re-entry; it is part of the moved composite contract.
- Do not drop `|| true` on the telemetry-mark fence.
- Do not leave duplicate authoritative bodies in `SKILL.md` after the split.
- Do not shorten the invalid-envelope fail-closed sentence when relocating to `self-review.md`.
- Avoid consecutive Bash-fence lint failures in new references.
- Do not wrap Consumer/Contract/When-to-load headers in markdown code fences in either new reference.
- Do not pass file-body strings to `require()` / `require_near()` in the structure harness.
- Relocating `step5-self-review` timeout pins to standalone `require_near` calls removes the for-loop tuple that `test_implement_dispatch.py` asserts today; update that test in the same change.
- Self-review `require_near` anchor must match stub capitalization (`When \`self_review=true\``), not lower-case `when`.
- `rebase_ref` must forbid stale "follow the degraded prompt path instead" once `bootstrap-recovery.md` owns degraded handling.
- Relocation loops must use valid `for needle in [...]:` syntax; never paste bare string lists without loop headers.

## Failure modes

- Filename-only mandatory-read stubs pass weak `require_near` checks while references never load at runtime.
- Inconsistent mandatory-read literals across stubs, macro line 158, `rebase-checkpoint-routing.md`, and harness pins let partial edits pass some checks while runtime disagrees.
- Bullet-prefixed or fenced Consumer/Contract/When-to-load headers fail `make test-references-headers`.
- Incorrect fence-count updates break `make test-implement-fence-shape` (`EXPECTED_NEW` must drop by exactly 4 for all four self-review fences; `EXPECTED_OLD` by 1).
- Enumerating only one departing fence in the plan causes implementers to decrement `EXPECTED_NEW` by 1 instead of 4 (`found new=27`).
- Stale `awk_count >= 3` in timing-rehydration harness fails `make test-implement-timing-rehydration` after resume fence relocation.
- Invalid Python in relocation loops (`Path(...).read_text()` followed by bare strings) breaks `make test-implement-structure` at parse time.
- Partial harness relocation leaves pytest or anti-halt harness failures even when references are correct.
- Missing mandatory `forbid(skill, ...)` pins allow duplicate authority in `SKILL.md` while references pass existence checks.
- Incomplete bootstrap-recovery relocation needles (missing `DEGRADED_PROMPT_REQUIRED=true`, `STAGE=step0-plan-materialize`, dirty-tree recheck, `RECOVERY_REQUIRED=false`, resumed-tail rebinding) let references ship without full dirty-recovery behavior.
- Incomplete self-review relocation needles (missing review rubric, `NEXT_ACTION=main-agent-edit`, or `|| true` telemetry) let references ship without full self-review contract.
- Truncated invalid-envelope needle (`without and skip to Step 18`) breaks structure harness after relocation.
- Anti-halt harness with `EXPECTED_SITES=4` on `SKILL.md` alone fails after self-review composite moves out.
- `test_composite_outer_timeout_budgets_match_leg_sums_and_fences` still asserting the removed for-loop tuple fails `make py-test`.
- Rebase Checkpoint Macro line 158 still pointing at deleted inline degraded prose leaves no authoritative procedure on absorbed `1.r` path.
- `rebase-checkpoint-routing.md` degraded carve-out without `bootstrap-recovery.md` pointer or with stale "follow the degraded prompt path instead" leaves a second gap on that entrypoint.
- `rebase_ref` loop without bootstrap-recovery needles lets partial reference edits pass `make test-implement-structure`.
- Moving dirty-recovery resume fence without plugin-root rehydration prelude breaks recovery when `CLAUDE_PLUGIN_ROOT` is absent.

## Testing strategy

Run focused checks:

```bash
make test-implement-structure
make test-implement-fence-shape
make test-implement-timing-rehydration
make test-references-headers
make lint-consecutive-bash
make test-implement-relevant-checks-anti-halt
make py-test  # covers test_review_and_fix.py and test_implement_dispatch.py

If a harness reports an exact missing string, update only the moved-string assertion or the new reference text. Do not broaden feature scope.

## Acceptance

Run focused checks:

```bash
make test-implement-structure
make test-implement-fence-shape
make test-implement-timing-rehydration
make test-references-headers
make lint-consecutive-bash
make test-implement-relevant-checks-anti-halt
make py-test  # covers test_review_and_fix.py and test_implement_dispatch.py

If a harness reports an exact missing string, update only the moved-string assertion or the new reference text. Do not broaden feature scope.

review_status: complete
rounds_completed: 5
diff_added: 385
diff_deleted: 115
mechanical_churn: false
diff_lines: 500

## Test plan
(no test plan section in plan-file)
