### OOS_1: [OUT_OF_SCOPE] Prepare sentinel success predicate is incomplete
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `file-design-oos.sh prepare` treats `oos-issue-sentinel` as proof of prior filing based mainly on `ISSUES_CREATED>0`. That can false-skip failed/corrupt sentinel states, while also failing to skip all-deduplicated success states where `ISSUES_CREATED=0` and `ISSUES_DEDUPLICATED>0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse ISSUES_FAILED (and optionally ISSUE_SENTINEL_VERSION) from the sentinel; only skip when ISSUES_FAILED=0; otherwise fall through or emit a logged degraded status
  - From cursor-specialist-correctness-output.txt: Treat ISSUES_FAILED=0 plus (ISSUES_CREATED>0 OR ISSUES_DEDUPLICATED>0) as skip-already-filed-sentinel; add harness case S2 for all-dedup sentinel.
  - From cursor-specialist-edge-cases-output.txt: Treat ISSUES_FAILED=0 and (ISSUES_CREATED>0 or ISSUES_DEDUPLICATED>0) as already-filed; add harness S2 for all-dedup sentinel
  - From cursor-specialist-edge-cases-output.txt: Also require ISSUES_FAILED=0 from sentinel before skip (defensive; pre-existing trust model)


### OOS_2: [OUT_OF_SCOPE] In-session guard precedence is not pinned by tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Tests do not cover the case where both `oos-issues-created.md` and `oos-issue-sentinel` are present, leaving the intended `skip-sentinel` precedence unpinned; related sentinel-skip assertions are also weak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a case with both files present asserting `skip-sentinel`, not `skip-already-filed-sentinel`.
  - From cursor-specialist-edge-cases-output.txt: Tighten assertions in follow-up if desired


### OOS_3: [OUT_OF_SCOPE] Annotate graceful-skip also diverges from quiet-mode output contract
- **Reviewer(s)**: dyn-bash-locals-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `cmd_annotate` graceful-skip output uses raw `printf` for both status and `WARN=`, creating the same quiet-mode contract divergence as the new prepare warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-locals-output.txt: Worth aligning in a follow-up.


### OOS_4: [OUT_OF_SCOPE] New `skip-already-filed-sentinel` status lacks Step 5b handling
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-sentinel-clear-cache-output.txt, dyn-bash-locals-output.txt
- **Severity**: important
- **Concern**: `cmd_prepare` can now emit `FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel`, but `skills/design/SKILL.md` Step 5b does not document a branch for it. Resumed runs may fall through/stall or skip silently without operator breadcrumb, WARN surfacing, execution-issues entry, URL recovery, or deterministic continuation to Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add Step 5b handling for skip-already-filed-sentinel with operator-visible warning and execution-issues.md breadcrumb; consider URL recovery before skip
  - From codex-specialist-security-output.txt: Add an explicit skills/design/SKILL.md Step 5b branch for skip-already-filed-sentinel that skips /larch:issue and continues to Step 5c.
  - From cursor-specialist-correctness-output.txt: Add Step 5b handler mirroring skip-sentinel with a distinct breadcrumb and WARN surfacing.
  - From codex-specialist-correctness-output.txt: Either emit existing skip-sentinel for this path or update skills/design/SKILL.md to handle skip-already-filed-sentinel like the sentinel skip path.
  - From cursor-specialist-edge-cases-output.txt: Update SKILL.md Step 5b with skip-already-filed-sentinel branch mirroring skip-sentinel (out of this branch scope)
  - From codex-specialist-edge-cases-output.txt: Emit skip-sentinel for this case or update skills/design/SKILL.md to handle skip-already-filed-sentinel as an idempotent sentinel skip.
  - From cursor-specialist-testing-output.txt: Add a Step 5b branch mirroring `skip-sentinel` (skip pipeline + surface WARN to `execution-issues.md`).
  - From codex-specialist-testing-output.txt: Emit skip-sentinel for this path or update skills/design/SKILL.md Step 5b to handle skip-already-filed-sentinel as an idempotent skip.
  - From dyn-sentinel-clear-cache-output.txt: Add a Step 5b branch for `FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel` mirroring `skip-sentinel` (skip `/issue`, print an operator-visible `⏩` line, optionally attempt `annotate` when `oos-issue.stdout.txt` exists, append the prepare `WARN=` to `execution-issues.md`), and extend the harness or a skill-contract test to pin that routing.


### OOS_5: [OUT_OF_SCOPE] Final summary sentinel fallback trusts created count without failed check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` sentinel fallback can inflate OOS filed count from stale or malformed sentinel data because it trusts `ISSUES_CREATED` without verifying `ISSUES_FAILED=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate ISSUES_FAILED=0 before trusting sentinel counts (not introduced by this branch)


### OOS_6: [OUT_OF_SCOPE] Annotate graceful-skip stdout is not surfaced by Step 5b
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-sentinel-clear-cache-output.txt
- **Severity**: latent
- **Concern**: Step 5b checks annotate exit/stderr but does not parse annotate stdout for `FILE_DESIGN_OOS_STATUS=annotate-skipped-empty-stdout`, so the graceful-skip/degraded outcome can be invisible to the orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Surface annotate-skipped-empty-stdout as a first-class degraded outcome in Step 5b


### OOS_7: [OUT_OF_SCOPE] A1/A2 WARN tests do not assert path diagnostics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The A1/A2 harness only checks that `WARN=` exists, not that it includes the relevant `--issue-stdout-file` path. A regression could remove the operator diagnostic while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: grep for the fixture path inside $out_a1 / $out_a2 in addition to ^WARN=.
  - From codex-specialist-correctness-output.txt: Assert out_a1 contains $TMP/a1/issue-empty.stdout and out_a2 contains $TMP/a2/nonexistent.stdout, or match exact WARN patterns.
  - From cursor-specialist-edge-cases-output.txt: Tighten assertions in follow-up if desired
  - From cursor-specialist-testing-output.txt: Add e.g. `grep -q 'issue-empty.stdout' <<<"$out_a1"` and `grep -q 'nonexistent.stdout' <<<"$out_a2"` (or match the full WARN prefix from `file-design-oos.sh:344`).


### OOS_8: [OUT_OF_SCOPE] Annotate-skip idempotency remains session-local
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After annotate-skip, a fresh `DESIGN_TMPDIR` has neither sentinel nor cross-session cache proof, so a later `/design` session on the same issue can duplicate OOS filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Broader follow-up: persist filing proof cross-session (e.g. promote sentinel to cache on /issue success) — outside this PR scope.


### OOS_9: [OUT_OF_SCOPE] Sentinel negative-path tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness lacks negative cases for `ISSUES_CREATED=0` or malformed `ISSUES_CREATED` where `prepare` should fall through to `ready`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `S2` with `ISSUES_CREATED=0` (and optionally invalid values) asserting `FILE_DESIGN_OOS_STATUS=ready` and that `oos-combined.md` is created.


