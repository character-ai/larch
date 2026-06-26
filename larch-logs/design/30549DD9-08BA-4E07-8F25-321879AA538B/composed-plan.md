## Plan

Make a Markdown-only lazy-load split.

Keep every-run routing and eligibility text inline. Move only branch-only procedure bodies into new references. Retarget the Step 8 CI-fix harness to the new reference. Add ordering pins and **section-scoped** body-specific forbid guards so partial moves cannot pass lint without colliding with every-run Exit 3 routing, seeder, bail-time, or gate/skip prose.

## Files to modify/create

### NEW: skills/implement/references/step18a5-filing.md

Create a focused Step 18a.5 filing procedure reference.

Include:

- `# /implement Step 18a.5 escalation-success filing`
- `**Consumer**: /implement Step 18a.5 after eligibility passes.`
- `**Contract**: Owns the eligible-path escalation-success artifact reads, root-cause artifact writes, Tier A/B filing, and sentinel write.`
- `**When to load**: MANDATORY only after Step 18a.5 skip predicates are false and escalation evidence exists.`

Move the full eligible-path body from `step18-cleanup.md` (lines 42–44), including:

- `If eligible, Main Claude reads` validated failure detail and state reads (`ship-pr-state.sh`, `finalize-state.sh`, `session-env.sh`, attempts, classification, ledger, fallback evidence, record-failure marker, execution issues, run-log pointer when present, and prompt-state values it used)
- root-cause artifact writing (`writes root-cause artifacts for why the script loop needed Main Claude`)
- prompt-state sensitive supplement (`writes the prompt-state sensitive supplement immediately before`)
- `compose-report --report-kind escalation-success`
- Tier A `/larch:issue --input-file ... --no-dedup` after full-output secret redaction and exact-signature dedup
- `Tier A files through`
- `after full-output secret redaction and exact-signature dedup`
- Tier B `stall-recovery-chat-print.md` filing (`Tier B files or comments upstream after composing`)
- `after composing \`stall-recovery-chat-print.md\``
- atomic `stall-recovery-escalation-success.env` write (the write-after-filed/commented/fallback sentence: `Write \`stall-recovery-escalation-success.env\` atomically after filed, commented, fallback-printed, dry-run, or operator-action skip result`)

Do not move skip predicates, escalation evidence definition, or generic Tool Failures exclusion.

### NEW: skills/implement/references/ship-pr-oos-checkpoint-router.md

Create a focused OOS checkpoint router reference.

- `# Ship PR OOS checkpoint router`
- `**Consumer**: /implement Step 8+ after NEXT_ACTION=oos-pipeline and after the OOS pipeline body runs.`
- `**Contract**: Owns the Step 8+ OOS checkpoint wrapper routing semantics and success bookkeeping contract.`
- `**When to load**: MANDATORY only on the NEXT_ACTION=oos-pipeline branch before invoking step-8-oos-checkpoint.sh.`

Move the full current `## OOS checkpoint router` body from `ship-pr-exit-matrix.md` (lines 90–100).

Preserve all existing semantics:

- `python/cli.py implement step-8-oos-checkpoint` opener
- `runs \`oos disposition-checkpoint\`, owns success bookkeeping, and emits exactly one \`NEXT_ACTION=\` when routing succeeds`
- `Its process rc is 0 whenever \`NEXT_ACTION\` is emitted`
- `returns non-zero only when no \`NEXT_ACTION\` is emitted`
- disposition rc bookkeeping
- one `NEXT_ACTION=` emission contract
- `never emits \`OOS_CHECKPOINT_RC=0\` with \`NEXT_ACTION=stall\``
- `On disposition rc 0 and successful bookkeeping`
- rc 0 success bookkeeping (`writes run-scoped \`run-statistics.md\``, `steps_ran.step9a1=true`, `OOS_PENDING=false`, `NEXT_ACTION=reship`)
- filed-count provenance (`Filed count comes from \`larch-logs/implement/&lt;RUN_ID&gt;/oos-issues.ndjson\``)
- `with fallback counts only when ndjson is absent`
- stats, manifest, and state-patch failure behavior (`best-effort stamps \`steps_ran.step9a1=false\``, `ship._patch_ship_state_keys`, `leaves \`OOS_PENDING\` unchanged`, `writes no stats, and clears no state`)
- non-zero disposition routing (`On disposition rc 1, rc 2, 126, 127, or other non-zero rc`)
- stderr preservation note (`oos-disposition-checkpoint.stderr.log`)
- `The checkpoint wrapper preserves non-empty child-written`
- child-stdout forwarding note (`Child stdout is not forwarded on success`)
- OOS-checkpoint `stall` distinctness, including the exact sentence: `OOS-checkpoint \`stall\` is distinct from post-driver \`stall\``

### NEW: skills/implement/references/ship-pr-ci-fix.md

Create a focused autonomous CI-fix reference.

- `# Ship PR autonomous CI-fix`
- `**Consumer**: /implement Step 8+ on NEXT_ACTION=ci-fix.`
- `**Contract**: Owns the main-agent CI-fix attempt guard, CI log capture, minimal repair, checks, commit, refresh, reassessment, push, and ship re-entry procedure.`
- `**When to load**: MANDATORY only on NEXT_ACTION=ci-fix after fork and repo-unavailable skips are ruled out or before applying that branch's autonomous repair body.`

Move the current `## autonomous main-agent CI-fix sub-procedure` body from `ship-pr-exit-matrix.md` (lines 102–117), including the opener paragraph that begins `This reference retains the Python driver non-zero routing contract...`.

Keep the exact covered reasons:

- `first-fixer-non-health`
- `ship-pr-internal-lint-fix`
- `ci-local-unfixable:*`
- exact `local-unfixable`
- `ci-fix-exhausted` remains operator-bail

Retain the numbered steps 1–12 (two-space list markers `  1.` through `  12.`), handoff read (`.ship-route-exit-handoff.env`, `larch_io.read_kvs` where applicable in procedure steps), `stall-recovery record-escalation` when `ledger_ready=true`, `main-agent-ci-fix-$FAILED_RUN_ID.attempted`, `main-agent-ci-fix.count`, `gh run-logs`, `python/cli.py" push branch`, `Make the minimal repo edit`, `git add -- <paths>`, `Fix CI failure (main-agent)`, `run-log refresh`, architectural-guidelines Phase A rerun, and `re-invoke \`step-8-ship.sh\``.

### UPDATED: skills/implement/references/step18-cleanup.md

Keep the Step 18a.5 gate text inline:

- timing: after active stall gate and before Step 18b
- ordinary success and `clear-stall` guidance
- all skip predicates (including `stall-recovery-escalation-success.env` exists)
- escalation evidence definition
- generic Tool Failures exclusion
- missing attempts history default

Remove the full eligible filing paragraph (lines 42–44). Replace with a mandatory-read pointer to `step18a5-filing.md` that says to load the new file only after all skip predicates are false and evidence exists.

Gate-only `step18-cleanup.md` must not retain any eligible-body phrases.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

Keep every-run routing text inline:

- durable handoff sidecars
- `ship route-exit` contract
- required JSON fields
- Exit 3 reason routing (including `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, exact `local-unfixable`, and `ledger_ready=true` in handoff prose)
- handoff env shape
- transient retry authority
- `## Branch semantics`
- initial seeder contract (including `OOS_PENDING=false`)
- long-running re-entry (including `reship` branch bullet)
- OOS cap contract
- bail-time `steps_ran` invariant (including `steps_ran.step9a1=true` / `steps_ran.step9a1=false`)
- execution-issues checkpoint and metadata refresh
- active driver ownership notes
- the separate pre-driver vs OOS-checkpoint discriminator sentences in `## Branch semantics` (lines 52–53: pre-driver `NEXT_ACTION=stall` and OOS-checkpoint `NEXT_ACTION=stall` remain separate)

Replace branch-only bodies with pointers:

- In `oos-pipeline`, replace "run the OOS checkpoint router" with **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely after the OOS pipeline and before the checkpoint wrapper.
- In `ci-fix`, reduce the branch bullet to routing and fork/repo-unavailable skip-to-operator-bail only. Remove the inline autonomous repair summary (`read .ship-route-exit-handoff.env`, `larch_io.read_kvs`, `ledger_ready`, `stall-recovery record-escalation`, `Run autonomous repair`, `FAILED_RUN_ID`, `DETAIL_FILE`, `local-unfixable` repair prose). Then add **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-ci-fix.md` completely when not skipped to operator-bail and before autonomous repair / `step-8-ship.sh` re-entry.
- Remove the old `## OOS checkpoint router` section body entirely.
- Remove the old `## autonomous main-agent CI-fix sub-procedure` section body (including the `Python driver non-zero routing` opener paragraph).

Do not add a second branch table.

### UPDATED: skills/implement/SKILL.md

Update Step 8+ branch prose.

- Keep the mandatory read of `ship-pr-exit-matrix.md` at Step 8+ entry.
- In the `oos-pipeline` branch, add **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely after the OOS pipeline and before the OOS checkpoint fence.
- In the `ci-fix` branch, keep fork/repo-unavailable skip-to-operator-bail inline, then replace the `ship-pr-exit-matrix.md` sub-procedure pointer with **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-ci-fix.md` completely when not skipped to operator-bail and before autonomous repair / `step-8-ship.sh` re-entry. Do not anchor `ci-fix` ordering on `step-8-oos-checkpoint.sh` (that fence is `oos-pipeline` only).
- Retire legacy every-run CI-fix authority: remove `run the autonomous CI-fix sub-procedure from \`ship-pr-exit-matrix.md\`` from the `**ci-fix**` skeleton bullet.
- Keep the branch skeleton inline.
- Keep the checkpoint wrapper fence unchanged.

Update Step 18 prose.

- Keep the mandatory read of `step18-cleanup.md` at Step 18 entry.
- In Step 18a.5, replace `Follow step18-cleanup.md for the escalation-success report procedure` with gate-only wording: skip predicates and evidence live in `step18-cleanup.md`; after the inline skip summary, add **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18a5-filing.md` completely only when eligible.
- Keep the `#### Step 18a.5 — Escalation-success report gate` header, harness-pinned routing stubs, and Step 18b finalize fence unchanged.

### UPDATED: scripts/test-implement-structure.sh

Extend the reference harness.

- Add `step18a5-filing.md`, `ship-pr-oos-checkpoint-router.md`, and `ship-pr-ci-fix.md` to the mandatory reference/header check list.
- Require `SKILL.md` pointers for each new reference.

**Step 18a.5 split enforcement**

- Move Step 18a.5 eligible-body needles from `step18-cleanup.md` to `step18a5-filing.md`, including:
  - `If eligible, Main Claude reads`
  - `validated failure detail`
  - `attempts, classification, ledger`
  - `fallback evidence`
  - `execution issues`
  - `run-log pointer when present`
  - `prompt-state values it used`
  - `writes root-cause artifacts for why the script loop needed Main Claude`
  - `prompt-state sensitive supplement`
  - `compose-report --report-kind escalation-success`
  - `Tier A files through`
  - `after full-output secret redaction and exact-signature dedup`
  - Tier A `/larch:issue --input-file`
  - Tier B `stall-recovery-chat-print.md`
  - `Tier B files or comments upstream`
  - `after composing \`stall-recovery-chat-print.md\``
  - atomic write sentence for `stall-recovery-escalation-success.env`
- Add matching `require(step18a5-filing.md, ...)` for every moved eligible-body needle above (mirror the OOS-router child `require` block).
- Keep skip predicate and evidence needles required in `step18-cleanup.md`, including bare `stall-recovery-escalation-success.env` in the skip list.
- Remove `compose-report --report-kind escalation-success` from the `step18-cleanup.md` stay-inline `require` loop (child-only `require`).
- Add **filing-body-only** `forbid(step18-cleanup.md, ...)` for distinctive eligible-path sentences and phrases. Do **not** globally forbid substrings that also appear in every-run gate or skip prose (`ship-pr-state.sh`, `finalize-state.sh`, `session-env.sh`, bare `record-failure marker`). Scope forbids to filing-only fragments such as:
  - `/larch:issue --input-file`
  - `Write \`stall-recovery-escalation-success.env\` atomically after filed, commented, fallback-printed, dry-run, or operator-action skip result`

**OOS router split enforcement**

- Move OOS checkpoint router needles from `ship-pr-exit-matrix.md` to `ship-pr-oos-checkpoint-router.md`.
- Remove `OOS-checkpoint \`stall\` is distinct from post-driver \`stall\`` from the `exit_matrix` stay-inline `require` loop; require it only in `ship-pr-oos-checkpoint-router.md`.
- Keep the different `## Branch semantics` pre-driver/OOS-checkpoint discriminator sentences required inline in `ship-pr-exit-matrix.md`.
- Keep every-run tokens required inline where they belong outside the router section: `OOS_PENDING=false` (seeder), `steps_ran.step9a1` (bail-time invariant), `NEXT_ACTION=reship` (reship bullet). Do **not** add file-wide `forbid` for those tokens.
- Add `forbid(ship-pr-exit-matrix.md, '## OOS checkpoint router', ...)`.
- Add `forbid(ship-pr-exit-matrix.md, 'run the OOS checkpoint router', ...)`.
- Add **router-body-only** `forbid(ship-pr-exit-matrix.md, ...)` for distinctive moved OOS router prose, including at minimum:
  - `python/cli.py implement step-8-oos-checkpoint`
  - `runs \`oos disposition-checkpoint\``
  - `emits exactly one \`NEXT_ACTION=\``
  - `Its process rc is 0 whenever`
  - `returns non-zero only when no \`NEXT_ACTION\` is emitted`
  - `never emits \`OOS_CHECKPOINT_RC=0\` with \`NEXT_ACTION=stall\``
  - `On disposition rc 0 and successful bookkeeping`
  - `writes run-scoped \`run-statistics.md\``
  - `ship._patch_ship_state_keys`
  - `with fallback counts only when ndjson is absent`
  - `leaves \`OOS_PENDING\` unchanged`
  - `writes no stats, and clears no state`
  - `On disposition rc 1, rc 2, 126, 127, or other non-zero rc`
  - `OOS_CHECKPOINT_RC=0`
  - `oos-disposition-checkpoint.stderr.log`
  - `The checkpoint wrapper preserves non-empty child-written`
  - `Child stdout is not forwarded on success`
  - `OOS-checkpoint \`stall\` is distinct from post-driver \`stall\``
- Add matching `require` needles in `ship-pr-oos-checkpoint-router.md` for all moved body tokens.

**CI-fix parent forbid (structure harness only)**

- Do **not** move autonomous CI-fix body `require` needles here; those stay in `test-implement-step8-exit3-first-fixer.sh`.
- Do **not** add file-wide `forbid` for Exit 3 routing tokens that must stay inline: `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable`, `local-unfixable`, or `ledger_ready=true`.
- Add `forbid(ship-pr-exit-matrix.md, '## autonomous main-agent CI-fix sub-procedure', ...)`.
- Add `forbid(ship-pr-exit-matrix.md, 'Run autonomous repair', ...)`.
- Add **sub-procedure-body-only** `forbid(ship-pr-exit-matrix.md, ...)` for distinctive moved CI-fix prose:
  - `Python driver non-zero routing`
  - `read .ship-route-exit-handoff.env`
  - `larch_io.read_kvs`
  - `stall-recovery record-escalation`
  - `main-agent-ci-fix-$FAILED_RUN_ID.attempted`
  - `main-agent-ci-fix.count`
  - `gh run-logs`
  - `python/cli.py" push branch`
  - `python/cli.py checks run-relevant --site step8-main-agent-fix`
  - `Fix CI failure (main-agent)`
  - `Make the minimal repo edit`
  - `git add -- <paths>`
  - `run-log refresh`
  - `architectural-guidelines Phase A`
  - two-space numbered-step markers `  1.` through `  12.` (also forbid one-space ` 1.` … ` 12.` as a secondary guard)
  - `re-invoke \`step-8-ship.sh\``

**Legacy authority retirement (structure harness)**

- Add `forbid(SKILL.md, 'run the autonomous CI-fix sub-procedure from \`ship-pr-exit-matrix.md\`', ...)`.
- Add `forbid(SKILL.md, 'autonomous CI-fix sub-procedure from \`ship-pr-exit-matrix.md\`', ...)` as a secondary substring guard if wording varies slightly.
- Add `forbid(SKILL.md, 'Follow \`step18-cleanup.md\` for the escalation-success report procedure', ...)`.

**Branch bullet and ordering pins**

- Require `ship-pr-exit-matrix.md` `## Branch semantics` `oos-pipeline` and `ci-fix` bullets name `ship-pr-oos-checkpoint-router.md` and `ship-pr-ci-fix.md` instead of generic "run the OOS checkpoint router" or inline repair-summary wording.
- Add `require(ship-pr-exit-matrix.md, ship-pr-oos-checkpoint-router.md)` and `require(ship-pr-exit-matrix.md, ship-pr-ci-fix.md)` for branch bullets.
- Add `require(step18-cleanup.md, step18a5-filing.md)` pointer presence.
- **oos-pipeline ordering** (do not anchor on the distant `**oos-pipeline**` skeleton bullet alone):
  - `require_near(SKILL.md, 'oos-pipeline.md', 'ship-pr-oos-checkpoint-router.md', 'oos router mandatory read after OOS pipeline')`
  - `require_near(SKILL.md, 'ship-pr-oos-checkpoint-router.md', 'step-8-oos-checkpoint.sh', 'oos router mandatory read before checkpoint fence')`
  - Optionally `require_near(SKILL.md, '**OOS checkpoint fence.**', 'ship-pr-oos-checkpoint-router.md', 'oos router read before checkpoint fence header')` as a secondary guard.
- **ci-fix ordering** (use ci-fix-local sentinels; do not false-pass via the oos-pipeline `MANDATORY — READ ENTIRE FILE` line):
  - Extract a `ci_fix_slice` bounded to the `**ci-fix**` branch bullet paragraph in `SKILL.md` and `ship-pr-exit-matrix.md` (from the `**ci-fix**` line through the next sibling branch bullet or blank line).
  - `require(ci_fix_slice, 'ship-pr-ci-fix.md', 'ci-fix branch names child reference')`
  - `require(ci_fix_slice, 'MANDATORY — READ ENTIRE FILE', 'ci-fix branch carries mandatory-read marker')`
  - `require_near(SKILL.md, 'ship-pr-ci-fix.md', '**operator-bail**', 'ci-fix mandatory read precedes operator-bail skeleton')` only when that ordering remains in SKILL after the split.
  - `require_near(ship-pr-exit-matrix.md, 'FORKED_TARGET=true', 'ship-pr-ci-fix.md', 'ci-fix mandatory read after fork skip inline text')` scoped within the matrix `ci_fix_slice`.
- `require_near(SKILL.md, 'step18a5-filing.md', 'step-18.sh --phase finalize', 'Step 18a.5 filing read before finalize fence')` after Step 18a.5 skip summary when eligible path is wired.
- Keep existing checks that `ship-pr-exit-matrix.md` retains branch semantics and does not add `## Post-driver branch table`.

### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh

Retarget CI-fix harness coverage to the new reference.

- Read autonomous CI-fix body from `skills/implement/references/ship-pr-ci-fix.md` instead of `ship-pr-exit-matrix.md` for all body needles.
- Keep routing-token checks on `SKILL.md` and/or `ship-pr-exit-matrix.md` only where they remain after the split: `step-8-ship.sh` invocation and Python ship wrapper prose stay on `SKILL.md`.
- Retarget body needles (`first-fixer-non-health`, `ci-fix-exhausted`, `# Ship PR autonomous CI-fix` or legacy heading equivalent, `.ship-route-exit-handoff.env`, `ledger_ready=true`, `stall-recovery record-escalation`, `main-agent-ci-fix.count`, `gh run-logs`, `python/cli.py" push branch`, two-space numbered steps `  1.` through `  12.`, `Python driver non-zero routing`, `Make the minimal repo edit`, `git add --`, `run-log refresh`, `re-invoke \`step-8-ship.sh\``) to `ship-pr-ci-fix.md`.
- Add `require(skill, 'skills/implement/references/ship-pr-ci-fix.md', ...)` for the `ci-fix` branch pointer.
- Add `forbid(ship-pr-exit-matrix.md, 'Python driver non-zero routing', ...)`.
- Add `forbid(ship-pr-exit-matrix.md, 'read .ship-route-exit-handoff.env', ...)` and `forbid(ship-pr-exit-matrix.md, 'larch_io.read_kvs', ...)` so stripped branch-bullet handoff prose cannot remain inline.
- Add `require_near(ship-pr-ci-fix.md, 'MANDATORY — READ ENTIRE FILE', 're-invoke \`step-8-ship.sh\`', 'ci-fix procedure read before ship re-entry')` in the child reference only (not as a SKILL upper bound).

### UPDATED: scripts/test-implement-step8-exit3-first-fixer.md

Update the contract note to state the autonomous CI-fix sub-procedure lives in `skills/implement/references/ship-pr-ci-fix.md`, including the `Python driver non-zero routing` opener; `ship-pr-exit-matrix.md` keeps routing and skip-to-operator-bail only on the `ci-fix` bullet.

## Edge cases

- **Eligibility drift**: Do not move Step 18a.5 skip predicates into the conditional file. They must stay loaded before deciding whether to load `step18a5-filing.md`.
- **Skip-predicate vs body forbid**: Bare `stall-recovery-escalation-sentinel.env` stays in `step18-cleanup.md` skip predicates; structure `forbid` targets only filing-body phrases, not gate-layer state-file names or bare `record-failure marker` in the escalation-evidence list.
- **Route drift**: Do not move Exit 3 reason routing or the branch list out of `ship-pr-exit-matrix.md`. Do not `forbid` Exit 3 routing tokens or `ledger_ready=true` file-wide in the matrix.
- **OOS stall semantics**: Keep the `## Branch semantics` pre-driver vs OOS-checkpoint discriminator inline; move only the router-body `OOS-checkpoint \`stall\` is distinct from post-driver \`stall\`` sentence with the router procedure. Do not `forbid` `OOS_PENDING=false`, `steps_ran.step9a1`, or `NEXT_ACTION=reship` file-wide; those belong in seeder, bail-time, and reship bullets.
- **Fork or repo-unavailable CI-fix**: Keep the skip-to-operator-bail rule visible inline in `ship-pr-exit-matrix.md` and `SKILL.md` before the mandatory read of `ship-pr-ci-fix.md`.
- **ci-fix vs oos-pipeline anchors**: `step-8-oos-checkpoint.sh` is `oos-pipeline` only; `ci-fix` ordering pins must use `ci_fix_slice`, fork skip text, and local mandatory-read markers — never distant `step-8-ship.sh` on the `reship` bullet or the oos-pipeline mandatory-read line as ci-fix proof.
- **ci-fix bullet duplication**: After adding the mandatory-read pointer, strip the autonomous repair summary from the `ci-fix` branch bullet so the every-run matrix does not retain duplicate CI-fix authority; enforce with sub-procedure-body `forbid` plus `forbid(SKILL.md, ...)` for the legacy matrix sub-procedure pointer.
- **require_near false-pass**: Do not use file-global first `MANDATORY — READ ENTIRE FILE` or ±900-char windows around distant branch bullets. Anchor oos-pipeline ordering on `oos-pipeline.md` / checkpoint-fence proximity; anchor ci-fix ordering on `ci_fix_slice`.
- **Harness split**: `test-implement-structure.sh` owns lazy-load ordering, header loop, Step 18a.5 child `require` + filing-body `forbid`, OOS-router parent forbids (router-only), CI-fix parent forbids (sub-procedure-only), and legacy-authority retirement; `test-implement-step8-exit3-first-fixer.sh` owns CI-fix body `require` needles exclusively.
- **SKILL.md stale 18a.5 pointer**: Replace the old "full procedure in step18-cleanup.md" line and add `forbid(SKILL.md, ...)` so eligible paths cannot skip `step18a5-filing.md`.
- **Numbered-list spacing**: CI-fix parent forbids must match live two-space `  {n}.` markers; add one-space secondary guards only as backup.

## Failure modes

- A branch pointer may load too late. Guard with oos-pipeline pins anchored on `oos-pipeline.md` → router read → `step-8-oos-checkpoint.sh`, and ci-fix pins on `ci_fix_slice` plus child-local `require_near`.
- A moved body may remain duplicated. Guard with heading `forbid` checks plus expanded **scoped** body-token `forbid` checks in parent files for OOS router, CI-fix sub-procedure, and Step 18a.5 filing bodies.
- Partial OOS or 18a.5 moves may pass heading retirement but leave body authority inline. Extend parent `forbid` lists to full router/filing sentence coverage; add child `require` loops mirroring every moved needle.
- Partial CI-fix moves may retire the heading while leaving handoff read, record-escalation, numbered steps, or repair prose inline. Extend CI-fix parent forbids to minimal-edit / git-add / commit / run-log-refresh sentences and two-space numbered steps; keep Exit 3 routing tokens out of parent forbids.
- **Forbid/routing collision**: File-wide substring forbids for `ship-pr-state.sh`, `ledger_ready=true`, `OOS_PENDING=false`, or `NEXT_ACTION=reship` force implementers to delete required every-run prose. Scope all parent forbids to removed subsection bodies only.
- CI-fix harness drift may pass structure lint but fail `make test-implement-step8-exit3-first-fixer`. Retarget the dedicated harness body reads and the `Python driver non-zero routing` pin to `ship-pr-ci-fix.md` in the same change.
- Mis-anchoring `ci-fix` mandatory read on `step-8-oos-checkpoint.sh`, distant `step-8-ship.sh`, or oos-pipeline mandatory-read markers may false-pass while mis-wiring branch semantics. Use `ci_fix_slice` and child-reference-local ordering only.
- Legacy every-run CI-fix or OOS router authority may survive alongside new pointers. Add explicit `forbid(SKILL.md, ...)`, `forbid(ship-pr-exit-matrix.md, 'run the OOS checkpoint router', ...)`, and matrix branch-bullet cleanup.
- A new file may miss reference headers or child `require` needles. Add files to the header loop and mirror OOS-style child `require` for Step 18a.5.
- Forbidding bare `stall-recovery-escalation-success.env` or gate-layer state filenames in `step18-cleanup.md` breaks skip predicates or stall gate text. Use filing-body-only forbid needles instead.

## Testing strategy

Run:

- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`
- `make test-implement-structure`
- `make test-implement-step8-exit3-first-fixer`
- `make lint`

No Python tests are required because the approved scope is Markdown-only and harness-only.

## Acceptance

Run:

- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`
- `make test-implement-structure`
- `make test-implement-step8-exit3-first-fixer`
- `make lint`

No Python tests are required because the approved scope is Markdown-only and harness-only.

review_status: complete
rounds_completed: 5
diff_added: 245
diff_deleted: 68
mechanical_churn: false
diff_lines: 313
