## Decision 1: Scope — fix both /design and /implement
- **Question**: Should the fix restore the per-round review table + Gantt in /design only (body scope) or both /design and /implement (title scope)?
- **Resolution**: Both. Splice `render-review-phase-detail.sh` output into BOTH `python/design_summary.py` (the `/design` final summary) and `python/pr_body.py` (the `/implement` final report). Both renderers are confirmed regressed; `/implement`'s harness `skills/implement/scripts/test-write-final-report.sh` (CI shard `test-harnesses-19`) is currently RED asserting `## Review Phase Detail` + `### Round 1 reviewer timing`, so the fix must turn it green.
- **Source**: user

## Decision 2: Placement — chat + public comment, redacted
- **Question**: Where should the spliced per-round detail appear?
- **Resolution**: In the final-summary body so it shows BOTH in chat AND in the upserted public issue/run-summary comment, with outbound redaction applied to the spliced content before the public upsert. Restores pre-#3681 parity (the old `render-final-summary.sh` spliced into `final-summary.md`, which feeds both chat and the comment).
- **Source**: user

## Decision 3: Gantt data availability (codebase, not user)
- **Question**: Does the /design plan-review loop produce the `type=round` / `type=vendor` timing-ledger rows the Gantt needs, or would the fix have to add new timing writes?
- **Resolution**: Design already writes `DESIGN_TMPDIR/timing-ledger.tsv` (read live by `progress_report.py::_render_design_review_detail`) and `python/plan_review.py` emits vendor/round timing rows; design review rounds live under `DESIGN_TMPDIR/plan-review/round-N/round-meta.json`. So the splice can reuse the existing data and degrade gracefully (table from round-meta; Gantt only when timing rows exist). No new timing-ledger writes are in scope.
- **Source**: codebase

## Decision 4: Reuse the live-report rendering path (codebase, not user)
- **Question**: Build new rendering logic or reuse what the live `p` report already does?
- **Resolution**: Mirror the live-report helpers. Design: rounds-root `DESIGN_TMPDIR/plan-review`, skill `design`, timing `DESIGN_TMPDIR/timing-ledger.tsv`, token ledger latest `larch-tokens-*.jsonl` (see `progress_report.py::_render_design_review_detail` / `_call_render_phase_detail_script` / `_latest_token_ledger`). Implement: rounds-root via `_review_rounds_root(implement_tmpdir, run_id)`, skill `implement`, same timing/token ledgers (see `_render_review_detail`). `--findings-file review-findings-full.jsonl` is optional (Top-reviewers sub-section only); compose/point it where available, degrade gracefully when absent.
- **Source**: codebase

## Hard constraints
- Renderer `scripts/render-review-phase-detail.sh` and the live `p` report (`progress_report.py:404`) must keep working unchanged; this is consumption-only restoration.
- Best-effort/observability-only: a renderer failure or missing inputs must NEVER break the final summary/report (renderer already exits 0 on missing inputs; the splice must swallow failures).
- Reconcile `scripts/render-review-phase-detail.md` (its contract already claims `design render-final-summary` feeds the renderer).
- Outbound redaction required on the public comment surface for the spliced content.
