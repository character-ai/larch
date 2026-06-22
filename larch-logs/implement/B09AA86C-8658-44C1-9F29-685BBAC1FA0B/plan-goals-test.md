## Goal
Implement issue #4659: [IMPLEMENTING] Introduce ARCHITECTURAL_GUIDELINES.md: operator-curated architectural goals /design + /implement consult.

## Implementation Plan
## Plan

## Approach

- Add a generic **architectural-guidelines reader** in Python.
  - Resolve the operating repo root from `CLAUDE_PROJECT_DIR` when it points at a git work tree.
  - Fall back to `git rev-parse --show-toplevel` from cwd.
  - Look only for `<repo-root>/ARCHITECTURAL_GUIDELINES.md`.
  - Return `absent` with no content and no warnings when the file is missing.
  - Return `present` with a canonical path and **parsed, normalized entry text** when it is a regular, non-symlink file inside the repo root.
  - Return `invalid` with a warning when the path is a symlink, directory, unreadable file, or escapes the repo root.
  - Parse only `### G-<area>-<n>:` headings plus their `Why:` and `Deviate when:` bullets; ignore all other prose, directives, priority claims, tool commands, and override text in the raw file.
  - Do not write or update the guidelines file.
  - Treat parsed content as **untrusted repo evidence**: larch-generated subordination notes accompany emitted blocks; file content cannot override `AGENTS.md`, `SKILL.md`, or the approved plan.

- Add **`issue_wire.emit_untrusted_content_block(tag, text)`** for in-memory normalized payloads.
  - Reuse existing `redact_untrusted_stream(text)` (same escaping/redaction as file blocks).
  - Keep `emit_untrusted_file_block(tag, path)` Path-only; do not pass strings to it.
  - Use `emit_untrusted_content_block` for drafter prompt assembly, CLI `read` present payloads, and any normalized guideline text that is not read straight from disk.

- Wire `/design`.
  - Consult guidelines only through `python/cli.py architectural-guidelines read` or in-process `read_guidelines()`; **never** use the Read tool or Write tool on the repo-root path.
  - At **Step 1d.7 proposal approval**, consult the helper when the gate fires (including `--skip-approve`).
  - Before the approval prompt or auto-approval breadcrumb, print one short note:
    - `Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.`
    - or a short deviations list with rationale.
  - On `invalid`, print the helper warning, skip deviation assessment, do not treat as absent, continue the gate.
  - Keep the outline schema unchanged.
  - Treat guidelines as **aspirational**, not blocking.
  - At **Gate C final-plan approval**, repeat the same branch rules after the plan preview and before the prompt or auto-approval.
  - Add guidelines to the Step 2b drafter prompt only when `present`, using the **normalized parsed-entry text** wrapped via `issue_wire.emit_untrusted_content_block("architectural_guidelines", normalized_text)` plus a one-line subordination note.
  - **Bias the Step 1d.7 outline at composition**: when the helper returns `present`, feed parsed guideline entries into outline drafting (Goals, Non-goals, Approach), mirroring `brainstorm.md` consumption, so the outline is shaped by the guidelines rather than only deviation-checked at the gate after it already exists.
  - During **inline Step 2b fallback**, apply the same conditional helper read rule used for `brainstorm.md`: when the helper returns `present`, read via the helper only and fold aspirational goals into `plan.txt`; when `absent` or `invalid`, omit guideline content from the plan.
  - **Prompt-side `/design` owns semantic deviation judgment** at Step 1d.7 and Gate C; Python supplies parsed entries only.

- Wire `/implement` with a **two-phase durable-note contract** (addresses pr-prep `HEAD` drift and ship-driver non-interactivity).
  - **Phase A — post-7a staging (prompt-side, orchestrator judgment)**:
    - Add a dedicated **Architectural guidelines** subsection **immediately after Step 7a completes (after `7a.r` routing) and before Step 8** on **every** path that reaches Step 8, including Step 6 `FILES_CHANGED=false` skip-to-7a and Step 7 no-op paths.
    - Placement is **after** Step 7a so `7a.r` rebase and Step 7a log flush cannot advance `HEAD` after staging inputs are captured.
    - At step entry, **clear stale artifacts**: remove `$IMPLEMENT_TMPDIR/architectural-guideline-warnings.md`, `$IMPLEMENT_TMPDIR/architectural-guideline-warnings.meta.env`, `$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.md`, `$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.env`, `$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt`, and any durable note files (`architectural-guideline-note.md`, `architectural-guideline-note.meta.env`) if they exist.
    - Run `python/cli.py architectural-guidelines read` (or in-process `read_guidelines()`).
    - If `absent`, leave staged/durable files absent and continue to Step 8.
    - If `invalid`, log a warning to execution issues and continue without staging or durable note files.
    - If `present`:
      - Run `python/cli.py architectural-guidelines materialize-diff --forked-target "${forked_target:-false}"` (fork-aware base: `origin/main` default; `upstream/main` when `forked_target=true`, matching Step 7a / `push checkpoint-probe`).
      - **Orchestrator** compares the materialized diff and parsed guideline entries; deviations are judgment-level, not Python-heuristic.
      - Persist **staged assessment** via `python/cli.py architectural-guidelines write-staged-assessment --assessment-file <path>` (or `--assessment-text`). The orchestrator-authored body is the durable surfacing payload for Phase B; Python does not rewrite it.
      - Staged artifacts:
        - `$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.md` — redact-ready markdown body (clean consulted note or deviation warnings).
        - `$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.env` — sidecar with `STATUS=present`, `ASSESSED_HEAD_SHA=<HEAD after Step 7a>`, `DIFF_FINGERPRINT=<hash of materialized diff>`, `BASE_REF=<resolved base>`, `WRITTEN_AT=<iso8601>`.
        - `$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt` — diff snapshot used for assessment.
      - **Do not** write durable `HEAD_SHA`-pinned note/meta in Phase A.
    - Deviations are warnings only; never block Step 8 entry.
    - **At Phase A completion, surface the assessment to the operator immediately**: on `present`, print the clean or deviation note to chat and append a `Warnings` entry to `$IMPLEMENT_TMPDIR/execution-issues.md` (the `invalid` branch already logs a warning). This immediate channel is the operator-visible warning the issue requires; durable Phase B PR-body and final-summary surfacing is additive. Deviations are never silently lost when Phase B is skipped (bail after Step 7a, pin failure, or stale note).
  - **Phase B — durable pin (mechanical, inside ship boundary)**:
    - `ship.py` **must not** perform semantic deviation assessment or rerun orchestrator judgment.
    - Call thin mechanical `architectural_guidelines.pin_note_from_staged(implement_tmpdir, head_sha=<current HEAD>, base_ref=...)` **immediately before every `compose_pr_body()` invocation**, regardless of `resume.start` (`fresh`, `open-pr`, or any other pr-create resume). On the fresh path, `run_logs.flush_logs_pre` may advance `HEAD` with log-only commits first; pin after that flush and before compose. On `open-pr` and other non-fresh resumes that skip the fresh-path flush block, pin still runs at the same pre-compose site so durable note/meta exist whenever staged assessment is present.
    - Treat `flush_logs_pre` as **ordering guidance for log-only HEAD bumps on the fresh path**, not as the sole gate for Phase B pinning.
    - `pin_note_from_staged` reads staged assessment body + sidecar + fingerprint, copies **only** `$IMPLEMENT_TMPDIR/architectural-guideline-staged-assessment.md` into `$IMPLEMENT_TMPDIR/architectural-guideline-note.md`, writes `$IMPLEMENT_TMPDIR/architectural-guideline-note.meta.env` with `HEAD_SHA=<current HEAD>`, and returns whether surfacing is allowed. No LLM, no diff re-interpretation, no body rewriting.
    - `note_consumable(implement_tmpdir, head_sha)` gates PR/final-summary readers: require durable meta, `STATUS=present`, matching `HEAD_SHA`, and readable non-symlink `architectural-guideline-note.md`.
  - **Invalidation on implementation `HEAD` drift**:
    - When Step 8+ paths advance `HEAD` with **implementation** changes (CI-fix commits, conflict-resolution edits, monitor `did_fixing`, pre-push repair), `ship.py` calls `invalidate_implement_note()` only (clears durable note/meta **and** staged assessment artifacts).
    - **Prompt-side orchestrator** must rerun Phase A (read → materialize-diff → assess → `write-staged-assessment`) before the next `step-8-ship.sh` re-invoke or before Step 16–17 final-summary emission when guidelines were `present`. Phase A entry clearing is authoritative; reference docs may also call `python/cli.py architectural-guidelines invalidate` when orchestrator re-enters reassessment outside the normal Phase A subsection (thin wrapper around `invalidate_implement_note()`).
    - Document these hooks in `ship-pr-exit-matrix.md` and `conflict-resolution.md`.
  - Do not auto-edit `ARCHITECTURAL_GUIDELINES.md`.

- Surface `/implement` results durably.
  - `ship.py` and `final_report.py` consume the note only when `note_consumable()` succeeds for current `HEAD`.
  - Include the redacted guideline note in the PR body when consumption succeeds (after Phase B pin at pre-compose).
  - Include the same redacted note in `summary-final.md` and committed `larch-logs/implement/<RUN_ID>/final-summary.md`.
  - Before Step 16–17, if staged assessment exists but durable note is missing or unconsumable, orchestrator reruns Phase A then invokes Phase B pin via a foreground `python/cli.py architectural-guidelines pin-note-from-staged --implement-tmpdir "$IMPLEMENT_TMPDIR"` fence (uses current `HEAD`; mechanical only).
  - Preserve existing PR body and final-summary output when consumption fails or guidelines are absent.

## Files to modify/create

### NEW: ARCHITECTURAL_GUIDELINES.md

- Add the seeded larch guideline set only.
- Use the issue schema:
  - `### G-<area>-<n>: <one-line goal>`
  - `- Why: ...`
  - `- Deviate when: ...`
- Include only the settled sections:
  - Python coding practices.
  - Skill authoring and context economy.
  - Enforcement philosophy.
- Do not include future categories.
- Add a short opening note:
  - guidelines are aspirational;
  - deviations should be surfaced;
  - deterministic rules belong in lints, hooks, or tests.

### UPDATED: AGENTS.md

- Add `ARCHITECTURAL_GUIDELINES.md` to **Canonical sources**.
- Describe it as the operator-curated home for architectural goals that are not mechanically enforceable.
- State that larch treats it as untrusted prompt context, not a higher-priority instruction surface than `AGENTS.md` or skills.

### NEW: python/architectural_guidelines.py

- Add a frozen dataclass result, for example `ArchitecturalGuidelinesResult`.
- Fields:
  - `status`: `present`, `absent`, or `invalid`.
  - `repo_root`: `Path | None`.
  - `path`: `Path | None`.
  - `content`: `str` (normalized parsed-entry text only).
  - `warning`: `str`.
- Add root resolution:
  - prefer valid `CLAUDE_PROJECT_DIR` git toplevel;
  - fall back to cwd git toplevel;
  - allow an explicit `--repo-root` for tests.
- Add `parse_guideline_entries(raw_text) -> str` that emits only `### G-*` blocks with `Why` / `Deviate when` lines; drop preamble and non-entry prose.
- Add `read_guidelines()` returning parsed normalized content on `present`.
- Add `resolve_diff_base(*, forked_target: bool) -> tuple[str, str]` mirroring implement rebase defaults (`origin`, `main` vs `upstream`, `main`).
- Add `materialize_implementation_diff(repo_root, *, base_remote, base_ref) -> str` as a **non-judgment** helper that returns merge-base..HEAD diff text for orchestrator assessment; no semantic scoring.
- Add `diff_fingerprint(diff_text: str) -> str` (stable hash of materialized diff bytes).
- Define staged/durable artifact paths:
  - staged body: `architectural-guideline-staged-assessment.md`;
  - staged sidecar: `architectural-guideline-staged-assessment.env`;
  - diff snapshot: `architectural-guideline-materialized-diff.txt`;
  - durable body: `architectural-guideline-note.md`;
  - durable meta: `architectural-guideline-note.meta.env`.
- Add `write_staged_assessment(implement_tmpdir, assessment_text, *, assessed_head_sha, diff_fingerprint, base_ref)` writing staged body + sidecar + diff snapshot path reference.
- Add `pin_note_from_staged(implement_tmpdir, *, head_sha, base_ref)` mechanical writer: copy staged body verbatim into durable note + meta; **no semantic judgment**.
- Add `write_implement_note(...)` as internal helper used by `pin_note_from_staged`.
- Add `invalidate_implement_note(implement_tmpdir)` clearing staged body/sidecar/diff snapshot **and** durable note/meta.
- Add `note_consumable(implement_tmpdir, head_sha)` used by ship/final-report readers.
- Add `read_main()`, `materialize_diff_main()`, `write_staged_assessment_main()`, `pin_note_from_staged_main()`, and `invalidate_main()` CLI entries.
- **Do not** add `assess_implementation()` or any Python semantic deviation scorer.
- CLI `read` output:
  - absent: `ARCHITECTURAL_GUIDELINES_STATUS=absent` only.
  - present: status and canonical path KVs, then normalized parsed-entry block via `issue_wire.emit_untrusted_content_block("architectural_guidelines", normalized_text)` (no raw whole-file markers; no non-`G-*` prose).
  - invalid: status plus warning; no content block.
- Keep the helper side-effect-free except for explicit staged/durable implement paths and `invalidate`.

### UPDATED: python/issue_wire.py

- Add `emit_untrusted_content_block(tag: str, text: str) -> str` using `redact_untrusted_stream(text)` with the same XML wrapper shape as file blocks.
- Register CLI `untrusted content-block TAG` (stdin or `--text`) if needed for harness parity.
- Leave `emit_untrusted_file_block` Path-only unchanged.

### UPDATED: python/cli.py

- Register `architectural-guidelines read`, `materialize-diff`, `write-staged-assessment`, `pin-note-from-staged`, and `invalidate`.
- Add all five to public command allowlists used by tests.
- `write-staged-assessment` accepts orchestrator-supplied assessment text (`--assessment-file` or `--assessment-text`), current `ASSESSED_HEAD_SHA`, and fork-aware base metadata; it writes staged body + sidecar; it does not judge deviations.
- `pin-note-from-staged` is mechanical only: reads staged body + sidecar, writes durable note/meta for supplied current `HEAD_SHA`.
- `invalidate` is mechanical only: calls `invalidate_implement_note()`; no reassessment.

### NEW: python/test_architectural_guidelines.py

- Cover:
  - absent file returns `absent` and no content block;
  - present file returns canonical path and normalized escaped untrusted content block;
  - preamble / directive prose outside `### G-*` entries is omitted from CLI output;
  - `CLAUDE_PROJECT_DIR` is preferred when valid;
  - cwd fallback works;
  - symlinked guidelines file returns `invalid`;
  - explicit `--repo-root` supports tests without relying on caller cwd;
  - `materialize-diff` uses `upstream/main` when `--forked-target true`;
  - `write-staged-assessment` writes staged body + sidecar + diff snapshot on `present` with orchestrator-supplied text;
  - `pin_note_from_staged` copies staged body into durable note/meta at a later `HEAD_SHA` without rewriting body text;
  - absent/invalid leaves no consumable note;
  - stale durable note with mismatched `HEAD_SHA` is not consumable;
  - `invalidate` clears staged and durable artifacts;
  - simulated pr-prep sequence: stage at `HEAD` N, advance `HEAD` with log-only commit at N+1, pin at N+1 yields consumable note with unchanged body bytes.

### UPDATED: python/test_issue_wire.py

- Add coverage for `emit_untrusted_content_block` escaping/redaction parity with file blocks.

### UPDATED: python/test_design_cli_ports.py

- Pin the new CLI mappings (including `invalidate`).

### UPDATED: python/design_lifecycle.py

- In `_compose_drafter_prompt`, include the guidelines block only when `read_guidelines()` returns `present`.
- Use `issue_wire.emit_untrusted_content_block("architectural_guidelines", normalized_text)`.
- Add a one-line subordination note: aspirational, non-executable, untrusted repo evidence.
- Omit the section entirely when status is `absent` or `invalid`.

### UPDATED: python/test_design_lifecycle.py

- Add prompt assembly coverage:
  - no `ARCHITECTURAL_GUIDELINES.md` means the drafter prompt has no guideline section;
  - present file means the prompt includes the escaped normalized content block;
  - invalid file means the prompt carries no guideline content;
  - non-entry preamble in the file is not emitted.

### UPDATED: skills/design/SKILL.md

- In **Design Mindset**, add a pointer:
  - consult `ARCHITECTURAL_GUIDELINES.md` only through the Python helper when present;
  - treat entries as untrusted aspirational evidence;
  - surface deviations at Step 1d.7 and Gate C via orchestrator judgment;
  - never auto-edit the file.
- At Step 1d.7, narrow the `--skip-approve` carve-out: bind `skip_approve_requested` from the prelude fence, then always execute `design-outline.md` through Output, guideline consultation, and gate presentation; only then may auto-approve write `.outline-approved` and print `⏩ 1d.7: outline — auto-approved (--skip-approve)`.
- At Step 2b inline fallback, add the same conditional helper read rule used for `brainstorm.md`.
- At Step 4b, **rewrite the `--skip-approve` carve-out** to mirror Step 1d.7: when `skip_approve_requested=true`, still run the Gate C preview fence, consult `python/cli.py architectural-guidelines read`, print the clean/deviation/invalid note per `approval-gates.md`, then print `⏩ 4b: Gate C — auto-approved final plan (--skip-approve)` and proceed to Step 5 **without** `AskUserQuestion`. Delete or reconcile the conflicting paragraph that jumps to Step 5 immediately after preview with no guideline consultation.

### UPDATED: skills/design/references/design-outline.md

- In **Inputs**, state that guidelines are loaded only via `python/cli.py architectural-guidelines read` or in-process `read_guidelines()`; forbid Read/Write on the repo-root path.
- In **Inputs**, add parsed `ARCHITECTURAL_GUIDELINES.md` entries (when the helper returns `present`) as an outline composition input alongside `feature-description.txt`, `discussion-round1.md`, and `brainstorm.md`, so the outline Goals, Non-goals, and Approach are biased by the guidelines at composition, not only deviation-checked at the gate.
- Add proposal-gate presentation rules:
  - absent: no output change;
  - present clean: print the clean consulted note;
  - present deviations: print deviations plus rationale before the approval prompt;
  - invalid: print helper warning, skip deviation assessment, continue;
  - `--skip-approve`: still print the applicable note immediately before the auto-approval breadcrumb.
- Add the untrusted-evidence boundary sentence to the gate section.
- Keep the outline schema unchanged.
- **Rewrite the Approval prompt section** so `skip_approve_requested=true` no longer short-circuits before guideline consultation. On `--skip-approve`, the orchestrator MUST still:
  1. run Output (print the proposed outline when the entry guard did not skip it);
  2. call `python/cli.py architectural-guidelines read` (or in-process `read_guidelines()`);
  3. print the absent/present-clean/present-deviations/invalid note per the presentation rules above;
  4. only then write `$DESIGN_TMPDIR/.outline-approved`, print `⏩ 1d.7: outline — auto-approved (--skip-approve)`, and proceed to Step 2a without `AskUserQuestion`.
- Remove or replace the stale text that writes `.outline-approved` immediately and skips outline/guideline surfacing on the auto-approve path.

### UPDATED: skills/design/references/approval-gates.md

- In Gate C presentation, add the same absent / present-clean / present-deviations / invalid branches after the mandatory plan preview and before the prompt.
- **Rewrite the Gate C `--skip-approve` auto-approve carve-out**: when `skip_approve_requested=true`, still run the Step 4b preview fence, consult guidelines, print the applicable note, then print `⏩ 4b: Gate C — auto-approved final plan (--skip-approve)` and proceed to Step 5 without `AskUserQuestion`. The skip path must not bypass guideline consultation.
- Preserve existing large-plan preview behavior.
- Preserve `See full plan`, `Other`, cap, and interactive Gate C semantics on non-skip runs; auto-approve still runs guideline note after preview and before the `⏩ 4b` breadcrumb.

### UPDATED: skills/implement/SKILL.md

- Add a dedicated **Architectural guidelines (Phase A — staging)** subsection **immediately after Step 7a** (after `7a.r` routing completes) and **before Step 8**.
- State explicitly that it runs unconditionally on every path that completes Step 7a, including Step 6 `FILES_CHANGED=false` skip-to-7a and Step 7 skipped/no-op paths; do not nest it under Step 7's `FILES_CHANGED=true` rebase subsection.
- In that subsection:
  - clear stale durable, staged, and diff artifacts first (including `architectural-guideline-staged-assessment.md`);
  - run `python/cli.py architectural-guidelines read`;
  - if absent, do nothing further;
  - if invalid, log warning and continue;
  - if present, run `python/cli.py architectural-guidelines materialize-diff --forked-target "${forked_target:-false}"`, perform prompt-side deviation judgment against parsed entries, then persist staged assessment body + sidecar via `python/cli.py architectural-guidelines write-staged-assessment` with orchestrator-authored text for `ASSESSED_HEAD_SHA` at current `HEAD`;
  - at Phase A completion on `present`, also print the clean or deviation note to chat and append a `Warnings` entry to `$IMPLEMENT_TMPDIR/execution-issues.md` so the operator sees deviations even when Phase B (PR body / final report) is later skipped; durable Phase B surfacing is additive, not the sole channel;
  - **do not** call durable `pin-note-from-staged` here;
  - continue to Step 8 only after Phase A completes (or is skipped because absent/invalid).
- **Rewrite the Step 7a terminal anti-halt line** from "Continue to Step 8 IMMEDIATELY" to require **Architectural guidelines Phase A staging** (read → materialize-diff → orchestrator assess → write-staged-assessment when `present`) **before Step 8**, then continue to Step 8. Step 7a diagrams are still not the end of the run; PR creation, CI monitoring, and merge still must run after Step 8+.
- **Rewrite the Step 6 `FILES_CHANGED=false` anti-halt line** so it still says IMMEDIATELY skip to Step 7a for checks/diagrams, and add an explicit cross-reference that architectural-guidelines **staging** runs **after Step 7a**, not on the Step 6 skip branch itself.
- Document **Phase B**: `ship.py` pins durable note from staged assessment **immediately before every `compose_pr_body()` call** (fresh and `open-pr` resumes alike); Python performs no semantic assessment. On the fresh path, pin after any pre-compose `flush_logs_pre` log-only HEAD bump; on `open-pr` and other resumes that skip that flush block, pin still runs at the shared pre-compose site.
- Document **reassessment on implementation `HEAD` drift**: after CI-fix commits, conflict-resolution edits, or other code-mutating Step 8+ paths, orchestrator reruns Phase A before the next `step-8-ship.sh` re-invoke; `ship.py` only invalidates stale notes. Prompt-side reassessment may call `python/cli.py architectural-guidelines invalidate` when re-entering outside the normal Phase A subsection; Phase A entry clearing remains authoritative.
- Before Step 16–17, when staged assessment exists but note is not consumable, run foreground `python/cli.py architectural-guidelines pin-note-from-staged` against current `HEAD` (mechanical).
- State deviations are warnings only and never block PR creation.
- Add the untrusted-evidence boundary sentence for prompt-side assessment.

### NEW: skills/implement/scripts/step-architectural-guidelines-read.sh

- Thin launcher for `python/cli.py architectural-guidelines read` (single post-7a fence site).

### NEW: skills/implement/scripts/step-architectural-guidelines-materialize.sh

- Thin launcher for `python/cli.py architectural-guidelines materialize-diff --forked-target "${forked_target:-false}"`.

### NEW: skills/implement/scripts/step-architectural-guidelines-write-staged.sh

- Thin launcher for `python/cli.py architectural-guidelines write-staged-assessment` with orchestrator-supplied `--assessment-file`.

### UPDATED: scripts/residual-bash-paths.txt

- Register all four new implement guideline scripts alongside existing `skills/implement/scripts/*.sh` rows:
  - `skills/implement/scripts/step-architectural-guidelines-read.sh`
  - `skills/implement/scripts/step-architectural-guidelines-materialize.sh`
  - `skills/implement/scripts/step-architectural-guidelines-write-staged.sh`
  - `skills/implement/scripts/test-architectural-guidelines-step.sh`

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- After autonomous CI-fix step 9 (commit) and before step 11 (push), insert **architectural-guidelines reassessment (Phase A)** when guidelines were previously `present` or staged/durable artifacts exist:
  - optionally call `python/cli.py architectural-guidelines invalidate` (or rely on Phase A entry artifact clearing, which is authoritative);
  - rerun read → materialize-diff → orchestrator assess → `write-staged-assessment` (staged body + sidecar);
  - do **not** call durable pin here (Phase B runs inside ship at the shared pre-`compose_pr_body` site).
- Before step 12 re-invoke of `step-8-ship.sh`, note that ship will pin from staged assessment during pr-create compose regardless of `resume.start`.
- On Exit 0 continuation loops that follow internal ship CI-fix commits, same reassessment rule applies before re-invoke when implementation diff changed.

### UPDATED: skills/implement/references/conflict-resolution.md

- Before Phase 4 exit 0 re-invoke of `step-8-ship.sh` for `caller_kind=ship_pr_pre_push`, add the same Phase A reassessment block when conflict-resolution edits changed implementation files and guidelines were `present` (optional `architectural-guidelines invalidate`, then Phase A rerun).

### UPDATED: python/pr_body.py

- Add an optional `architectural_guidelines_note: str = ""` parameter to `compose_pr_body()`.
- When non-empty, append it as a `## Architectural guidelines` section before the Code Flow Diagram or Test plan.
- Preserve exact existing body output when the parameter is empty.
- Keep Mermaid validation and `redact_pr_body` behavior unchanged.

### UPDATED: python/ship.py

- Extract a single pre-compose helper (for example `_pin_and_load_guidelines_note(implement_tmpdir, head_sha, base_ref) -> str`) that calls mechanical `architectural_guidelines.pin_note_from_staged()` when staged assessment exists, then returns the redacted note text only when `note_consumable()` succeeds for current `HEAD`.
- Invoke that helper **immediately before every `pr_body.compose_pr_body()` call** in the pr-create path, including `resume.start=open-pr` and other non-fresh resumes that skip the fresh-path `flush_logs_pre` block. On `resume.start=fresh`, run after `run_logs.flush_logs_pre` (when present) and before compose so log-only HEAD bumps are reflected in the pinned `HEAD_SHA`.
- Pass the returned note into `compose_pr_body()` only when consumable.
- On CI-fix, conflict-resolution, or other **implementation** commits inside the driver, call `invalidate_implement_note()` only; **do not** rerun orchestrator assessment inside Python.
- Do not fail PR creation if guidelines are absent, unstaged, or unconsumable.
- Treat unreadable, symlinked, or stale note files as absent.

### UPDATED: python/final_report.py

- Load the implement note only through `note_consumable()` for current `HEAD`.
- Pipe appended note text through `python/cli.py redact secrets` (and existing tmpdir-path redaction helpers if needed) before writing `summary-final.md` and committed run-log final summaries.
- Append after the compact run summary and before review detail, or after review detail if that is less invasive.
- Preserve existing summary output when absent or unconsumable.
- Ensure both Step 17 and Step 18b paths reuse the same final-report writer.
- Rely on orchestrator Phase A + mechanical pin before Step 16–17 when staged assessment exists but note is stale.

### UPDATED: python/test_pr_body.py

- Assert `compose_pr_body()` output is byte-identical on the no-note path.
- Assert a non-empty guideline note appears in the PR body.
- Assert redaction and Mermaid validation still run.

### UPDATED: python/test_ship.py

- Add coverage that `pin_note_from_staged` runs immediately before `compose_pr_body()` on the fresh happy path (after `flush_logs_pre` when applicable).
- Add coverage that `resume.start=open-pr` (or equivalent non-fresh pr-create resume) still pins before `compose_pr_body()` even when the fresh-path flush block is skipped.
- Add coverage that internal CI-fix implementation commits call `invalidate_implement_note()` only (no in-driver reassessment).
- Add coverage that consumable notes reach `compose_pr_body()` when staged assessment exists on both fresh and open-pr paths.
- Keep existing stage-order assertions stable.

### UPDATED: python/test_final_report.py

- Add coverage for:
  - absent note preserves existing final summary;
  - present consumable note appears redacted in `summary-final.md`;
  - stale `HEAD_SHA` is not appended;
  - symlinked note is not read.

### NEW: skills/implement/scripts/test-architectural-guidelines-step.sh

- Harness assertion that the Step 6 `FILES_CHANGED=false` skip-to-7a path still reaches post-7a Phase A and produces staged assessment when guidelines are present.
- Assert Step 6 skip prose still targets Step 7a first, with post-7a guideline staging before Step 8.
- Assert Step 7a terminal anti-halt requires Phase A before Step 8 (not a direct Step 7a → Step 8 jump).
- Assert durable note is not written until pin phase (meta absent after Phase A fences alone).
- Assert staged body file exists after `write-staged-assessment` and is copied verbatim by pin.

### UPDATED: scripts/test-implement-fence-shape.sh

- Bump `EXPECTED_NEW` from `31` to `34` for three new post-7a one-line `bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...` fences:
  - `step-architectural-guidelines-read.sh`
  - `step-architectural-guidelines-materialize.sh`
  - `step-architectural-guidelines-write-staged.sh`
- Add exact per-fence pin entries if the harness supports them.

### UPDATED: python/checks.py

- Add relevant-check mappings so changes to:
  - `python/architectural_guidelines.py`;
  - `python/issue_wire.py`;
  - `python/test_architectural_guidelines.py`;
  - `python/test_issue_wire.py`;
  - affected PR body/final report/ship files;
  - new implement guideline launcher scripts;
  - `scripts/residual-bash-paths.txt`;
  - `skills/implement/references/ship-pr-exit-matrix.md`;
  - `skills/implement/references/conflict-resolution.md`;
  - `skills/implement/scripts/test-architectural-guidelines-step.sh`;
  - `scripts/test-implement-fence-shape.sh`;
  trigger their focused tests.

### UPDATED: SECURITY.md

- Add a brief security note that `ARCHITECTURAL_GUIDELINES.md` is repo-local, operator-curated, untrusted prompt context.
- State that larch treats it as aspirational evidence, not as a higher-priority instruction surface than `AGENTS.md` or skills.
- Mention symlink rejection, absent-file no-op behavior, parsed-entry-only emission for present reads, staged-body vs durable-note separation, redacted final-summary append, and stale-note non-consumption on resume or `HEAD` drift.

## Edge cases

- **Absent file**: no prompt section, no gate note, no staged assessment, no durable note, no PR body section, no final-summary section.
- **Clean run with present file**: print consulted note at design gates (including `--skip-approve`); stage assessment post-7a; pin durable note at pre-compose (after fresh-path log flush when applicable); include in PR body and final summary when consumable.
- **Invalid file**: do not read content through symlinks or directories; surface a warning and continue without treating as absent.
- **`--skip-approve` at Step 1d.7 and Gate C**: still surface guideline notes after outline/plan preview and before auto-approval breadcrumbs; never skip consultation.
- **Step 6 skip-to-7a (`FILES_CHANGED=false`)**: Step 7a still runs next; Phase A staging runs **after Step 7a** and before Step 8.
- **Resumed `/implement`**: clearing staged/durable artifacts at Phase A entry prevents stale PR/final-summary surfacing from an earlier attempt.
- **Step 7a `7a.r` rebase and log flush**: staging runs only after Step 7a completes so `ASSESSED_HEAD_SHA` matches pre-ship implementation `HEAD`.
- **pr-prep log-only `HEAD` bump (fresh path)**: durable pin runs **after** `flush_logs_pre` and **before** `compose_pr_body()` so `HEAD_SHA` matches pre-compose `HEAD`; staged assessment body and fingerprint remain valid because implementation diff is unchanged.
- **`open-pr` resume**: no fresh-path `flush_logs_pre`, but Phase B pin still runs immediately before `compose_pr_body()` so PR body can include guideline warnings from post-7a staged assessment.
- **Late Step 8+ implementation edits**: invalidate staged/durable artifacts; orchestrator reruns Phase A before next ship re-entry; Phase B repins on next compose path.
- **Forked `/implement`**: `materialize-diff` and meta `BASE_REF` use `upstream/main`; still include the note in the PR body and run summary when a PR is created.
- **Emergency `/implement`**: consult and warn when present, but never block emergency flow.
- **Non-`G-*` prose in guidelines file**: ignored by parser; never reaches drafter, gates, or implement assessment input.
- **Generated code-flow or log-only changes**: orchestrator judgment decides whether they constitute notable deviations; log-only commits do not invalidate staged assessment body, but do require Phase B repin at a new `HEAD_SHA`.

## Failure modes

- If the reader cannot resolve a repo root, treat guidelines as absent and preserve behavior.
- If helper output is malformed, surface a warning and continue.
- If `materialize-diff` fails, log a warning and continue without staged or durable artifacts.
- If writing staged assessment fails in `/implement`, log a warning and continue without durable surfacing.
- If staged body is missing at pin time, `pin_note_from_staged` logs a warning and skips durable surfacing.
- If `pin_note_from_staged` fails, log a warning, leave durable note absent, and continue PR creation without the guideline section.
- If PR body or final summary append logic fails, fail through existing PR/final-report error paths, not a special new path.
- If post-drift Phase A reassessment fails before ship re-entry, log a warning and omit the guideline section rather than surfacing a stale pre-fix note.
- If orchestrator skips Phase A after Step 7a, Step 8 may proceed but PR/final-summary will lack guideline sections until a later Phase A + pin path runs.

## Testing strategy

- Run `make lint`.
- Run `make py-lint`.
- Run `make py-test`.
- Focused tests during development:
  - `python3 -m pytest python/test_architectural_guidelines.py`
  - `python3 -m pytest python/test_issue_wire.py -k content_block`
  - `python3 -m pytest python/test_design_lifecycle.py -k guideline`
  - `python3 -m pytest python/test_pr_body.py -k guideline`
  - `python3 -m pytest python/test_final_report.py -k guideline`
  - `python3 -m pytest python/test_ship.py -k guideline`
  - `python3 -m pytest python/test_design_cli_ports.py`
  - `make test-implement-fence-shape`

## Acceptance

- `ARCHITECTURAL_GUIDELINES.md` exists with only the seeded current categories.
- `AGENTS.md` links it as a canonical source.
- `/design` proposal approval and Gate C surface clean, deviation, or invalid-warning notes when applicable, including `--skip-approve`.
- `/design` gates never load repo-root guidelines through the Read tool.
- `design-outline.md` and `approval-gates.md` `--skip-approve` sections no longer short-circuit before guideline consultation.
- `skills/design/SKILL.md` Step 4b `--skip-approve` carve-out matches Step 1d.7 (preview + guideline note, then auto-approve).
- The Step 1d.7 outline consumes parsed guideline entries when present, so the outline is biased at composition, not only deviation-checked afterward.
- CLI `read` emits only parsed `G-*` entries via `emit_untrusted_content_block`; non-entry prose is excluded (test-covered).
- Inline Step 2b fallback accounts for present guidelines, not only the drafter subprocess.
- `/implement` runs Phase A staging unconditionally **after Step 7a** and before Step 8, including the Step 6 no-review-changes path.
- Phase A writes `architectural-guideline-staged-assessment.md` plus sidecar; Phase B copies staged body verbatim into durable note.
- Step 7a terminal anti-halt requires Phase A before Step 8; orchestrator does not jump directly from Step 7a to Step 8 when guidelines are present.
- Durable note/meta are pinned mechanically **immediately before every `compose_pr_body()` call** (fresh and `open-pr` alike), with fresh-path pin after any pre-compose log flush.
- Python does not perform semantic deviation scoring; orchestrator judgment supplies assessment text to `write-staged-assessment`.
- `ship.py` never reruns orchestrator assessment; it only invalidates on implementation drift and pins from staged assessment before compose.
- `python/cli.py architectural-guidelines invalidate` exists and is allowlisted; reference docs no longer cite a nonexistent verb.
- All four new Bash scripts are listed in `scripts/residual-bash-paths.txt`.
- CI-fix and conflict-resolution reference docs document Phase A reassessment before `step-8-ship.sh` re-invoke.
- Forked runs materialize diffs against `upstream/main`.
- `/implement` includes clean or deviation notes in PR body and final run summary only when note/meta are consumable for current `HEAD`.
- `/implement` Phase A prints the clean or deviation note to chat and appends a `Warnings` entry to `execution-issues.md` on `present` at completion, so deviations reach the operator even when Phase B surfacing is skipped (not solely via PR body / final summary).
- Missing or stale guidelines produce no extra output or persisted sections.
- Post-implementation `HEAD` changes invalidate artifacts and require orchestrator reassessment before durable surfacing resumes.
- `scripts/test-implement-fence-shape.sh` `EXPECTED_NEW=34` matches three new post-7a fences.
- No code path auto-edits `ARCHITECTURAL_GUIDELINES.md`.

diff_lines: 1040

## Test plan
(no test plan section in plan-file)
