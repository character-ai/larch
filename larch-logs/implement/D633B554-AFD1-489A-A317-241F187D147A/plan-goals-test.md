## Goal
Implement issue #7197: [IMPLEMENTING] [FEATURE] /issue dedup and dep reasoning via a read-only verdict subagent.

## Implementation Plan
#### Summary

/issue runs two LLM reasoning passes inside the invoking agent's context: Phase 1 Tier-1 title triage (walks up to 500 open titles) and Phase 2 semantic reasoning over the fetched candidates corpus, which is untrusted GitHub content (a routine 18-candidate fetch measured 91KB on 2026-07-12). Move both passes into a read-only verdict subagent (new `agents/issue-dedup.md`). The invoking agent keeps every deterministic step and validates all subagent output through the existing pipeline.

#### Current state (verified 2026-07-12 by executing the skill)

- `skills/issue/SKILL.md` Steps 4-5: `issue list-issues` snapshot (TSV) feeds Tier-1 in-prompt triage; CAND rows feed the deterministic `issue allocate-candidates`; `issue fetch-issue-details --output candidates.md` builds the corpus; Phase 2 in-prompt reasoning over `<external_issues_corpus>` and `<new_item_i>` blocks emits verdicts and dep edges; a deterministic validation pipeline (snapshot membership, intra-batch range, DUPLICATE override, SCC cycle resolution) gates everything before `issue create-one` and `issue add-blocked-by`.
- Consumers: operator /issue (single and batch), /implement Step 9a.1 OOS filing, /bug, /research findings filing, /learn-from-bugs --file.
- The corpus is wrapped as untrusted data per `SECURITY.md` "Untrusted GitHub Issue Content"; today it is nonetheless ingested by an agent holding full session tools.

#### Proposed design

1. New agent definition `agents/issue-dedup.md`: tools `Read`, `Grep`, `Glob` only; no `model` pin. The body carries the data-not-instructions framing and the exact CAND-row and verdict/edge output grammars currently embedded in the SKILL steps.
2. Call 1 (Tier-1): inputs are paths only: snapshot TSV, new-item body files, plus flag context (`no_dep_llm`, `blocked_by_issue`). Output: CAND rows in the existing grammar. The orchestrator then runs the allocator and the fetch exactly as today.
3. Call 2 (Phase 2): continue the same subagent via `SendMessage` with the corpus path; output: verdict lines plus optional dep-edge lines in the existing grammar. When `SendMessage` is unavailable, fresh-spawn call 2 with snapshot, corpus, and body paths together.
4. Validation is unchanged and stays with the invoking agent: every subagent-emitted verdict and edge passes the existing Step 5 pipeline; invalid output degrades exactly as today (fail-open to CREATE with stderr warnings). No new trust is placed in the subagent.
5. Security: the untrusted corpus is ingested by a tool-restricted read-only subagent instead of the full-tool invoking agent, shrinking the prompt-injection blast radius. Update the residual-risk framing in `SECURITY.md`.
6. One shared implementation in the SKILL steps; no per-consumer forks.

#### Keep unchanged

- All Python helpers: `list-issues`, `allocate-candidates`, `fetch-issue-details`, `create-one`, `add-blocked-by`, `cleanup-failed`, `write-sentinel`.
- The validation pipeline, fail-open posture, counters and sentinel grammar, OOS template assembly, and the `--no-dedup` / `--no-dep-llm` / `--blocked-by-issue` flag semantics.

#### Acceptance criteria

1. Batch and single /issue runs produce identical verdict semantics through the subagent on a scripted fixture corpus (golden comparison).
2. A prompt-injection fixture inside the corpus cannot cause tool actions: the subagent has no Bash, Edit, or Write, and its output passes the validation pipeline or is dropped.
3. SendMessage and fresh-spawn paths are pinned by structure tests.
4. `SECURITY.md`, `docs/agents.md`, and the SKILL are updated; `make lint` green.

#### Non-goals

- Changing dedup or dep-edge detection quality thresholds or grammars.
- /combine-issues and /deps.

#### Priority and dependencies

Blocked by #7193 (native edge; operator ordering). #7192 and #7193 are top priority and land first; this issue reuses their SendMessage gating pattern.

## Test plan
(no test plan section in plan-file)
