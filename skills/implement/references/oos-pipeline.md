# Step 9a.1 OOS Pipeline Procedure

**Consumer**: `/implement` Step 8+ OOS checkpoint on the bash path: the Exit 0 `OOS_PENDING=true` branch and the **OOS checkpoint** block. Python accepted-OOS filing is owned by `python/cli.py oos file` before `step-8-ship.sh`; Python `needs_user_reason=oos-filing` is reserved for the security sidecar pre-PR stall in `python/ship.py`.

**Path note**: executable steps 1–7 below are bash-path instructions for the `OOS_PENDING=true` checkpoint. Do not load this procedure for Python accepted-OOS filing.

**Contract**: Step 9a.1 owns `oos-issues` larch-log evidence on the bash path, including sentinel recovery and all-already-filed design batches. On the bash path, `run-statistics` is owned by the post-checkpoint Step 8+ block after `python/cli.py oos disposition-checkpoint` exits 0; on sentinel recovery or all-already-filed, NEVER #5 applies only to the `oos-issues` half, not `run-statistics`. On the Python path, `python/cli.py oos file` writes checkpoint-visible evidence first, runs `python/cli.py oos disposition-checkpoint`, then writes `run-statistics.md` and completion markers only after checkpoint exit 0. A checkpoint failure may leave provisional `oos-issues.ndjson`, but that file alone is not Step 9a.1 completion.

**Python path parity**: `python/cli.py oos file` checks persisted filed evidence before combining or filing a new batch. Checkpoint-failed retries reuse persisted filed evidence before creating any new public OOS issues. Persisted evidence is matched to accepted blocks by filed URL or stable identifier first, then by normalized title fallback; only unmatched accepted blocks are filed. Sentinel-only recovery materializes accepted-OOS recovery evidence before running the checkpoint, using the strict `- **Filed URL**: <url>` accepted evidence form so the real checkpoint can pass.

**Priority labels**: the Python path labels filed accepted-OOS issues with `oos-correctness` when the accepted or post-cap combined OOS block has `focus-area: correctness` or `focus-area: regression`. Rollup/cap aggregates inherit priority when any embedded source block is high-risk. Filed-url-only duplicate bodies merge high-risk priority into the retained same-title block before combine/cap.

Priority label failure fails only the affected high-risk item. Successful non-priority issues in the same mixed batch remain filed, and sentinel plus NDJSON evidence is written before the non-zero return. `_run_issue_batch()` returns an explicit `failure_mode` so `_file()` does not treat label failures like hard create failures. Label provisioning failure blocks only priority-tagged items, not the whole batch. Idempotent and mixed reruns backfill missing priority labels from persisted sentinel evidence before early return or new filing. Security-routed OOS remains private and is not affected.

**When to load**: MANDATORY immediately before executing the full Step 9a.1 procedure (steps 1–7). Do not load outside that checkpoint.

## Step 9a.1 OOS pipeline procedure

1. **Resolve accepted-OOS inputs** (read-only). Do not parse external implementer manifest JSON in prompt-side Step 9a.1; manifest provenance and extraction live in `python/cli.py oos materialize-manifest`.
   - Resolve design input in the same order as `python/cli.py oos disposition-checkpoint`: `$DESIGN_TMPDIR/oos-accepted-design.md` when `$DESIGN_TMPDIR` is set and that file exists, else `$IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md` when present, else `$IMPLEMENT_TMPDIR/oos-accepted-design.md`.
   - Also read `$IMPLEMENT_TMPDIR/oos-accepted-review.md` and `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`. The main-agent file already includes dispatcher-materialized manifest OOS when Step 2 or the Python ship driver ran `python/cli.py oos materialize-manifest`.
   - Treat missing files as empty.
   - **Security sidecar (`security-oos-observations.md`)**: security-routed manifest OOS is retained locally by `python/cli.py oos materialize-manifest` in `$IMPLEMENT_TMPDIR/security-oos-observations.md` (never merged into public accepted-OOS files). Handle disposition through SECURITY.md's private flow; do not file via `/issue`. While this sidecar is non-empty, `python/cli.py oos disposition-checkpoint` and `python/ship.py` refuse all-clear / PR creation (they set or retain `OOS_PENDING=true` and stall until private security disposition clears the sidecar).
   - **Security routing (gate-aligned)**: exclude a `### OOS_` block only when its body contains a dedicated `- **focus-area**:` field line whose value begins with `security` (case-folded), optionally continued with `-word` tokens such as `security-hardening`. This is the same predicate as `${CLAUDE_PLUGIN_ROOT}/python/larch/issue/file_oos.py` (`_count_non_security_markdown` / `count_non_security`) and `oos-disposition-gate.md` Counting rules (`non_security_oos`). Manifest `focus_area` / `focus-area` values are preserved by the dispatcher and materializer as this dedicated field before routing. Prose such as `focus-area = security` inside a `**Description**` line does **not** mark a block security-routed, and title prefixes alone do not security-route. Route excluded blocks through SECURITY.md's private flow; do not file them via `/issue`.
   - Apply the design-phase carve-out: exclude any `### OOS_` block whose body already contains `- **Filed URL**:`, while retaining those URLs as already-filed disposition evidence.
2. **Handle empty or already-filed batches**.
   - True no-input batch: emit no Accepted-OOS bullets and early-exit before steps 3–7.
   - All-already-filed design batch: do not call `/issue` and skip steps 3.3–3.5 (combine, cap, and file-conflict pre-passes). Still run step 6 and step 7 to materialize checkpoint-visible `oos-issues` NDJSON evidence from existing `- **Filed URL**:` lines and any recovered sentinel URLs so `python/cli.py oos disposition-checkpoint` can pass without a new filing batch.
3. **Idempotency guard**.
   - If `$IMPLEMENT_TMPDIR/oos-issues-created.md` exists, recover created-or-deduplicated URLs and tallies from it, then skip `/issue` for matched accepted blocks.
   - On this branch, still perform the NEVER #5 `oos-issues` larch-log append from recovered URLs and refresh the terminal summary when applicable; do not write `run-statistics` here.
   - Do not run combine, cap, worksheet, or helper pre-passes on sentinel-only recovery (steps 3.4–3.5). If persisted evidence matches only part of the current batch, remove matched blocks from the working set and run combine, cap, and filing only for unmatched blocks.
3.3. **Cross-phase dedup**. Build the working batch from `### OOS_N:` blocks in fixed phase order: main-agent, design, review (same accepted-file order as `python/cli.py oos disposition-checkpoint`). Deduplicate equivalent titles across phases before grouping.
3.4. **Combine pass**. Write `$IMPLEMENT_TMPDIR/oos-combined.md` and `$IMPLEMENT_TMPDIR/oos-grouping-worksheet.md` for the post-3.3 working batch.
   - **Sanitize before compose**: apply the dual-write redaction rules from `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` to combined issue bodies and session-derived worksheet prose destined for public `/issue` bodies or committed larch-log records: secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII → `<REDACTED-PII>`. Paraphrase when in doubt.
   - Cascade `Rule A → Rule B → criteria 1-4 → criterion 5 → criterion 6` with the `~30` LOC threshold convention from `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md`.
   - **Rule A — same logical concern**: COMBINE; overrides the independence carve-out. Group by LLM-judged thematic concern; every group with 2+ entries becomes one combined entry. Preserve actionable content; indent or fence structural source lines such as `###`, `- **Description**:`, `- **Reviewer**:`, `- **Vote tally**:`, and `- **Phase**:` so `issue parse-input` does not mis-parse.
   - **Rule B**: combine entries at the same `< ~30` LOC boundary used by the triage policy.
   - **Criteria 1–4**: same file/module, similar pattern, overlapping scope, and sequential dependency. Respect the independence carve-out except where Rules A/B or criteria 5/6 override it.
   - **Criteria 5–6**: hard-combine medium bugs (`>= ~30` LOC) and moderate documentation changes (`~30–100` lines), with a minimum of 2 entries in each class.
   - **Worksheet contract**: `oos-grouping-worksheet.md` has one `### INPUT_<i>` block per post-3.3 ordinal with `concern:`, `group:`, `justification:`, and optional `sources:`. Add a banner that indices are pre-cap only.
   - Skip the entire combine pass on sentinel-recovery and all-already-filed branches.
3.4b. **Per-run cap pre-pass**.
   - Invoke `python/cli.py oos issue-cap --input-file "$IMPLEMENT_TMPDIR/oos-combined.md"`.
   - Fail closed on non-zero: do not write `oos-issues-created.md`, skip filing, breadcrumb the failure, and leave the checkpoint to block unresolved disposition.
3.5. **File-conflict pre-pass**.
   - Invoke `python/cli.py oos file-conflict-deps --input-file "$IMPLEMENT_TMPDIR/oos-combined.md" --output "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"`.
   - Exit 0 plus non-empty TSV: forward `--intra-batch-deps-file` in step 4.
   - Exit 0 plus empty TSV: omit `--intra-batch-deps-file`; Phase-2 LLM dependency analysis remains the sole dependency path.
   - Non-zero exit: degraded-continue with a warning and a `Tool Failures` entry, then omit `--intra-batch-deps-file`. Do not treat an empty TSV as failure.
4. **Run the `/issue` batch**.
   - Forward `--input-file "$IMPLEMENT_TMPDIR/oos-combined.md"`, `--title-prefix "[OOS]"`, and, when `$ISSUE_NUMBER` is set, not deferred, and not repo-unavailable, `--blocked-by-issue "$ISSUE_NUMBER"`.
   - Forward `--intra-batch-deps-file "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"` only when step 3.5 produced an exit-0 non-empty TSV.
   - Never pass `--no-dep-llm`.
   - **Sanitize** every item Description and session-derived field per `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` before the batch call; `/issue` forwards Description verbatim.
   - Parse `ISSUES_CREATED`, `ISSUES_FAILED`, `ISSUES_DEDUPLICATED`, `ISSUE_<i>_NUMBER=`, `ISSUE_<i>_URL=`, `ISSUE_<i>_DUPLICATE_OF_NUMBER=`, and `ISSUE_<i>_DUPLICATE_OF_URL=`.
   - **Treat both created URLs and duplicate-of URLs as valid disposition URLs.**
   - If `/issue` exits non-zero or `ISSUES_FAILED>0`, do not write `$IMPLEMENT_TMPDIR/oos-issues-created.md`; breadcrumb partial failure and let the checkpoint block until missing dispositions are resolved. Do not treat any URL from the failed batch as disposition-satisfied.
5. **Write the sentinel**. Write `$IMPLEMENT_TMPDIR/oos-issues-created.md` only after a successful `/issue` batch with no failed items, using the created-or-deduplicated sentinel format below.
6. **Append the `oos-issues` larch-log batch**.
   - Accepted entries include created and deduplicated disposition URLs; sanitize NDJSON `body` per `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` before `jq -nc` compose.
   - On non-zero `/issue` or `ISSUES_FAILED>0`, do **not** append accepted disposition URL rows to the `oos-issues` NDJSON batch or any other gate-read surface. Log the partial failure only under `Tool Failures` or operator breadcrumbs outside gate-satisfaction paths until the batch succeeds with no failed items.
   - Rejected/non-accepted entries remain under the Rejected sub-block per `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` OOS carve-outs and the Terminal disposition invariant (`## Rejected` with structured `### OOS_` markers in the NDJSON body). Use `docs/run-log-batches.md` only for the compact NDJSON record schema (`jq -nc` with `-c`).
   - Sentinel-recovery and all-already-filed branches still write the required evidence rows; step 6 is not skipped on all-already-filed.
7. **Return control to the Step 8+ checkpoint**.
   - `python/cli.py oos disposition-checkpoint` gates clearing `OOS_PENDING` (non-security accepted OOS requires a resolved `oos-issues.ndjson`; non-empty `security-oos-observations.md` refuses all-clear until SECURITY.md disposition).
   - `run-statistics` OOS-filed counts are written only by the existing post-checkpoint SKILL.md block, after the disposition checkpoint passes.
   - Recovered-from-sentinel items remain excluded from newly filed counts.

## Carve-outs

- `forked_target=true`: skip `/issue` and accepted-OOS log updates, preserving existing fork behavior.
- `repo_unavailable=true`: skip `/issue`, but still write the documented `oos-issues` audit row such as `Skipped — repo unavailable`.

## oos-issues-created.md sentinel format

The sentinel is a Markdown table consumed as loose disposition evidence by `oos-disposition-gate.md` Counting rules and by the Terminal disposition invariant in `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` for URL tables in `oos-issues-created.md`.

| OOS title | Issue | URL |
|---|---|---|
| Example OOS title | #123 | https://…/issues/<n> |

- **Filed**: <N>

Write one row per created or deduplicated disposition issue. The URL column must contain a literal `https://…/issues/<n>` token so the gate's loose grep counter sees it. Use neutral wording: filed/disposition URLs may be newly created issues or duplicate-of existing issues.
