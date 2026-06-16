# Round 1 — Scope and Hard Constraints (issue #4169, sh-to-py C1a5 waterfall dispatcher)

## Decision 1: Cutover scope = full hard cutover + delete
- **Question**: How far does this piece go, given the plan-review panel/voter dispatch (C3a1) reaches the waterfall via gzip-embedded bash, plus the C1b /review façade and dispatch-code-voters.sh?
- **Resolution**: Full cutover. Add the `agent dispatch-waterfall` CLI verb + importable function + colocated pytest. Retarget every live caller: `python/decompose.py` (panel + aggregate), `python/legacy_review_shell/dispatch-panel.sh` and `aggregate-findings.sh`, `scripts/dispatch-code-voters.sh`, and the C3a1 gzip-embedded plan-review panel/voter bash (regenerate the embedded blobs from reviewable sources so they call the new verb). Then delete `scripts/dispatch-with-waterfall.sh` + harnesses, add the manifest row, and make `lint-retired-scripts` green. This satisfies the umbrella Definition of Done.
- **Source**: user

## Decision 2: Preserve full process-subtree teardown
- **Question**: Must the Python port preserve the bash dispatcher's aggressive process-group / subtree kill on timeout and cancel?
- **Resolution**: Yes. Replicate the EXIT/TERM teardown that reaps each launched reviewer's whole process-group subtree (current bash uses `set -m` + traps + recursive pgrep kill). The Python port must avoid orphaned codex/cursor/claude subprocesses on cancel or timeout (e.g. start each launcher in a new session and kill the process group, plus a descendant sweep).
- **Source**: user

## Decision 3: Reuse existing agent launcher/collector CLI surface (no re-implementation)
- **Question**: Does the port re-implement reviewer launch/collection, or reuse existing surfaces (Pieces 3/4 dependency)?
- **Resolution**: Reuse. The current `.sh` already shells out to `python3 cli.py agent launch-review`, `agent launch-claude-review`, and `agent collect-results --summary-only`. The port keeps calling that same stable CLI surface (or its importable equivalent). It does not re-implement launching or collection. This is how the blocked-by Piece 3 / Piece 4 dependency is satisfied.
- **Source**: codebase

## Decision 4: Caller inventory to retarget (must-not-break surfaces)
- **Question**: Which call sites must be retargeted under full cutover?
- **Resolution**:
  - `python/decompose.py` lines ~460 (panel) and ~610 (aggregate); currently env-overridable via `DECOMPOSE_PANEL_WATERFALL_SH` / `DECOMPOSE_AGGREGATE_WATERFALL_SH`.
  - `python/legacy_review_shell/dispatch-panel.sh` (`DISPATCH_WATERFALL` default) and `aggregate-findings.sh` (`AGGREGATE_DISPATCH_SH` default).
  - `scripts/dispatch-code-voters.sh` (direct invocation, ~line 142) — a separate migration piece but a live caller; its call site must repoint to the new verb so the `.sh` can be deleted.
  - C3a1 gzip-embedded plan-review panel + voter bash inside `python/plan_review.py` (materialized root symlinks the real `scripts/`, so it reaches the on-disk `.sh`). Regenerate the embedded source to call the new verb.
  - On-disk skill/doc references: `skills/design/references/plan-review.md`, `skills/design/references/decompose-panel.md`, `skills/review/SKILL.md`, `skills/shared/voting-protocol.md`, `docs/*`, `SECURITY.md`.
- **Source**: codebase

## Decision 5: Behavioral parity surface (preserve byte-for-byte contracts)
- **Question**: What observable behavior must the port preserve?
- **Resolution**: Preserve all of: NDJSON slot parsing + validation (slot/tool/output/agent|prompt_file, mutual-exclusion, newline-in-path rejection, empty-manifest exit 2); three-phase fallback (primary tool -> other present tool -> claude); `STATUS=OK`/`cap_hit` settle semantics; `--require-result-pattern` and `--require-first-line-pattern` ERE pre-validation + gating, including #3423 preamble salvage (strip leading narration, rewrite in place, settle); `--no-fallback` single-phase drop-on-failure with the per-slot dropped-slots TSV sidecar (`slot<TAB>tool<TAB>reason<TAB>snippet`, reasons format-gate-miss/result-gate-miss/empty/collector-failure/result-unreadable/tool-absent) and `ALL_SLOTS_DROPPED`; phase output path derivation (`-phaseN` suffix, `.txt` aware); line-oriented paths-file with atomic temp+`mv` replace and default `<slots-file>.output-files`; the full stdout KV grammar (PHASE1/2/3_SLOTS, ALL_OUTPUT_FILES[_PATH], ALL_OUTPUT_TOOLS, FALLBACK_COUNT, COMBINED_FALLBACK_COUNT, WARN=cost-fallback-exceeded-threshold, DISPATCH_OK, STATIC_DISPATCH_OK, DYNAMIC_DISPATCH_OK); `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default 3); fd-3 `emit_kv` contract-stream output.
- **Source**: codebase + issue scope text

## Non-goals
- Do not port `dispatch-code-voters.sh` itself (separate piece); only retarget its call site.
- Do not port the C1b /review or C3a1 plan-review bodies in-process (separate tracks); only repoint their waterfall invocation.
- No grouped reuse-by-copy (already removed; keep it removed — `test-no-grouped-reuse-guard.sh` intent must be preserved in pytest).
