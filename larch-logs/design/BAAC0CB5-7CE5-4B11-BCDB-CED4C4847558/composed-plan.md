## Plan

## Files to modify/create

### UPDATED: `skills/design/SKILL.md`

- Add Step 2b drafter instructions for **optional dialectic candidates**:
  - Detect only genuine bistable forks.
  - Require two concrete approaches and a material, non-obvious tradeoff.
  - Cap at the top 1-2 decisions.
  - Do not classify scope questions or internal preferences as dialectic candidates.
- Extend the drafter output contract with an optional post-plan `LARCH_DIALECTIC_BEGIN` / `LARCH_DIALECTIC_END` JSON block before `LARCH_SCOUT_BEGIN`.
- Keep `NO_SKETCHES` and the Step 2a sentinel path intact.
- Document that `dialectic-resolutions.md` remains an empty legacy placeholder for this clarifier flow.
- **Defer candidate promotion until postplan success**: `parse_drafter_output()` may parse and validate dialectic JSON but must **not** write `dialectic-clarifier-candidates.json` during the drafter subprocess. The drafter launcher must write validated raw JSON to `$DESIGN_TMPDIR/.dialectic-raw-pending.json` before the subprocess exits so promotion survives the process boundary. Promotion runs only after terminal postplan success (`POSTPLAN_RC=0`) when `plan.txt` bytes are final for that Step 2b pass (see `agents.py` / `design_lifecycle.py`).
- Add **inline Step 2b fallback** instructions: when `DRAFTER_STATUS=fallback` or postplan inline retry writes `plan.txt`, the orchestrator may call `python/cli.py design dialectic-write-candidates` **only after** the retained `design-step2b-postplan.sh` fence succeeds (`POSTPLAN_RC=0`); same promotion/validation path as post-drafter promotion. Candidate absence remains non-fatal.
- In Step 4b, load `references/dialectic-clarifier.md` **only when** `skip_approve_requested=false` **and** any of these exist under `$DESIGN_TMPDIR` **and** pass fingerprint validity (see `dialectic-clarifier.md` § deferred-load guard):
  - `dialectic-clarifier-candidates.json` whose `plan_fingerprint` matches current `plan.txt` sha256.
  - `dialectic-clarifier-status.json` whose fingerprint + ordered candidate ids match current `plan.txt` and live candidates, with a fingerprint-valid `dialectic-clarifier-digest.md`.
  - `dialectic-manual-candidates.json` whose `plan_fingerprint` matches current `plan.txt` (manual path; debate still re-validates fingerprint before id lookup).
  - On the common `NO_CONTESTED_DECISIONS` path, on `--skip-approve` runs, or when only stale/unfingerprinted artifacts exist: skip the load and use `approval-gates.md` alone.
- **Retarget Gate C mechanical emit**: replace all `design-step4b-preview.sh` references with `design-step3b-tail.sh`. Document Step 4 ordering owned by the tail wrapper: rejected findings → optional dialectic digest (cached sync no-op or foreground `dialectic-gatec` debate inside the tail) → `plan-review preview --variant gatec` → `SKIP_APPROVE_REQUESTED_GATEC` row. Gate C presentation prose in `approval-gates.md` must match this single entrypoint.
- **Step 4 orchestrator long-running contract** (normative; `run_in_background` is a Bash-tool attribute shells cannot set):
  - Before the Step 4 tail fence, bind mental `_step4_debate_may_run` when `skip_approve_requested=false` **and** fingerprint-valid `dialectic-clarifier-candidates.json` exists **and** no fingerprint-valid cached digest in `dialectic-clarifier-status.json` + `dialectic-clarifier-digest.md` (orchestrator may use a sync `python/cli.py design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR" --probe-only` fence when implemented, or read the same predicates from artifact files).
  - **Fast path** (`_step4_debate_may_run=false`): invoke `design-step3b-tail.sh` as a **foreground** Bash fence (default timeout).
  - **Debate path** (`_step4_debate_may_run=true`): invoke the **same** `design-step3b-tail.sh` fence with `run_in_background: true` and `timeout: 900000` (≥ clarifier budget 300-600s + cleanup slack). Read and apply `skills/shared/design-background-wait.md` with terminal sentinel `.completed/step-4`, confirmation purpose `durable completion`, and after-present: parse rejected-findings markers from notification stdout, then continue to Step 4b. **Do not** document or require immediate-background inside the shell wrapper; long-running wait is orchestrator-owned on the whole tail fence, mirroring Step 3.
  - Remove any contradictory prose assigning `run_in_background` or `<task-notification>` wait to `design-step3b-tail.sh` itself.
- In Gate C `Other` handling, follow the explicit dispatch table in `approval-gates.md` (debate prefix → write request file → `dialectic-manual --request-file`, then re-fire Gate C).
- Preserve `--skip-approve`: show any digest already produced by the tail when present and fingerprint-valid, but **do not launch new auto debate** on skip runs; then auto-approve without adding a halt.
- **Resume / re-entry digest presentation only**: on `resume@4b`, pause recovery, or any Step 4b entry where the current turn has **no** fresh Step 4 tail stdout (tail wrapper did not run in this turn), Gate C Presentation must read and emit fingerprint-valid `dialectic-clarifier-digest.md` with untrusted advisory framing before the prompt. On the **normal same-turn path** (Step 4 tail just ran in this turn), treat tail stdout as authoritative for the digest; **do not** re-read and re-emit `dialectic-clarifier-digest.md` from disk. `.completed/step-4` alone is **not** a re-read trigger.

### NEW: `skills/design/references/dialectic-clarifier.md`

- Define the new **clarifier** contract.
- Include:
  - Detection bar.
  - Candidate JSON schema.
  - **Plan fingerprint binding**: each promoted candidate file carries `plan_fingerprint` = `sha256` of the exact `plan.txt` bytes that produced it; `dialectic-gatec` and deferred-load guards treat mismatch as stale and no-op auto debate.
  - **Promotion timing (normative)**: candidate files are written **only after** terminal Step 2b postplan success (`POSTPLAN_RC=0`). Drafter parse validates shape in the launcher subprocess and writes `$DESIGN_TMPDIR/.dialectic-raw-pending.json` before exit; `dialectic-promote-candidates` consumes that sidecar (or `--raw-dialectic-file`) after postplan using **final** `plan.txt` bytes for `plan_fingerprint`. Clear `.dialectic-raw-pending.json` at Step 2b drafter start and after successful promotion. Inline orchestrator fallback follows the same post-postplan rule.
  - **Stale invalidation**: any post-Step-2b `plan.txt` rewrite clears auto candidates and cached auto digest. **Authoritative choke points** (all invoke `python/cli.py design dialectic-clear-stale --design-tmpdir "$DESIGN_TMPDIR" --reason plan-rewrite` only after the rewrite chain that mutates `plan.txt` has fully succeeded, and **after** any `gate-b-dedup` rewrite when dedup runs on that path):
    1. **`design-step35-settle.sh`** — after successful post-dedup `gate-b-dedup` (when dedup rc is 0 and `plan.txt` may have changed) and again after successful `step2b-postplan` when `POSTPLAN_RC=0` (covers Gate A discussion rewrite, Gate B prompt-side apply, and discussion-round2 settle paths).
    2. **`python/plan_review.py`** — at successful exit of `_run_dedup` when rc is 0 (central hook site after dedup completes, including the `plan_changed` early-return path at `_run_apply` lines 1771-1773 that calls `_run_dedup` without a revise pass in that invocation). Do **not** call clear-stale immediately after `revise-waterfall` alone when dedup will still run and may mutate `plan.txt` again.
    3. **`python/design_postplan.py` / `python/cli.py design step2b-postplan`** — when `plan.txt` bytes change (hash compare against entry hash), including validator auto-fix success paths that rewrite `plan.txt` without touching `plan_review.py`.
    Document these three choke points here; callers must not add prompt-side-only clears that run before dedup completes.
  - **Manual request artifact (canonical)**: `$DESIGN_TMPDIR/dialectic-manual-request.txt` is the sole manual-request path. Gate C writes operator `Other` text there; `dialectic-manual --request-file` reads it. Deferred-load guards and `dialectic-clear-stale` never key off a separate dot sentinel.
  - **Manual request lifecycle on plan rewrite**: `dialectic-clear-stale` removes `dialectic-manual-request.txt` and stale manual digest/status when `plan.txt` fingerprint no longer matches, unless `dialectic-manual-candidates.json` still has a matching `plan_fingerprint` and a fingerprint-valid manual status+digest sidecar. Bare request-file presence without fingerprint-valid manual artifacts does **not** trigger deferred load.
  - **CHOSEN/ALTERNATIVE mapping** (normative; single binding rule):
    - `option_a` and `option_b` are **display labels only** (Option A / Option B in digest and operator-facing text).
    - `drafter_pick` ∈ `{option_a, option_b}` names the side aligned with the **current plan** (the choice the drafter already made).
    - **CHOSEN** = the option matching `drafter_pick`; **ALTERNATIVE** = the other option.
    - Ballot assembly maps CHOSEN → `THESIS` slot semantics and ALTERNATIVE → `ANTI_THESIS` slot semantics per `dialectic-protocol.md` (position rotation applies to Defense A/B placement, not to which option is CHOSEN).
    - Digest labels steelmen as **Option A** / **Option B** without attaching CHOSEN/ALTERNATIVE to a fixed side; separate lines carry **Drafter pick** and **Panel lean (advisory)**.
  - **Clarifier debater contract** (slim profile; not Step 2a.5 six-tag quorum):
    - One debater subprocess per side per decision, read-only.
    - Minimal required output: compact steelman text per side (plain prose or a small tagged block defined here).
    - Position rotation and attribution stripping per `dialectic-protocol.md` clarifier subset.
  - **Ballot assembly** (owned by `design_dialectic.py`):
    - Build **one** `dialectic-ballot.txt` containing all capped decisions (1-2 `DECISION_N` entries).
    - Launch **exactly three** Claude judge subprocesses for that single ballot (one vote line per `DECISION_N` per judge), reusing `dialectic-protocol.md` multi-decision ballot semantics.
    - Apply binary `THESIS` / `ANTI_THESIS` threshold rules and disposition enum from `dialectic-protocol.md`.
    - Do **not** import external-judge waterfalls, `render debate-retry`, per-decision judge panels, or six-tag quorum gates.
  - **Child-process lifecycle** (normative):
    - Launch each debater/judge via `python/cli.py agent launch-claude-subprocess` inside a `subprocess.Popen` started with **`start_new_session=True`** (or equivalent new process group) so the wrapper PID names a killable process group.
    - Run debaters in parallel under a shared clarifier wall-clock budget (300-600s total; per-slot timeouts derived from it).
    - On budget exceed, subprocess launch failure, or parent fail-open exit: **terminate then kill the entire process group** for every tracked wrapper PID (not the wrapper alone), drain outputs, and rely on the generation guard below so parent status/digest writers ignore stale results.
    - `finally` cleanup always reaps tracked process groups even on success.
  - **Late-write guard (normative; parent writers only)**:
    - Maintain `$DESIGN_TMPDIR/dialectic-clarifier-generation.txt` as a monotonic integer string.
    - **Increment** at the start of each auto or manual debate round (before launching debaters); record the active value as `generation` in `dialectic-clarifier-status.json` before any subprocess launch.
    - **Increment again** on fail-open kill/timeout before returning to Gate C so any in-flight children hold a stale generation.
    - `dialectic-clarifier-status.json` and `dialectic-clarifier-digest.md` writers must read the current generation file and **no-op** (exit without mutation) when the embedded `generation` does not match the live file value; use atomic write patterns (write temp + rename) after the generation check.
    - **Subprocess sidecars do not observe generation**; only parent-owned status/digest writers enforce the guard. Do not pass `DIALECTIC_GENERATION` env to subprocess collectors.
  - **Gate C tail debate contract** (Python foreground inside shell; orchestrator backgrounds whole tail when debate may run):
    - `dialectic-gatec` runs debate as a **foreground Python subprocess** inside `design-step3b-tail.sh` when auto debate is required (not Bash-tool immediate-background).
    - The Step 4 **orchestrator** backgrounds the entire tail fence when debate may be required (see `SKILL.md` Step 4 long-running contract).
    - `dialectic-gatec` writes `.completed/dialectic-gatec-terminal` on completion for optional mid-chain probes; the tail still writes `.completed/step-4` after preview completes.
  - Auto-run timing at Gate C (subject to fingerprint match and `skip_approve_requested=false`).
  - Manual on-demand flow.
  - Digest format with **untrusted advisory framing** (see `design_dialectic.py`): prefix every line of untrusted steelman/rationale text with a fixed marker (for example `> `) **and** escape any chosen Markdown fence delimiter in model text so debater/judge output cannot close the advisory boundary.
  - Operator outcomes:
    - **Approve final design** approves the **current plan** (drafter pick), not an automatic plan rewrite to the panel lean.
    - **Discuss further** is the path to revise the plan when the operator disagrees with the panel lean or drafter pick.
    - Manual debate via `Other` then re-fire Gate C.
  - Visible `Other` affordance shape: `debate <decision>: <option A> vs <option B>`; also allow `debate <candidate-id>` when `dialectic-clarifier-candidates.json` supplies both options **and** `plan_fingerprint` matches current `plan.txt`.
  - **Deferred-load guard** for Step 4b: load this reference only when `skip_approve_requested=false` **and** fingerprint-valid auto candidates, fingerprint-valid auto status+digest, or fingerprint-valid manual candidates+digest exist; bare stale file presence or a lone `dialectic-manual-request.txt` must not trigger load.
- State that debate output is advisory.
- State that the operator remains judge of last resort.
- State that digest stdout/markdown is **display-only** and must not drive orchestrator control flow.
- State that the external Codex/Cursor deep path is out of scope.

### UPDATED: `skills/design/references/approval-gates.md`

- Update Gate C **Presentation** to name `design-step3b-tail.sh` as the sole mechanical emit on the normal path (remove `design-step4b-preview.sh`). Document ordering inside the tail wrapper:
  1. Rejected-findings markers (unchanged).
  2. Read `skip_approve_requested` from `run-params.json`.
  3. When `skip_approve_requested=false`: optional `dialectic-gatec` (foreground Python debate inside tail when needed, or synchronous cached digest / no-op).
  4. When `skip_approve_requested=true`: skip auto debate; optionally print fingerprint-valid cached digest only.
  5. `plan-review preview --variant gatec` under `## Final Design Plan`.
  6. `SKIP_APPROVE_REQUESTED_GATEC` row.
- Document that long-running auto debate is bounded by the **orchestrator** backgrounding the whole Step 4 tail fence when debate may be required (`SKILL.md` Step 4 contract); the shell wrapper does not set `run_in_background`.
- **Resume / missing-stdout digest re-read** (narrow): when control arrives at Step 4b **without** digest stdout from a tail run in the **current turn** — for example `resume@4b`, pause recovery, or re-entry after `.completed/step-4` was written in a prior turn — read `$DESIGN_TMPDIR/dialectic-clarifier-digest.md` when `dialectic-clarifier-status.json` fingerprint matches current `plan.txt` and ordered candidate ids; emit with untrusted advisory framing. **Do not** re-read or re-emit on the normal same-turn path where Step 4 tail stdout already printed the digest. Skip when fingerprint-invalid or absent.
- Update Gate C presentation to include dialectic digest output when present, wrapped as untrusted advisory content (emitted by tail stdout on normal path, or by resume file read only when stdout absent, before preview).
- Add an explicit **`Other` dispatch table** with precedence:
  1. `debate …` / `debate-this …` (case-insensitive prefix) → write verbatim Other text to `$DESIGN_TMPDIR/dialectic-manual-request.txt` via the Write tool (no shell interpolation); invoke `python/cli.py design dialectic-manual --design-tmpdir "$DESIGN_TMPDIR" --request-file "$DESIGN_TMPDIR/dialectic-manual-request.txt"`; print digest or shape-error help; re-fire the same Gate C prompt. **Do not** pass operator text through `--request` at the prompt-side Gate C callsite.
  2. Full-plan phrases (`full plan`, `show plan`, etc.) → existing `plan-review preview --variant full` path.
  3. Unknown → short help listing both shapes, then re-fire Gate C.
- When text could match both debate and full-plan intents, **debate prefix wins**.
- Add prompt text making the on-demand affordance visible, for example: `Use Other to request debate <decision>: <option A> vs <option B> (or debate <candidate-id> when fingerprint-valid candidates exist).`
- Document that on-demand debate loops back to the same Gate C prompt.
- Clarify **Approve final design** semantics with digest present: approval publishes the current `plan.txt`; panel lean is recommendation only; use **Discuss further** to change the plan before approval.
- Keep the existing primary options and review-round cap behavior unchanged.

### UPDATED: `skills/design/scripts/design-step3b-tail.sh`

- Read `skip_approve_requested` from `run-params.json` **before** preview (move jq/grep block above `dialectic-gatec` and preview; today it sits after preview).
- When `skip_approve_requested=true`:
  - Skip `design dialectic-gatec` auto debate entirely (no new subprocess launches).
  - Optionally print an already-cached digest if present and fingerprint-valid (synchronous).
  - Continue existing preview and `SKIP_APPROVE_REQUESTED_GATEC` row unchanged.
- When `skip_approve_requested=false`, **before** the Gate C preview:
  - Invoke `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR"` as a **foreground** Python subprocess inside this shell script (not Bash-tool immediate-background).
  - `dialectic-gatec` behavior at this callsite:
    - Return 0 when there are no candidates, candidates are stale, or fingerprint mismatches.
    - Print nothing on no-op.
    - Print the compact digest when debate ran or a valid cached digest exists.
  - Write `$DESIGN_TMPDIR/.completed/dialectic-gatec-terminal` on `dialectic-gatec` completion (success, no-op, or fail-open).
- Keep the existing rejected-findings markers, pause check, preview call, and `SKIP_APPROVE_REQUESTED_GATEC` row ordering (dialectic only on non-skip auto path; preview always runs **after** `dialectic-gatec` returns).
- **Do not** document or implement `run_in_background` / `<task-notification>` in this wrapper; orchestrator-owned background applies to the whole tail fence per `SKILL.md` Step 4.

### UPDATED: `skills/design/scripts/design-step3b-tail.md`

- Add the Gate C dialectic clarifier call to the wrapper contract.
- Document `skip_approve_requested` gating before `dialectic-gatec` (before preview).
- Document foreground `dialectic-gatec` subprocess inside the tail and `.completed/dialectic-gatec-terminal` completion marker.
- Document that orchestrator backgrounds the **whole tail fence** when debate may be required; wrapper does not own immediate-background.
- Document digest-before-preview ordering and retirement of `design-step4b-preview.sh`.
- Note that the call is no-op when no candidate file exists, fingerprint mismatches, or skip-approve suppresses auto debate.
- Note that it must not mutate repository files.

### UPDATED: `skills/design/scripts/design-step35-settle.sh`

- After successful `gate-b-dedup` when dedup rc is 0 (post-rewrite dedup path; skip when dedup did not run or did not mutate), invoke `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-clear-stale --design-tmpdir "$DESIGN_TMPDIR" --reason plan-rewrite`.
- After successful `step2b-postplan` when `POSTPLAN_RC=0`, invoke the same clear-stale verb (covers Gate A, Gate B prompt-side apply, discussion-round2).
- Ordering: dedup → clear-stale (if dedup succeeded) → postplan → clear-stale (if postplan succeeded). Never clear before dedup on paths where dedup will still rewrite `plan.txt`.

### UPDATED: `skills/design/scripts/design-step35-settle.md`

- Document the two post-mutation `dialectic-clear-stale` calls and their ordering relative to dedup and postplan.

### UPDATED: `skills/design/references/discussion-rounds.md`

- In the Gate A plan-revision authority paragraph, note that successful discussion rewrites reach `design-step35-settle.sh`, which owns post-dedup stale clearing; orchestrator must not call `dialectic-clear-stale` before settle dedup completes.

### UPDATED: `skills/shared/design-background-wait.md`

- Register `.completed/step-4` as a valid `{terminal_sentinel}` for Step 4 whole-tail immediate-background waits (debate path).
- Register `.completed/dialectic-gatec-terminal` as an optional mid-chain sentinel for `dialectic-gatec` completion inside the tail.
- Add a **Step 4 post-notification** subsection: after confirmed completion, parse rejected-findings markers from tail stdout, bind `SKIP_APPROVE_REQUESTED_GATEC` and any digest stdout, then continue to Step 4b without re-reading digest file on the same turn.

### UPDATED: `python/cli.py`

- Register new verbs:
  - `design dialectic-gatec --design-tmpdir <path>` (optional `--probe-only` for orchestrator fast-path predicate)
  - `design dialectic-manual --design-tmpdir <path> --request-file <path>` (primary Gate C path); keep `--request <string>` for tests and internal callers only
  - `design dialectic-write-candidates --design-tmpdir <path> --content-file <path>` (inline fallback / orchestrator-authored candidates; **post-postplan only**)
  - `design dialectic-promote-candidates --design-tmpdir <path> --raw-dialectic-file <path>` (consume `.dialectic-raw-pending.json` after postplan)
  - `design dialectic-validate-candidates` (helper)
  - `design dialectic-clear-stale --design-tmpdir <path> --reason <token>` (called on plan rewrite choke points)
- Keep the verbs under `python/` stdlib-only runtime.

### NEW: `python/design_dialectic.py`

- Implement the dialectic clarifier logic.
- Data model:
  - Frozen dataclasses for candidate, option, debate output, judge vote, digest row, and status sidecar.
  - Parse external JSON at the edge.
- Candidate schema:
  - `plan_fingerprint`: required on promoted files.
  - `decisions`: list, capped to 2.
  - Each item includes `id`, `title`, `option_a`, `option_b`, `tradeoff`, `drafter_pick`, and `why_this_matters`.
  - Validate `drafter_pick` ∈ `{option_a, option_b}`.
- **Artifact ownership** (avoid conflicting writers):
  - `dialectic-clarifier-candidates.json`: written **once** after postplan success by `dialectic-promote-candidates` / `dialectic-write-candidates`; treated read-only thereafter.
  - `.dialectic-raw-pending.json`: written by drafter launcher after parse validation; consumed and removed by `dialectic-promote-candidates` after postplan success.
  - `dialectic-clarifier-generation.txt`: monotonic generation counter; incremented at debate start and again on fail-open kill.
  - `design_dialectic.py` writes distinct files only: `dialectic-clarifier-status.json`, `dialectic-clarifier-digest.md`, `dialectic-manual-candidates.json` (manual path), `dialectic-ballot.txt` (ephemeral), and optional digest-cache metadata inside status json.
  - `dialectic-manual-request.txt`: written by Gate C orchestrator only; read by `dialectic-manual`; cleared by `dialectic-clear-stale` on plan rewrite unless fingerprint-valid manual debate artifacts remain.
- Shared helpers:
  - `plan_fingerprint(design_tmpdir) -> sha256(plan.txt bytes)`.
  - `candidates_fingerprint_valid(design_tmpdir) -> bool`.
  - `should_defer_load_clarifier_reference(design_tmpdir) -> bool`: returns true only when `skip_approve_requested=false` from `run-params.json` **and** (fingerprint-valid auto candidates, fingerprint-valid auto status+digest, or fingerprint-valid manual candidates with matching status+digest). Lone `dialectic-manual-request.txt` or stale artifacts return false.
  - `read_generation(design_tmpdir) -> int`, `bump_generation(design_tmpdir) -> int`, `write_if_generation_matches(design_tmpdir, generation, writer_fn) -> bool`.
- `dialectic-gatec` behavior:
  - Validate `$DESIGN_TMPDIR`.
  - `--probe-only`: print `DIALECTIC_GATEC_DEBATE_REQUIRED=true|false` from fingerprint-valid candidates minus cached digest; exit 0; no subprocess launches.
  - Read `skip_approve_requested` from `run-params.json`; when true, no auto subprocess launches (cached digest print only if fingerprint-valid).
  - If no candidates or fingerprint ≠ current `plan.txt`: exit 0 with no output; call `dialectic-clear-stale` when stale artifacts remain.
  - If digest exists and status fingerprint matches current `plan.txt` plus ordered candidate ids: print cached digest (sync).
  - Otherwise bump generation, run debate within the clarifier wall-clock budget with tracked process-group terminate/kill on exceed or fail-open; on kill bump generation again before cleanup.
  - Write `.completed/dialectic-gatec-terminal` on all exit paths.
- `dialectic-clear-stale` behavior:
  - Remove or mark stale `dialectic-clarifier-candidates.json`, digest, status, `.dialectic-raw-pending.json`, and `dialectic-manual-request.txt` when `plan.txt` fingerprint no longer matches.
  - Preserve `dialectic-manual-candidates.json` and manual digest/status only when their embedded `plan_fingerprint` still matches current `plan.txt`.
- `dialectic-promote-candidates` behavior:
  - Read `--raw-dialectic-file` (default `$DESIGN_TMPDIR/.dialectic-raw-pending.json`).
  - Require current `plan.txt`; embed `plan_fingerprint` from **final** postplan bytes.
  - Atomically promote to `dialectic-clarifier-candidates.json`; remove raw pending sidecar on success.
- Cheap debate:
  - Use `python/cli.py agent launch-claude-subprocess` inside `Popen(..., start_new_session=True)`.
  - Launch one debater per side per decision with read-only constraints.
  - Build one multi-decision ballot; launch exactly three judge subprocesses (each in its own process group).
  - One bounded wait loop with clarifier-specific timeouts (total budget 300-600s).
  - On timeout/fail-open: bump generation, kill all tracked process groups; all status/digest writes go through `write_if_generation_matches`.
  - Use current `plan.txt` and candidate JSON as context files or bounded prompt content.
- Adjudication:
  - Derive CHOSEN from `drafter_pick`; ALTERNATIVE is the other option; map to THESIS/ANTI_THESIS for ballot/judges per `dialectic-protocol.md`.
  - Parse one vote line per `DECISION_N` from each of the three judges on the shared ballot.
  - Reuse binary threshold rules, 3-judge panel semantics, disposition enum (`voted | fallback-to-synthesis | bucket-skipped | over-cap`), and parser tolerance from `skills/shared/dialectic-protocol.md`.
  - Use Claude subprocess judge slots only.
  - Treat failed or malformed outputs as advisory fallback, not a blocker.
- Digest output:
  - Write `$DESIGN_TMPDIR/dialectic-clarifier-digest.md` only via `write_if_generation_matches`.
  - Write `dialectic-clarifier-status.json` including fingerprint = `sha256(plan.txt bytes)` + ordered candidate ids + `generation`.
  - Print a compact Markdown block inside an explicit untrusted advisory fence:
    - Prefix **every line** of steelman/rationale text with a fixed marker (for example `> `).
    - Escape whole-line larch markers, `KEY=value` control rows, and any Markdown fence delimiter characters in model text.
    - Decision
    - Option A steelman
    - Option B steelman
    - Panel lean and why (advisory)
    - Drafter pick
    - Operator note: Approve keeps current plan; Discuss further to change it
- Manual mode (`dialectic-manual`):
  - Read `--request-file` (canonical path `$DESIGN_TMPDIR/dialectic-manual-request.txt`; `--request` for tests only).
  - For `debate <id>`: require `dialectic-clarifier-candidates.json` with matching `plan_fingerprint`; reject with shape help when stale or missing options.
  - For free-form shapes: accept `debate <id>` when valid; otherwise require `decision + option A + option B` shape.
  - Write `dialectic-manual-candidates.json` with matching `plan_fingerprint`, run the same debate/digest path for one manual decision without overwriting the drafter candidates file.
- Failure behavior:
  - Fail open to Gate C with a warning when Claude subprocess launch fails or budget is exceeded (after process-group cleanup and generation bump).
  - Never block final approval solely because dialectic failed.
  - Append warnings to `execution-issues.md`.

### UPDATED: `python/agents.py`

- Extend `parse_drafter_output()` to accept the optional `LARCH_DIALECTIC_BEGIN` / `LARCH_DIALECTIC_END` block after `LARCH_PLAN_END` and before `LARCH_SCOUT_BEGIN`.
- Reject dialectic sentinels inside summary or plan envelopes (fatal, like scout).
- **Parse-only dialectic handling**: validate shape and cap in `parse_drafter_output()` but **do not write** `dialectic-clarifier-candidates.json` there. Extend `DrafterParseResult` with optional retained dialectic payload (or path to transient sidecar).
- **Mandatory process-boundary sidecar**: after successful dialectic parse in the drafter launcher path (`launch_codex_drafter` / Claude drafter collector), write validated JSON to `$DESIGN_TMPDIR/.dialectic-raw-pending.json` before the launcher subprocess exits. Parent `step2b_drafter_main` promotes from this file only after postplan success.
- **Malformed or missing dialectic JSON is non-fatal**: keep valid plan; emit `DIALECTIC_CANDIDATES_WRITTEN=false` and `DIALECTIC_CANDIDATES_FAIL_REASON=<reason>`; no candidate file until promotion succeeds post-postplan.
- Promotion to `dialectic-clarifier-candidates.json` happens in `step2b_drafter_main` via `dialectic-promote-candidates` **only after** internal postplan returns `POSTPLAN_RC=0`, using final `plan.txt` fingerprint.
- Add status rows:
  - `DIALECTIC_CANDIDATES_WRITTEN=true|false` (true only after post-postplan promotion)
  - `DIALECTIC_CANDIDATES_FAIL_REASON=<reason>` when applicable
  - `DIALECTIC_CANDIDATES_PARSED=true|false` when dialectic block was present and parsed
  - `DIALECTIC_RAW_PENDING_WRITTEN=true|false` when sidecar written at launcher exit
- Update `_CODEX_DRAFTER_TRUSTED_INSTRUCTIONS` and Claude drafter prompt expectations.
- Preserve existing plan/scout parsing behavior.
- In `launch_claude_subprocess` (or the dialectic caller wrapper): when invoked from `design_dialectic.py`, ensure the launched wrapper process is placed in a new session/process group and that SIGTERM/SIGKILL to the group reliably terminates the inner `claude` child on timeout (document the contract; implement via `start_new_session=True` on the outer `Popen` and group kill in clarifier cleanup).

### UPDATED: `python/design_lifecycle.py`

- Add the dialectic candidate instructions to `_compose_drafter_prompt()`.
- At Step 2b drafter start, remove stale dialectic candidate/digest/status artifacts and `.dialectic-raw-pending.json`.
- In `step2b_drafter_main`, after internal postplan succeeds (`POSTPLAN_RC=0`), call `dialectic-promote-candidates --raw-dialectic-file "$DESIGN_TMPDIR/.dialectic-raw-pending.json"` when the sidecar exists and validates.
- Preserve the existing Step 2a sentinel invariant:
  - `approach-synthesis.txt` is `NO_SKETCHES`.
  - `contested-decisions.md` is `NO_CONTESTED_DECISIONS`.
  - `dialectic-resolutions.md` exists and is empty.
- Do not make candidate absence a structural failure.
- Include dialectic status in Step 2b diagnostics only when relevant.

### UPDATED: `python/design_postplan.py`

- When `plan.txt` bytes change during postplan emit/validation (hash compare at entry vs exit), invoke `dialectic-clear-stale --reason plan-rewrite` so validator auto-fix and other postplan rewrites cannot leave stale candidates until Gate C.
- Postplan hash-change clear runs **before** any post-postplan candidate promotion in the same fence so promotion always keys off final bytes.

### UPDATED: `python/plan_review.py`

- At successful return (rc 0) of `_run_dedup`, invoke `python/cli.py design dialectic-clear-stale --design-tmpdir <tmpdir> --reason plan-rewrite`. This centralizes the hook for both the post-`revise-waterfall` dedup path and the `plan_changed` early-exit at `_run_apply` lines 1771-1773 that calls `_run_dedup` without a revise pass in that invocation.
- Do **not** call clear-stale immediately after `revise-waterfall` when dedup will still run and may mutate `plan.txt` again.

### UPDATED: `skills/shared/dialectic-protocol.md`

- Reframe stale Step 2a.5 decider language to the new Gate C clarifier language.
- **Explicitly preserve** as reusable core:
  - Ballot format (`DECISION_N`, Defense A/B, THESIS/ANTI_THESIS tokens)
  - **One ballot, multiple decisions** (up to caller cap)
  - Position rotation
  - Attribution stripping
  - Parser tolerance
  - Binary threshold rules
  - **3-judge panel** semantics (exactly three judges vote on the shared ballot; one vote line per `DECISION_N` per judge)
  - Disposition enum (`voted | fallback-to-synthesis | bucket-skipped | over-cap`)
  - `dialectic-resolutions.md` schema as **legacy/shared reference**
- Add a **Clarifier profile** subsection pointing to `dialectic-clarifier.md` for debater output shape and CHOSEN/ALTERNATIVE mapping (`drafter_pick` defines CHOSEN; Option A/B are display labels only).
- Remove or mark stale references to `skills/design/references/dialectic-execution.md`, `render debate-retry`, external per-side waterfalls, per-decision judge panels, and Step 3.5 still-contested handling.
- Document that `/design` now writes a compact clarifier digest, not a binding Step 2b resolution file.

### UPDATED: `SECURITY.md`

- Remove dialectic from the Codex/Cursor `launch-review` sentence (or mark that path legacy for removed Step 2a.5).
- Replace the stale Step 2a.5 debater waterfall note with the new trust boundary:
  - Step 2b drafter self-declared candidates derive from untrusted issue/operator text plus repo inspection; promoted only after postplan stabilizes `plan.txt`.
  - Claude subprocess debater and judge outputs are untrusted model output.
  - Only compact digests in an explicit untrusted advisory block reach Gate C; every untrusted line is prefixed and fence-delimiter-escaped so model text cannot break the display boundary.
  - Dialectic is advisory, display-only at Gate C, and never edits repository files.
  - Gate C manual debate requests must use `--request-file` pointing at `dialectic-manual-request.txt` (no shell-interpolated argv) at the prompt-side callsite.
- Update the outline trust-boundary paragraph if it still says dialectic agents consume the outline pre-draft.

### UPDATED: `python/test_agents.py`

- Add parser tests for:
  - Valid optional dialectic block parsed but **not** promoted by `parse_drafter_output()` (no candidates file).
  - Drafter launcher writes `.dialectic-raw-pending.json` on valid dialectic parse before subprocess exit.
  - Missing dialectic block remains valid.
  - Dialectic sentinels inside plan fail.
  - Malformed dialectic JSON degrades without invalidating a valid plan.
  - More than 2 candidates are capped or rejected consistently at parse edge.
  - Promotion after mock postplan uses final `plan.txt` fingerprint from sidecar.

### NEW: `python/test_design_dialectic.py`

- Cover:
  - No candidates: no output, rc 0.
  - Fingerprint mismatch: no output, rc 0, stale artifacts cleared.
  - Candidate validation rejects missing options and invalid `drafter_pick`.
  - Candidate cap is enforced.
  - Cached digest prints without relaunch when fingerprint matches.
  - `skip_approve_requested=true` suppresses auto subprocess launches.
  - `should_defer_load_clarifier_reference` false when `skip_approve_requested=true` even if cached digest exists.
  - `should_defer_load_clarifier_reference` false when only stale candidates or lone `dialectic-manual-request.txt` exists.
  - `--probe-only` emits correct `DIALECTIC_GATEC_DEBATE_REQUIRED` for orchestrator fast path.
  - Wall-clock budget exceed fails open **and** terminates tracked process groups; inner claude child does not survive wrapper kill.
  - **Generation guard (parent writers only)**: mocked late writer with stale generation cannot update status/digest after kill; generation bumps on fail-open; no sidecar generation env contract.
  - Malformed subprocess output yields advisory fallback.
  - Manual `debate <id>` rejects stale fingerprint with shape help (no debate).
  - Manual request without two options asks for clearer shape.
  - Digest rendering prefixes every untrusted line and escapes fence delimiters; includes Decision, Option A/B steelmen (no fixed-side CHOSEN labels), panel lean, drafter pick, and untrusted framing.
  - CHOSEN/ALTERNATIVE derived from `drafter_pick` when `drafter_pick=option_b`.
  - One shared ballot with two decisions launches exactly three judge subprocesses; each judge emits one vote line per `DECISION_N`.
  - Simulated postplan rewrite clears stale candidates then re-promotion matches final bytes from `.dialectic-raw-pending.json`.
  - Resume path: fingerprint-valid digest readable from `dialectic-clarifier-digest.md` when tail stdout is absent; normal path does not require file re-read.

### UPDATED: `python/test_design_lifecycle.py`

- Assert Step 2b prompt includes the dialectic candidate instructions.
- Assert Step 2b cleanup removes stale dialectic candidate/digest artifacts and `.dialectic-raw-pending.json`.
- Assert structural success does not require dialectic candidates.
- Assert `step2b_drafter_main` promotes candidates only after `POSTPLAN_STATUS=ok` and fingerprint matches final `plan.txt`.
- Assert postplan `plan.txt` mutation + promotion: candidates fingerprint equals post-postplan hash, not pre-postplan drafter hash.
- Assert promotion reads `.dialectic-raw-pending.json` written by launcher, not in-memory-only parse result.

### MAY_UPDATE: `scripts/test-design-structure.sh`

- Update wrapper contract checks for `design-step3b-tail.sh` dialectic-before-preview ordering, `skip_approve_requested` read placement, foreground `dialectic-gatec` + `.completed/dialectic-gatec-terminal`, and `design-step35-settle.sh` clear-stale calls after dedup/postplan.
- Assert `SKILL.md` Step 4 documents orchestrator `run_in_background` on whole tail when debate may run (not wrapper immediate-background).
- Keep the test focused on wrapper shape and ordering.

## Approach

- Use **Gate C** as the default surfacing point for post-review forks.
- Reason:
  - Step 2b can detect forks cheaply while drafting.
  - Gate C already has operator approval.
  - Post-review surfacing avoids adding a pre-draft pause.
- **Defer candidate promotion until postplan stabilizes `plan.txt`**: parse during drafter; write `.dialectic-raw-pending.json` at launcher exit; promote only after `POSTPLAN_RC=0` so validator auto-fix and inline-retry rewrites cannot orphan fingerprint-valid candidates before Gate C.
- Bind auto candidates to the **plan fingerprint** and clear them on every post-promotion `plan.txt` rewrite at documented choke points (**settle after dedup/postplan**, **`_run_dedup` rc=0 in plan_review**, **postplan hash change**) so Gate C never debates obsolete forks.
- Use **one canonical manual-request path** (`dialectic-manual-request.txt`) everywhere; deferred load requires fingerprint-valid contested artifacts, not bare request-file presence; clear manual request text on plan rewrite unless fingerprint-valid manual debate artifacts remain.
- On **`--skip-approve`**, suppress both auto debate launches **and** deferred `dialectic-clarifier.md` load; rely on tail stdout for any fingerprint-valid cached digest only.
- On **resume@4b / missing tail stdout**, re-read fingerprint-valid digest from disk before Gate C; **never** duplicate digest on normal same-turn path where tail already printed it.
- **Orchestrator-owned long-running wait**: when debate may be required, background the **whole Step 4 tail fence** (`run_in_background: true`, `timeout: 900000`); `dialectic-gatec` runs as foreground Python inside the tail. Do not assign Bash-tool immediate-background to the shell wrapper.
- Keep debate **cheap and inert by default**.
  - No fingerprint-valid candidates means no debate and no output.
  - Detection is self-declaration from the drafter (plus optional inline-fallback write after postplan), not a separate classifier pass.
  - Debate runs only for 1-2 fingerprint-valid candidates with **one three-judge panel** on a shared ballot.
  - `--skip-approve` suppresses auto debate launches entirely.
- Use **Claude subprocesses** through existing launcher infrastructure in **new process groups** with an explicit clarifier time budget, **parent-only generation-token late-write guard**, and mandatory group terminate/kill on fail-open so inner `claude` children cannot leak after Gate C continues.
- Keep dialectic **advisory**.
  - It never rewrites `plan.txt`.
  - Approve publishes the current plan; panel lean is recommendation only.
  - **Discuss further** owns plan revision when the operator disagrees.
  - CHOSEN follows `drafter_pick`; Option A/B labels stay neutral in digest text.
  - Untrusted digest text uses per-line prefixing plus fence-delimiter escaping so model output cannot break the advisory boundary.
- Defer `dialectic-clarifier.md` load only when `skip_approve_requested=false` and fingerprint-valid contested artifacts exist.
- Consolidate Gate C mechanical emit in **`design-step3b-tail.sh`**; retire `design-step4b-preview.sh` references.
- Gate C manual debate uses **`--request-file`** pointing at **`dialectic-manual-request.txt` only** at the orchestrator callsite to avoid shell metacharacter injection.

## Edge cases

- **No fork detected**: no candidate file, no reference load, no Gate C digest, no added cost beyond a cheap fingerprint check.
- **Over-eager drafter**: candidate validator enforces two concrete options, material tradeoff text, valid `drafter_pick`, and cap 2.
- **Postplan rewrites plan before promotion**: candidates not written until postplan success; promotion fingerprints final bytes; fork still valid for final plan or dropped at validation.
- **Drafter subprocess boundary**: without `.dialectic-raw-pending.json`, parent postplan promotion has no dialectic payload; sidecar is mandatory on valid parse.
- **Plan changes after promotion**: `dialectic-clear-stale` at settle/postplan/`_run_dedup` choke points drops auto candidates, cached auto digest, raw pending, and manual request text unless fingerprint-valid manual debate artifacts remain; `dialectic-gatec` no-ops unless fingerprint-valid candidates or manual debate is re-requested.
- **Dedup after apply**: clear-stale runs only at `_run_dedup` rc=0, not immediately after `revise-waterfall` when dedup will still rewrite `plan.txt`.
- **`plan_changed` early dedup-only path**: `_run_apply` lines 1771-1773 still triggers clear-stale via `_run_dedup` success hook.
- **`--skip-approve`**: no auto debate subprocesses, no deferred clarifier reference load; optional fingerprint-valid cached digest print only; preview and auto-approve proceed.
- **resume@4b / missing stdout**: digest file read before Gate C; normal same-turn uses tail stdout only (no duplicate emit).
- **Manual request is vague**: return a short instruction asking for `decision: option A vs option B` or `debate <candidate-id>`, then re-fire Gate C.
- **Manual `debate <id>` with stale fingerprint**: reject with shape help; no debate; operator must rewrite plan and re-declare or use explicit A vs B text.
- **Claude unavailable or fails / budget exceeded**: bump generation, terminate tracked process groups, print warning, append `execution-issues.md`, continue Gate C; parent status/digest writers ignore stale generation.
- **Malformed optional dialectic JSON in drafter output**: valid plan kept; no candidate file; diagnostics only.
- **Stale candidates file on disk**: deferred-load guard and `dialectic-gatec` no-op; no `dialectic-clarifier.md` load overhead.
- **Lone manual request after Discuss further**: request file cleared on rewrite; deferred load stays false until a new fingerprint-valid manual debate completes.
- **Long debate at Gate C**: orchestrator backgrounds whole tail with 900s+ timeout; preview inside tail runs only after `dialectic-gatec` returns.

## Failure modes

1. **Dialectic spam**
   - Warning signal: many ordinary implementation choices appear as Gate C debates.
   - Mitigation: strict validator plus cap 2; require two named options and a real tradeoff.

2. **Hidden decider regression**
   - Warning signal: `plan.txt` changes based on dialectic output before operator approval.
   - Mitigation: dialectic runner writes digest artifacts only; Gate C **Discuss further** owns any plan revision; Approve semantics explicitly keep current plan.

3. **Cost creep**
   - Warning signal: no-fork or skip-approve runs launch Claude subprocesses or load the clarifier reference.
   - Mitigation: no-op-first `dialectic-gatec`; fingerprint stale no-op; skip-approve gates both auto debate and deferred reference load; one three-judge panel per debate round; clarifier wall-clock budget with fail-open and process-group kill; tests assert no launches on absent/stale candidates and on skip-approve.

4. **Stale fork debate**
   - Warning signal: digest discusses options the current plan already resolved.
   - Mitigation: plan fingerprint on candidates and digest status; clear-stale at all rewrite choke points including `_run_dedup`; promotion only after postplan; manual id lookup requires fingerprint match.

5. **Orphan subprocess corruption**
   - Warning signal: digest/status changes after Gate C continued or during cleanup; claude processes survive past budget.
   - Mitigation: process-group terminate/kill on budget exceed; generation increment on start and kill; parent-only `write_if_generation_matches`; tests assert post-timeout immutability and inner-child reap.

6. **Shell injection via Gate C Other**
   - Warning signal: operator quotes/metacharacters break the manual debate fence.
   - Mitigation: Write-tool request file + `--request-file` only at Gate C; `--request` reserved for tests/internal callers.

7. **Advisory boundary escape**
   - Warning signal: debater/judge text closes the Markdown fence or injects control rows into orchestrator context.
   - Mitigation: per-line prefix on all untrusted digest fields; escape fence delimiters and whole-line control tokens.

8. **Context bloat from duplicate digest**
   - Warning signal: Gate C context contains digest twice on first pass.
   - Mitigation: file re-read only on resume/missing-stdout paths; same-turn tail stdout authoritative.

9. **Premature candidate loss**
   - Warning signal: fork detected but Gate C never surfaces debate after validator auto-fix.
   - Mitigation: defer promotion until `POSTPLAN_RC=0`; mandatory `.dialectic-raw-pending.json` sidecar; test postplan mutation + promotion fingerprint.

10. **Tail tool timeout during debate**
    - Warning signal: Gate C proceeds without digest mid-debate.
    - Mitigation: orchestrator backgrounds whole tail with `timeout: 900000`; `.completed/step-4` sentinel; preview runs only after `dialectic-gatec` returns inside tail.

11. **Foreground tail blocks orchestrator on contested fork**
    - Warning signal: default Bash timeout kills debate before digest.
    - Mitigation: `SKILL.md` Step 4 debate-path uses `run_in_background: true` on whole tail; register `.completed/step-4` in `design-background-wait.md`.

## Testing strategy

- Run `make py-test`.
- Run `make py-lint`.
- Run `make lint`.
- Add targeted tests listed above.
- If `scripts/test-design-structure.sh` changes, run its Makefile target or the script directly per repo convention.
- Manually inspect one generated Step 2b drafter prompt in a temp fixture if tests do not already snapshot the relevant excerpt.

## Acceptance

- The Step 2b drafter emits an optional `LARCH_DIALECTIC_BEGIN` / `LARCH_DIALECTIC_END` JSON block after `LARCH_PLAN_END` and before `LARCH_SCOUT_BEGIN`. `parse_drafter_output()` parses and caps it (at most 2 decisions) but does **not** write `dialectic-clarifier-candidates.json`; a valid parse writes `$DESIGN_TMPDIR/.dialectic-raw-pending.json` before the launcher subprocess exits. Missing or malformed dialectic JSON keeps the plan valid and is non-fatal. Dialectic sentinels inside the summary or plan envelope are fatal.
- Candidates are promoted to `dialectic-clarifier-candidates.json` (with `plan_fingerprint` = sha256 of final `plan.txt` bytes) only after terminal Step 2b postplan success (`POSTPLAN_RC=0`), via `dialectic-promote-candidates`. The common `NO_CONTESTED_DECISIONS` run writes no candidate file.
- `dialectic-clear-stale` fires at all three choke points (`design-step35-settle.sh` after dedup/postplan succeed, `python/plan_review.py` at `_run_dedup` rc 0, and `python/design_postplan.py` on postplan hash change). A `plan.txt` rewrite drops stale auto candidates, cached digest, raw-pending, and manual request unless fingerprint-valid manual artifacts remain.
- `dialectic-gatec` runs as a foreground Python subprocess inside `design-step3b-tail.sh` only when `skip_approve_requested=false` and fingerprint-valid candidates exist. It is a no-op (no output, exit 0) when there are no candidates, the fingerprint is stale, or `--skip-approve` is set; it prints a cached digest when the fingerprint matches; it writes `.completed/dialectic-gatec-terminal` on every exit path.
- Debate uses `agent launch-claude-subprocess` in new process groups (`start_new_session=True`) under a 300-600s clarifier budget, with one three-judge panel on a single multi-decision ballot reusing `dialectic-protocol.md` (binary THESIS/ANTI_THESIS thresholds, position rotation, attribution stripping, disposition enum). Budget exceed or launch failure terminates and kills tracked process groups and bumps the monotonic generation; parent status/digest writers no-op on stale generation. Dialectic never blocks Gate C approval.
- The digest is advisory and display-only: it never rewrites `plan.txt`, every untrusted steelman/rationale line is prefixed and fence-delimiter-escaped, and Approve publishes the current plan (panel lean is recommendation only; Discuss further owns plan revision).
- Gate C `Other` debate requests write `$DESIGN_TMPDIR/dialectic-manual-request.txt` via the Write tool and call `dialectic-manual --request-file`, then re-fire the same Gate C prompt; `--request <string>` is reserved for tests and internal callers. The on-demand affordance is visible in the Gate C prompt text.
- Stale dialectic references are reconciled: `dialectic-protocol.md` is reframed to the clarifier flow with its reusable core preserved; `SECURITY.md` documents the new trust boundary and drops the stale Step 2a.5 debater note; `design-step4b-preview.sh` references are retired in favor of `design-step3b-tail.sh`; `dialectic-resolutions.md` stays an empty legacy placeholder; the Step 2a sentinel invariant (`NO_SKETCHES`, `NO_CONTESTED_DECISIONS`, empty `dialectic-resolutions.md`) is preserved.
- `python/design_dialectic.py` is new, stdlib-only, and uses frozen dataclasses for candidate/option/debate-output/judge-vote/digest-row/status. New `cli.py` verbs (`design dialectic-gatec`, `dialectic-manual`, `dialectic-write-candidates`, `dialectic-promote-candidates`, `dialectic-validate-candidates`, `dialectic-clear-stale`) are registered.
- Tests cover the contract: new `python/test_design_dialectic.py` plus extended `python/test_agents.py` and `python/test_design_lifecycle.py` assert no-candidate no-op, fingerprint-mismatch clear, cap enforcement, cached-digest reuse, `--skip-approve` suppression, the parent-only generation guard and process-group kill, advisory framing, CHOSEN-from-`drafter_pick` mapping, the single shared ballot launching exactly three judges, and promotion keyed on post-postplan `plan.txt` bytes. `make py-test`, `make py-lint`, and `make lint` pass.

review_status: complete
rounds_completed: 5
diff_lines: 1900
