# Round 1 — Scope boundaries & hard constraints (issue #6797)

Step 1c/1d short-circuited: issue is fully specified (complete policy matrix,
explicit OOS section, per-item file:line anchors). No open scope-decision
branches. The items below are scope/constraints carried from the issue text and
verified codebase anchors, NOT answers to operator questions.

## Decision 1: Scope is the full 12-item model-policy refresh, landed atomically
- **Question**: What is in scope?
- **Resolution**: All 12 work items (config constants, `resolve_model_args`
  role-path `default_model`, panel composition, voters, three fixer waterfalls,
  rate table, mini-split set, cost-line labels, plugin.json text, docs, tests,
  verification). Land as one change — the pricing couplings (below) make
  splitting unsafe.
- **Source**: issue / codebase

## Decision 2: Out of scope (do NOT touch composition of these)
- **Question**: What is explicitly out of scope?
- **Resolution**: `design.plan_review_panel`, `design.decompose_panel`,
  `design.plan_voters` keep their composition (Codex slots only inherit the new
  role defaults). `implement.lint_fix_coder` and
  `implement.rebase_conflict_fixer` keep order/models except where shared role
  defaults move them. No Cursor model changes beyond the named `auto` pins. No
  effort-tier changes (stays `high`). No third pricing display bucket. Keep the
  design-side tier-to-role machinery (`DIFFICULTY_CODEX_MODEL_ROLES`, remaining
  `DIFFICULTY_CODEX_MODEL_ROLE_OVERRIDES` entries) for the OOS surfaces.
- **Source**: issue

## Decision 3: Hard constraint — three pricing couplings must land together
- **Question**: What must not break when constants change?
- **Resolution**:
  (1) `rate_row()` resolves the codex vendor-default via
  `DEFAULT_VENDOR_MODEL["codex"] = CODEX_DEFAULT_MODEL`; the new
  `("codex","gpt-5.6-sol")` rate row MUST exist or every cost report raises
  `KeyError`.
  (2) `CODEX_MINI_MODEL = CODEX_REVIEW_MODEL_DEFAULT`; flipping the review
  default to `gpt-5.6-luna` requires the `CODEX_MINI_MODELS` membership set so
  historical `gpt-5.4-mini` rows stay in the mini bucket.
  (3) Claude by-model accounting exact-matches `CLAUDE_SONNET_4_6_MODEL`;
  `claude-sonnet-4-6[1m]` must be normalized (strip `[1m]`) at record time so
  ledger rows keep matching `rate_row` and `CLAUDE_SUB_MODEL_FLAG_PREFIXES`.
- **Source**: issue (Pricing coupling 1-3) / codebase

## Decision 4: Hard constraint — byte-stable wire names
- **Question**: Which identifiers must stay byte-stable?
- **Resolution**: Keep KV key `CODEX_GPT_5_4_MINI_COST`, kwarg
  `codex_gpt_5_4_mini_cost`, `--codex-*` / `--codex-mini-*` flags,
  `LARCH_CODEX_MINI_*` env names, and the `Codex-mini` label unchanged. Only the
  human display label `Codex-5.5` -> `Codex-5.6` changes. Env precedence
  (`LARCH_CODEX_MODEL`, `LARCH_CODEX_REVIEW_MODEL`, `LARCH_CODEX_VOTE_MODEL`,
  `LARCH_CODEX_FIX_MODEL`, `codex_model` plugin option) must keep beating
  `default_model`.
- **Source**: issue (work items 8, 2, Rollback)

## Decision 5: Carried assumption — external model facts unverifiable at design time
- **Question**: How are the new model ids/prices treated during design?
- **Resolution**: GPT-5.6 (`sol`/`terra`/`luna`) ids and prices and
  `claude-sonnet-4-6[1m]` postdate the assistant's training cutoff and are taken
  from the issue as source-of-truth. The plan wires the strings through; WI-12
  live probes (`codex exec -m <model>`, `claude --model 'claude-sonnet-4-6[1m]'
  -p ping`, `/report-tokens analyze` KeyError check) are the authoritative
  gate at /implement time, and existing launch-failure waterfalls cover a bad id.
- **Source**: issue (work item 12) / assistant honesty note

Decisions resolved: 5 (all from issue/codebase; 0 operator questions required).
