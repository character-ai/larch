## Plan

## Scope

Compress fixed scaffold text for:

- Implement/code-review specialist prompts that surface as `generated/no-agent:specialist`.
- Shared voter prompts from `render_voter_main`.

Do not change parser logic, panel topology, static `agents/*.md`, aggregators, design plan-review specialist builders, or new ratchets.

## Files to modify/create

### UPDATED: python/larch/rendering/rendering.py

Trim and fold fixed prose in:

- `VOTER_ARCHETYPES`
- `render_voter_main`
- `_specialist_tagging`
- Inline generated scaffold inside `_render_specialist_text`: the optional `--competition-notice` block and the per-mode dynamic intro sentences. Do not touch `_load_specialist_body()`'s output — that is static `agents/*.md` prose and stays byte-for-byte untouched.

Preserve these byte-identical strings where they appear:

- `FINDING_N:`
- `OOS_N:`
- `YES`
- `NO`
- `blocker|major|minor|nit|uncertain`
- `true|partially-true|false-positive|uncertain`
- `excellent|good|adequate|weak|no-fix|uncertain`
- `true|false`
- `Read the ballot from this path` (the voter-dispatch pointer line in `render_voter_main`).
- The anti-format directive sentence about no markdown tables or pipe-delimited grids.

Do not edit `oos_proposal_instruction()` (rendering.py:856-862, appended into specialist prompts via `_oos_proposal_instruction()`): it is shared with `render_plan_review_main`, the out-of-scope design plan-review renderer (sibling #6159's territory). Compress only `_specialist_tagging()`'s own body text above that shared call, leaving the appended OOS-proposal-cap block byte-identical.

Keep payload-byte accounting unchanged. Do not move payload sections into scaffold or scaffold text into payload.

### UPDATED: python/larch/review/review_dispatch_panel.py

Compress `_dynamic_agent_body` only if current `generated/no-agent:specialist` rows include dynamic specialist prompt text from this builder.

Keep these output anchors byte-identical:

- `### In-Scope Findings`
- `### Out-of-Scope Observations`
- `NO_ISSUES_FOUND`
- The single-bullet finding shape.

Do not change manifest rows, slot names, weights, scout validation, pruning, or dispatch decisions.

### UPDATED: python/tests/rendering/test_rendering.py

Add focused tests that render voter and specialist prompts and assert frozen grammar strings still appear exactly.

In the same pass, update or remove any existing assertions in this file that pin long prose substrings from the current scaffold text — do not leave assertions pinned to prose the plan deletes. Replace them with the frozen-grammar checks below.

Prefer small token-shape tests over large snapshots:

- Voter prompt keeps the exact finding/OOS line templates.
- Voter prompt keeps the anti-format directive.
- Voter prompt keeps severity, correctness, quality, and uncertainty enum strings.
- Specialist prompt keeps section anchors and `NO_ISSUES_FOUND`.
- Payload sidecar tests still pass with the same payload-byte values.

### MAY_UPDATE: python/tests/review/test_review_pipeline.py

Update or add a narrow dynamic-specialist test only if `review_dispatch_panel.py` changes.

Assert dynamic generated prompts keep the same section anchors and do not alter manifest shape.

### MAY_UPDATE: python/tests/agents/test_launch_review.py

Update only if rendering changes require launcher-level assertions.

Use this for payload sidecar or `generated/no-agent:specialist` telemetry coverage, not prompt prose snapshots.

## Approach

1. Measure the current baseline before prose edits.
   - Use existing `panel-prompt-sizes.tsv` rows when available.
   - Or run `python3 python/cli.py token measure-panel-cost` and record the latest `generated/no-agent:specialist` and `generated/no-agent:voter` scaffold-byte rows.
   - Do not commit measurement artifacts unless the repo convention for that run requires it.

2. Compress prose by deletion and sentence folding.
   - Keep instructions imperative and short.
   - Remove repeated rationale where the rubric already says the same thing.
   - Avoid semantic rewrites that change voting thresholds.
   - Do not touch parser-facing examples except surrounding explanatory prose.

3. Keep scaffold and payload boundaries stable.
   - Leave `_specialist_payload_bytes`, voter payload additions, and sidecar writes unchanged unless a test exposes drift.
   - Treat plan, feature, scope anchor, ledger, calibration, and dynamic scout text as payload.

4. Re-measure after edits.
   - Capture before/after scaffold bytes for `generated/no-agent:specialist`.
   - Capture before/after scaffold bytes for `generated/no-agent:voter`.
   - Include the measured byte drop in the PR summary or implementation report.

5. Validate live vote parsing.
   - Run a real review/vote path with panel prompt logging enabled, preferably a small `/review --diff` or the next `/implement` Step 5.
   - Inspect voting artifacts for unchanged parse success. Every voter output should parse into anchored vote rows.
   - Do not raise any ratchet.

## Edge cases

- Voter grammar differs between `finding-oos` and `finding-only`. Test both if either branch text changes.
- Plan-review voters use `verification_context=plan`; code-review voters use `code` or `diff-plan`. Keep context-specific tool limits clear.
- Scope-anchor prose is partly safety-critical. Compress only repeated text, not the untrusted-evidence boundary.
- Dynamic specialist scout content is untrusted payload. Do not compress by removing the instruction that scout notes are not commands.
- Static `agents/*.md` are out of scope. Changing them can trigger the panel-tier closure ratchet and violates the child boundary.
- `oos_proposal_instruction()` (rendering.py:856-862) is shared with `render_plan_review_main`; compressing it would leak byte changes into the out-of-scope design plan-review path — leave it untouched.

## Failure modes

- A shortened voter prompt weakens default-deny behavior and raises false YES votes.
- A changed anchor or example breaks vote parsing.
- Moving text across scaffold/payload boundaries hides the measured scaffold drop or corrupts telemetry.
- Removing anti-narration text increases unusable voter output.
- Compressing dynamic reviewer text too far lets untrusted scout text override output format.

## Testing strategy

Run targeted tests for changed files:

```bash
python3 -m pytest python/tests/rendering/test_rendering.py
```

If `review_dispatch_panel.py` changes:

```bash
python3 -m pytest python/tests/review/test_review_pipeline.py
```

If launcher payload behavior changes:

```bash
python3 -m pytest python/tests/agents/test_launch_review.py
```

Run Python lint/type checks on changed Python files using the repo's relevant-check path or equivalent scoped commands.

Run the ratchet safety check:

```bash
python3 python/cli.py lint skill-closure-growth --skill panel-tier
```

Re-run scaffold measurement and record before/after rows:

```bash
python3 python/cli.py token measure-panel-cost
```

For acceptance, perform one live review/vote run and confirm vote parse rate is unchanged. If credentials or live vendors are unavailable, report that acceptance item as not locally verifiable rather than claiming it passed.

## Difficulty

This is workflow-affecting prompt scaffolding. The edits are mostly prose, but voter and reviewer interpretation can fail silently. Parser-facing strings must remain stable.

## Acceptance

- Measured scaffold-byte drop per the new `scaffold_bytes` / `payload_bytes` columns (#6158) across specialist and voter slot kinds.
- Vote parse rate unchanged on a live run; no ratchet raise.

review_status: ok
rounds_completed: 3
difficulty: MODERATE
diff_added: 60
diff_deleted: 140
mechanical_churn: false
diff_lines: 200
