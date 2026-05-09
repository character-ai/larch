# Triage and Classification

**Consumer**: `/fix-issue` Steps 3 (Triage) and 4 (Classify Intent and Complexity).

**Contract**: Authoritative detail for the triage checks, the not-material closure flow, the intent dimension (PR vs NON_PR) with its "default to PR only when genuinely ambiguous" rule, and the complexity dimension (SIMPLE vs HARD, evaluated only when `INTENT=PR`) with its "default to HARD when uncertain" rule. SKILL.md carries the step-level breadcrumbs, the `issue-lifecycle.sh close` invocations, and the `Print ✅ 4: classify — INTENT=**$INTENT** [COMPLEXITY=🟨 **$COMPLEXITY** 🟨]` line (bold is required for `INTENT`; yellow-square markers plus bold are required for `COMPLEXITY` so the classification values stand out at a glance); this file carries the judgment-heavy detail that would bloat the main-file knowledge delta.

**When to load**: before executing Step 3 (Triage) OR Step 4 (Classify). Load once — the two step-bodies consume the same detail. **Do NOT load** in any other step — Steps 0 / 1 / 2 / 5 / 6 / 7 / 8 do not consume this content. **Do NOT load** on any path that has already branched to Step 8 — concrete examples: Step 0 `find-lock-issue.sh` exit 1 / 2 / 3 (no eligible issue, error, or lock-failed-after-eligibility-pass), Step 1 setup abort (`REPO_UNAVAILABLE=true`). Steps 3 and 4 do not run on those paths.

**Sibling**: `skills/fix-issue/references/non-pr-execution.md` owns the NON_PR-path execution detail consumed by Step 5b.

---

## Step 3 — Triage detail

Read the issue details from Step 2. Explore the codebase using Read, Grep, and Glob to determine if the issue is still actual — that is, whether it describes a real problem that still needs fixing.

Check for:

- Has the issue already been fixed by recent commits?
- Is the code/feature the issue references still present?
- Is the issue a valid bug/feature request, or was it filed in error?
- For investigation/review-only issues (whose deliverable is research findings or new issues rather than code changes): is the **task itself** still relevant — are the targets, scope, and constraints it describes still meaningful — rather than "is the referenced bug still in code"?

### Not-material closure flow

If the issue is no longer material (already fixed, invalid, or no longer relevant):

1. Compose a detailed explanation of why the issue is no longer material. Include a summary of the research performed: which files were checked, what recent commits were examined, and what evidence led to the conclusion. This explanation is posted as the closing comment on the issue so that anyone reviewing the closed issue can understand the rationale without re-investigating.
2. **Pick a `--close-class` value** at decision time from the triage conclusion, using this canonical mapping:
   - `already-fixed` (the issue describes a bug that has been fixed by a later commit, or a feature that has since been added) → `done`
   - `duplicate-of #N` (the issue restates an existing open or closed issue) → `duplicate`
   - `superseded-by #N` (a later issue or PR replaces the scope of this one) → `superseded`
   - `invalid` / `not-a-bug` / `false-positive` (the issue does not describe real work — e.g., the reported behavior is by design, or the OOS observation was filed in error) → `false-positive`
3. SKILL.md Step 3 invokes `issue-lifecycle.sh close` with the detailed explanation as the `--comment` value and passes `--close-class <inferred>` from the mapping above. The enum deterministically drives the `[FALSE-POSITIVE]` title marker — applied for `false-positive`, `duplicate`, and `superseded`; suppressed for `done`. The closing comment is NOT scanned under `--close-class`, so legitimate research narrative containing words like "duplicate" or "superseded" cannot misclassify the close. The legacy `--mark-false-positive-if-keyword` flag remains available for unstructured-prose close paths but is NOT used here.
4. SKILL.md Step 3 invokes `tracking-issue-write.sh rename --state done` (best-effort) to clear the `[IN PROGRESS]` title prefix Step 0 applied at lock time, replacing it with `[DONE]` so the closed issue's title accurately reflects that automated processing concluded.
6. SKILL.md Step 3 prints the not-material breadcrumb and skips to Step 8.

If the issue is still actual, SKILL.md Step 3 prints the active breadcrumb and continues to Step 4.

## Step 4 — Classification detail

Based on the issue details and codebase exploration from Step 3, determine two independent dimensions.

### Dimension 1 — Intent

Does this issue prescribe work that should produce a pull request?

- **PR**: The issue prescribes a code change — bug fix, refactor, new feature, documentation edit, prompt/skill edit, config change, test addition, etc. — whose natural output is a pull request against the current repository.
- **NON_PR**: The issue prescribes an investigative or review task whose natural output is something other than a PR: new GitHub issues summarizing research findings, new GitHub issues flagging code-review problems, a written report, or similar. Typical signals: the issue body contains phrases like "research and summarize", "investigate and report", "code-review this module and file issues", "do not create a PR", or otherwise makes clear that the deliverable is issues/reports rather than code changes.

**Default to `PR` only when the issue is genuinely ambiguous.** The `PR` path is the pre-existing behavior. A mis-classified borderline `NON_PR` may sometimes surface during `/implement`'s `/review` phase (which reviews code changes, not the shape-of-work contract), in which case the operator may need to stop the run. When the issue text explicitly forbids a PR or mandates research/issues as the deliverable, pick `NON_PR` regardless of the default — overriding the stated deliverable is not recoverable downstream. Mis-classifying a genuine code-change request as `NON_PR` silently skips real work.

### Dimension 2 — Complexity (evaluated only when `INTENT=PR`)

- **SIMPLE**: Isolated fix in 2 or fewer files. Obvious solution with no architectural decisions needed. Examples: typo fix, small bug with clear root cause, config change.
- **HARD**: Everything else. Multi-file changes, new features, architectural decisions, unclear root cause, or any uncertainty.

**Default to HARD when uncertain.** A HARD classification uses the full `/design` + `/review` pipeline, which is safer for non-trivial changes.

**`--quick` short-circuit (overrides the HARD-vs-SIMPLE evaluation on the PR path).** When the operator passed `--quick` to `/fix-issue` (`quick_mode=true`) AND `INTENT=PR`, set `COMPLEXITY=SIMPLE` without running the SIMPLE-vs-HARD decision rules above — the operator has explicitly opted into the SIMPLE pipeline. SKILL.md Step 4 owns the short-circuit logic and the augmented breadcrumb (the `(forced by --quick)` suffix); this reference describes the same rule on the decision-detail side. The short-circuit does NOT apply when `INTENT=NON_PR` (complexity is not meaningful there).

When `INTENT=NON_PR`, complexity is not meaningful — leave `COMPLEXITY` unset and skip the SIMPLE/HARD determination. SKILL.md Step 4 prints the classification breadcrumb (omitting the `COMPLEXITY=` segment when `INTENT=NON_PR`) and proceeds to Step 5.
