## Goal
Implement issue #4565: [IMPLEMENTING] Fix 3 non-fatal larch Python runtime bugs from a live /implement run + add [BUG]/--urgent title prefix to /bug.

## Implementation Plan
## Plan

## Approach

Implement all four scoped items with small, local changes. Incorporate accepted review findings: register the bug-structure harness in `agent-lint.toml`, make diagram failure diagnostics durable in committed run logs (not only tmpdir paths), and emit `DIAGRAM_REASON` on every Step 7a terminal KV path.

- Keep `voting.py` unchanged.
- Keep diagram generation and tally flushing best-effort.
- Reuse `/issue --title-prefix` for `/bug`.
- Do not change `/combine-issues`.

## Files to modify/create

### UPDATED: python/pr_body.py

**Item 1 — OOS URL derive:** Replace `_derive_oos_fields` URL scraping with NDJSON parsing.

- Preserve existing count behavior: count non-empty `oos-issues.ndjson` lines.
- For each line, `json.loads` when possible; read `body` from the object.
- Extract URLs with the existing filed-URL pattern (reuse `oos_filer._FILED_URL_LINE_RE` or equivalent `**Filed URL**:` line grammar).
- Ignore malformed JSON lines for URL extraction (still count the line).
- Do not scan raw NDJSON text with the buggy `[^\"\\s>)]` character class.

**Item 3 — Diagram failure surfacing:** Enrich `generate_code_flow_diagram` failure handling.

- Add a small helper (module-local) to build a **one-line** failure reason from exit code plus a **capped redacted** stderr/stdout tail (e.g. collapse whitespace, cap ~200 chars, `redact.redact(...)` first).
- On `completed.returncode != 0`:
  - Build full redacted diagnostic text (rc, stderr, stdout) via `redact.redact(...)`.
  - Write optional tmpdir log: `implement_tmpdir / "code-flow-diagram.failure.log"`.
  - Return reason like `generation-failed rc=<N> tail=<capped-redacted-tail>` (no raw stderr/stdout in the returned reason).
  - If log write fails, append `log-write-failed` to the reason; still omit raw stderr.
- If `redact.redact` fails unexpectedly, use a generic `redaction-failed` tail token; keep diagram non-fatal.
- Remove stale `code-flow-diagram.failure.log` after successful generation (same as other diagram artifact cleanup).
- Keep `empty-generation` and sanitizer behavior unchanged.

### UPDATED: python/step_7a.py

Thread enriched diagram failure detail through Step 7a output and make it durable.

- Track `diagram_reason = ""` after `generate_code_flow_diagram`.
- Set `diagram_reason` from the returned failure reason when `diagram_rc != 0` or `diagram_status == "failed"`.
- Pass `diagram_reason` (not bare `generation-failed`) to `_append_diagram_warning` so the **committed** `execution-issues` batch carries the capped redacted tail (primary durable diagnostic per FINDING_3).
- When `run_id` is non-empty and the tmpdir failure log exists, **best-effort copy** it to `implement_tmpdir / "larch-logs" / "implement" / run_id / "code-flow-diagram.failure.log"` before rebase (secondary durable artifact; do not rely on tmpdir path alone).
- Emit `DIAGRAM_REASON=<diagram_reason>` on **both** terminal KV paths:
  - rebase-checkpoint early return (`probe.returncode != 0`, ~291–298)
  - normal return (~310–315)
- Keep Step 7a exit status non-fatal for diagram failures (rebase failure may still return non-zero from probe).

### UPDATED: python/test_pr_body.py

Add regression coverage for Items 1 and 3.

- Add `_derive_oos_fields` test with `oos-issues.ndjson` containing JSON whose `body` includes `- **Filed URL**: https://github.com/acme/repo/issues/123`.
  - Assert count is `1`.
  - Assert URL is the full `/issues/123` URL, not truncated at `/i`.
  - Include a JSON-escaped `\n` after the URL to catch the old raw-text escaping hazard.
- Update `test_generate_code_flow_diagram_uses_launcher_not_stub`:
  - Fake launcher failure with stderr/stdout containing diagnosable text.
  - Assert reason includes `generation-failed rc=1`.
  - Assert reason includes a capped `tail=` fragment with redacted/diagnosable content (not bare `generation-failed`).
  - Assert reason does **not** contain raw stderr verbatim when secrets-like content is present.
  - Assert tmpdir `code-flow-diagram.failure.log` exists and holds redacted full capture.
  - Assert reason is not bare `generation-failed`.

### UPDATED: python/review_and_fix.py

Align the rejected-findings aggregate with the existing validator.

- Change `write_rejected_findings_aggregate` from `## Round {round_num}` to `# Review Round {round_num}`.
- Do not change `_validate_code_review_headers`.

### UPDATED: python/test_review_and_fix.py

Update the aggregate round-header test.

- Change assertions from `## Round 1` / `## Round 2` to `# Review Round 1` / `# Review Round 2`.
- Keep assertions for `FINDING_1` and `FINDING_2`.

### UPDATED: python/test_voting.py

Add a positive validator regression without editing `voting.py`.

- Create a valid code-review tally body containing:
  - `# Rejected Findings`
  - `# Review Round 2`
  - at least one accepted `### FINDING_N: ...` or accepted code-review finding header.
- Run `voting write-tally --phase code-review`.
- Assert it exits successfully.
- Keep the existing `## Foo` negative test unchanged.

### UPDATED: python/test_step_7a.py

Update diagram failure coverage and add rebase-failure KV coverage.

- In `test_step7a_diagram_failure_exits_zero_and_clears_stale_artifacts`:
  - Fake generator returns enriched reason such as `generation-failed rc=7 tail=timeout after 600s`.
  - Assert Step 7a still returns `0`.
  - Assert `DIAGRAM_STATUS=failed`.
  - Assert `DIAGRAM_REASON=generation-failed rc=7 tail=...`.
  - Assert `execution-issues.md` contains the enriched reason (capped tail), not bare `generation-failed`.
  - Assert stale diagram artifacts are still removed.
- Add `test_step7a_diagram_failure_emits_diagram_reason_on_rebase_failure`:
  - Fake diagram failure with enriched reason.
  - Fake `rebase-checkpoint-probe.sh` returning non-zero.
  - Assert `DIAGRAM_REASON=...` is present in stdout alongside `DIAGRAM_STATUS=failed`.
  - Assert `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
- Add coverage that when `run_id` is set, the failure log is copied under `larch-logs/implement/<run_id>/` (mock or temp path).

### UPDATED: skills/bug/SKILL.md

Add `/bug --urgent` and forced title prefixes.

- Change frontmatter `argument-hint` to `[--urgent] <bug description>`.
- Replace “This skill has no flags” with a small parser contract:
  - `--urgent` is the only flag.
  - Remove one or more leading `--urgent` tokens from the description.
  - If any other leading `--...` token remains, treat it as prose unless existing behavior says otherwise.
- Preserve the existing empty-description check after removing `--urgent`.
- Define the title prefix for Step 5:
  - default: `[BUG]`
  - urgent: `[BUG] (URGENT)`
- Update the `/issue` invocation to pass one title prefix:
  - `/issue --title-prefix "[BUG]" --body-file ...`
  - or `/issue --title-prefix "[BUG] (URGENT)" --body-file ...`
- Do not reimplement prefix deduplication.
- Keep title derivation unchanged.

### NEW: scripts/test-bug-structure.sh

Add a small structural regression harness for `skills/bug/SKILL.md`.

Assert:

- Frontmatter includes `[--urgent]`.
- Contract documents `--urgent`.
- The skill no longer says it has no flags.
- Step 5 invocation includes `--title-prefix`.
- Both `[BUG]` and `[BUG] (URGENT)` literals appear.
- The skill still says not to pass `--no-dedup`.

Follow `scripts/test-alias-structure.sh` style (header comment, `set -euo pipefail`, `fail()` helper).

### NEW: scripts/test-bug-structure.md

Add sibling contract doc per repo convention (mirror `scripts/test-alias-structure.md`).

Document:

- Purpose: pin `/bug` `--urgent` and `--title-prefix` prompt-side contract.
- Assertion table for each grep/check in the shell harness.
- Makefile wiring (`test-bug-structure` target).
- `agent-lint.toml` registration note.
- Edit-in-sync rules when `skills/bug/SKILL.md` Step 5 or flags section changes.

### UPDATED: agent-lint.toml

Register the new Makefile-only harness (FINDING_2).

- Add `scripts/test-bug-structure.sh` to the Makefile-only `exclude` block adjacent to `scripts/test-alias-structure.sh`, with a short comment mirroring that entry's pattern.
- Add `scripts/test-bug-structure.md` to the sibling-doc exclude block adjacent to `scripts/test-alias-structure.md`.

### UPDATED: Makefile

Wire the new shell harness into lint.

- Add `test-bug-structure` to `.PHONY`.
- Add the target:
  - `python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-bug-structure.sh`
- Add `test-bug-structure` to `test-harnesses-13` (same shard as `test-alias-structure`).

## Edge cases

- Malformed `oos-issues.ndjson` rows should not crash summary rendering.
- Multiple OOS rows should dedupe and sort URLs as before.
- OOS rows without a `body` or `Filed URL` should still count, but add no URL.
- Diagram subprocess stdout may contain secrets; only redacted content lands in failure log, execution-issues bullet, and `tail=` reason fragment.
- Diagram failure reason must stay one line so execution-issues bullets and `DIAGRAM_REASON` KV stay valid.
- Durable post-run diagnosis must not depend on `$IMPLEMENT_TMPDIR` paths; the execution-issues warning and optional run-dir failure log carry the redacted tail.
- `/bug --urgent --urgent desc` can be accepted as urgent once, but must not stack prefixes.
- A bug description that starts with `--` but is not `--urgent` should retain the current prose behavior unless the implementer finds an existing parser contract that requires stricter handling.
- Rebase failure at 7a.r must still emit `DIAGRAM_REASON` when diagram generation failed first.

## Failure modes

- If the failure log cannot be written, return a reason with `generation-failed rc=<N>` and `log-write-failed`; still include `tail=` when stderr capture succeeded.
- If `redact.redact` fails unexpectedly, fail closed with a generic `tail=redaction-failed` token and keep the diagram non-fatal.
- If run-dir copy of the failure log fails, log a Warnings entry best-effort; execution-issues `tail=` remains the primary durable record.
- If the new `/bug` parser text is ambiguous for prompt execution, simplify it to a numbered parse rule with concrete examples.

## Testing strategy

Run targeted tests first:

- `python3 -m pytest python/test_pr_body.py -q`
- `python3 -m pytest python/test_review_and_fix.py -q`
- `python3 -m pytest python/test_voting.py -q`
- `python3 -m pytest python/test_step_7a.py -q`
- `bash scripts/test-bug-structure.sh`

Then run required repo checks:

- `make py-lint`
- `make py-test`
- `make lint`

## Notes

- `approach-synthesis` is `NO_SKETCHES`, so this plan uses direct code and doc inspection.
- Review revisions: Item 3 now commits diagnostics via execution-issues `tail=` plus optional run-dir failure log; Item 4 threads `DIAGRAM_REASON` on both Step 7a KV exit paths; bug harness follows `test-alias-structure` registration (`agent-lint.toml` + sibling `.md`).
- The approved outline has no open questions.


## Acceptance

- Item 1 (OOS URL): `_derive_oos_fields` returns the full `/issues/<n>` URL (not truncated at `/i`); the run-summary `- **OOS filed**:` line is complete and clickable. Regression in `python/test_pr_body.py` covers a URL containing `s` plus a JSON-escaped newline.
- Item 2 (round header): a code-review tally body with `# Rejected Findings` + `# Review Round <n>` validates cleanly; `flush_review_batches` writes the `code-review-tally` batch across multi-round rejected findings. `python/voting.py` validator unchanged.
- Item 3 (diagram failure): on a non-zero diagram subprocess exit, a redacted `code-flow-diagram.failure.log` is written and the returned reason carries `rc=<N>` plus a capped redacted tail; `python/step_7a.py` emits `DIAGRAM_REASON` on both terminal KV paths and stays non-fatal; no raw stderr in committed artifacts.
- Item 4 (/bug prefix): `/bug "<desc>"` files `[BUG] <title>`; `/bug --urgent "<desc>"` files `[BUG] (URGENT) <title>` (single prefix, no stacking); the empty-description guard runs after stripping leading `--urgent`. Reuses `/issue --title-prefix`.
- `scripts/test-bug-structure.sh` passes and is wired into the Makefile and `agent-lint.toml` (with sibling `scripts/test-bug-structure.md`).
- `make py-lint`, `make py-test`, and `make lint` all pass.

diff_lines: 308

## Test plan
(no test plan section in plan-file)
