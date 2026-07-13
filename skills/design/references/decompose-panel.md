# Split-path: inline partition

**Consumer**: `/design` skill orchestrator at every Split-path entry: size-triggered routes, explicit `--partition` / `-p`, semantic-sprawl, Gate B, settle-dispatch, and Step 5c publish-size refusal.

**Contract**: normative inline partition procedure — main-agent builds proposal, one `AskUserQuestion`, then file/annotate/migrate-deps/close-original.

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

## 4. File and annotate

On valid Partition acceptance, invoke `/larch:issue` in batch mode with `$DESIGN_TMPDIR/decompose/partition-input.txt` and `--no-dep-llm`. Keep dedup enabled. Pass `--context-file "$DESIGN_TMPDIR/source-env.sh"` to nested issue creation. Supply `--intra-batch-deps-file "$DESIGN_TMPDIR/decompose/partition-deps.tsv"` only when that TSV is non-empty; declared edges are authoritative and independent pieces must remain independent.

Capture stdout and run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" decompose annotate \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --issue-stdout-file "$DESIGN_TMPDIR/decompose/issue-run.stdout"
```

Do not continue unless annotation records a complete batch.

## 5. Migrate dependencies, then close

Run migration before closure:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" decompose migrate-deps \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --original-issue "$ISSUE_NUMBER" \
  --repo "$REPO"
```

Migration validates session-backed live-mutation authorization before any GitHub read or mutation. Authorization denial makes zero GitHub calls and leaves the run retryable. It snapshots the original incoming and outgoing relations, adds and read-verifies all replacement edges, then removes and read-verifies original edges. It persists retry state and writes `.decompose-deps-migrated` only after the full live graph verifies.

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" decompose close-original \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --original-issue "$ISSUE_NUMBER" \
  --repo "$REPO"
```

`close-original` revalidates the migration sentinel and live postcondition, including every declared intra-piece edge, before comment or close. Any partial filing, denied authorization, stale state, or verification failure preserves the original issue and tmpdir. On resume after filing, if migration is absent, incomplete, or stale, rerun `migrate-deps` before `close-original`.

For Step 5c size refusal, accepted Partition is terminal. Export `SUMMARY_OUTCOME=approved-partition`, run the Final summary block, and exit `0`. Do not rerun Step 5c or continue against the closed original. Only Override reruns `design-step5c.sh --fresh-attempt`.

Panel dispatch and aggregate CLI commands remain available to their existing non-Split callers.
