### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and validating it against the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/plan_review.py:1193-1264	Plan keeps identity-key filtering only and does not suppress or per-finding-annotate cross-wording concern overlap	#4884 reproduction still lists already-satisfied concerns (e.g. 5/7 in run 58D5F692) because differently worded rejected blocks pass `_filter_rejected_findings_body`; section relabel alone still presents them as open suggestions	Add a minimal report-side filter keyed on normalized Location+Concern against cumulative applied ledger and/or final `plan.txt` cues, or annotate each rejected block already addressed; keep audit file byte-faithful
2	out_of_scope	nit	completeness	skills/implement/SKILL.md:1-1	#4838 asks to audit /design and /implement for stale breadcrumbs but plan only changes /design plus a generic progress-reporting note	Issue acceptance for #4838 may be marked done without an explicit /implement stale-breadcrumb audit even if no edits are needed	Add a one-line Testing strategy audit step documenting /implement review (expected no-op) or cite checked paths
3	in_scope	important	correctness	skills/design/SKILL.md:584-641	Plan removes post-launch reviewer table prints but does not bind post-notification table emission in the Step 3 wait/resume rules	After launch ack the orchestrator END TURNs with no table; if the notification-resume path never prints the compact table, operators lose all reviewer status output	Update both Step 3 immediate-background wait rules and the resume fence rule to print the compact reviewer status table once after confirmed `<task-notification>` / `.completed/step-3-terminal`, using `latest-reviewer-status.tsv`

**1. [completeness] Cross-wording overlap still emitted (#4884 primary gap)**  
`python/plan_review.py:1193-1264`

The plan explicitly keeps `_filter_rejected_findings_body` identity-key behavior unchanged and only reframes output via `--report-framing`. That does not meet #4884 expected behavior: concerns already satisfied in the final plan should not be presented as open suggestions, or should be clearly annotated per finding.

The issue’s core failure mode is a later-round rejected block whose `_finding_dedup_key` differs from an earlier accepted finding that already implemented the same concern. Section-level copy (“Some may already be addressed…”) does not identify which entries are false positives; the operator still sees the full rejected list (e.g. 5/7 in run `58D5F692`).

**Suggested revision:** Add a minimal, deterministic overlap filter (e.g. suppress when normalized Location+Concern matches any applied ledger entry, or when the final `plan.txt` already contains the proposed fix text), or annotate each already-addressed block individually. Keep `rejected-findings.md` byte-faithful for audit.

**2. [OUT_OF_SCOPE] #4838 `/implement` audit not in plan**  
`skills/implement/SKILL.md`

#4838 requires auditing both `/design` and `/implement` for stale breadcrumbs. The plan fixes the `/design` pre-launch table and adds a generic note to `skills/shared/progress-reporting.md`, but does not include an explicit `/implement` audit step. `/implement` may have no matching stale pattern (no `📊` post-launch tables found in implement skills/scripts), yet the issue still asks for verification.

**Suggested revision:** Add one Testing strategy bullet: grep `/implement` for static pre-launch status tables and record “no change needed” if clean.

**3. [correctness] Post-notification table print not wired after removing launch print**  
`skills/design/SKILL.md:584-641`

The plan removes the post-launch “print compact reviewer status table” directive from both Step 3 wait rules but only implicitly keeps the post-notification table via the Compact reviewer status table subsection. The wait rules themselves still say END TURN after launch ack without saying to print the table after notification.

If the notification-resume path does not explicitly print the table, operators get zero reviewer status output after this change.

**Suggested revision:** In both Step 3 immediate-background wait rules and the resume-fence wait rule, add: after confirmed `<task-notification>` (and `.completed/step-3-terminal`), print the compact table once from `latest-reviewer-status.tsv` before parsing the review envelope.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 4848 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt)

I'll read the plan and the code paths it cites to check requirements coverage and minimum-change scope.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	plan.txt:7-15	#4884 expected behavior to not present already-satisfied concerns is only partially addressed via section relabel	The #4884 reproduction (5/7 rejected blocks already present in plan-pre-apply-round-5.txt with different dedup keys) still emits verbatim under the new heading; operators still read long already-done concerns as open suggestions, only with softer framing	Either add a minimal plan-text overlap filter in emit-rejected (e.g. drop rejected blocks whose Location/Concern surfaces appear in current plan.txt) or explicitly document in Approach/PR that this PR closes mislabeling only and file a follow-up for concern-level suppression
2	in_scope	important	risk-integration	plan.txt:35-55	python/plan_review.py subsection has unclosed example fence and nested ### UPDATED heading	The plan grammar breaks mid-file: the markdown example starting at line 46 is not closed before ### UPDATED: design-step3b-tail.sh at line 55, so file-boundary instructions for plan_review.py vs the tail wrapper can be misread during implementation	Close the example fence, finish the plan_review.py bullet list, then start the design-step3b-tail.sh ### UPDATED subsection as a separate top-level file entry

## Findings

### 1. [completeness] #4884 still presents already-satisfied concerns (important, in_scope)

**Location:** `plan.txt:7-15`, `plan.txt:35-54`

The binding scope (#4884) says Step 4 **should not present** concerns the final plan already satisfies, or must **clearly annotate** each as already addressed. The plan chooses **output hygiene only**: keep identity-key filtering (#4849), relabel the section, and add a generic disclaimer. Rejected blocks whose concerns are already in `plan.txt` but use different dedup keys (the reported 5/7 case) still print in full.

That fixes the **"Unimplemented"** mislabel but not the core operator confusion: a long list of already-implemented items remains. Source-side prompt hardening (`python/rendering.py`, `plan-review.md`) may reduce future re-raises but does not fix the Step 4 report for the existing failure mode.

**Suggested revision:** Add a minimal, deterministic overlap check in `emit-rejected --report-framing` (e.g. suppress blocks whose `Location` / `Concern` text matches plan surfaces), **or** state explicitly in Approach that concern-level presentation is deferred and the umbrella closes on relabel + #4838 only.

### 2. [risk-integration] Malformed plan file subsection boundaries (important, in_scope)

**Location:** `plan.txt:35-55`

Under `### UPDATED: python/plan_review.py`, an opening ` ```markdown ` example at line 46 is never closed. `### UPDATED: skills/design/scripts/design-step3b-tail.sh` appears inside that block (line 55). Implementers may miss tail-wrapper changes or treat them as part of the Python example.

**Suggested revision:** Close the fence after the example shape, complete the `plan_review.py` bullets, then list `design-step3b-tail.sh` as its own `### UPDATED:` entry.

---

## Coverage notes (no additional findings)

**#4838:** Adequately covered: remove pre-launch all-pending table, post-notification-only cadence in both Step 3 wait rules, grep audit with documented `/implement` no-change default, `progress-reporting.md` clarification.

**#4884 source-side:** `render_plan_review_main` already instructs reviewers not to flag plan-addressed current-state behavior; the plan adds a stronger pre-raise check. Round dispatch already uses `--plan-file "$DESIGN_TMPDIR/plan.txt"` (`python/plan_review.py:1090-1091`).

**Step 4 orchestrator:** Plan removes the duplicate `## Unimplemented Plan Review Suggestions` heading and the Step 4 `readability-style.md` load; aligns with `skills/design/SKILL.md:732-740`.

**Tests:** Framing tests for `--report-framing` are proportionate to the chosen approach; the issue’s concern-level suppression test is intentionally omitted given the reframing strategy.
## Reviewer stderr (<TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-3/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 4520 bytes)
  ```
### Warnings

- **Step design Step 5b — design file-oos-prepare (deps degraded) failed (exit 0)**:
  ```
OOS filing deps pre-pass unavailable (FILE_DESIGN_OOS_DEPS_AVAILABLE=false); intra-batch dependency edges skipped. Single OOS item, so no intra-batch deps apply. Filing via graceful-degrade /larch:issue without --intra-batch-deps-file / --no-dep-llm (mirrors /implement Step 9a.1 degraded-mode).
  ```
