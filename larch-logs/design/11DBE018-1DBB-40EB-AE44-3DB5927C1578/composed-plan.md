## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Make a prose-only prompt refactor.
- Do not move runtime logic.
- Do not change review routing, sentinels, `AskUserQuestion`, or Python table rendering.
- Add one shared `/design` background-wait anchor file.
- Replace duplicated hot-path blocks with imperative read-and-apply call sites plus inline parameters.
- Shared files are not auto-loaded with `SKILL.md`; every hot path must carry an explicit load contract before the background fence.

## Files to modify/create

### NEW: skills/shared/design-background-wait.md

Create a shared anchor file for `/design` background wait prose.

Include these sections:

- `## Immediate-background wait rule`
  - Define the common rule with parameters:
    - `{breadcrumb}`: optional plain progress breadcrumb.
    - `{terminal_sentinel}`: `.completed/step-final-summary`, `.completed/step-3-terminal`, or `.completed/step-5c-terminal`.
    - `{confirmation_purpose}`: `completion` or `envelope durability` (controls premature-notification probe wording).
    - `{after_present}`: site-specific next action.
    - `{extra_guards}`: site-specific carve-outs.
  - Preserve the shared constraints:
    - end the turn after the background ack.
    - primary resume is `<task-notification>`.
    - one foreground probe only after premature non-empty task output; probe confirms `{confirmation_purpose}`.
    - empty task output means end the turn without probing.
    - ignore the launch ack's interim-output suggestion.
    - do not read tmpdir files, task outputs, stdout captures, result env files, or reviewer directories before notification or confirmed terminal sentinel.

- `## Step 3 task notification boundary`
  - Move the duplicated Step 3 `NEVER poll .step3-review-result.env with a sleep loop` prose here.
  - Preserve the consequences:
    - polling bypasses Claude Code task lifecycle.
    - it can leave the task registered as running.
    - it can block session exit until `TaskStop`.
  - Preserve the recovery and routing requirements:
    - probe `.completed/step-3-terminal`.
    - do not launch a background recovery waiter.
    - run the compact-table sequence when `step-3-terminal` is present.
    - route to Step 3b or later only when `.completed/step-3` is also present.
    - mid-loop bail-outs may have `step-3-terminal` without `step-3`.

- `## Step 3 post-notification sequence`
  - Move the authoritative compact-table sequence here.
  - Preserve the exact missing-table warning:
    - `**⚠ Reviewer status table omitted: pre-rendered table not found.**`
  - Preserve the Read-tool-only table emit contract.
  - Preserve the ordering:
    - completion gate.
    - print table once.
    - parse `.step3-review-result.env`.

### UPDATED: skills/design/SKILL.md

Replace the duplicated blocks with imperative read-and-apply directives to `${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md`. Do not use passive cross-references alone.

**Load contract pattern (all five sites):** immediately before applying the shared rule at each site, include:

`Read and apply ## <section-name> in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`

For Step 3 launch and Step 3 resume, also read `## Step 3 task notification boundary` before the background fence. Keep the compact-table high-level rule in Verbosity Control; do not duplicate the numbered sequence there.

Change these hot-path sites:

- **Verbosity Control — Post-notification for Step 3 waits**
  - Replace the full numbered sequence with:
    - `Read and apply ## Step 3 post-notification sequence in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`
  - Keep the compact-table high-level rule in place.

- **Final summary block**
  - Replace the `Immediate-background wait rule` paragraph with:
    - `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`
  - Pass these parameters inline after the read directive:
    - breadcrumb: `⏳ final-summary: writing final summary...`
    - terminal sentinel: `.completed/step-final-summary`
    - confirmation purpose: `completion`
    - after present: proceed to marker extraction or the Read fallback
    - extra guards: keep the `WAIT when absent` clause.

- **Step 3 first launch**
  - Apply these three read-and-apply replacements:
    1. `Read and apply ## Step 3 task notification boundary in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`
    2. `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.` plus the inline parameter block:
       - breadcrumb: none
       - terminal sentinel: `.completed/step-3-terminal`
       - confirmation purpose: `envelope durability`
       - after present: run the Step 3 post-notification sequence
       - extra guards: end the turn with no reviewer table after launch ack
    3. `Read and apply ## Step 3 post-notification sequence in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`
  - Remove the duplicated `After the completion gate, execute this authoritative sequence:` numbered list.

- **Step 3 resume fence**
  - Apply these three read-and-apply replacements (byte-identical literals to Step 3 first launch).
  - Keep the resume-specific `NEXT_ACTION` and wrapper-flag prose around the pointers.

- **Step 5c**
  - Replace the duplicated `Immediate-background wait rule` paragraph with:
    - `Read and apply ## Immediate-background wait rule in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md completely.`
  - Pass these parameters inline:
    - breadcrumb: `⏳ 5c: writing plan to GitHub...`
    - terminal sentinel: `.completed/step-5c-terminal`
    - confirmation purpose: `completion`
    - after present: parse `_publish_rc` and `.design-publish-result.env`
    - extra guards:
      - do not treat `.completed/step-5c` as completion.
      - do not parse `.design-publish-result.env` until `step-5c-terminal` is present.
      - do not wait for a second notification once the terminal sentinel is present.

Keep these local, not shared:

- The shell fences.
- The pre-wait one-line `Wait for <task-notification>` summaries.
- The Step 3 sentinel gate before Step 3b routing.
- The Step 5c validator and publish-tail exit-code contract.
- The Anti-patterns section, except only adjust cross-reference wording if needed for consistency.

**Dedup invariant:** after migration, `skills/design/SKILL.md` must contain zero copies of the extracted full boilerplate (no full `Immediate-background wait rule` paragraphs, no full Step 3 post-notification numbered sequence, no `NEVER poll \`.step3-review-result.env\` with a sleep loop.` literal). Only short read-and-apply pointers plus inline parameter blocks remain at the five sites.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

Update the harness so it enforces full dedup across all replacement sites, not only Step 3 launch/resume.

Add:

```bash
SHARED_DESIGN_WAIT_MD="$REPO_ROOT/skills/shared/design-background-wait.md"
SHARED_REF='skills/shared/design-background-wait.md'
LOAD_LITERAL='Read and apply ##'
CONFIRMATION_COMPLETION='confirmation purpose: completion'
```

Replace the `step3_count == 2` assertion with:

- `grep -cF -- "$STEP3_LITERAL" "$DESIGN_MD"` must be **0** (literal now lives only in the shared file).
- `grep -cF -- "$STEP3_LITERAL" "$SHARED_DESIGN_WAIT_MD"` must be **1**.

Assert the shared file exists and contains:

- `NEVER poll \`.step3-review-result.env\` with a sleep loop.`
- the background-recovery-waiter ban (`NEVER launch a background recovery waiter`).
- the compact-table missing warning (`**⚠ Reviewer status table omitted: pre-rendered table not found.**`).

Assert `skills/design/SKILL.md` references `$SHARED_REF` at **all five** replacement loci. Use anchored context greps (or equivalent) so each site is pinned independently:

1. Verbosity Control / `Post-notification for Step 3 waits`
2. `Final summary block`
3. Step 3 first launch (`design-step3-review.sh` without `--starting-round`)
4. Step 3 resume (`design-step3-review.sh --starting-round`)
5. Step 5c (`design-step5c.sh`)

At each of the five loci, also assert the imperative load contract via `$LOAD_LITERAL` (or equivalent per-site greps pinning the expected section name), not merely `$SHARED_REF` path presence. Per-site expected section names:

1. Verbosity Control: `Read and apply ## Step 3 post-notification sequence`
2. Final summary block: `Read and apply ## Immediate-background wait rule`
3. Step 3 first launch: all three directives
4. Step 3 resume: same three directives as first launch
5. Step 5c: `Read and apply ## Immediate-background wait rule`

At each Step 3 call site, assert the inline parameter block still names `.completed/step-3-terminal`.

At Final summary and Step 5c loci, assert the inline parameter block contains `$CONFIRMATION_COMPLETION` (`confirmation purpose: completion`).

Assert zero remaining extracted boilerplate in `skills/design/SKILL.md`:

- `grep -cF -- '**Immediate-background wait rule**:' "$DESIGN_MD"` must be **0**.
- `grep -cF -- '1. **Completion gate**:' "$DESIGN_MD"` must be **0**.

Keep the existing assertions for:

- `AGENTS.md`
- `skills/implement/SKILL.md`
- `skills/shared/orchestrator-never.md`
- `/design` Anti-patterns

### UPDATED: scripts/test-implement-anti-polling-rule.md

Update the harness documentation to reflect that the Step 3 anti-polling literal and post-notification sequence now live in `skills/shared/design-background-wait.md`. Document the five loci, the imperative `Read and apply ##` load contract assertion, and the zero-boilerplate count assertions.

## Edge cases

- Missing or symlinked `reviewer-status-table.txt` must still print the exact warning and continue.
- Step 3 launch must not print a reviewer table before completion.
- Step 3 launch and resume must still end the turn after the background ack.
- Final summary must keep the `WAIT when absent` recovery clause.
- Step 5c must still reject `.completed/step-5c` as terminal completion.
- Step 3 must still require `.completed/step-3` before Step 3b or later routing.
- Orchestrators that skip the shared file must be blocked by the imperative read-and-apply directive at each hot path, not by a passive pointer.

## Failure modes

- Passive cross-references without a read directive may cause the orchestrator to skip the shared file. Use imperative `Read and apply ## <section>` wording at every site.
- Partial migration leaving one full boilerplate copy in `SKILL.md` can pass a narrowed harness. Assert zero counts for extracted literals and paragraphs.
- Omitting `confirmation purpose` at Final summary or Step 5c leaves premature-notification probe wording ambiguous. Wire `confirmation purpose: completion` at both sites.
- Step 3 resume that omits the task notification boundary or post-notification read directives breaks parity with first launch.
- Updating only `SKILL.md` will break `scripts/test-implement-anti-polling-rule.sh`. Update the harness in the same change.
- Dropping the exact missing-table warning may regress Step 3 absent-table behavior.

## Testing strategy

Run:

- `bash scripts/test-implement-anti-polling-rule.sh`
- `make lint`

No Python-specific tests are required unless the implementation changes Python files.

## Acceptance

Plan approved at Gate C after 5-round review with 2 accepted findings incorporated.

review_status: complete
rounds_completed: 5
diff_added: 170
diff_deleted: 65
mechanical_churn: false
diff_lines: 235
