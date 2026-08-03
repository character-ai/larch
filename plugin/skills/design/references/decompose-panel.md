# Split-path: inline partition

**Consumer**: `/design` skill orchestrator at every Split-path entry: size-triggered routes, explicit `--partition` / `-p`, semantic-sprawl, Gate B, settle-dispatch, and Step 5c publish-size refusal.

**Contract**: normative inline partition procedure. The main agent builds and validates the exact proposal, asks one `AskUserQuestion`, then delegates conversion of the original issue and leaf creation to `/umbrella`.

**When to load**: load when any Split-path entry condition triggers in `SKILL.md` or the referenced routing files.

This file is the normative partition procedure for every size trigger, explicit `--partition` / `-p`, semantic-sprawl route, Gate B route, settle-dispatch route, and Step 5c publish-size refusal.

## 1. Build the proposal inline

The main agent reads `$DESIGN_TMPDIR/plan.txt` when it exists. Before plan materialization, it reads `$DESIGN_TMPDIR/feature-description.txt` and the optional discussion artifact. Do not dispatch decomposition subagents or ask a preliminary Split question.

Write one risk-minimizing proposal to `$DESIGN_TMPDIR/decompose/inline-partition.md`. Put shared and risky foundations first. Use this exact shape for at least two pieces:

```markdown
## Pieces

### Piece 1: <title>
- Scope: <paths and behavior>
- Firm-headings: <complete parent plan headings owned by this piece>
- Acceptance: <concrete checks>
- Dependencies: none | blocked-by Piece N[, Piece M]
- Size estimate: <lines or effort>
```

Declare only necessary dependencies. Independent pieces stay independent.

## 2. Validate before the question

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" decompose prepare \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --partition-file "$DESIGN_TMPDIR/decompose/inline-partition.md" \
  ${ISSUE_NUMBER:+--issue-number "$ISSUE_NUMBER"}
```

`prepare` rejects one-piece proposals, missing metadata or coverage, bad references, and cycles. It writes only proposal-declared edges to `partition-deps.tsv`; it never adds serial edges. Repair an invalid proposal inline and rerun. Do not ask the operator to resolve partition internals.

## 3. Ask exactly one question

After preparation, make exactly one `AskUserQuestion` call.

- Valid proposal: offer **Partition into the listed pieces (Recommended)**, **Override size guardrail**, and Other/chat.
- Still invalid after inline repair: use the same question. Mark Partition unavailable and include the concise `DECOMPOSE_PARTITION_STATUS` reason. If selected, record the validation failure and end Split-path.
- Other/chat exits the structured Split-path. Do not ask another partition question.

Override keeps the existing warning and caller-specific continuation. No Split-path branch emits a second `AskUserQuestion`.

## 4. Convert through `/umbrella`

`prepare` writes each piece's filed-issue title with a common, traceable prefix: any leading square-bracket prefix from the original issue title (for example `[BUG]`, `[FEATURE]`) is preserved, followed by `split-<original-issue-number>-<piece-number>`. The original-issue title and number are read from `.design-step0-route-state.env` (bound at Step 0). The prepared batch and TSV are the exact approved partition. Do not rewrite them after approval.

Before delegation, require non-empty `CONTEXT_FILE` from Step 0 lifecycle output and remove any stale `$DESIGN_TMPDIR/decompose/umbrella-complete.sentinel`. If the context is absent, preserve `$DESIGN_TMPDIR` and fail closed before invoking a child or mutating GitHub.

Invoke `/umbrella` via the Skill tool:

- First try the bare skill name `umbrella`.
- Pass `--lifecycle-parent-context "$CONTEXT_FILE"` first.
- Then pass `--skip-approve`, `--prepared-root "$DESIGN_TMPDIR/decompose"`, `--prepared-input-file "$DESIGN_TMPDIR/decompose/partition-input.txt"`, `--prepared-deps-file "$DESIGN_TMPDIR/decompose/partition-deps.tsv"`, `--completion-sentinel "$DESIGN_TMPDIR/decompose/umbrella-complete.sentinel"`, and `$ISSUE_NUMBER`.
- Only if the tool reports `Unknown skill: umbrella`, retry once as `larch:umbrella` with byte-identical arguments. Do not retry any other failure.

The nested skill consumes the prior exact approval, keeps `/issue` duplicate detection enabled, applies the prepared dependency graph, converts the original issue in place to `[UMBRELLA]`, and leaves it open. It must not independently decompose or ask another question.

## 5. Verify the child handoff

After the child returns, validate the completion proof against the live approved artifacts and target identity:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" umbrella verify-completion \
  --sentinel-file "$DESIGN_TMPDIR/decompose/umbrella-complete.sentinel" \
  --sentinel-root "$DESIGN_TMPDIR/decompose" \
  --prepared-input "$DESIGN_TMPDIR/decompose/partition-input.txt" \
  --prepared-deps "$DESIGN_TMPDIR/decompose/partition-deps.tsv" \
  --repo "$REPO" \
  --issue "$ISSUE_NUMBER"
```

Require exit zero, `UMBRELLA_COMPLETION_VERIFIED=true`, and the exact `UMBRELLA_NUMBER=$ISSUE_NUMBER`. A missing, malformed, or stale sentinel, partial filing, denied authorization, stale state, or failed graph read-back preserves the open original issue and `$DESIGN_TMPDIR` without claiming success. Do not invoke `decompose annotate`, `decompose migrate-deps`, or `decompose close-original` on the Split-path; `/umbrella` is the single mutation owner.

For Step 5c size refusal, accepted Partition is terminal. Export `SUMMARY_OUTCOME=approved-partition`, run the Final summary block, and exit `0`. Do not rerun Step 5c or continue against the converted original. Only Override reruns `design-step5c.sh --fresh-attempt`.

Panel dispatch and aggregate CLI commands remain available to their existing non-Split callers.
