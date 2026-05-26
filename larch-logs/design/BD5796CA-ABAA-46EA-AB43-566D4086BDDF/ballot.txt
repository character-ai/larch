### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:18-82
- **Concern**: Plan says wire test-design-reentry-guard into lint dependencies but lint only runs the test-harnesses aggregate. Scenario: Adding a standalone recipe without appending it to a test-harnesses-N prerequisite leaves make lint and CI harness shards blind to the new harness
- **Proposed resolution**: Register test-design-reentry-guard on a test-harnesses-N line (test-harnesses-1 or test-harnesses-14 beside test-design-structure), add .PHONY, and use harness-timer.sh like other harness targets

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:971-975
- **Concern**: Marker write is planned after the [DESIGNED] rename even though it is supposed to cover rename failure. Scenario: If tracking-issue-write.sh rename exits non-zero after plan publish, the Bash step can stop before item 11 and no session-cache marker is created; if marker write fails after item 9, the warning is appended after final-summary rendering and can be deleted by Step 6 cleanup
- **Proposed resolution**: Move marker write to immediately after successful design-log-publish and before post-publish final-summary and rename; capture marker failures there, and keep rename failure best-effort/logged so it cannot prevent marker creation

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: Makefile:18; Makefile:43-82; docs/linting.md:40-42
- **Concern**: The plan wires the new harness directly into lint instead of the sharded test-harnesses inventory. Scenario: scripts/test-harness-shards-coverage.sh treats every test-* recipe target as required shard inventory; a new test-design-reentry-guard target not assigned to exactly one test-harnesses-N shard will make make lint fail
- **Proposed resolution**: Define the target, add it to .PHONY, and place it in exactly one test-harnesses-N prerequisite list rather than adding it as a direct lint dependency

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: AGENTS.md:51-53; scripts/lib-design-reentry-guard.sh (planned)
- **Concern**: Marker path is keyed only by issue number and PPID, not repository identity. Scenario: A same Claude process can work across repositories while the invariant is only per repo; issue #2935 in another repo within the TTL can be falsely refused by a marker from this repo
- **Proposed resolution**: Include a stable repo discriminator in the marker grammar, such as resolved owner/repo or a sanitized/hash repo root, and add same-PPID same-issue different-repo coverage to the harness

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-external-launcher-common.sh:96-106; skills/implement/scripts/lib-resolve-implement-tmpdir.sh:73-83; scripts/lib-design-reentry-guard.sh (planned)
- **Concern**: The stat portability contract does not require the existing GNU-first numeric-guard pattern. Scenario: On Linux, BSD-form stat -f %m can succeed with filesystem text rather than an epoch if tried first, which can break age arithmetic under set -u or classify markers incorrectly
- **Proposed resolution**: Specify and implement a small mtime helper that tries stat -c %Y first, falls back to stat -f %m, and accepts only ^[0-9]+$ before computing age

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:23,82,975
- **Concern**: Step 5c item 11 ties marker write to the same PUBLISH_OK/rename gate as item 10. Scenario: When plan-block-write succeeds but PUBLISH_OK=false (item 8 continues) or rename is skipped, no marker is written; a same-session re-fire sees no [DESIGNED] title and passes sub-step 2.6 — the gap the plan cites is only partially closed
- **Proposed resolution**: Gate design_reentry_marker_write on Step 5c step-4 success (PLAN_WRITE_OK=true) only; keep rename/publish semantics separate

### FINDING_7:
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18, Makefile:43-82, scripts/test-harness-shards-coverage.sh:213-272
- **Concern**: New harness is planned as a direct lint dependency instead of a shard member. Scenario: The current lint target delegates harnesses through test-harnesses, and the shard coverage guard requires every test-* recipe to be in exactly one test-harnesses-N shard and .PHONY. Adding only test-design-reentry-guard to lint either skips the harness in CI split runs or trips the partition invariant.
- **Proposed resolution**: Add test-design-reentry-guard to .PHONY, define the recipe with the existing harness-timer pattern, and place it in one test-harnesses-N shard; keep lint depending on test-harnesses rather than individual test targets.

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: agent-lint.toml:52-67, agent-lint.toml:282-288, agent-lint.toml:883
- **Concern**: New Makefile-only test harness is missing the dead-script exclusion pattern. Scenario: agent-lint is run by make lint and its documented dead-script rule does not follow Makefile targets. Existing Makefile-only harnesses such as scripts/test-design-structure.sh are excluded explicitly, so scripts/test-design-reentry-guard.sh and its sibling md are likely to fail agent-lint despite being wired through Makefile.
- **Proposed resolution**: Add scripts/test-design-reentry-guard.sh and scripts/test-design-reentry-guard.md to agent-lint.toml exclude with a short comment near scripts/test-design-structure.sh, or otherwise add a structural reference agent-lint can actually resolve.

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-reentry-guard.sh (proposed), scripts/test-design-reentry-guard.sh (proposed)
- **Concern**: Cross-platform stat selection is underspecified for GNU stat. Scenario: GNU stat accepts stat -f %m but returns filesystem mount data, not mtime, so a naive macOS-first fallback will not fall through to stat -c %Y. Fresh Linux markers can be misread as invalid and the guard silently admits the exact re-entry it is meant to block.
- **Proposed resolution**: Specify platform detection or numeric validation before accepting stat output, prefer stat -c %Y on GNU/Linux, and add a harness case that exercises both stat dialect paths or stubs stat to catch macOS-first fallback bugs.

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-design-reentry-guard.sh (proposed marker path), scripts/session-setup.sh:230-267
- **Concern**: Marker key omits repository identity. Scenario: The planned design-completed-<issue>-<ppid> path collides for sequential same-session work in two repositories with the same issue number within the TTL. The plan cites the single-runner invariant, but that invariant is per repository and does not prevent sequential same-PPID multi-repo designs.
- **Proposed resolution**: Include a sanitized repo key in the marker path, using resolved owner/repo when available or the same clone-tag style session-setup already uses, and cover same issue plus different repo in the harness.

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18-43
- **Concern**: Plan wires test-design-reentry-guard only into a new target and says add it to lint dependencies but lint runs test-harnesses not per-target lists. Scenario: CI never executes the new harness unless the target is added to a test-harnesses-N shard
- **Proposed resolution**: make test-design-reentry-guard use harness-timer.sh like peer targets and register it on test-harnesses-14 or test-harnesses-20 next to test-design-structure test-plan-block

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:970-975
- **Concern**: Marker write is sequenced after the [DESIGNED] rename even though the plan says the guard fills the rename-failed gap. Scenario: If tracking-issue-write.sh rename exits non-zero after plan-block-write and design-log-publish succeeded, the marker write may never run, so the exact spurious re-entry case described in the plan is still admitted
- **Proposed resolution**: Write the marker immediately after successful publish and before the rename, or wrap the rename in set +e and always attempt marker creation when plan write succeeded and publish is ok; log marker and rename failures independently

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18,43-82
- **Concern**: Adding the new test directly to lint misreads the current harness topology. Scenario: make lint delegates to test-harnesses, and CI can run test-harnesses separately; a new test recipe not added to a test-harnesses-N shard will be caught by scripts/test-harness-shards-coverage.sh or missed by split CI
- **Proposed resolution**: Add test-design-reentry-guard to .PHONY, add a harness-timer recipe near the other test-design targets, and place it in one test-harnesses-N shard rather than wiring it as a direct lint prerequisite

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:49-50,114
- **Concern**: Marker identity is repo-agnostic while issue numbers are only repo-scoped. Scenario: A same Claude session can legitimately operate on another checkout or fork with the same issue number, but design-completed-<issue>-<ppid> would refuse it; the plan dismisses this by treating the single-runner invariant as global when it is per repo
- **Proposed resolution**: Include a repo/checkout discriminator in the marker key, preferably a sanitized resolve-repo.sh owner/repo value after issue binding, or fall back to the clone tag pattern used by session-setup.sh

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18,43-82
- **Concern**: Plan says add test-design-reentry-guard to lint: dependencies alongside test-design-structure, but lint: only lists test-harnesses (not individual harnesses) and test-design-structure lives on test-harnesses-14. Scenario: Implementer adds a standalone recipe or orphans the target; make test-harness-shards-coverage fails (missing shard assignment) and CI never runs the harness
- **Proposed resolution**: Add test-design-reentry-guard to exactly one test-harnesses-N: prerequisite line (e.g. test-harnesses-14 next to test-design-structure), append the name to the long .PHONY list on line 4, and use harness-timer.sh in the recipe like sibling targets—not a direct lint: prerequisite

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18-82
- **Concern**: New test is wired to lint instead of the harness shard system. Scenario: Current lint runs test-harnesses, and scripts/test-harness-shards-coverage.sh treats every non-carve-out test-* recipe as shard-bound; adding test-design-reentry-guard only to lint leaves it missing from shards and fails the partition guard
- **Proposed resolution**: Add the recipe and .PHONY entry, append test-design-reentry-guard to one test-harnesses-N shard line, and do not add it as a direct lint prerequisite

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:969-975; scripts/tracking-issue-write.sh:465-471
- **Concern**: Marker write is planned after the rename that it is meant to defend against. Scenario: If tracking-issue-write.sh rename exits non-zero after plan write and publish succeed, the proposed item 11 may never run, so the fresh marker is absent and the spurious same-session re-entry is still admitted
- **Proposed resolution**: Run design_reentry_marker_write immediately after publish success and before rename, or wrap rename as best-effort with captured rc and always write the marker on the successful plan-write plus publish path

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-external-launcher-common.sh:96-106
- **Concern**: Proposed stat compatibility contract is underspecified for GNU stat. Scenario: GNU stat accepts stat -f but returns filesystem-format non-epoch output, so a naive stat -f %m then stat -c %Y implementation can feed non-numeric data into age arithmetic and break the guard on Linux
- **Proposed resolution**: Specify the existing repo pattern: try stat -c %Y first, then stat -f %m, assign mtime only after ^[0-9]+$ validation, and treat nonnumeric output as invalid-mtime/miss with best-effort cleanup

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:7-17,129-134; scout-dynamic-archetypes-prompt.md:48-51
- **Concern**: Original acceptance #1 requires identifying the re-entry source via instrumentation over recent larch-logs/design runs plus ScheduleWakeup/SendMessage/loop touchpoints; the plan substitutes a code-only audit (no run-log pass) and defers telemetry, with no committed audit artifact path or post-land verification step.. Scenario: Implementers can close #2935 without ever disambiguating always vs random re-entry or confirming which suspected mechanism fired; if the session-cache guard is insufficient, investigators lack the forensics AC #1 demanded.
- **Proposed resolution**: Keep the defensive guard, but add an explicit deliverable: a short audit section in the PR body or docs/run-logs.md (or issue comment) summarizing grep/read results and, where logs still exist, a sampled pass over recent larch-logs/design/*/session-transcript or manifest files for second-entry signatures; note DECISION_2 deferral and follow-up issue criteria.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:189-191,262-281; skills/design/scripts/render-final-summary.sh:32-43; <TMPDIR>/plan.txt:80-80
- **Concern**: Step 0b sub-step 2.6 is specified as banner + exit 1 only, unlike neighboring Step 0b refusals that export SUMMARY_OUTCOME and run the Final summary block; render-final-summary.sh has no outcome for session-cache refusal.. Scenario: Operators lose the structured larch:final-summary on spurious re-entry refusal; ad-hoc SUMMARY_OUTCOME tokens fail render-final-summary case validation; omitting SUMMARY_OUTCOME breaks the Final summary block ${SUMMARY_OUTCOME:?...} guard if an implementer tries to align with other refuse paths.
- **Proposed resolution**: Specify export SUMMARY_OUTCOME=cancelled-session-reentry (or reuse cancelled-title-filter only if semantically correct), run Final summary block before exit 1, extend the SKILL.md orchestrator enum at line 266 and render-final-summary.sh case arms, and add harness coverage.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:761-767; <TMPDIR>/plan.txt:86-93
- **Concern**: Proposed checks 21-22 are literal grep pins only; Check 20 still asserts ordering 2 → 2.5 → 3 and will not fail if sub-step 2.6 is inserted in the wrong position or sub-step numbering drifts.. Scenario: A future edit could place the guard after the clarify loop or before title-eligibility while checks 21-22 still pass, breaking the stated precedence (lifecycle/archival/brainstorm before session-cache before clarify).
- **Proposed resolution**: Extend Check 20 (or add Check 23) to resolve guard_line from ^2\.6\. or design_reentry_marker_hit and assert fetch_line < filter_line < guard_line < clarify_line.

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:95-104; Makefile:18,43,70,365-366
- **Concern**: Makefile wiring adds test-design-reentry-guard to lint dependencies with a bare bash recipe; repo convention binds harnesses to exactly one test-harnesses-N shard (test-design-structure is on test-harnesses-14) and wraps recipes with harness-timer.sh.. Scenario: Direct lint-only wiring or missing shard membership fails test-harness-shards-coverage; bare bash diverges from adjacent harness targets and drops timing instrumentation.
- **Proposed resolution**: State: add test-design-reentry-guard to top-level .PHONY, add to test-harnesses-14 beside test-design-structure, use bash scripts/harness-timer.sh $@ bash scripts/test-design-reentry-guard.sh — do not add as a direct lint: prerequisite.

### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:970-975; <TMPDIR>/plan.txt:23-24,82-82
- **Concern**: Step 5c item 11 ties marker write to the same guard as item 10 rename; the plan’s gap-filler case is rename failure after successful plan write/publish, but item 11 is only “after item 10” under the rename guard.. Scenario: If tracking-issue-write.sh rename fails or is skipped while step 4 succeeded, no marker is written and same-session spurious re-entry is admitted despite a published larch:plan — the scenario the guard targets.
- **Proposed resolution**: Decouple item 11: run design_reentry_marker_write whenever step 4 succeeded (PLAN_WRITE_OK=true), independent of rename outcome; keep best-effort Warnings on write failure.

### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:118-118; scripts/test-design-reentry-guard.sh (proposed F2)
- **Concern**: Failure mode 1 claims F2 pins the refusal banner format; F2 only exercises design_reentry_marker_hit returning MARKER_HIT=true, not SKILL.md banner text or exit-1 path.. Scenario: Banner regressions (TTL wording, override path, guard=session-cache token) ship without automated detection despite plan claiming otherwise.
- **Proposed resolution**: Add F6 (or extend test-design-structure) to grep-pin the banner substring in SKILL.md sub-step 2.6, or a harness that sources the guard and asserts stderr/chat banner shape on hit.

### FINDING_25:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:49-52,107-114
- **Concern**: Edge cases document invalid-mtime and invalid-input handling but F1-F5 omit fixtures for design_reentry_marker_write, REASON=invalid-mtime, and return code 2 invalid-input.. Scenario: Regressions in write path, clock-skew handling, or input validation slip through make lint until production.
- **Proposed resolution**: Add F6-F8 (or fold into F3) covering marker_write, future-dated mtime cleanup, and invalid issue/ppid arguments.

### FINDING_26:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:49-51; scripts/lib-design-reentry-guard.sh (proposed)
- **Concern**: Marker write uses touch without stating mkdir -p on ~/.cache/larch/sessions before touch (write-design-current-env.sh mkdirs at Step 0a, but marker write is best-effort at Step 5c).. Scenario: Unusual paths (Step 0a failure recovery, manual marker write tests without prior session-setup) could fail MARKER_WRITE_FAILED and leave guard ineffective with only Warnings.
- **Proposed resolution**: Document in lib-design-reentry-guard.md and implement design_reentry_marker_write with mkdir -p "$(dirname "$path")" before touch.

### FINDING_27:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:93-93
- **Concern**: Plan says new structural checks are “consistent with existing checks 20 and 23” but test-design-structure.sh has no Check 23 today.. Scenario: Misleads implementers searching for a nonexistent anchor.
- **Proposed resolution**: Change the reference to Check 20 only, or renumber explicitly (e.g., new checks 21-22, ordering extension bundled into Check 20).

### FINDING_28:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:975
- **Concern**: Marker write is sequenced after a rename command whose hard failure is not made non-fatal. Scenario: The plan says the new guard covers the case where plan write and publish succeeded but the [DESIGNED] rename failed, yet Step 5c item 11 is inserted after item 10. If tracking-issue-write exits nonzero before the marker write runs, the exact gap remains unguarded.
- **Proposed resolution**: Revise Step 5c so the [DESIGNED] rename is explicitly best-effort with rc capture and warning logging, then always attempt design_reentry_marker_write whenever PLAN_WRITE_OK=true and the publish/session guard allows it, regardless of rename failure.

### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:972-975; skills/design/SKILL.md:1015-1032
- **Concern**: Marker-write failure warning is logged too late to be durable or visible. Scenario: Step 5c publishes logs and renders the post-publish final summary before the proposed marker write, then Step 6 removes DESIGN_TMPDIR on the happy path. If marker creation fails, the appended execution-issues warning can be deleted during cleanup and never appears in committed logs or the final summary.
- **Proposed resolution**: Make marker-write failure user-visible and durable: either attempt it before the final visible summary and print a warning, or skip cleanup/preserve DESIGN_TMPDIR on marker-write failure, or otherwise ensure the warning is emitted after the failed write and before exit.

### FINDING_30:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:570-585
- **Concern**: Planned structural checks only grep for symbol presence, not the new guard contracts. Scenario: The plan requires Step 0b ordering after title eligibility and before clarify/already-planned routing, plus a specific refusal banner and Step 5c write semantics. A bare grep for design_reentry_marker_hit/write would pass if the calls appear in comments, the wrong step, or after the already-planned branch.
- **Proposed resolution**: Expand structural coverage to extract the relevant SKILL.md windows and assert ordering: title filter before marker_hit before clarify/already-planned, publish/rename/marker Step 5c ordering with the intended guards, and the banner literals including marker path, age/ttl, remaining wait, and override text.

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-makefile-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:104; Makefile:18
- **Concern**: Plan adds test-design-reentry-guard as a direct lint: prerequisite alongside test-design-structure. Scenario: test-design-structure is not a lint: dependency; lint: is only test-harnesses lint-bash32 lint-foreground-markers lint-only (Makefile:18). CI runs make test-harnesses-N per shard (.github/workflows/ci.yaml:226), not individual lint: extras. A direct lint:-only add would not run in CI unless the target is also sharded; following the plan literally may skip CI entirely or duplicate runs locally
- **Proposed resolution**: Do not extend lint: prerequisites. Register test-design-reentry-guard only via the test-harnesses-N shard aggregate (Makefile:43), matching test-design-structure on test-harnesses-14 (Makefile:70)

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-makefile-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:95-104; Makefile:4-18; Makefile:37-43; Makefile:70
- **Concern**: The proposed Makefile wiring tells implementers to add test-design-reentry-guard directly to lint alongside test-design-structure, but current lint only depends on test-harnesses lint-bash32 lint-foreground-markers lint-only, and test-design-structure is actually shard-bound through test-harnesses-14. The plan also does not explicitly require .PHONY membership plus exactly one test-harnesses-N shard entry, despite the shard coverage guard contract.. Scenario: Adding only a direct lint dependency, or adding .PHONY plus a recipe but no shard membership, bypasses the established shard layout and can be flagged by scripts/test-harness-shards-coverage.sh or create CI/local drift.
- **Proposed resolution**: Revise the plan to say: add test-design-reentry-guard to the top-level .PHONY declaration, add it to exactly one test-harnesses-N line, preferably Makefile:70 next to test-design-structure, and do not add it as a direct lint prerequisite.

### FINDING_33:
- **Reviewer(s)**: Codex-dyn-makefile-harness-wiring
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:99-102; Makefile:365-366
- **Concern**: The proposed recipe uses bare bash scripts/test-design-reentry-guard.sh, but adjacent harness targets use the harness-timer wrapper, including test-design-structure.. Scenario: The new harness would lose the standard timing wrapper and diverge from Makefile harness conventions.
- **Proposed resolution**: Revise the Makefile snippet to test-design-reentry-guard: followed by bash scripts/harness-timer.sh $@ bash scripts/test-design-reentry-guard.sh.

### FINDING_34:
- **Reviewer(s)**: Cursor-dyn-guard-exit-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:26-28,80
- **Concern**: Step 0b sub-step 2.6 prose omits SUMMARY_OUTCOME export and ### Final summary block before terminal exit. Scenario: Peer Step 0b refuses at skills/design/SKILL.md:189-190 and :198-199 all export cancelled-* and run the fenced Final summary block; proposed 2.6 only prints the banner and exit 1, so spurious re-entry leaves no final-summary.md, no larch:final-summary upsert, and no run-outcome record for the second invocation
- **Proposed resolution**: Mirror the title-filter pattern: export SUMMARY_OUTCOME (new token below), run ### Final summary block, then print the session-cache banner to stderr and exit 1; preserve $DESIGN_TMPDIR as already planned

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-guard-exit-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:189-199,262-266,280-281; skills/design/scripts/render-final-summary.sh:32-43
- **Concern**: Plan adds a new Step 0b terminal refusal after DESIGN_TMPDIR exists but only says to print the re-entry banner and exit 1, unlike neighboring Step 0b exits that export SUMMARY_OUTCOME and run the Final summary block.. Scenario: The re-entry refusal would skip the larch:final-summary path entirely. If the implementer tries to fix that by exporting a new outcome, render-final-summary.sh currently rejects any token outside its case enum; if SUMMARY_OUTCOME is omitted, the Final summary block fails at ${SUMMARY_OUTCOME:?set SUMMARY_OUTCOME before Final summary block}.
- **Proposed resolution**: Revise sub-step 2.6 to export SUMMARY_OUTCOME=cancelled-session-reentry, run the Final summary block before the banner/exit, add cancelled-session-reentry to the SKILL.md orchestrator contract enum and render-final-summary.sh case enum, and add render-final-summary harness coverage for that outcome.

### FINDING_36:
- **Reviewer(s)**: Codex-dyn-guard-exit-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:761-767; <TMPDIR>/plan.txt:86-93
- **Concern**: Plan proposes presence-only checks for design_reentry_marker_hit and design_reentry_marker_write, but does not extend the existing Step 0b ordering assertion to prove sub-step 2.6 remains between the title filter and clarify loop.. Scenario: A future edit could place the guard before issue fetch/title filtering or after clarify/already-planned routing while still satisfying the proposed checks 21 and 22, changing precedence from the stated lifecycle/archival guards first contract.
- **Proposed resolution**: Extend Check 20 to bind guard_line from the ^2\.6\. anchor or design_reentry_marker_hit line and assert fetch_line < filter_line < guard_line < clarify_line, with a failure message naming the 2 -> 2.5 -> 2.6 -> 3 invariant.

### FINDING_37:
- **Reviewer(s)**: Cursor-dyn-bash-library-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-reentry-guard.sh (proposed, plan L51)
- **Concern**: Plan lists macOS and Linux stat flags but does not specify runtime selection or numeric validation. Scenario: Implementer may call only stat -f %m on Linux; GNU stat treats -f as --file-system and emits multi-line non-numeric output, breaking now-mtime arithmetic or misclassifying hits (see scripts/lib-external-launcher-common.sh:96-106)
- **Proposed resolution**: Specify GNU-first then BSD try-fallback: stat -c %Y then stat -f %m, each with 2>/dev/null and [[ value =~ ^[0-9]+$ ]]; on failure emit MARKER_HIT=false REASON=stat-unavailable return 1; document in lib-design-reentry-guard.md

### FINDING_38:
- **Reviewer(s)**: Codex-dyn-bash-library-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-reentry-guard.sh (proposed), <TMPDIR>/plan.txt:49-51
- **Concern**: Plan names macOS and Linux stat forms but not a concrete runtime branching strategy. Scenario: Implementer can pick an order that emits unsupported-stat errors on the opposite platform or fails the fresh-marker check; BASH_AUTHORING.md:34-48 requires Bash 3.2-compatible scripts, and the current repo pattern in scripts/check-reviewers.sh:93-98 uses a stderr-suppressed try-fallback with numeric validation
- **Proposed resolution**: Specify a Bash 3.2-safe helper such as try stat -c %Y "$marker" 2>/dev/null, validate ^[0-9]+$, else try stat -f %m "$marker" 2>/dev/null, validate again, else return a clean miss; avoid Bash 4 constructs listed in BASH_AUTHORING.md:38-44

### FINDING_39:
- **Reviewer(s)**: Codex-dyn-bash-library-portability
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-design-reentry-guard.sh (proposed), <TMPDIR>/plan.txt:49-50
- **Concern**: design_reentry_marker_write does not require mkdir -p for ~/.cache/larch/sessions before touch. Scenario: With a fresh HOME, deleted cache parent, or test HOME from mktemp -d, touch fails because the parent directory is absent; the plan only discusses filesystem-full and permission failures at plan.txt:110, so the expected MARKER_WRITE_FAILED diagnostic can be misleading or absent
- **Proposed resolution**: Add explicit mkdir -p "$(dirname "$marker_path")" before touch, capture mkdir/touch stderr, emit MARKER_WRITE_FAILED=true with a reason token such as mkdir-failed or touch-failed, and add a harness case where HOME starts empty and marker_write succeeds

### FINDING_40:
- **Reviewer(s)**: Codex-dyn-bash-library-portability
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-design-reentry-guard.sh (proposed), <TMPDIR>/plan.txt:51
- **Concern**: design_reentry_marker_hit does not specify clean handling for race deletion between the existence check and stat. Scenario: A marker can be removed after the function decides it is present but before stat runs; without stderr suppression and an explicit failed-stat branch, raw stat errors can surface in the operator Bash transcript instead of a clean MARKER_HIT=false return
- **Proposed resolution**: Add an explicit stat-failure branch that treats ENOENT or any nonnumeric mtime as a miss, prints a single KV line such as MARKER_HIT=false REASON=absent-or-stat-failed, returns 1, and suppresses stat stderr; add a test using a stubbed stat or removed marker to pin no stderr leakage

