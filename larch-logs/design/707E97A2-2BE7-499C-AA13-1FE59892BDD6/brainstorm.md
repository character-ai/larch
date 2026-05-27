## Brainstorm Synthesis

### Issue-anchored workflow checkpoint
**Source:** cursor-brainstorm
Pause is a named **checkpoint on the feature issue** — the same anchor that already holds `larch:plan` and clarify threads. Pausing is the operator saying "stop here on purpose"; the issue records *where* the workflow was so a later `/design <N>` re-enters without treating the run as finished. The temp directory is optional acceleration; GitHub is the durable checkpoint tape.

### Cross-machine serialization protocol
**Source:** cursor-brainstorm
A wire format alongside the existing plan-block family: a redacted, machine-readable snapshot of orchestration state posted to the issue so any clone/machine/session can deserialize intent. `/design` stays stateless in the prompt; **state lives in the protocol**, not in Claude's context window or `$DESIGN_TMPDIR`. Esc/Ctrl-C is encode trigger; plain `/design <N>` is decode trigger.

### Cooperative hibernate (not crash recovery)
**Source:** cursor-brainstorm
Pause behaves like **hibernate**: the operator freezes the run at an arbitrary step (mid-sketch, mid-panel, mid-gate) and expects the same logical process to wake later. It is explicitly **not** SIGSTOP on a live subprocess tree or automatic crash-recovery. Ownership sits with the user: only intentional interrupt + explicit pause intent creates a resumable marker.

### GitHub issue as system of record
**Source:** cursor-brainstorm
The tracking issue is treated as a **small database row** for design-in-progress: title/status (`[DESIGNING]`), body markers (`larch:design-pause` alongside `larch:plan`), and comments as auxiliary facts. `$DESIGN_TMPDIR` is a cache that may be rebuilt or discarded; the issue row is authoritative. Concurrent human edits are a known conflict class — warn but the pause marker wins.

### Shared "workflow suspend" primitive for larch
**Source:** cursor-brainstorm | codex-brainstorm
A reusable suspend primitive under `scripts/`, born in `/design` but shaped so `/implement` and `/review` can adopt the same grammar later. The helper API surface (named block read/write, redaction, manifesting, artifact packing, restore primitives) is generic; only `/design` is wired in this issue. Costs: upfront abstraction before a second adopter exists.

### Explicit abandonment boundary for partial work
**Source:** cursor-brainstorm
The frame emphasizes what pause **does not save**: in-flight Cursor/Codex/sketch launches are torn down and discarded, so resume never tries to graft stale partial transcripts onto a fresh panel. Pause captures **decisions and artifacts already landed**, not the live fleet of agents. Mid-sketch pause means "we know we were in Step 2a slot 3"; it does not mean "reattach to agent job X."

### Lean pause snapshot only (minimal scope)
**Source:** codex-brainstorm
Persist a pause record only when user explicitly interrupts and says "pause": run identity, current phase/step, run params, issue metadata, redacted bundle of only artifacts needed to resume at nearest safe boundary. Tradeoff: smaller persistence surface vs imprecise "pause anywhere" — mid-step work may be replayed or discarded. Excludes streaming every artifact write and reuse by `/implement` / `/review`.

### Checkpointed anywhere resume
**Source:** codex-brainstorm
Pause available anywhere, but resume lands at last completed **checkpoint** rather than the exact interrupted instruction. `/design` refreshes issue-backed checkpoints at major step boundaries and on explicit pause; in-flight externals abandoned. Practical reliability while honoring pause-from-anywhere intent, at the cost of repeating expensive reviewer/sketch work after interruption.

### Issue body + comment artifact bundle
**Source:** codex-brainstorm
Compact resume marker in the issue body; larger redacted artifacts spilled into one or more structured issue **comments**. Body marker remains the auto-detect entrypoint; comments carry versioned artifact manifests and chunked content when the 65 KB body limit risks overflow. Tradeoff: full GitHub-native cross-session restore without branches/gists, at the cost of comment-discovery / chunking / stale-comment machinery.

### Log-branch backed restore
**Source:** codex-brainstorm | claude-brainstorm
Body is the authoritative resume **pointer**; redacted tempdir snapshot lives under the existing `larch-logs/design/<RUN_ID>/` publishing path. Resume reconstructs `$DESIGN_TMPDIR` from the committed artifact bundle, then lets `design-driver.sh --resume-from` (or equivalent) continue. Tradeoff: room for large artifacts and reuses existing log-publish, but couples pause to git-worktree mechanics — "state lives in issue" is only true by pointer.

### Strict full-fidelity restore (ambitious scope)
**Source:** codex-brainstorm
Persist enough state to rebuild `$DESIGN_TMPDIR` and resume with minimal re-derivation across unbounded cycles: artifact manifests, run-params, token ledger, review outputs, synthesis files, explicit invalidation rules for abandoned externals. Strongest UX, least repeated work; costs the most in schema design, storage, validation, migration, edge cases. Still excludes byte-for-byte live shell/process restore.

### Re-derive expensive artifacts; persist only user-decided state
**Source:** claude-brainstorm
Pause persists only: `run-params.json`, `feature-description.txt`, `discussion-round1.md`, `brainstorm.md` (when complete), `accepted-plan-findings.md`, `discussion-round2.md`, current `plan.txt`, and operator Gate A/B/C choices. Everything else (sketches, dialectic, reviewer panel) re-derived on resume. Body marker holds base64-gzipped tar of the "decision" files (kilobytes, not megabytes). Risk: $5-20 per resume in re-launched reviewers; mitigate by surfacing cost prominently in the resume confirmation.

### Pause at Bash-tool boundary; mid-Bash is best-effort kill
**Source:** claude-brainstorm
Pause request recorded in `$DESIGN_TMPDIR/.pause-requested` sentinel. After **every** Bash tool call returns (and at top of each step), orchestrator checks the sentinel; if present, snapshot runs and run exits. Mid-Bash pause is handled by Claude Code's native Esc semantics: harness kills in-flight Bash, orchestrator never writes snapshot, on resume the missing snapshot triggers re-entry from last completed step. Worst case: one step of lost work.

### Two-marker protocol: pause-marker + state-blob
**Source:** claude-brainstorm
Issue body holds two named blocks: `<!-- larch:design-pause -->` (small pointer with step name, session id, edit-content hash) and `<!-- larch:design-state -->` (base64-gzipped opaque tar of artifacts, passed through `redact-secrets.sh` before zipping). Mirror of `plan-block-write.sh` pattern. Single helper `scripts/design-pause-save.sh` + `scripts/design-pause-load.sh`. Risk: large artifact set won't fit 65 KB body; error out at pause with "too big" or spill to comments.

### "Kill the run; mark state" — no in-flight nuance
**Source:** claude-brainstorm
Esc → user types "pause" → orchestrator immediately writes pause marker and exits cleanly. No attempt to drain in-flight Bash or externals; they die when Claude exits. Resume re-launches from last completed step boundary. Zero coordination logic. Risk: partial-step work loss; mitigate by writing step outputs ATOMICALLY (tmp + rename) so resume re-runs any incomplete step.

### Pause is a Skill, not a flag (`/larch:pause`)
**Source:** claude-brainstorm
User-facing pause is a dedicated tiny skill `/larch:pause` that operates on the running session via the env file (`~/.cache/larch/sessions/current-design-env-$PPID.sh` already gives a stable handle). The skill writes the pause marker and exits. `/design` on the next turn detects the marker and unwinds cleanly. Zero coupling to `/design` argv; same skill works for `/implement` and `/review` later (Decision 4 generalization). Risk: requires user to know about the slash command.

---

## Proposed Solution (lean composite — operator-selected direction)

**Goal**: save the majority of work already done; some rework is OK; simplicity + minimum-change is the priority.

**Composition**: Issue-anchored pointer marker (cursor #1, #4) + log-branch backed bulk store (codex #4, claude A) + Bash-boundary sentinel (claude C) + abandonment of in-flight externals (cursor #6, claude E) + `/larch:pause` skill as user trigger (claude F). Generic save/restore helper exposed under `scripts/` (cursor #5, codex #5). Re-derivation cost is accepted because Decision 5 already abandons in-flight externals; the lean composite only re-runs the step that was interrupted, not all prior steps.

### Persistence boundary

Save the substantive artifacts already on disk (sketches, plan.txt, reviewer outputs, voting tally, gates already passed) into a **single committed snapshot** under `larch-logs/design/<RUN_ID>/` via the **already-existing** `design-log-publish.sh`. The issue body gets a tiny `larch:design-pause` pointer block. No new storage layer; no body-size pressure; no comment-chunking machinery.

### What pause writes (issue body marker)

A new `<!-- larch:design-pause -->` block (sibling of `larch:plan`) containing only:

```
STEP=<step-id>                  # e.g. "1d", "2a", "2b", "3.5", "4b"
SESSION_ID=<orig>               # original SESSION_ID at pause time
RUN_ID=<orig>                   # branch path for snapshot
TIER=<simple|hard|trivial>      # so resume re-reads run-params from snapshot consistently
BRAINSTORM_DONE=<true|false>    # so brainstorm doesn't re-run on resume
BODY_HASH=<sha256>              # for warn-but-continue concurrent-edit check
PAUSED_AT=<ISO-8601>            # for human readability and TTL decisions later
```

Total marker size: < 300 bytes. The block follows the same `<!-- larch:design-pause -->` / `<!-- /larch:design-pause -->` grammar as `larch:plan` so the same parser helpers (`plan-block-write.sh` pattern) generalize.

### What pause does NOT write to the issue

- Sketch outputs, reviewer outputs, voting tally, contested-decisions.md, dialectic-resolutions.md — these live in the log-branch snapshot, not in the issue.
- Token ledger, execution-issues.md — log-branch only.
- In-flight launcher state — discarded entirely.

### Trigger mechanism (simplest path)

1. User hits Esc → Claude turn interrupts.
2. User invokes `/larch:pause` (a tiny new skill, ~30 lines).
3. That skill writes `$DESIGN_TMPDIR/.pause-requested` (when found via `current-design-env-$PPID.sh`) AND a flag in `~/.cache/larch/sessions/pause-requested-<ISSUE>.flag`. The skill exits without waiting.
4. On the next `/design` invocation (could be same session, could be next day on a different machine), `/design`'s Step 0 reads the cache flag (if `$DESIGN_TMPDIR` is gone, the cache flag is the breadcrumb).
5. The `/design` SKILL.md adds a **single new "between-Bash-boundary check"**: after each Bash call returns, if `.pause-requested` exists, run `design-pause-save.sh` and exit cleanly. The "anywhere" requirement collapses to "anywhere a step boundary fires", which honors Decision 3 in practice (mid-step interrupts via Esc lose only the in-flight step's work, consistent with Decision 5).

### What resume does

1. `/design <N>` fetches the issue body, parses `larch:design-pause`.
2. If absent: fresh run (current behavior, unchanged).
3. If present:
   - `BODY_HASH` mismatch → warn but continue (Decision 8).
   - Fetch `larch-logs/design/<RUN_ID>/` via `git fetch` + `git show`-style restore (or a new `design-pause-load.sh`).
   - Restore `$DESIGN_TMPDIR` from the snapshot (a fresh session prefix; existing `session-setup.sh` handles allocation).
   - Set `BRAINSTORM_DONE`/tier from the marker; re-write `run-params.json` from the snapshot.
   - Use `design-driver.sh --resume-from STEP` (extended to cover all major steps, not just the EMIT_PLAN/VALIDATE/TALLY/FINALIZE actions today) to skip to the named step.
   - Remove the `larch:design-pause` block from the issue body atomically before continuing (so failed-resume can't leave a stale marker that interferes with the next pause attempt).

### Shared helper surface (Decision 4 future-proofing)

Two new committed scripts:

- `scripts/design-pause-save.sh` — given `--design-tmpdir`, `--issue N`, runs `design-log-publish.sh` for the bulk snapshot, computes the marker, calls a new generic `scripts/named-block-write.sh` to install the body block, exits.
- `scripts/design-pause-load.sh` — given `--issue N`, parses marker, fetches log-branch, restores tmpdir, writes the source-env, prints `STEP=` for `/design` to consume.

Both are thin compositions of `plan-block-write.sh`, `design-log-publish.sh`, `redact-secrets.sh`. `/implement` and `/review` can later wire their own `*-pause-save.sh` and `*-pause-load.sh` against the same `named-block-write.sh` + log-branch pattern.

### Approximate change footprint

- **New scripts** (4): `scripts/design-pause-save.sh`, `scripts/design-pause-load.sh`, `scripts/named-block-write.sh` (extraction of `plan-block-write.sh` block-edit logic), `skills/pause/SKILL.md` (the `/larch:pause` skill — ~30 lines).
- **Modified scripts** (2): `scripts/design-log-publish.sh` (accept `--reason pause` to use distinct commit message), `skills/design/scripts/design-driver.sh` (extend `--resume-from` to recognize step IDs like `1c`, `1d`, `2a`, `2b`, `3`, `3.5`, `3b`, `4`, `4b`).
- **SKILL.md edits** (1): add a "pause-check" sentence after every Bash block prelude in `skills/design/SKILL.md` directing the orchestrator to check `.pause-requested` and unwind.
- **Step 0 resume detection** (1): add a step early in Step 0b that reads `larch:design-pause` and branches into the resume path.
- **Tests** (1 harness): `skills/design/scripts/test-design-pause-roundtrip.sh` — save → load → verify identical artifacts.

### What we explicitly do NOT build

- No comment-based chunked artifact storage (codex #3).
- No streaming-per-artifact-write persistence (codex #6 partial).
- No live external-reviewer reattach (cursor #3, codex #6 partial).
- No `/implement` or `/review` adopter code (Decision 4 — later).
- No TTL / paused-state expiry (default: pause lives until resumed or manually cleared).
- No automatic crash recovery (Decision 2 — user-initiated only).
